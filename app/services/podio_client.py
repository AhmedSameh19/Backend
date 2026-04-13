"""Podio REST client used by market research endpoints."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import requests

# Podio rate-limits /oauth/token aggressively. FastAPI creates a new PodioClient per request,
# so without caching every API call was a new token request → 429/400 after heavy use.
_token_lock = threading.Lock()
_token_cache: Dict[Tuple[str, str, str, str], Tuple[str, float]] = {}


@dataclass(frozen=True)
class PodioClient:
    client_id: str
    client_secret: str
    app_id: Optional[str] = None
    app_token: Optional[str] = None
    timeout_seconds: int = 60
    base_url: str = "https://api.podio.com"

    def _token_cache_key(self) -> Tuple[str, str, str, str]:
        return (
            self.client_id,
            self.client_secret,
            str(self.app_id or ""),
            self.app_token or "",
        )

    def _fetch_access_token_uncached(self) -> Tuple[str, float]:
        """POST /oauth/token and return (access_token, monotonic expiry time)."""
        if not self.app_id or not self.app_token:
            raise ValueError("app_id and app_token must be provided for app authentication")

        url = f"{self.base_url}/oauth/token"
        app_id_int = int(self.app_id) if self.app_id else None
        data = {
            "grant_type": "app",
            "app_id": app_id_int,
            "app_token": self.app_token,
        }
        try:
            resp = requests.post(
                url,
                data=data,
                auth=(self.client_id, self.client_secret),
                timeout=self.timeout_seconds,
            )
            resp.raise_for_status()
            token_data: Dict[str, Any] = resp.json()
            access_token = token_data.get("access_token", "")
            if not access_token:
                raise ValueError("Podio token response missing access_token")
            expires_in = token_data.get("expires_in")
            if expires_in is not None:
                try:
                    ttl = max(int(expires_in) - 120, 300)
                except (TypeError, ValueError):
                    ttl = 3300
            else:
                ttl = 3300
            expires_at = time.monotonic() + float(ttl)
            return access_token, expires_at
        except requests.exceptions.HTTPError as e:
            error_detail = "Unknown error"
            if e.response is not None:
                try:
                    error_data = e.response.json()
                    error_detail = error_data.get(
                        "error_description", error_data.get("error", str(e))
                    )
                    if "error" in error_data:
                        error_detail = error_data.get(
                            "error_description", error_data.get("error", error_detail)
                        )
                except Exception:
                    error_detail = e.response.text or str(e)
            raise ValueError("Failed to get Podio access token: " + error_detail) from e

    def _get_access_token(self) -> str:
        """OAuth app token, cached per credentials to avoid Podio /oauth/token rate limits."""
        key = self._token_cache_key()
        now = time.monotonic()
        with _token_lock:
            hit = _token_cache.get(key)
            if hit and now < hit[1]:
                return hit[0]
            token, expires_at = self._fetch_access_token_uncached()
            _token_cache[key] = (token, expires_at)
            return token

    def _headers(self, access_token: str) -> Dict[str, str]:
        return {
            "Authorization": f"OAuth2 {access_token}",
            "Content-Type": "application/json",
        }

    def get_app_items(
        self,
        app_id: Optional[int] = None,
        limit: int = 500,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get items from a Podio app
        
        Args:
            app_id: Podio app ID (uses self.app_id if not provided)
            limit: Maximum number of items to return (default 500, max 500)
            offset: Offset for pagination
            filters: Optional filters to apply
            
        Returns:
            List of item dictionaries
        """
        access_token = self._get_access_token()
        app_id = app_id or int(self.app_id) if self.app_id else None
        
        if not app_id:
            raise ValueError("app_id must be provided either as parameter or in client config")
        
        url = f"{self.base_url}/item/app/{app_id}/"
        params = {
            "limit": min(limit, 500),  # Podio max is 500
            "offset": offset,
        }
        
        if filters:
            params.update(filters)
        
        all_items: List[Dict[str, Any]] = []
        current_offset = offset
        
        while True:
            params["offset"] = current_offset
            resp = requests.get(
                url,
                headers=self._headers(access_token),
                params=params,
                timeout=self.timeout_seconds,
            )
            resp.raise_for_status()
            response_data: Dict[str, Any] = resp.json()
            
            # Podio API returns items in different formats depending on endpoint
            # Check if response is a list directly, or has an 'items' key
            if isinstance(response_data, list):
                data = response_data
            elif isinstance(response_data, dict) and "items" in response_data:
                data = response_data["items"]
            else:
                # If it's a dict but no 'items' key, might be a single item or different structure
                data = []
            
            if not data:
                break
                
            all_items.extend(data)
            
            # If we got fewer items than requested, we've reached the end
            if len(data) < params["limit"]:
                break
                
            current_offset += len(data)
            
            # Safety check to prevent infinite loops
            if len(all_items) >= limit:
                break
        
        return all_items[:limit]

    def get_app_items_filtered(
        self,
        app_id: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Get items from a Podio app using the filter endpoint (POST).
        Use this when filtering by field values (e.g. category) so Podio returns only
        matching items — faster and smaller payload than get_app_items + in-memory filter.

        Args:
            app_id: Podio app ID (uses self.app_id if not provided)
            filters: Dict mapping field_id (str) to filter value. For category fields
                     use a list of option ids, e.g. {"123456": [option_id1, option_id2]}.
            limit: Maximum number of items to return (default 100, max 500)
            offset: Offset for pagination

        Returns:
            List of item dictionaries
        """
        access_token = self._get_access_token()
        app_id = app_id or (int(self.app_id) if self.app_id else None)
        if not app_id:
            raise ValueError("app_id must be provided either as parameter or in client config")
        if not filters:
            return self.get_app_items(app_id=app_id, limit=limit, offset=offset)

        url = f"{self.base_url}/item/app/{app_id}/filter/"
        payload = {
            "limit": min(limit, 500),
            "offset": offset,
            "filters": filters,
            "remember": False,
        }
        resp = requests.post(
            url,
            headers=self._headers(access_token),
            json=payload,
            timeout=self.timeout_seconds,
        )
        resp.raise_for_status()
        data: Dict[str, Any] = resp.json()
        items = data.get("items") if isinstance(data, dict) else []
        return list(items) if isinstance(items, list) else []

    def get_item(self, item_id: int) -> Dict[str, Any]:
        """Get a single item by ID"""
        access_token = self._get_access_token()
        url = f"{self.base_url}/item/{item_id}"
        
        resp = requests.get(
            url,
            headers=self._headers(access_token),
            timeout=self.timeout_seconds,
        )
        resp.raise_for_status()
        return resp.json()

    def create_item(
        self,
        fields: List[Dict[str, Any]],
        app_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Create a new item in a Podio app
        
        Args:
            fields: List of field dictionaries with 'external_id' and 'value' keys
                   Example: [{"external_id": "company-name", "value": "Acme Corp"}]
            app_id: Podio app ID (uses self.app_id if not provided)
            
        Returns:
            Created item dictionary with item_id
        """
        access_token = self._get_access_token()
        app_id = app_id or int(self.app_id) if self.app_id else None
        
        if not app_id:
            raise ValueError("app_id must be provided either as parameter or in client config")
        
        url = f"{self.base_url}/item/app/{app_id}/"
        payload = {"fields": fields}
        
        resp = requests.post(
            url,
            headers=self._headers(access_token),
            json=payload,
            timeout=self.timeout_seconds,
        )
        resp.raise_for_status()
        return resp.json()

    def update_item(
        self,
        item_id: int,
        fields: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Update an existing Podio item's field values.

        Args:
            item_id: Podio item ID
            fields: List of field dicts with 'external_id' and 'values' (array).
                   Example: [{"external_id": "assigned-to", "values": ["expa_123"]}]

        Returns:
            Updated item dictionary
        """
        access_token = self._get_access_token()
        url = f"{self.base_url}/item/{item_id}"
        payload = {"fields": fields}
        resp = requests.put(
            url,
            headers=self._headers(access_token),
            json=payload,
            timeout=self.timeout_seconds,
        )
        resp.raise_for_status()
        return resp.json()

    def get_app_field(
        self,
        field_id_or_external_id: Union[int, str],
        app_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get a single field configuration from a Podio app.
        Use this to get category options (e.g. LC list) for building PODIO_LC_OPTION_IDS.

        Args:
            field_id_or_external_id: Podio field_id (int) or external_id (str, e.g. "status")
            app_id: Podio app ID (uses self.app_id if not provided)

        Returns:
            Field config dict with config.settings.options for category fields.
        """
        access_token = self._get_access_token()
        app_id = app_id or (int(self.app_id) if self.app_id else None)
        if not app_id:
            raise ValueError("app_id must be provided either as parameter or in client config")
        url = f"{self.base_url}/app/{app_id}/field/{field_id_or_external_id}"
        resp = requests.get(
            url,
            headers=self._headers(access_token),
            timeout=self.timeout_seconds,
        )
        resp.raise_for_status()
        return resp.json()
