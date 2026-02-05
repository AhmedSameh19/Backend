from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import requests


ICX_REALIZATIONS_QUERY = """
query AllOpportunityApplication(
  $from: DateTime
  $per_page: Int!
  $page: Int!
  $opportunity_committee: Int
) {
  allOpportunityApplication(
    filters: {
      opportunity_committee: $opportunity_committee
      date_realized: { from: $from }
    }
    page: $page
    per_page: $per_page
  ) {
    data {
      id
      person {
        id
        created_at
        full_name
        email
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
      }
      opportunity {
        id
        title
        programme {
          short_name_display
        }
        host_lc {
          id
          name
        }
      }
      slot {
        start_date
        end_date
      }
      status
      updated_at
      date_approved
      date_realized
      experience_end_date
    }
  }
}
"""


@dataclass(frozen=True)
class ExpaICXRealizationsClient:
    api_url: str
    api_token: str
    timeout_seconds: int = 60

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"{self.api_token}",
            "Accept": "*/*",
        }

    def fetch_icx_realizations_page(
        self,
        *,
        from_date: str,
        per_page: int,
        page: int,
      opportunity_committee: int,
    ) -> List[Dict[str, Any]]:
        payload = {
            "query": ICX_REALIZATIONS_QUERY,
            "variables": {
                "from": str(from_date),
                "per_page": int(per_page),
                "page": int(page),
            "opportunity_committee": int(opportunity_committee),
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
