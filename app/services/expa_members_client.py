from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import requests


MEMBERS_QUERY = """
query MemberPositionList($home_lc_id: Int, $from: DateTime, $to: DateTime, $page: Int) {
  memberPositions(
    per_page: 2000
    page: $page
    filters: {
      office_id: $home_lc_id
      status: "active"
      start_date: {
        from: $from
        to: $to
      }
    }
    sort: "created_at"
  ) {
    data {
      id
      role {
        name
      }
      person {
        id
        full_name
        email
      }
      function {
        name
      }
      reports_to {
        id
        person {
          id
        }
      }
    }
    paging {
      current_page
      total_pages
    }
  }
}
"""


@dataclass(frozen=True)
class ExpaMembersClient:
    api_url: str
    api_token: str
    timeout_seconds: int = 60

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"{self.api_token}",
            "Accept": "*/*",
        }

    # To fetch all members of specific LC within date range
    def fetch_members(self, *, home_lc_id: int, from_date: str, to_date: str) -> List[Dict[str, Any]]:
        all_members: List[Dict[str, Any]] = []
        current_page = 1
        total_pages = 1

        while current_page <= total_pages:
            payload = {
                "query": MEMBERS_QUERY,
                "variables": {
                    "home_lc_id": int(home_lc_id),
                    "from": from_date,
                    "to": to_date,
                },
            }

            resp = requests.post(
                self.api_url,
                json=payload,
                headers=self._headers(),
                timeout=self.timeout_seconds,
            )
            resp.raise_for_status()
            data: Dict[str, Any] = resp.json()

            if "errors" in data:
                raise RuntimeError(f"AIESEC GraphQL errors: {data['errors']}")

            member_positions = (((data.get("data") or {}).get("memberPositions") or {}))
            members = member_positions.get("data") or []
            paging = member_positions.get("paging") or {}
            total_pages = paging.get("total_pages", 1)

            if isinstance(members, list):
                all_members.extend(members)

            current_page += 1

        return all_members
