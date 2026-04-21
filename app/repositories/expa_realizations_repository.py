from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy import tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.leads.expa_lead_realizations import ExpaLeadRealization


def upsert_expa_realizations(db: Session, rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0

    batch_size = 1000
    total_rowcount = 0

    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        stmt = insert(ExpaLeadRealization.__table__).values(batch)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_expa_lead_realizations_person_opp",
            set_={
                "full_name": stmt.excluded.full_name,
                "email": stmt.excluded.email,
                "created_at": stmt.excluded.created_at,
                "contact_number": stmt.excluded.contact_number,
                "home_lc_id": stmt.excluded.home_lc_id,
                "host_lc_name": stmt.excluded.host_lc_name,
                "host_mc_name": stmt.excluded.host_mc_name,
                "assigned_member_id": stmt.excluded.assigned_member_id,
                "assigned_member_name": stmt.excluded.assigned_member_name,
                "programme": stmt.excluded.programme,
                "opp_title": stmt.excluded.opp_title,
                "status": stmt.excluded.status,
                "slot_start_date": stmt.excluded.slot_start_date,
                "slot_end_date": stmt.excluded.slot_end_date,
                "updated_at": stmt.excluded.updated_at,
            },
        )
        result = db.execute(stmt)
        total_rowcount += result.rowcount or 0

    return total_rowcount

def sync_realizations_for_lc(db: Session, rows: List[Dict[str, Any]], home_lc_id: int) -> Dict[str, int]:
    """Full sync for realizations of an LC: adds/updates current realizations and DELETES those no longer in the list."""
    if not rows:
        # If no realizations returned for this LC, delete all existing for this LC
        delete_stmt = ExpaLeadRealization.__table__.delete().where(ExpaLeadRealization.home_lc_id == home_lc_id)
        res = db.execute(delete_stmt)
        return {"upserted": 0, "deleted": res.rowcount or 0}

    # Identify realizations to keep (composite key: expa_person_id, opp_id)
    # We use a tuple in the notin_ clause if possible, or construct a set of keys.
    # Postgres supports `(col1, col2) NOT IN ((val1, val2), ...)`
    
    # Upsert first to ensure everything is current
    upserted_count = upsert_expa_realizations(db, rows)

    # Delete realizations in this LC who are NOT in the new batch
    # Since SQLAlchemy's notin_ with tuples can be tricky across versions/dialects,
    # and we already have the home_lc_id scope, we can fetch existing and compare, 
    # or use a raw-ish expression.
    
    # Collect new keys
    new_keys = {(str(r["expa_person_id"]), int(r["opp_id"])) for r in rows}

    from sqlalchemy import and_, not_
    
    # A cleaner way: delete where home_lc_id matches and (person_id, opp_id) NOT IN new_keys
    # However, for simplicity and safety with SQLAlchemy 2.0+, we can just use the tuple approach.
    from sqlalchemy import tuple_
    delete_stmt = (
        ExpaLeadRealization.__table__.delete()
        .where(ExpaLeadRealization.home_lc_id == home_lc_id)
        .where(
            not_(
                tuple_(ExpaLeadRealization.expa_person_id, ExpaLeadRealization.opp_id).in_(
                    list(new_keys)
                )
            )
        )
    )
    delete_res = db.execute(delete_stmt)
    deleted_count = delete_res.rowcount or 0

    return {"upserted": upserted_count, "deleted": deleted_count}
