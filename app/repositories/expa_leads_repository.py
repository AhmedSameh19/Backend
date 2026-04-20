from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.leads.expa_leads import ExpaLead


def upsert_expa_leads(db: Session, rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0

    stmt = insert(ExpaLead.__table__).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["expa_person_id"],
        set_={
            "created_at": stmt.excluded.created_at,
            "full_name": stmt.excluded.full_name,
            "email": stmt.excluded.email,
            "phone": stmt.excluded.phone,
            "gender": stmt.excluded.gender,
            "dob": stmt.excluded.dob,
            "expa_status": stmt.excluded.expa_status,
            "academic_backgrounds": stmt.excluded.academic_backgrounds,
            "selected_programmes": stmt.excluded.selected_programmes,
            "home_lc_name": stmt.excluded.home_lc_name,
            "home_mc_name": stmt.excluded.home_mc_name,
            "home_lc_id": stmt.excluded.home_lc_id,
            "home_mc_id": stmt.excluded.home_mc_id,
            "latest_graduation_date": stmt.excluded.latest_graduation_date,
            "opportunity_applications_count": stmt.excluded.opportunity_applications_count,
            "last_synced_at": stmt.excluded.last_synced_at,
            # NOTE: This preserves your current behavior (updates inserted_at on conflict).
            # If you want inserted_at to remain the first insert time, remove this line.
            "inserted_at": stmt.excluded.inserted_at,
            "updated_at": stmt.excluded.updated_at,
        },
    )

    result = db.execute(stmt)
    return result.rowcount or 0


def sync_leads_for_lc(db: Session, rows: List[Dict[str, Any]], home_lc_id: int) -> Dict[str, int]:
    """Full sync for leads of an LC: adds/updates current leads and DELETES those no longer in the list."""
    if not rows:
        # If no leads returned for this LC, delete all existing for this LC
        delete_stmt = ExpaLead.__table__.delete().where(ExpaLead.home_lc_id == home_lc_id)
        res = db.execute(delete_stmt)
        return {"upserted": 0, "deleted": res.rowcount or 0}

    # Identify leads to keep
    new_expa_person_ids = {str(r["expa_person_id"]) for r in rows if r.get("expa_person_id")}

    # Delete leads in this LC who are NOT in the new batch
    delete_stmt = (
        ExpaLead.__table__.delete()
        .where(ExpaLead.home_lc_id == home_lc_id)
        .where(ExpaLead.expa_person_id.notin_(list(new_expa_person_ids)))
    )
    delete_res = db.execute(delete_stmt)
    deleted_count = delete_res.rowcount or 0

    # Upsert the current batch
    upserted_count = upsert_expa_leads(db, rows)

    return {"upserted": upserted_count, "deleted": deleted_count}