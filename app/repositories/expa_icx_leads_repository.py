from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.icx.expa_icx_leads import ExpaICXLead


def upsert_expa_icx_leads(db: Session, rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0

    stmt = insert(ExpaICXLead.__table__).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["application_id"],
        set_={
            "expa_person_id": stmt.excluded.expa_person_id,
            "created_at": stmt.excluded.created_at,
            "person_created_at": stmt.excluded.person_created_at,
            "full_name": stmt.excluded.full_name,
            "phone": stmt.excluded.phone,
            "email": stmt.excluded.email,
            "gender": stmt.excluded.gender,
            "home_lc_id": stmt.excluded.home_lc_id,
            "home_lc_name": stmt.excluded.home_lc_name,
            "home_mc_id": stmt.excluded.home_mc_id,
            "home_mc_name": stmt.excluded.home_mc_name,
            "cv_url": stmt.excluded.cv_url,
            "opportunity_id": stmt.excluded.opportunity_id,
            "opportunity_title": stmt.excluded.opportunity_title,
            "programme": stmt.excluded.programme,
            "opportunity_duration_type": stmt.excluded.opportunity_duration_type,
            "host_lc_id": stmt.excluded.host_lc_id,
            "host_lc_name": stmt.excluded.host_lc_name,
            "opportunity_host_mc_id": stmt.excluded.opportunity_host_mc_id,
            "opportunity_host_mc_name": stmt.excluded.opportunity_host_mc_name,
            "status": stmt.excluded.status,
            "date_approved": stmt.excluded.date_approved,
            "date_approval_broken": stmt.excluded.date_approval_broken,
            "date_realized": stmt.excluded.date_realized,
            "experience_end_date": stmt.excluded.experience_end_date,
            "last_synced_at": stmt.excluded.last_synced_at,
            "inserted_at": stmt.excluded.inserted_at,
            "updated_at": stmt.excluded.updated_at,
        },
    )

    result = db.execute(stmt)
    return result.rowcount or 0

def delete_stale_icx_leads(db: Session, fetched_application_ids: List[str], host_mc_id: str) -> int:
    """Removes ICX leads for the given MC that are not in the fetched list."""
    if not fetched_application_ids:
        # If no leads fetched, delete all for this MC
        delete_stmt = ExpaICXLead.__table__.delete().where(ExpaICXLead.opportunity_host_mc_id == host_mc_id)
        res = db.execute(delete_stmt)
        return res.rowcount or 0

    delete_stmt = (
        ExpaICXLead.__table__.delete()
        .where(ExpaICXLead.opportunity_host_mc_id == host_mc_id)
        .where(ExpaICXLead.application_id.notin_(fetched_application_ids))
    )
    res = db.execute(delete_stmt)
    return res.rowcount or 0
