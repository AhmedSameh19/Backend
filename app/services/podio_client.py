from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests


@dataclass(frozen=True)
class PodioClient:
    client_id: str
    client_secret: str
    app_id: Optional[str] = None
    app_token: Optional[str] = None
    timeout_seconds: int = 60
    base_url: str = "https://api.podio.com"

    def _get_access_token(self) -> str:
        """Get OAuth access token using app authentication"""
        if not self.app_id or not self.app_token:
            raise ValueError("app_id and app_token must be provided for app authentication")
        
        url = f"{self.base_url}/oauth/token"
        # Podio expects app_id as integer in the request
        app_id_int = int(self.app_id) if self.app_id else None
        
        # Prepare form data (not JSON) for OAuth token request
        data = {
            "grant_type": "app",
            "app_id": app_id_int,  # Keep as integer as per Podio API
            "app_token": self.app_token,
        }
        
        try:
            resp = requests.post(
                url,
                data=data,  # Using form data, not JSON
                auth=(self.client_id, self.client_secret),
                timeout=self.timeout_seconds,
            )
            resp.raise_for_status()
            token_data: Dict[str, Any] = resp.json()
            return token_data.get("access_token", "")
        except requests.exceptions.HTTPError as e:
            # Get more details about the error
            error_detail = "Unknown error"
            if e.response is not None:
                try:
                    error_data = e.response.json()
                    error_detail = error_data.get("error_description", error_data.get("error", str(e)))
                    # Also log the full error response for debugging
                    if "error" in error_data:
                        error_detail = error_data.get("error_description", error_data.get("error", error_detail))
                except:
                    error_detail = e.response.text or str(e)
            raise ValueError("Failed to get Podio access token: " + error_detail) from e

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

