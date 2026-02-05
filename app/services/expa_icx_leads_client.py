from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import requests


ICX_LEADS_QUERY = """
query AllOpportunityApplication(
  $opportunity_home_mc: [Int!]
  $programmes: [Int!]
  $from: DateTime
  $to: DateTime
  $per_page: Int!
  $page: Int!
) {
  allOpportunityApplication(
    filters: {
      sort: created_at
      opportunity_home_mc: $opportunity_home_mc
      programmes: $programmes
      created_at: { from: $from, to: $to }
    }
    page: $page
    per_page: $per_page
  ) {
    data {
      id
      person {
        created_at
        full_name
        email
        gender
        id
        contact_detail {
          phone
        }
        home_lc {
          id
          name
        }
        home_mc {
          id
          name
        }
        cv_url
      }
      opportunity {
        id
        title
        programme {
          short_name_display
        }
        opportunity_duration_type {
          duration_type
        }
        host_lc {
          id
          name
        }
      }
      created_at
      date_approved
      date_approval_broken
      date_realized
      experience_end_date
      status
      home_mc {
        id
        name
      }
    }
  }
}
"""


@dataclass(frozen=True)
class ExpaICXLeadsClient:
    api_url: str
    api_token: str
    timeout_seconds: int = 60

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"{self.api_token}",
            "Accept": "*/*",
        }

    def fetch_icx_leads_page(
        self,
        *,
        opportunity_home_mc: int,
        programmes: List[int],
        created_from: str,
      created_to: str | None = None,
        per_page: int,
        page: int,
    ) -> List[Dict[str, Any]]:
        payload = {
            "query": ICX_LEADS_QUERY,
            "variables": {
            "opportunity_home_mc": [int(opportunity_home_mc)],
                "programmes": [int(x) for x in programmes],
                "from": str(created_from),
          "to": str(created_to) if created_to else None,
                "per_page": int(per_page),
                "page": int(page),
            },
        }

        response = requests.post(
            self.api_url,
            json=payload,
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()

        data = response.json()
        errors = data.get("errors")
        if errors:
            raise RuntimeError(f"EXPA GraphQL errors: {errors}")

        return data.get("data", {}).get("allOpportunityApplication", {}).get("data", [])
