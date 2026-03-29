"""
Dashboard endpoint – per-LC aggregated statistics, cached in Redis for 15 mins.

Exposed as:  GET /api/v1/dashboard/?lc_id={lc_id}
"""
from __future__ import annotations

import json
import logging
from typing import Optional

import redis
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db

# ── Models ──────────────────────────────────────────────────────────────────
from app.models.leads.expa_leads import ExpaLead
from app.models.leads.expa_lead_realizations import ExpaLeadRealization
from app.models.leads.expa_lead_followups import ExpaLeadFollowUp
from app.models.icx.expa_icx_leads import ExpaICXLead
from app.models.icx.expa_icx_realizations import ExpaICXRealization
from app.models.icx.expa_icx_lead_followups import ExpaICXLeadFollowUp
from app.models.market_research.igv import IGVMarketResearch
from app.models.market_research.b2b_market_research import B2BMarketResearch

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

# ── Redis client – lazy singleton ────────────────────────────────────────────
_redis_client: Optional[redis.Redis] = None

def _get_redis() -> Optional[redis.Redis]:
    global _redis_client
    if _redis_client is None:
        url = settings.REDIS_URL
        if not url:
            return None
        try:
            _redis_client = redis.from_url(url, decode_responses=True)
            _redis_client.ping()
        except Exception as exc:
            logger.warning("Redis unavailable, caching disabled: %s", exc)
            _redis_client = None
    return _redis_client


CACHE_TTL = 900  # 15 minutes


def _cache_key(lc_id: int) -> str:
    return f"dashboard_stats_v1:{lc_id}"


# ── Helpers ──────────────────────────────────────────────────────────────────
def _count(db: Session, model, *filters) -> int:
    stmt = select(func.count()).select_from(model)
    for f in filters:
        stmt = stmt.where(f)
    return db.execute(stmt).scalar() or 0


def _count_distinct(db: Session, model, col, *filters) -> int:
    stmt = select(func.count(func.distinct(col))).select_from(model)
    for f in filters:
        stmt = stmt.where(f)
    return db.execute(stmt).scalar() or 0


def _status_breakdown(db: Session, model, status_col, *filters) -> dict:
    stmt = (
        select(status_col, func.count().label("cnt"))
        .select_from(model)
    )
    for f in filters:
        stmt = stmt.where(f)
    stmt = stmt.group_by(status_col)
    rows = db.execute(stmt).all()
    return {(r[0] or "unknown"): r[1] for r in rows}


# ── Main endpoint ────────────────────────────────────────────────────────────
@router.get("/")
def get_dashboard_stats(
    lc_id: int = Query(..., description="Home/Host LC ID (pass 1609 for all)"),
    db: Session = Depends(get_db),
):
    """Return cached or freshly-computed dashboard stats for a given LC."""

    # ── Cache read ───────────────────────────────────────────────────────────
    r = _get_redis()
    key = _cache_key(lc_id)
    if r:
        try:
            cached = r.get(key)
            if cached:
                return json.loads(cached)
        except Exception as exc:
            logger.warning("Redis GET failed: %s", exc)

    try:
        all_lc = lc_id == 1609

        # ── OGX Leads ────────────────────────────────────────────────────────
        ogx_filters = [] if all_lc else [ExpaLead.home_lc_id == lc_id]
        ogx_total          = _count(db, ExpaLead, *ogx_filters)
        ogx_status_dist    = _status_breakdown(db, ExpaLead, ExpaLead.expa_status, *ogx_filters)
        ogx_assigned       = _count(db, ExpaLead, ExpaLead.assigned_member_id.isnot(None), *ogx_filters)

        # ── OGX Realizations ─────────────────────────────────────────────────
        rlz_filters = [] if all_lc else [ExpaLeadRealization.home_lc_id == lc_id]
        ogx_rlz_total      = _count(db, ExpaLeadRealization, *rlz_filters)
        ogx_rlz_status     = _status_breakdown(db, ExpaLeadRealization, ExpaLeadRealization.status, *rlz_filters)

        # ── OGX Follow-ups (via join to ExpaLead) ────────────────────────────
        # ExpaLeadFollowUp links to expa_leads via expa_person_id
        if all_lc:
            ogx_fu_total    = _count(db, ExpaLeadFollowUp)
            ogx_fu_pending  = _count(db, ExpaLeadFollowUp, ExpaLeadFollowUp.status == "pending")
            ogx_fu_done     = _count(db, ExpaLeadFollowUp, ExpaLeadFollowUp.status == "completed")
        else:
            # Join follow-ups → leads to filter by LC
            fu_base = (
                select(func.count())
                .select_from(ExpaLeadFollowUp)
                .join(ExpaLead, ExpaLeadFollowUp.expa_person_id == ExpaLead.expa_person_id)
                .where(ExpaLead.home_lc_id == lc_id)
            )
            ogx_fu_total   = db.execute(fu_base).scalar() or 0
            ogx_fu_pending = db.execute(fu_base.where(ExpaLeadFollowUp.status == "pending")).scalar() or 0
            ogx_fu_done    = db.execute(fu_base.where(ExpaLeadFollowUp.status == "completed")).scalar() or 0

        # ── ICX Leads ────────────────────────────────────────────────────────
        icx_filters = [] if all_lc else [ExpaICXLead.host_lc_id == str(lc_id)]
        icx_total          = _count(db, ExpaICXLead, *icx_filters)
        icx_status_dist    = _status_breakdown(db, ExpaICXLead, ExpaICXLead.status, *icx_filters)
        icx_assigned       = _count(db, ExpaICXLead, ExpaICXLead.assigned_member_id.isnot(None), *icx_filters)

        # ── ICX Realizations ─────────────────────────────────────────────────
        icx_rlz_filters = [] if all_lc else [ExpaICXRealization.host_lc_id == str(lc_id)]
        icx_rlz_total      = _count(db, ExpaICXRealization, *icx_rlz_filters)
        icx_rlz_status     = _status_breakdown(db, ExpaICXRealization, ExpaICXRealization.status, *icx_rlz_filters)

        # ── ICX Follow-ups ───────────────────────────────────────────────────
        if all_lc:
            icx_fu_total   = _count(db, ExpaICXLeadFollowUp)
            icx_fu_pending = _count(db, ExpaICXLeadFollowUp, ExpaICXLeadFollowUp.status == "pending")
            icx_fu_done    = _count(db, ExpaICXLeadFollowUp, ExpaICXLeadFollowUp.status == "completed")
        else:
            icx_fu_base = (
                select(func.count())
                .select_from(ExpaICXLeadFollowUp)
                .join(ExpaICXLead, ExpaICXLeadFollowUp.application_id == ExpaICXLead.application_id)
                .where(ExpaICXLead.host_lc_id == str(lc_id))
            )
            icx_fu_total   = db.execute(icx_fu_base).scalar() or 0
            icx_fu_pending = db.execute(icx_fu_base.where(ExpaICXLeadFollowUp.status == "pending")).scalar() or 0
            icx_fu_done    = db.execute(icx_fu_base.where(ExpaICXLeadFollowUp.status == "completed")).scalar() or 0

        # ── Market Research – IGV ────────────────────────────────────────────
        igv_filters = [] if all_lc else [IGVMarketResearch.home_lc_id == lc_id]
        igv_total          = _count(db, IGVMarketResearch, *igv_filters)
        igv_status_dist    = _status_breakdown(db, IGVMarketResearch, IGVMarketResearch.status, *igv_filters)
        igv_visits         = _count(db, IGVMarketResearch, IGVMarketResearch.visit_date.isnot(None), *igv_filters)

        # ── Market Research – B2B ────────────────────────────────────────────
        b2b_filters = [] if all_lc else [B2BMarketResearch.home_lc_id == lc_id]
        b2b_total          = _count(db, B2BMarketResearch, *b2b_filters)
        b2b_status_dist    = _status_breakdown(db, B2BMarketResearch, B2BMarketResearch.status, *b2b_filters)
        b2b_visits         = _count(db, B2BMarketResearch, B2BMarketResearch.visit_date.isnot(None), *b2b_filters)

        # ── Compose response ─────────────────────────────────────────────────
        payload = {
            "lc_id": lc_id,
            "ogx": {
                "leads": {
                    "total": ogx_total,
                    "assigned": ogx_assigned,
                    "unassigned": ogx_total - ogx_assigned,
                    "status_distribution": ogx_status_dist,
                },
                "realizations": {
                    "total": ogx_rlz_total,
                    "status_distribution": ogx_rlz_status,
                },
                "follow_ups": {
                    "total": ogx_fu_total,
                    "pending": ogx_fu_pending,
                    "completed": ogx_fu_done,
                },
            },
            "icx": {
                "leads": {
                    "total": icx_total,
                    "assigned": icx_assigned,
                    "unassigned": icx_total - icx_assigned,
                    "status_distribution": icx_status_dist,
                },
                "realizations": {
                    "total": icx_rlz_total,
                    "status_distribution": icx_rlz_status,
                },
                "follow_ups": {
                    "total": icx_fu_total,
                    "pending": icx_fu_pending,
                    "completed": icx_fu_done,
                },
            },
            "market_research": {
                "igv": {
                    "total": igv_total,
                    "visits_scheduled": igv_visits,
                    "status_distribution": igv_status_dist,
                },
                "b2b": {
                    "total": b2b_total,
                    "visits_scheduled": b2b_visits,
                    "status_distribution": b2b_status_dist,
                },
                "total": igv_total + b2b_total,
                "total_visits": igv_visits + b2b_visits,
            },
        }

        # ── Cache write ──────────────────────────────────────────────────────
        if r:
            try:
                r.set(key, json.dumps(payload), ex=CACHE_TTL)
            except Exception as exc:
                logger.warning("Redis SET failed: %s", exc)

        return payload

    except SQLAlchemyError as exc:
        logger.exception("DB error in get_dashboard_stats(lc_id=%s)", lc_id)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database error") from exc
    except Exception as exc:
        logger.exception("Unexpected error in get_dashboard_stats(lc_id=%s)", lc_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from exc


@router.delete("/cache")
def invalidate_dashboard_cache(
    lc_id: int = Query(..., description="LC ID whose cache should be cleared"),
):
    """Manually invalidate the cached dashboard stats for a given LC (useful after data imports)."""
    r = _get_redis()
    if not r:
        return {"ok": False, "message": "Redis not available"}
    key = _cache_key(lc_id)
    deleted = r.delete(key)
    return {"ok": True, "deleted": deleted, "key": key}
