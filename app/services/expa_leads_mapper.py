from __future__ import annotations

from datetime import datetime, date, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import null


def safe_date(value: Optional[str]):
    return value or None


def extract_backgrounds(person: Dict[str, Any]) -> List[str]:
    bgs: List[str] = []
    for ae in person.get("academic_experiences") or []:
        for bg in (ae.get("backgrounds") or []):
            name = bg.get("name")
            if name:
                bgs.append(name)

    # dedupe while preserving order
    seen = set()
    out: List[str] = []
    for x in bgs:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def extract_programmes(person: Dict[str, Any]) -> str:
    pp = person.get("person_profile") or {}
    progs = pp.get("selected_programmes") or []

    # Normalize to list
    if isinstance(progs, (str, int)):
        progs_list = [progs]
    elif isinstance(progs, list):
        progs_list = progs
    else:
        progs_list = []

    code_to_name = {
        "7": "GV New",
        "8": "GTa",
        "9": "GTe",
        "1": "GV Old",
        "2": "GT",
        "5": "GE",
    }

    names: List[str] = []
    for p in progs_list:
        name = code_to_name.get(str(p))
        if name:
            names.append(name)

    # Dedupe while preserving order
    seen = set()
    unique: List[str] = []
    for n in names:
        if n not in seen:
            seen.add(n)
            unique.append(n)

    # If you only want the first programme, replace with: return unique[0] if unique else "-"
    return ", ".join(unique) if unique else "-"


def people_to_rows(
    people: List[Dict[str, Any]],
    *,
    home_committee_id: int,
    home_mc_id: int = 1609,
    now: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    if not people:
        return []

    now = now or datetime.utcnow()
    rows: List[Dict[str, Any]] = []

    for p in people:
        rows.append({
            "expa_person_id": p["id"],
            "created_at": _parse_datetime(p.get("created_at")),
            "full_name": p.get("full_name") or "",
            "email": p.get("email"),
            "phone": p.get("phone"),
            "gender": _norm_gender(p.get("gender")),
            "dob": _parse_date(p.get("dob")),
            "expa_status": p.get("status"),
            "academic_backgrounds": extract_backgrounds(p),
            "selected_programmes": extract_programmes(p),
            "home_lc_name": (p.get("home_lc") or {}).get("name"),
            "home_mc_name": (p.get("home_mc") or {}).get("name"),
            "home_lc_id": int(home_committee_id),
            "home_mc_id": int(home_mc_id),
            "latest_graduation_date": _parse_date(p.get("latest_graduation_date")),
            "opportunity_applications_count": int(p.get("opportunity_applications_count") or 0),
            "last_synced_at": now,
            "inserted_at": now,
            "updated_at": now,
        })


    return rows


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    v = value.strip()
    # handle "Z"
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(v)
    except ValueError:
        return None


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    v = value.strip()
    try:
        return date.fromisoformat(v)
    except ValueError:
        return None


def _norm_gender(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    v = value.strip().lower()
    # keep only known values (adjust if your DB enum differs)
    if v in {"male", "female"}:
        return v
    return None