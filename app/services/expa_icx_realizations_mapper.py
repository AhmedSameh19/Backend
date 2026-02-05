from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    v = str(value).strip()
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(v)
    except ValueError:
        return None


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    v = str(value).strip()
    try:
        return date.fromisoformat(v)
    except ValueError:
        return None


def icx_realizations_to_rows(
    realizations: List[Dict[str, Any]],
    *,
    host_lc_id: int,
) -> List[Dict[str, Any]]:
    if not realizations:
        return []

    rows: List[Dict[str, Any]] = []

    for r in realizations:
        application_id = r.get("id")
        person = r.get("person") or {}
        opp = r.get("opportunity") or {}
        slot = r.get("slot") or {}

        person_id = person.get("id")
        opp_id = opp.get("id")

        if not application_id:
            continue

        contact = person.get("contact_detail") or {}
        home_lc = person.get("home_lc") or {}
        home_mc = person.get("home_mc") or {}
        programme = (opp.get("programme") or {})
        host_lc = opp.get("host_lc") or {}

        rows.append(
            {
                "application_id": str(application_id),
                "expa_person_id": str(person_id) if person_id else None,
                "full_name": person.get("full_name"),
                "email": person.get("email"),
                "created_at": _parse_datetime(person.get("created_at")),
                "contact_number": contact.get("phone"),
                "home_lc_id": str(home_lc.get("id")) if home_lc.get("id") is not None else None,
                "home_lc_name": home_lc.get("name"),
                "home_mc_id": str(home_mc.get("id")) if home_mc.get("id") is not None else None,
                "home_mc_name": home_mc.get("name"),
                "host_lc_id": str(host_lc.get("id")) if host_lc.get("id") is not None else str(host_lc_id),
                "host_lc_name": host_lc.get("name"),
                "programme": programme.get("short_name_display"),
                "opp_title": opp.get("title"),
                "opp_id": opp_id if opp_id is not None else None,
                "status": r.get("status"),
                "slot_start_date": _parse_date(slot.get("start_date")),
                "slot_end_date": _parse_date(slot.get("end_date")),
                "date_approved": _parse_datetime(r.get("date_approved")),
                "date_realized": _parse_datetime(r.get("date_realized")),
                "experience_end_date": _parse_datetime(r.get("experience_end_date")),
                "last_synced_at": datetime.now(timezone.utc),
                "updated_at": _parse_datetime(r.get("updated_at"))
                or _parse_datetime(r.get("date_realized"))
                or datetime.now(timezone.utc),
            }
        )

    return rows
