from __future__ import annotations

from typing import Any, Dict, List, Set

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.members import Member


def _dedupe_and_merge_by_expa_person_id(db: Session, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Prevent unique violations on members.expa_person_id.

    The DB enforces unique expa_person_id, but EXPA can return multiple memberPositions
    for the same person (same expa_person_id with different member_id).

    Strategy:
    - If expa_person_id already exists in DB, rewrite the incoming row's member_id to
      the existing row's member_id so the upsert updates the existing row.
    - Deduplicate rows within the batch by member_id (keep the last occurrence).
    """

    if not rows:
        return rows

    expa_person_id_col = Member.__table__.c.expa_person_id
    member_id_col = Member.__table__.c.member_id

    # 1) Collapse duplicates in the same batch by expa_person_id
    # (otherwise Postgres can throw unique violations within a single INSERT).
    by_expa_person_id: Dict[str, Dict[str, Any]] = {}
    no_expa_person_id: List[Dict[str, Any]] = []
    for r in rows:
        expa_id = r.get("expa_person_id")
        if expa_id in (None, "", "null"):
            no_expa_person_id.append(r)
            continue
        by_expa_person_id[str(expa_id)] = r  # keep last occurrence

    rows = list(by_expa_person_id.values()) + no_expa_person_id

    expa_person_ids: Set[str] = set(by_expa_person_id.keys())

    if expa_person_ids:
        existing = db.execute(
            select(expa_person_id_col, member_id_col).where(expa_person_id_col.in_(list(expa_person_ids)))
        ).all()
        expa_to_member_id: Dict[str, str] = {
            str(expa_id): str(member_id) for expa_id, member_id in existing if expa_id is not None
        }

        if expa_to_member_id:
            for r in rows:
                expa_id = r.get("expa_person_id")
                if expa_id in (None, "", "null"):
                    continue
                expa_id = str(expa_id)
                existing_member_id = expa_to_member_id.get(expa_id)
                if existing_member_id and str(r.get("member_id")) != existing_member_id:
                    r["member_id"] = existing_member_id

    # Deduplicate by member_id to avoid "ON CONFLICT DO UPDATE command cannot affect row a second time"
    # and to ensure we don't try to insert/update the same PK multiple times in one statement.
    deduped_by_member_id: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        mid = r.get("member_id")
        if mid in (None, ""):
            continue
        deduped_by_member_id[str(mid)] = r

    return list(deduped_by_member_id.values())


def _null_invalid_reports_to_member_ids(db: Session, rows: List[Dict[str, Any]]) -> None:
    """Avoid FK violations for the self-referential reports_to_member_id.

    EXPA can return reports_to_position_id values that aren't included in the current
    fetch range (or even in the same LC). If we upsert them as-is, Postgres will
    reject the insert/update due to the self-FK.
    """

    if not rows:
        return

    batch_member_ids: Set[str] = {
        str(r["member_id"]) for r in rows if r.get("member_id") not in (None, "")
    }

    referenced_ids: Set[str] = {
        str(r["reports_to_member_id"])
        for r in rows
        if r.get("reports_to_member_id") not in (None, "", "null")
    }

    if not referenced_ids:
        return

    # Use table columns to avoid triggering ORM mapper configuration
    # (other mappers/relationships may be unresolved at runtime).
    member_id_col = Member.__table__.c.member_id

    existing_ids: Set[str] = set(
        db.execute(select(member_id_col).where(member_id_col.in_(list(referenced_ids))))
        .scalars()
        .all()
    )

    valid_ids = batch_member_ids | existing_ids

    for r in rows:
        v = r.get("reports_to_member_id")
        if v in (None, "", "null"):
            r["reports_to_member_id"] = None
            continue

        v = str(v)
        r["reports_to_member_id"] = v if v in valid_ids else None


def upsert_members(db: Session, rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0

    rows = _dedupe_and_merge_by_expa_person_id(db, rows)

    _null_invalid_reports_to_member_ids(db, rows)

    stmt = insert(Member.__table__).values(rows)
    stmt = stmt.on_conflict_do_update(
        constraint="members_expa_person_id_key",
        set_={
            "full_name": stmt.excluded.full_name,
            "expa_person_id": stmt.excluded.expa_person_id,
            "email": stmt.excluded.email,
            "role": stmt.excluded.role,
            "function": stmt.excluded.function,
            "reports_to_member_id": stmt.excluded.reports_to_member_id,
            "reports_to_person_id": stmt.excluded.reports_to_person_id,
            "home_lc_id": stmt.excluded.home_lc_id,
            "home_mc_id": stmt.excluded.home_mc_id,
            "home_lc_name": stmt.excluded.home_lc_name,
            "home_mc_name": stmt.excluded.home_mc_name,
        },
    )

    result = db.execute(stmt)
    return result.rowcount or 0


def sync_members_for_lc(db: Session, rows: List[Dict[str, Any]], home_lc_id: str) -> Dict[str, int]:
    """Full sync for an LC: adds/updates current members and DELETES those no longer in the list."""
    if not rows:
        # If no members returned for this LC, delete all existing for this LC
        delete_stmt = Member.__table__.delete().where(Member.home_lc_id == home_lc_id)
        res = db.execute(delete_stmt)
        return {"upserted": 0, "deleted": res.rowcount or 0}

    # Identify members to keep
    new_member_ids = {str(r["member_id"]) for r in rows if r.get("member_id")}
    
    # Delete members in this LC who are NOT in the new batch
    delete_stmt = (
        Member.__table__.delete()
        .where(Member.home_lc_id == home_lc_id)
        .where(Member.member_id.notin_(list(new_member_ids)))
    )
    delete_res = db.execute(delete_stmt)
    deleted_count = delete_res.rowcount or 0
    
    # Upsert the current batch
    upserted_count = upsert_members(db, rows)
    
    return {"upserted": upserted_count, "deleted": deleted_count}
