"""Market research API: Podio items, LC filters, visits, IGV/B2B flows, assignments."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import get_db
from app.models.market_research.igv import IGVMarketResearch
from app.models.market_research.b2b_market_research import B2BMarketResearch
from app.models.market_research.podio_scheduled_visit import PodioScheduledVisit
from app.models.market_research.snapshot import MarketResearchSnapshot
from app.services.podio_client import PodioClient
from app.services.market_research_snapshot_service import (
    get_sync_status_payload,
    list_snapshot_items,
    to_market_research_item,
    upsert_snapshot_items,
)
from app.workers.celery_app import celery
from app.models.members import Member
from app.schemas.market_research import (
    MarketResearchItem,
    MarketResearchListResponse,
    IGVMarketResearchSubmit,
    B2BMarketResearchSubmit,
    MarketResearchSubmitResponse,
    CompanyAssignRequest,
    IGVMarketResearchCreate,
    B2BMarketResearchCreate,
    IGVMarketResearchOut,
    B2BMarketResearchOut,
    MarketResearchStatusUpdate,
    ScheduledVisitOut,
    PodioScheduledVisitCreate,
)
from app.utils.pagination import PaginatedResponse, PaginationParams, build_pagination_response

router = APIRouter()


def get_podio_client() -> PodioClient:
    """Create and return Podio client instance"""
    if not settings.PODIO_CLIENT_ID or not settings.PODIO_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Podio credentials not configured. Please set PODIO_CLIENT_ID, PODIO_CLIENT_SECRET, PODIO_APP_ID, and PODIO_APP_TOKEN environment variables.",
        )
    if not settings.PODIO_APP_ID or not settings.PODIO_APP_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Podio app credentials not configured. Please set PODIO_APP_ID and PODIO_APP_TOKEN environment variables. Make sure the app_token matches the app_id.",
        )
    return PodioClient(
        client_id=settings.PODIO_CLIENT_ID,
        client_secret=settings.PODIO_CLIENT_SECRET,
        app_id=settings.PODIO_APP_ID,
        app_token=settings.PODIO_APP_TOKEN,
    )


def get_optional_podio_client() -> Optional[PodioClient]:
    """Return Podio client when configured, otherwise None to allow snapshot-only reads."""
    if not settings.PODIO_CLIENT_ID or not settings.PODIO_CLIENT_SECRET:
        return None
    if not settings.PODIO_APP_ID or not settings.PODIO_APP_TOKEN:
        return None
    return PodioClient(
        client_id=settings.PODIO_CLIENT_ID,
        client_secret=settings.PODIO_CLIENT_SECRET,
        app_id=settings.PODIO_APP_ID,
        app_token=settings.PODIO_APP_TOKEN,
    )


def _set_snapshot_headers(response: Response, db: Session) -> None:
    status_payload = get_sync_status_payload(db, settings.PODIO_MR_SYNC_INTERVAL_MINUTES)
    response.headers["X-MR-Snapshot-Stale"] = str(bool(status_payload.get("is_stale"))).lower()
    last_success_at = status_payload.get("last_success_at")
    if last_success_at:
        response.headers["X-MR-Snapshot-Last-Success"] = str(last_success_at)


def _dict_to_display_text(d: dict) -> Optional[str]:
    """Extract user-facing text from a Podio category/dict value. Never return raw dict string."""
    if not isinstance(d, dict):
        return None
    if "text" in d and d.get("text"):
        return str(d["text"])
    if "name" in d and d.get("name"):
        return str(d["name"])
    inner = d.get("value")
    if isinstance(inner, dict):
        return _dict_to_display_text(inner)
    if inner is not None:
        return str(inner)
    return None


def _field_value_to_str(field: dict) -> Optional[str]:
    """Convert Podio field's first value to string. Handles category (text), link (embed.url), etc."""
    values = field.get("values", [])
    if not values:
        return None
    value = values[0]
    if isinstance(value, dict):
        display = _dict_to_display_text(value)
        if display:
            return display
        # Podio link/embed type: embed has resolved_url, url, or original_url
        embed = value.get("embed") or value.get("link")
        if isinstance(embed, dict):
            url = embed.get("resolved_url") or embed.get("url") or embed.get("original_url")
            if url:
                return str(url)
        if "url" in value:
            return str(value.get("url"))
        return None  # avoid returning raw dict string
    return str(value) if value is not None else None


def extract_field_value(item: dict, field_external_id: str) -> Optional[str]:
    """Extract value from Podio item field by external ID"""
    if not isinstance(item, dict):
        return None
    for field in item.get("fields", []):
        if field.get("external_id") == field_external_id:
            v = _field_value_to_str(field)
            if v and str(v).strip():
                return v
    return None


def _field_value_to_id(field: dict) -> Optional[int]:
    """Extract Podio category option id from field's first value. Category values are like {"value": 123, "text": "..."}."""
    values = field.get("values", [])
    if not values:
        return None
    value = values[0]
    if isinstance(value, dict):
        raw = value.get("value")
        opt_id = None
        if isinstance(raw, dict):
            opt_id = raw.get("id") or raw.get("value")
        else:
            opt_id = raw
        if opt_id is None:
            opt_id = value.get("id")
        if opt_id is not None:
            return int(opt_id) if isinstance(opt_id, (int, float)) else None
        return None
    if isinstance(value, (int, float)):
        return int(value)
    return None


def extract_field_value_id(item: dict, field_external_id: str) -> Optional[int]:
    """Extract category option id from Podio item field by external ID."""
    if not isinstance(item, dict):
        return None
    for field in item.get("fields", []):
        if field.get("external_id") == field_external_id:
            opt_id = _field_value_to_id(field)
            if opt_id is not None:
                return opt_id
    return None


def get_field_id_by_keyword(item: dict, *keywords: str) -> Optional[int]:
    """Find first Podio field by keyword and return its category option id."""
    if not isinstance(item, dict):
        return None
    keywords_norm = [k.lower().replace("-", "_").replace(" ", "_") for k in keywords]
    for field in item.get("fields", []):
        eid = (field.get("external_id") or "")
        eid_norm = eid.lower().replace("-", "_").replace(" ", "_")
        if any(kw in eid_norm or kw in eid.lower() for kw in keywords_norm):
            opt_id = _field_value_to_id(field)
            if opt_id is not None:
                return opt_id
    return None


def _first_id(*candidates: Optional[int]) -> Optional[int]:
    """Return the first non-None int."""
    for c in candidates:
        if c is not None:
            return c
    return None


def get_field_by_keyword(item: dict, *keywords: str) -> Optional[str]:
    """
    Find first Podio field whose external_id (normalized) contains any of the keywords.
    Use when exact external_id is unknown. E.g. get_field_by_keyword(item, "industry", "sector").
    """
    if not isinstance(item, dict):
        return None
    keywords_norm = [k.lower().replace("-", "_").replace(" ", "_") for k in keywords]
    for field in item.get("fields", []):
        eid = (field.get("external_id") or "")
        eid_norm = eid.lower().replace("-", "_").replace(" ", "_")
        if any(kw in eid_norm or kw in eid.lower() for kw in keywords_norm):
            v = _field_value_to_str(field)
            if v and str(v).strip():
                return v
    return None


def _first(*candidates: Optional[str]) -> Optional[str]:
    """Return the first non-empty value or None."""
    for c in candidates:
        if c and str(c).strip():
            return c
    return None


def map_podio_item_to_market_research(item: dict) -> MarketResearchItem:
    """Map Podio item to MarketResearchItem schema.
    Tries explicit external IDs first, then keyword match on field external_id.
    """
    item_id = item.get("item_id") or item.get("app_item_id")
    return MarketResearchItem(
        company_name=_first(
            extract_field_value(item, "company-name"),
            extract_field_value(item, "company_name"),
            get_field_by_keyword(item, "company-name", "company_name", "companyname"),
        ),
        product=_first(
            extract_field_value(item, "product"),
            extract_field_value(item, "PRODUCT"),
            get_field_by_keyword(item, "product"),
        ),
        sub_project_igv=_first(
            extract_field_value(item, "sub-project-igv"),
            extract_field_value(item, "sub_project"),
            extract_field_value(item, "igv"),
            get_field_by_keyword(item, "sub_project", "igv", "sub-project"),
        ),
        local_committee=_first(
            extract_field_value(item, "status"),  # your app uses "status" for LC (e.g. 6th October University)
            extract_field_value(item, "local-committee"),
            extract_field_value(item, "local_committee"),
            extract_field_value(item, "lc"),
            get_field_by_keyword(item, "local", "committee", "lc"),
        ),
        local_committee_id=_first_id(
            extract_field_value_id(item, "status"),
            extract_field_value_id(item, "local-committee"),
            extract_field_value_id(item, "local_committee"),
            extract_field_value_id(item, "lc"),
            get_field_id_by_keyword(item, "local", "committee", "lc"),
        ),
        type_of_pr_deal=_first(
            extract_field_value(item, "type-of-pr-deal"),
            extract_field_value(item, "type_of_pr_deal"),
            extract_field_value(item, "pr_deal_type"),
            get_field_by_keyword(item, "type", "pr", "deal"),
        ),
        reason_of_approach=_first(
            extract_field_value(item, "reason-of-approach"),
            extract_field_value(item, "reason_of_approach"),
            get_field_by_keyword(item, "reason", "approach"),
        ),
        item_id=item_id,
        industry=_first(
            extract_field_value(item, "industry"),
            extract_field_value(item, "company-industry"),
            extract_field_value(item, "company_industry"),
            get_field_by_keyword(item, "industry", "sector"),
        ),
        size=_first(
            extract_field_value(item, "size"),
            extract_field_value(item, "company-size"),
            extract_field_value(item, "company_size"),
            extract_field_value(item, "employee-size"),
            get_field_by_keyword(item, "size", "employee", "company-size"),
        ),
        address=_first(
            extract_field_value(item, "address"),
            extract_field_value(item, "company-address"),
            extract_field_value(item, "location"),
            get_field_by_keyword(item, "address", "location", "company-address"),
        ),
        website=_first(
            extract_field_value(item, "link"),  # your app: link field (embed url)
            extract_field_value(item, "website"),
            extract_field_value(item, "company-website"),
            extract_field_value(item, "url"),
            get_field_by_keyword(item, "website", "url", "web", "link"),
        ),
        contact_person_name=_first(
            extract_field_value(item, "contact-at-company"),  # your app
            extract_field_value(item, "account-manager-name"),  # your app
            extract_field_value(item, "contact-person"),
            extract_field_value(item, "contact_person"),
            extract_field_value(item, "contact name"),
            extract_field_value(item, "person-name"),
            get_field_by_keyword(item, "contact", "person", "name", "contact-person"),
        ),
        contact_position=_first(
            extract_field_value(item, "position"),
            extract_field_value(item, "contact-position"),
            extract_field_value(item, "contact_position"),
            get_field_by_keyword(item, "position", "title", "job"),
        ),
        contact_email=_first(
            extract_field_value(item, "email"),  # your app
            extract_field_value(item, "account-mnagaer-email"),  # your app (Podio typo)
            extract_field_value(item, "contact-email"),
            extract_field_value(item, "contact_email"),
            get_field_by_keyword(item, "email", "mail"),
        ),
        contact_phone=_first(
            extract_field_value(item, "companys-responsible-contact"),  # your app
            extract_field_value(item, "phone"),
            extract_field_value(item, "contact-phone"),
            extract_field_value(item, "contact_phone"),
            extract_field_value(item, "telephone"),
            get_field_by_keyword(item, "phone", "tel", "mobile", "number", "responsible", "contact"),
        ),
        contact_linkedin=_first(
            extract_field_value(item, "linkedin"),
            extract_field_value(item, "contact-linkedin"),
            extract_field_value(item, "linkedin-url"),
            get_field_by_keyword(item, "linkedin", "linked-in"),
        ),
    )


@router.get("/podio-fields", tags=["market-research"])
async def get_podio_field_ids(
    podio_client: PodioClient = Depends(get_podio_client),
):
    """
    Return external_id and sample value for each field in the first Podio item.
    Use this to see your app's field IDs and add them to the mapping if needed.
    """
    try:
        items = podio_client.get_app_items(limit=1, offset=0)
        if not items or not isinstance(items[0], dict):
            return {"message": "No items in Podio app", "fields": []}
        item = items[0]
        fields_out = []
        for field in item.get("fields", []):
            eid = field.get("external_id")
            fid = field.get("field_id")
            val = _field_value_to_str(field)
            val_id = _field_value_to_id(field)
            fields_out.append({
                "field_id": fid,
                "external_id": eid,
                "sample_value": val,
                "sample_value_id": val_id,
            })
        return {"message": "Field IDs from first item. For LC filter: set PODIO_MARKET_RESEARCH_LC_FIELD_ID to field_id of Local Committee; set PODIO_LC_OPTION_IDS to {\"<lc_id>\": [<sample_value_id>, ...]} for each LC.", "fields": fields_out}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not fetch Podio fields: {str(e)}",
        )


@router.get("/podio-form-url", tags=["market-research"])
def get_podio_form_url():
    """Return the Podio webform URL so the frontend can open it in the browser (e.g. redirect button)."""
    return {"url": settings.PODIO_WEBFORM_URL}


@router.get("/podio-lc-options", tags=["market-research"])
async def get_podio_lc_options(
    field_id: Optional[int] = Query(None, description="Podio field_id of the LC/status category field"),
    external_id: Optional[str] = Query("status", description="Podio external_id of the LC field (e.g. status)"),
    podio_client: PodioClient = Depends(get_podio_client),
):
    """
    Return all options of the Podio LC (status) category field and a suggested PODIO_LC_OPTION_IDS
    mapping for all entity LCs. Use this to configure filtering for all 19 LCs at once.

    Either set field_id (from podio-fields) or use external_id (default "status"). 
    Response includes options (id, text) and suggested_podio_lc_option_ids: map of lc_id -> [option_id].
    """
    try:
        field_ref = field_id if field_id is not None else (external_id or "status")
        field_config = podio_client.get_app_field(field_ref)
        fid = field_config.get("field_id")
        eid = field_config.get("external_id")
        field_type = field_config.get("type", "")
        config = field_config.get("config") or {}
        podio_settings = config.get("settings") or {}
        options_raw = podio_settings.get("options") if isinstance(podio_settings, dict) else []
        options = []
        for opt in options_raw or []:
            if not isinstance(opt, dict):
                continue
            if opt.get("status") == "deleted":
                continue
            options.append({
                "id": opt.get("id"),
                "text": (opt.get("text") or "").strip(),
                "status": opt.get("status"),
            })

        # Build suggested mapping: lc_id -> [option_id] by matching option text to EXPA_LC_NAMES
        suggested: Dict[str, List[int]] = {}
        lc_names = getattr(settings, "EXPA_LC_NAMES", None) or {}
        for opt in options:
            opt_id = opt.get("id")
            text = (opt.get("text") or "").strip()
            if not text or opt_id is None:
                continue
            text_lower = text.lower()
            for lc_id_key, lc_name in (lc_names or {}).items():
                if not isinstance(lc_name, str):
                    continue
                name_lower = lc_name.strip().lower()
                if text_lower == name_lower:
                    key = str(lc_id_key)
                    if key not in suggested:
                        suggested[key] = []
                    if opt_id not in suggested[key]:
                        suggested[key].append(int(opt_id))
                # Allow "Alex" -> Alexandria
                if name_lower == "alexandria" and text_lower == "alex":
                    key = "899"
                    if key not in suggested:
                        suggested[key] = []
                    if opt_id not in suggested[key]:
                        suggested[key].append(int(opt_id))

        return {
            "field_id": fid,
            "external_id": eid,
            "type": field_type,
            "options": options,
            "suggested_podio_lc_option_ids": suggested,
            "message": "Set PODIO_MARKET_RESEARCH_LC_FIELD_ID to field_id above. Set PODIO_LC_OPTION_IDS to the suggested_podio_lc_option_ids JSON (copy as one line for .env).",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not fetch Podio LC options: {str(e)}",
        )


@router.get("/scheduled-visits", response_model=List[ScheduledVisitOut], tags=["market-research"])
def get_scheduled_visits(
    db: Session = Depends(get_db),
):
    """
    List IGV, B2B, and Podio scheduled visits (for calendar display and Google sync).
    """
    out: List[ScheduledVisitOut] = []
    igv_rows = db.execute(
        select(IGVMarketResearch).where(IGVMarketResearch.visit_date.isnot(None))
    ).scalars().all()
    for row in igv_rows:
        out.append(ScheduledVisitOut(id=row.id, company_name=row.company_name, visit_date=row.visit_date, source="igv"))
    b2b_rows = db.execute(
        select(B2BMarketResearch).where(B2BMarketResearch.visit_date.isnot(None))
    ).scalars().all()
    for row in b2b_rows:
        out.append(ScheduledVisitOut(id=row.id, company_name=row.company_name, visit_date=row.visit_date, source="b2b"))
    podio_rows = db.execute(select(PodioScheduledVisit)).scalars().all()
    for row in podio_rows:
        out.append(ScheduledVisitOut(id=row.id, company_name=row.company_name, visit_date=row.visit_date, source="podio"))
    return out


@router.get("/scheduled-visits/podio/{podio_item_id}", tags=["market-research"])
def get_podio_scheduled_visit(
    podio_item_id: int,
    db: Session = Depends(get_db),
):
    """Get scheduled visit date for a Podio item (for company card)."""
    row = db.execute(
        select(PodioScheduledVisit).where(PodioScheduledVisit.podio_item_id == podio_item_id)
    ).scalars().first()
    if not row:
        return {"visit_date": None}
    return {"visit_date": row.visit_date.isoformat(), "id": row.id}


@router.post("/scheduled-visits", status_code=status.HTTP_201_CREATED, tags=["market-research"])
def create_or_update_podio_scheduled_visit(
    payload: PodioScheduledVisitCreate,
    db: Session = Depends(get_db),
):
    """Create or update a scheduled visit for a Podio market research item. Used by company card date picker."""
    existing = db.execute(
        select(PodioScheduledVisit).where(PodioScheduledVisit.podio_item_id == payload.podio_item_id)
    ).scalars().first()
    try:
        if existing:
            existing.company_name = payload.company_name
            existing.visit_date = payload.visit_date
            existing.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(existing)
            return {"id": existing.id, "visit_date": existing.visit_date.isoformat(), "updated": True}
        else:
            row = PodioScheduledVisit(
                podio_item_id=payload.podio_item_id,
                company_name=payload.company_name,
                visit_date=payload.visit_date,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return {"id": row.id, "visit_date": row.visit_date.isoformat(), "updated": False}
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database error: " + str(e),
        )


@router.get("", response_model=PaginatedResponse[Any], tags=["market-research"])
async def get_market_research(
    response: Response,
    lc_id: Optional[int] = Query(None, description="Filter by LC id (EXPA/LC_CODES id); only items for this LC are returned"),
    params: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    podio_client: Optional[PodioClient] = Depends(get_optional_podio_client),
):
    """
    Fetch market research data from Podio.
    When lc_id is provided, only items whose local committee matches that LC are returned.
    If PODIO_MARKET_RESEARCH_LC_FIELD_ID and PODIO_LC_OPTION_IDS are set, uses Podio filter API (fast).
    Otherwise fetches a page and filters in memory (fallback).
    """
    try:
        option_ids: Optional[List[int]] = None
        if lc_id is not None and settings.PODIO_LC_OPTION_IDS:
            option_ids = settings.PODIO_LC_OPTION_IDS.get(str(lc_id)) or settings.PODIO_LC_OPTION_IDS.get(str(int(lc_id)))

        if response is not None:
            _set_snapshot_headers(response, db)
        snapshot_items, snapshot_total = list_snapshot_items(db, params.page, params.limit, lc_id, option_ids)
        if snapshot_total > 0:
            return build_pagination_response(
                list(snapshot_items),
                snapshot_total,
                params.page,
                params.limit,
            )

        if podio_client is None or (lc_id is not None and not option_ids):
            return build_pagination_response([], 0, params.page, params.limit)

        use_podio_filter = (
            lc_id is not None
            and getattr(settings, "PODIO_MARKET_RESEARCH_LC_FIELD_ID", None) is not None
            and getattr(settings, "PODIO_LC_OPTION_IDS", None) is not None
        )
        if use_podio_filter and not option_ids:
            use_podio_filter = False

        if use_podio_filter and settings.PODIO_MARKET_RESEARCH_LC_FIELD_ID is not None and option_ids:
            filter_key = str(settings.PODIO_MARKET_RESEARCH_LC_FIELD_ID)
            items = podio_client.get_app_items_filtered(filters={filter_key: option_ids}, limit=params.limit, offset=params.skip)
            mapped_items = [map_podio_item_to_market_research(item) for item in items if isinstance(item, dict)]
        else:
            items = podio_client.get_app_items(limit=params.limit, offset=params.skip)
            mapped_items = [map_podio_item_to_market_research(item) for item in items if isinstance(item, dict)]
            if lc_id is not None and option_ids:
                mapped_items = [m for m in mapped_items if m.local_committee_id in set(option_ids)]

        if mapped_items:
            upsert_snapshot_items(db, mapped_items)
            db.commit()

        simulated_total = params.skip + len(mapped_items) + (1 if len(mapped_items) == params.limit else 0)
        return build_pagination_response(
            list(mapped_items),
            simulated_total,
            params.page,
            params.limit
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except requests.exceptions.RequestException as e:
        error_detail = f"Error fetching data from Podio: {str(e)}"
        if hasattr(e, "response") and e.response is not None:
            try:
                error_data = e.response.json()
                error_detail = error_data.get("error_description", error_data.get("error", error_detail))
            except Exception:
                error_detail = e.response.text or error_detail
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=error_detail,
        )


def _rewrite_html_urls(html: str, base_url: str) -> str:
    """Rewrite relative URLs in HTML to absolute URLs for the given base."""
    base = base_url.rstrip("/")
    # Rewrite href="/path" and src="/path" (but not // or http)
    def replace(m: re.Match) -> str:
        attr, val = m.group(1), m.group(2)
        if val.startswith("//") or val.startswith("http") or val.startswith("mailto:") or val.startswith("#"):
            return m.group(0)
        if val.startswith("/"):
            return f'{attr}="{base}{val}"'
        return m.group(0)
    html = re.sub(r'(href|src|action)=["\']([^"\']+)["\']', replace, html)
    return html


@router.get("/podio-form-proxy", response_class=HTMLResponse, tags=["market-research"])
def get_podio_form_proxy():
    """
    Proxy the Podio webform to bypass X-Frame-Options for iframe embedding.
    Fetches the form from Podio and returns it without frame-blocking headers.
    """
    form_url = settings.PODIO_WEBFORM_URL
    try:
        resp = requests.get(
            form_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
            timeout=30,
        )
        resp.raise_for_status()
        html = resp.text
        base = "https://podio.com"
        html = _rewrite_html_urls(html, base)
        # Allow embedding in iframe from our frontend origins (no X-Frame-Options; use CSP)
        return HTMLResponse(
            content=html,
            headers={
                "Content-Security-Policy": f"frame-ancestors 'self' http://localhost:3000 http://localhost:5173 https://localhost:3000 https://localhost:5173 {settings.FRONTEND_URL}",
            },
        )
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch Podio form: {str(e)}",
        )


@router.patch("/companies/{item_id}/assign", status_code=status.HTTP_200_OK, tags=["market-research"])
def assign_company_to_member(
    item_id: int,
    payload: CompanyAssignRequest,
    db: Session = Depends(get_db),
):
    """
    Assign a market research company to a member (local only; no Podio update).
    Member is resolved from the EXPA-backed members table. Assignment is persisted
    in the frontend (e.g. localStorage).
    """
    member = (
        db.execute(select(Member).where(Member.expa_person_id == payload.member_id))
        .scalars()
        .first()
    )
    if not member:
        member = db.get(Member, payload.member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return {
        "ok": True,
        "assigned_to": {"member_id": payload.member_id, "member_name": member.full_name},
    }


def build_podio_fields(data: Dict[str, Any], field_mapping: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Build Podio field format from data dictionary
    
    Args:
        data: Dictionary with field values
        field_mapping: Mapping from data keys to Podio field external IDs
        
    Returns:
        List of Podio field dictionaries
    """
    fields = []
    for key, external_id in field_mapping.items():
        value = data.get(key)
        if value is not None:
            # Podio expects fields with "values" as an array, not "value"
            fields.append({
                "external_id": external_id,
                "values": [str(value)]  # Podio expects values as an array
            })
    return fields


# Field mappings - Update these with your actual Podio field external IDs
# You can find these in your Podio app settings
# Note: home_lc_id is NOT sent to Podio - it's for our database only
IGV_FIELD_MAPPING = {
    "company_name": "company-name",  # Update with actual external ID
    "product": "product",  # Update with actual external ID
    "sub_project": "sub-project",  # Update with actual external ID
    # home_lc_id is excluded - it's for our database, not Podio
}

B2B_FIELD_MAPPING = {
    "company_name": "company-name",  # Update with actual external ID
    "product": "product",  # Update with actual external ID
    "reason_for_approach": "reason-for-approach",  # Update with actual external ID
    # home_lc_id is excluded - it's for our database, not Podio
}


@router.post("/igv/submit", response_model=MarketResearchSubmitResponse, tags=["market-research"])
async def submit_igv_market_research(
    payload: IGVMarketResearchSubmit,
    podio_client: PodioClient = Depends(get_podio_client),
):
    """
    Submit IGV market research data to Podio
    
    Creates a new item in Podio with the provided IGV market research data.
    """
    try:
        data = payload.model_dump()
        fields = build_podio_fields(data, IGV_FIELD_MAPPING)
        
        result = podio_client.create_item(fields=fields)
        item_id = result.get("item_id")
        
        if not item_id:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Podio did not return an item_id",
            )
        
        return MarketResearchSubmitResponse(
            item_id=item_id,
            success=True,
            message="Successfully submitted IGV market research to Podio",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except requests.exceptions.RequestException as e:
        error_detail = "Error submitting to Podio"
        if hasattr(e, "response") and e.response is not None:
            try:
                error_data = e.response.json()
                error_detail = error_data.get("error_description", error_detail)
            except:
                error_detail = str(e)
        
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=error_detail,
        )


@router.post("/b2b/submit", response_model=MarketResearchSubmitResponse, tags=["market-research"])
async def submit_b2b_market_research(
    payload: B2BMarketResearchSubmit,
    podio_client: PodioClient = Depends(get_podio_client),
):
    """
    Submit B2B market research data to Podio
    
    Creates a new item in Podio with the provided B2B market research data.
    """
    try:
        data = payload.model_dump()
        fields = build_podio_fields(data, B2B_FIELD_MAPPING)
        
        result = podio_client.create_item(fields=fields)
        item_id = result.get("item_id")
        
        if not item_id:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Podio did not return an item_id",
            )
        
        return MarketResearchSubmitResponse(
            item_id=item_id,
            success=True,
            message="Successfully submitted B2B market research to Podio",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except requests.exceptions.RequestException as e:
        error_detail = "Error submitting to Podio"
        if hasattr(e, "response") and e.response is not None:
            try:
                error_data = e.response.json()
                error_detail = error_data.get("error_description", error_detail)
            except:
                error_detail = str(e)
        
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=error_detail,
        )


@router.post("/igv", response_model=IGVMarketResearchOut, status_code=status.HTTP_201_CREATED, tags=["market-research"])
def create_igv_market_research(
    payload: IGVMarketResearchCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new IGV market research record in the database
    
    Saves market research data to the database (not Podio).
    """
    try:
        data = payload.model_dump()
        data["status"] = data["status"].value if hasattr(data.get("status"), "value") else data.get("status", "lead")
        igv_record = IGVMarketResearch(**data)
        db.add(igv_record)
        db.commit()
        db.refresh(igv_record)
        return igv_record
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database error: " + str(e),
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error: " + str(e),
        )


@router.post("/b2b", response_model=B2BMarketResearchOut, status_code=status.HTTP_201_CREATED, tags=["market-research"])
def create_b2b_market_research(
    payload: B2BMarketResearchCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new B2B market research record in the database
    
    Saves market research data to the database (not Podio).
    """
    try:
        data = payload.model_dump()
        data["status"] = data["status"].value if hasattr(data.get("status"), "value") else data.get("status", "lead")
        b2b_record = B2BMarketResearch(**data)
        db.add(b2b_record)
        db.commit()
        db.refresh(b2b_record)
        return b2b_record
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database error: " + str(e),
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error: " + str(e),
        )


@router.patch("/igv/{item_id}", response_model=IGVMarketResearchOut, tags=["market-research"])
def update_igv_market_research_status(
    item_id: int,
    payload: MarketResearchStatusUpdate,
    db: Session = Depends(get_db),
):
    """
    Update IGV market research status and/or visit date (e.g. lead -> contacted -> visited).
    """
    record = db.query(IGVMarketResearch).filter(IGVMarketResearch.id == item_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="IGV market research record not found")
    try:
        if payload.status is not None:
            record.status = payload.status.value
        if payload.visit_date is not None:
            record.visit_date = payload.visit_date
        db.commit()
        db.refresh(record)
        return record
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database error: " + str(e),
        )


@router.patch("/b2b/{item_id}", response_model=B2BMarketResearchOut, tags=["market-research"])
def update_b2b_market_research_status(
    item_id: int,
    payload: MarketResearchStatusUpdate,
    db: Session = Depends(get_db),
):
    """
    Update B2B market research status and/or visit date (e.g. lead -> contacted -> visited).
    """
    record = db.query(B2BMarketResearch).filter(B2BMarketResearch.id == item_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="B2B market research record not found")
    try:
        if payload.status is not None:
            record.status = payload.status.value
        if payload.visit_date is not None:
            record.visit_date = payload.visit_date
        db.commit()
        db.refresh(record)
        return record
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database error: " + str(e),
        )


@router.get("/sync-status", tags=["market-research"])
def get_market_research_sync_status(db: Session = Depends(get_db)):
    return get_sync_status_payload(db, settings.PODIO_MR_SYNC_INTERVAL_MINUTES)


@router.post("/sync-now", tags=["market-research"])
def trigger_market_research_sync(
    mode: str = Query("incremental", pattern="^(incremental|full)$"),
    db: Session = Depends(get_db),
):
    if mode == "full":
        state = get_sync_status_payload(db, settings.PODIO_MR_SYNC_INTERVAL_MINUTES)
        last_run_at = state.get("last_run_at")
        cooldown_minutes = max(1, settings.PODIO_MR_FULL_SYNC_COOLDOWN_MINUTES)
        if last_run_at:
            if isinstance(last_run_at, str):
                try:
                    last_run = datetime.fromisoformat(last_run_at)
                except Exception:
                    last_run = None
            else:
                last_run = last_run_at
            if last_run is not None:
                if last_run.tzinfo is None:
                    last_run = last_run.replace(tzinfo=timezone.utc)
                elapsed = (datetime.now(timezone.utc) - last_run).total_seconds() / 60
                if elapsed < cooldown_minutes:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Full sync is rate-limited. Try again in {int(cooldown_minutes - elapsed) + 1} minutes.",
                    )

    if mode == "full":
        task = celery.send_task("podio.sync_market_research_snapshot_full")
    else:
        task = celery.send_task("podio.sync_market_research_snapshot")
    return {"ok": True, "queued": True, "mode": mode, "task_id": task.id}


@router.get("/{item_id}", response_model=MarketResearchItem, tags=["market-research"])
async def get_market_research_item(
    response: Response,
    item_id: int,
    db: Session = Depends(get_db),
    podio_client: Optional[PodioClient] = Depends(get_optional_podio_client),
):
    """Get a single market research item by Podio item ID. Defined last so static paths (e.g. /podio-lc-options) match first."""
    if response is not None:
        _set_snapshot_headers(response, db)
    cached_row = db.get(MarketResearchSnapshot, item_id)
    if cached_row is not None:
        return to_market_research_item(cached_row)

    if podio_client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found in snapshot")

    try:
        item = podio_client.get_item(item_id)
        mapped = map_podio_item_to_market_research(item)
        upsert_snapshot_items(db, [mapped])
        db.commit()
        return mapped
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if e.response and e.response.status_code == 404 else status.HTTP_502_BAD_GATEWAY,
            detail=f"Error fetching item from Podio: {str(e)}",
        )

