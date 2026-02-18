from __future__ import annotations

from typing import Any, Dict, List

def members_to_rows(members: List[Dict[str, Any]],home_lc_id: int, home_mc_id: int , home_lc_name: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for member in members:
        row: Dict[str, Any] = {
            "member_id": str(member.get("id")),
            "expa_person_id": str(member.get("person", {}).get("id")),
            "full_name": member.get("person", {}).get("full_name") or "",
            "role": member.get("role", {}).get("name", ""),
            "email": member.get("person", {}).get("email"),
            "function": member.get("function", {}).get("name"),
            "reports_to_member_id": (
                str(member.get("reports_to_position_id"))
                if member.get("reports_to_position_id") is not None
                else None
            ),
            "home_lc_id": str(home_lc_id),
            "home_mc_id": str(home_mc_id),
            "home_lc_name": home_lc_name,
            "home_mc_name": "MC Egypt",
        }
        rows.append(row)
    return rows