from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.market_research.snapshot import MarketResearchSnapshot, MarketResearchSyncState
from app.schemas.market_research import MarketResearchItem


def to_market_research_item(row: MarketResearchSnapshot) -> MarketResearchItem:
    return MarketResearchItem(
        item_id=row.item_id,
        company_name=row.company_name,
        product=row.product,
        sub_project_igv=row.sub_project_igv,
        local_committee=row.local_committee,
        local_committee_id=row.local_committee_id,
        type_of_pr_deal=row.type_of_pr_deal,
        reason_of_approach=row.reason_of_approach,
        industry=row.industry,
        size=row.size,
        address=row.address,
        website=row.website,
        contact_person_name=row.contact_person_name,
        contact_position=row.contact_position,
        contact_email=row.contact_email,
        contact_phone=row.contact_phone,
        contact_linkedin=row.contact_linkedin,
    )


def upsert_snapshot_items(db: Session, mapped_items: List[MarketResearchItem], prune_missing: bool = False) -> int:
    now = datetime.now(timezone.utc)
    item_ids: List[int] = []
    upserted = 0

    for item in mapped_items:
        if not item.item_id:
            continue
        item_ids.append(item.item_id)
        row = db.get(MarketResearchSnapshot, item.item_id)
        if row is None:
            row = MarketResearchSnapshot(item_id=item.item_id)
            db.add(row)
        row.company_name = item.company_name
        row.product = item.product
        row.sub_project_igv = item.sub_project_igv
        row.local_committee = item.local_committee
        row.local_committee_id = item.local_committee_id
        row.type_of_pr_deal = item.type_of_pr_deal
        row.reason_of_approach = item.reason_of_approach
        row.industry = item.industry
        row.size = item.size
        row.address = item.address
        row.website = item.website
        row.contact_person_name = item.contact_person_name
        row.contact_position = item.contact_position
        row.contact_email = item.contact_email
        row.contact_phone = item.contact_phone
        row.contact_linkedin = item.contact_linkedin
        row.podio_last_seen_at = now
        row.synced_at = now
        upserted += 1

    if prune_missing and item_ids:
        db.execute(
            delete(MarketResearchSnapshot).where(
                MarketResearchSnapshot.podio_last_seen_at < now,
                ~MarketResearchSnapshot.item_id.in_(item_ids),
            )
        )
    return upserted


def get_or_create_sync_state(db: Session) -> MarketResearchSyncState:
    state = db.get(MarketResearchSyncState, 1)
    if state is None:
        state = MarketResearchSyncState(id=1, last_synced_items=0)
        db.add(state)
        db.flush()
    return state


def get_sync_status_payload(db: Session, staleness_target_minutes: int) -> Dict[str, Any]:
    state = db.get(MarketResearchSyncState, 1)
    if state is None:
        return {
            "last_run_at": None,
            "last_success_at": None,
            "last_error": "sync_not_initialized",
            "last_synced_items": 0,
            "is_stale": True,
            "staleness_minutes": None,
            "staleness_target_minutes": staleness_target_minutes,
        }

    staleness_minutes: Optional[float] = None
    is_stale = True
    if state.last_success_at is not None:
        delta = datetime.now(timezone.utc) - state.last_success_at
        staleness_minutes = round(delta.total_seconds() / 60, 2)
        is_stale = staleness_minutes > staleness_target_minutes

    return {
        "last_run_at": state.last_run_at,
        "last_success_at": state.last_success_at,
        "last_error": state.last_error,
        "last_synced_items": state.last_synced_items,
        "is_stale": is_stale,
        "staleness_minutes": staleness_minutes,
        "staleness_target_minutes": staleness_target_minutes,
    }


def list_snapshot_items(
    db: Session,
    page: int,
    limit: int,
    lc_id: Optional[int] = None,
    lc_option_ids: Optional[List[int]] = None,
) -> tuple[list[MarketResearchItem], int]:
    q = select(MarketResearchSnapshot).order_by(MarketResearchSnapshot.item_id.desc())
    count_q = select(func.count()).select_from(MarketResearchSnapshot)
    if lc_id is not None:
        if lc_option_ids:
            q = q.where(MarketResearchSnapshot.local_committee_id.in_(lc_option_ids))
            count_q = count_q.where(MarketResearchSnapshot.local_committee_id.in_(lc_option_ids))
        else:
            return [], 0
    total = int(db.execute(count_q).scalar() or 0)
    rows = db.execute(q.offset((page - 1) * limit).limit(limit)).scalars().all()
    return [to_market_research_item(row) for row in rows], total


def snapshot_max_item_id(db: Session) -> Optional[int]:
    return db.execute(select(func.max(MarketResearchSnapshot.item_id))).scalar()
