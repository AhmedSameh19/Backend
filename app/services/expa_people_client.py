from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import requests


PEOPLE_QUERY = """
query People($home_committee: [Int], $from: DateTime, $to: DateTime, $per_page: Int!, $page: Int!) {
  people(
    filters: {
      home_committee: $home_committee
      registered: { from: $from, to: $to }
      sort: created_at
    }
    per_page: $per_page
    page: $page
  ) {
    data {
      created_at
      id
      full_name
      email
      phone
      gender
      dob
      status
      academic_experiences {
        backgrounds { name }
      }
      person_profile {
        selected_programmes
      }
      home_lc { name }
      home_mc { name }
      latest_graduation_date
      opportunity_applications_count
    }
  }
}
"""


@dataclass(frozen=True)
class ExpaPeopleClient:
    api_url: str
    api_token: str
    timeout_seconds: int = 60

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"{self.api_token}",
            "Accept": "*/*",
        }

    def fetch_people_page(
        self,
        *,
        home_committee: int,
        registered_from: str,
        registered_to: str,
        per_page: int,
        page: int,
    ) -> List[Dict[str, Any]]:
        payload = {
            "query": PEOPLE_QUERY,
            "variables": {
                "home_committee": [int(home_committee)],
                "from": registered_from,
                "to": registered_to,
                "per_page": int(per_page),
                "page": int(page),
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

        people = (((data.get("data") or {}).get("people") or {}).get("data")) or []
        return people if isinstance(people, list) else []
