from __future__ import annotations
from celery.utils.log import get_task_logger

from dataclasses import dataclass
from typing import Any, Dict, List

import requests
logger = get_task_logger(__name__)

REALIZATIONS_QUERY = """
query AllOpportunityApplication(
  $person_committee: Int
  $from: DateTime
  $per_page: Int!
  $page: Int!
) {
  allOpportunityApplication(
    filters: {
      person_committee: $person_committee
      date_approved: {
        from: $from
      }
    }
    pagination: {
      per_page: $per_page
      page: $page
    }
  ) {
    data {
      person {
        id
        created_at
        lc_alignment {
          keywords
        }
        full_name
        email
        contact_detail {
          phone
        }
        home_lc {
          name
        }
        home_mc {
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
        home_mc {
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
class ExpaRealizationsClient:
    api_url: str
    api_token: str
    timeout_seconds: int = 60

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"{self.api_token}",
            "Accept": "*/*",
        }

    def fetch_realizations(
      self,
      *,
      person_committee: int,
      from_date: str,
      per_page: int,
      page: int,
    ) -> List[Dict[str, Any]]:
        payload = {
            "query": REALIZATIONS_QUERY,
            "variables": {
                "person_committee": int(person_committee),
                "from": str(from_date),
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
        realizations = data.get("data", {}).get("allOpportunityApplication", {}).get("data", [])
        return realizations