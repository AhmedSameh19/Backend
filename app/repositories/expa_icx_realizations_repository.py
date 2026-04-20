from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.icx.expa_icx_realizations import ExpaICXRealization


def upsert_icx_realizations(db: Session, rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0

    stmt = insert(ExpaICXRealization.__table__).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[ExpaICXRealization.application_id],
        set_={
            "expa_person_id": stmt.excluded.expa_person_id,
            "full_name": stmt.excluded.full_name,
            "email": stmt.excluded.email,
            "created_at": stmt.excluded.created_at,
            "contact_number": stmt.excluded.contact_number,
            "home_lc_id": stmt.excluded.home_lc_id,
            "home_lc_name": stmt.excluded.home_lc_name,
            "home_mc_id": stmt.excluded.home_mc_id,
            "home_mc_name": stmt.excluded.home_mc_name,
            "host_lc_id": stmt.excluded.host_lc_id,
            "host_lc_name": stmt.excluded.host_lc_name,
            "programme": stmt.excluded.programme,
            "opp_title": stmt.excluded.opp_title,
            "opp_id": stmt.excluded.opp_id,
            "status": stmt.excluded.status,
            "slot_start_date": stmt.excluded.slot_start_date,
            "slot_end_date": stmt.excluded.slot_end_date,
            "date_approved": stmt.excluded.date_approved,
            "date_realized": stmt.excluded.date_realized,
            "experience_end_date": stmt.excluded.experience_end_date,
            "assigned_member_id": ExpaICXRealization.assigned_member_id,
            "assigned_member_name": ExpaICXRealization.assigned_member_name,
            "last_synced_at": stmt.excluded.last_synced_at,
            "updated_at": stmt.excluded.updated_at,
        },
    )

    result = db.execute(stmt)
    return result.rowcount or 0

def sync_icx_realizations_for_lc(db: Session, rows: List[Dict[str, Any]], host_lc_id: str) -> Dict[str, int]:
    """Full sync for ICX realizations of an LC: adds/updates current realizations and DELETES those no longer in the list."""
    if not rows:
        # If no realizations returned for this LC, delete all existing for this host LC
        delete_stmt = ExpaICXRealization.__table__.delete().where(ExpaICXRealization.host_lc_id == host_lc_id)
        res = db.execute(delete_stmt)
        return {"upserted": 0, "deleted": res.rowcount or 0}

    # Identify realizations to keep
    new_application_ids = {str(r["application_id"]) for r in rows if r.get("application_id")}

    # Delete realizations in this host LC who are NOT in the new batch
    delete_stmt = (
        ExpaICXRealization.__table__.delete()
        .where(ExpaICXRealization.host_lc_id == host_lc_id)
        .where(ExpaICXRealization.application_id.notin_(list(new_application_ids)))
    )
    delete_res = db.execute(delete_stmt)
    deleted_count = delete_res.rowcount or 0

    # Upsert the current batch
    upserted_count = upsert_icx_realizations(db, rows)

    return {"upserted": upserted_count, "deleted": deleted_count}
