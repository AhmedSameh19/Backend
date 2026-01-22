from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.leads.expa_lead_realizations import ExpaLeadRealization


def upsert_expa_realizations(db: Session, rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0

    stmt = insert(ExpaLeadRealization.__table__).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={
            "full_name": stmt.excluded.full_name,
            "email": stmt.excluded.email,
            "created_at": stmt.excluded.created_at,
            "contact_number": stmt.excluded.contact_number,
            "home_lc_id": stmt.excluded.home_lc_id,
            "host_lc_name": stmt.excluded.host_lc_name,
            "host_mc_name": stmt.excluded.host_mc_name,
            "programme": stmt.excluded.programme,
            "opp_title": stmt.excluded.opp_title,
            "status": stmt.excluded.status,
            "slot_start_date": stmt.excluded.slot_start_date,
            "slot_end_date": stmt.excluded.slot_end_date,
            "updated_at": stmt.excluded.updated_at,
        },
    )

    result = db.execute(stmt)
    return result.rowcount or 0
