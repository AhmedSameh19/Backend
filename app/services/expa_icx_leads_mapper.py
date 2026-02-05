from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional


def icx_applications_to_rows(
    items: List[Dict[str, Any]],
    *,
    now: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    if not items:
        return []

    now = now or datetime.utcnow()
    rows: List[Dict[str, Any]] = []

    for it in items:
        person = it.get("person") or {}
        contact = person.get("contact_detail") or {}
        home_lc = person.get("home_lc") or {}
        home_mc = person.get("home_mc") or {}
        opportunity_home_mc = it.get("home_mc") or {}

        opportunity = it.get("opportunity") or {}
        programme = (opportunity.get("programme") or {}).get("short_name_display")
        duration_type = (opportunity.get("opportunity_duration_type") or {}).get("duration_type")
        host_lc = opportunity.get("host_lc") or {}

        rows.append(
            {
                "application_id": it["id"],
                "expa_person_id": str(person.get("id") or ""),
                "created_at": _parse_datetime(it.get("created_at")),
                "person_created_at": _parse_datetime(person.get("created_at")),
                "full_name": person.get("full_name") or "",
                "email": person.get("email"),
                "gender": person.get("gender"),
                "phone": contact.get("phone"),
                "home_lc_id": home_lc.get("id"),
                "home_lc_name": home_lc.get("name"),
                "home_mc_id": home_mc.get("id"),
                "home_mc_name": home_mc.get("name"),
                "cv_url": person.get("cv_url"),
                "opportunity_id": opportunity.get("id"),
                "opportunity_title": opportunity.get("title"),
                "programme": programme,
                "opportunity_duration_type": duration_type,
                "host_lc_id": host_lc.get("id"),
                "host_lc_name": host_lc.get("name"),
                "opportunity_host_mc_id": opportunity_home_mc.get("id"),
                "opportunity_host_mc_name": opportunity_home_mc.get("name"),
                "status": it.get("status"),
                "date_approved": _parse_datetime(it.get("date_approved")),
                "date_approval_broken": _parse_datetime(it.get("date_approval_broken")),
                "date_realized": _parse_datetime(it.get("date_realized")),
                "experience_end_date": _parse_datetime(it.get("experience_end_date")),
                "last_synced_at": now,
                "inserted_at": now,
                "updated_at": now,
            }
        )

    return rows


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    v = value.strip()
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(v)
    except ValueError:
        return None



