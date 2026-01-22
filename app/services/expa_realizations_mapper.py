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


def realizations_to_rows(realizations: List[Dict[str, Any]],
                         *,
                          home_committee_id: int,
                         ) -> List[Dict[str, Any]]:
    if not realizations:
        return []

    rows: List[Dict[str, Any]] = []

    for r in realizations:
        person = r.get("person") or {}
        opp = r.get("opportunity") or {}
        slot = r.get("slot") or {}

        host_lc = opp.get("host_lc") or {}
        home_mc = opp.get("home_mc") or {}
        programme = opp.get("programme") or {}
        contact = person.get("contact_detail") or {}

        opp_id = opp.get("id")
        person_id = person.get("id")
        if not opp_id or not person_id:
            continue

        rows.append(
            {
                "expa_person_id": str(person_id),
                "full_name": person.get("full_name"),
                "email": person.get("email"),
                "created_at": _parse_datetime(person.get("created_at")),
                "contact_number": contact.get("phone"),
                "home_lc_id": home_committee_id,
                "host_lc_name": host_lc.get("name"),
                "host_mc_name": home_mc.get("name"),
                "programme": programme.get("short_name_display"),
                "opp_title": opp.get("title"),
                "opp_id": int(opp_id),
                "status": r.get("status"),
                "slot_start_date": _parse_date(slot.get("start_date")),
                "slot_end_date": _parse_date(slot.get("end_date")),
                "updated_at": _parse_datetime(r.get("updated_at"))
                or _parse_datetime(r.get("date_approved"))
                or datetime.now(timezone.utc),
            }
        )

    return rows
