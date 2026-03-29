from __future__ import annotations

from typing import Any, Dict, List

def members_to_rows(members: List[Dict[str, Any]],home_lc_id: int, home_mc_id: int , home_lc_name: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for member in members:
        reports_to = member.get("reports_to")
        row: Dict[str, Any] = {
            "member_id": str(member.get("id")),
            "expa_person_id": str(member.get("person", {}).get("id")),
            "full_name": member.get("person", {}).get("full_name") or "",
            "role": member.get("role", {}).get("name", ""),
            "email": member.get("person", {}).get("email"),
            "function": member.get("function", {}).get("name"),
            "reports_to_member_id": (
                str(reports_to.get("id"))
                if reports_to is not None
                else None
            ),
            "reports_to_person_id": (
                str(reports_to.get("person", {}).get("id"))
                if (reports_to and reports_to.get("person"))
                else None
            ),
            "home_lc_id": str(home_lc_id),
            "home_mc_id": str(home_mc_id),
            "home_lc_name": home_lc_name,
        }
        rows.append(row)
    return rows