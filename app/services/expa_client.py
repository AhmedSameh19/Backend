from __future__ import annotations

from dataclasses import dataclass

from typing import Any, Dict, List

from app.services.expa_members_client import ExpaMembersClient
from app.services.expa_people_client import ExpaPeopleClient

@dataclass(frozen=True)
class ExpaClient:
    api_url: str
    api_token: str
    timeout_seconds: int = 60

    def fetch_people_page(
        self,
        *,
        home_committee: int,
        registered_from: str,
        registered_to: str,
        per_page: int,
        page: int,
    ) -> List[Dict[str, Any]]:
      return ExpaPeopleClient(
        api_url=self.api_url,
        api_token=self.api_token,
        timeout_seconds=self.timeout_seconds,
      ).fetch_people_page(
        home_committee=home_committee,
        registered_from=registered_from,
        registered_to=registered_to,
        per_page=per_page,
        page=page,
      )
    
    # To fetch all members of specific LC within date range
    def fetch_members(self, *, home_lc_id: int, from_date: str, to_date: str) -> List[Dict[str, Any]]:
      return ExpaMembersClient(
        api_url=self.api_url,
        api_token=self.api_token,
        timeout_seconds=self.timeout_seconds,
      ).fetch_members(home_lc_id=home_lc_id, from_date=from_date, to_date=to_date)


    __all__ = [
    "ExpaClient",
    "ExpaPeopleClient",
    "ExpaMembersClient",
    ]