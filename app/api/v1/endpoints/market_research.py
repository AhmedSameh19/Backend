from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import get_db
from app.models.market_research.igv import IGVMarketResearch
from app.models.market_research.b2b_market_research import B2BMarketResearch
from app.services.podio_client import PodioClient
from app.schemas.market_research import (
    MarketResearchItem,
    MarketResearchListResponse,
    IGVMarketResearchSubmit,
    B2BMarketResearchSubmit,
    MarketResearchSubmitResponse,
    IGVMarketResearchCreate,
    B2BMarketResearchCreate,
    IGVMarketResearchOut,
    B2BMarketResearchOut,
)

router = APIRouter()


def get_podio_client() -> PodioClient:
    """Create and return Podio client instance"""
    if not settings.PODIO_CLIENT_ID or not settings.PODIO_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Podio credentials not configured. Please set PODIO_CLIENT_ID, PODIO_CLIENT_SECRET, PODIO_APP_ID, and PODIO_APP_TOKEN environment variables.",
        )
    
    if not settings.PODIO_APP_ID or not settings.PODIO_APP_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Podio app credentials not configured. Please set PODIO_APP_ID and PODIO_APP_TOKEN environment variables. Make sure the app_token matches the app_id.",
        )
    
    return PodioClient(
        client_id=settings.PODIO_CLIENT_ID,
        client_secret=settings.PODIO_CLIENT_SECRET,
        app_id=settings.PODIO_APP_ID,
        app_token=settings.PODIO_APP_TOKEN,
    )


def extract_field_value(item: dict, field_external_id: str) -> Optional[str]:
    """Extract value from Podio item field by external ID"""
    if not isinstance(item, dict):
        return None
    fields = item.get("fields", [])
    for field in fields:
        if field.get("external_id") == field_external_id:
            values = field.get("values", [])
            if values:
                # Handle different field types
                value = values[0]
                if isinstance(value, dict):
                    # For category fields: extract 'text' or 'value' or 'name'
                    # Category format: {'id': 7, 'status': 'active', 'text': 'B2B', 'color': 'DCEBD8'}
                    if "text" in value:
                        return value.get("text")
                    elif "value" in value:
                        return str(value.get("value"))
                    elif "name" in value:
                        return value.get("name")
                    # If none of the above, try to get a string representation
                    return str(value)
                # For simple string/number values
                return str(value)
    return None


def map_podio_item_to_market_research(item: dict) -> MarketResearchItem:
    """Map Podio item to MarketResearchItem schema"""
    # Note: You'll need to replace these field_external_id values with your actual Podio field external IDs
    # These are placeholders - adjust based on your Podio app structure
    
    # Podio uses 'item_id' or 'app_item_id' for the item identifier
    item_id = item.get("item_id") or item.get("app_item_id")
    
    return MarketResearchItem(
        company_name=extract_field_value(item, "company-name") or extract_field_value(item, "company_name"),
        product=extract_field_value(item, "product") or extract_field_value(item, "PRODUCT"),
        sub_project_igv=extract_field_value(item, "sub-project-igv") or extract_field_value(item, "sub_project") or extract_field_value(item, "igv"),
        local_committee=extract_field_value(item, "local-committee") or extract_field_value(item, "local_committee") or extract_field_value(item, "lc"),
        type_of_pr_deal=extract_field_value(item, "type-of-pr-deal") or extract_field_value(item, "type_of_pr_deal") or extract_field_value(item, "pr_deal_type"),
        reason_of_approach=extract_field_value(item, "reason-of-approach") or extract_field_value(item, "reason_of_approach"),
        item_id=item_id,
    )


@router.get("", response_model=MarketResearchListResponse, tags=["market-research"])
async def get_market_research(
    limit: int = Query(500, ge=1, le=500, description="Maximum number of items to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    podio_client: PodioClient = Depends(get_podio_client),
):
    """
    Fetch market research data from Podio
    
    Returns a list of market research items containing:
    - Company name
    - Product
    - Sub-project (IGV)
    - Local committee
    - Type of PR deal
    - Reason of approach
    """
    try:
        items = podio_client.get_app_items(
            limit=limit,
            offset=offset,
        )
        
        # Filter out non-dict items and map valid items
        mapped_items = [
            map_podio_item_to_market_research(item) 
            for item in items 
            if isinstance(item, dict)
        ]
        
        return MarketResearchListResponse(
            items=mapped_items,
            total=len(mapped_items),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except requests.exceptions.RequestException as e:
        error_detail = f"Error fetching data from Podio: {str(e)}"
        if hasattr(e, "response") and e.response is not None:
            try:
                error_data = e.response.json()
                error_detail = error_data.get("error_description", error_data.get("error", error_detail))
            except:
                error_detail = e.response.text or error_detail
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=error_detail,
        )


@router.get("/{item_id}", response_model=MarketResearchItem, tags=["market-research"])
async def get_market_research_item(
    item_id: int,
    podio_client: PodioClient = Depends(get_podio_client),
):
    """Get a single market research item by Podio item ID"""
    try:
        item = podio_client.get_item(item_id)
        return map_podio_item_to_market_research(item)
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if e.response and e.response.status_code == 404 else status.HTTP_502_BAD_GATEWAY,
            detail=f"Error fetching item from Podio: {str(e)}",
        )


def build_podio_fields(data: Dict[str, Any], field_mapping: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Build Podio field format from data dictionary
    
    Args:
        data: Dictionary with field values
        field_mapping: Mapping from data keys to Podio field external IDs
        
    Returns:
        List of Podio field dictionaries
    """
    fields = []
    for key, external_id in field_mapping.items():
        value = data.get(key)
        if value is not None:
            # Podio expects fields with "values" as an array, not "value"
            fields.append({
                "external_id": external_id,
                "values": [str(value)]  # Podio expects values as an array
            })
    return fields


# Field mappings - Update these with your actual Podio field external IDs
# You can find these in your Podio app settings
# Note: home_lc_id is NOT sent to Podio - it's for our database only
IGV_FIELD_MAPPING = {
    "company_name": "company-name",  # Update with actual external ID
    "product": "product",  # Update with actual external ID
    "sub_project": "sub-project",  # Update with actual external ID
    # home_lc_id is excluded - it's for our database, not Podio
}

B2B_FIELD_MAPPING = {
    "company_name": "company-name",  # Update with actual external ID
    "product": "product",  # Update with actual external ID
    "reason_for_approach": "reason-for-approach",  # Update with actual external ID
    # home_lc_id is excluded - it's for our database, not Podio
}


@router.post("/igv/submit", response_model=MarketResearchSubmitResponse, tags=["market-research"])
async def submit_igv_market_research(
    payload: IGVMarketResearchSubmit,
    podio_client: PodioClient = Depends(get_podio_client),
):
    """
    Submit IGV market research data to Podio
    
    Creates a new item in Podio with the provided IGV market research data.
    """
    try:
        data = payload.model_dump()
        fields = build_podio_fields(data, IGV_FIELD_MAPPING)
        
        result = podio_client.create_item(fields=fields)
        item_id = result.get("item_id")
        
        if not item_id:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Podio did not return an item_id",
            )
        
        return MarketResearchSubmitResponse(
            item_id=item_id,
            success=True,
            message="Successfully submitted IGV market research to Podio",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except requests.exceptions.RequestException as e:
        error_detail = "Error submitting to Podio"
        if hasattr(e, "response") and e.response is not None:
            try:
                error_data = e.response.json()
                error_detail = error_data.get("error_description", error_detail)
            except:
                error_detail = str(e)
        
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=error_detail,
        )


@router.post("/b2b/submit", response_model=MarketResearchSubmitResponse, tags=["market-research"])
async def submit_b2b_market_research(
    payload: B2BMarketResearchSubmit,
    podio_client: PodioClient = Depends(get_podio_client),
):
    """
    Submit B2B market research data to Podio
    
    Creates a new item in Podio with the provided B2B market research data.
    """
    try:
        data = payload.model_dump()
        fields = build_podio_fields(data, B2B_FIELD_MAPPING)
        
        result = podio_client.create_item(fields=fields)
        item_id = result.get("item_id")
        
        if not item_id:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Podio did not return an item_id",
            )
        
        return MarketResearchSubmitResponse(
            item_id=item_id,
            success=True,
            message="Successfully submitted B2B market research to Podio",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except requests.exceptions.RequestException as e:
        error_detail = "Error submitting to Podio"
        if hasattr(e, "response") and e.response is not None:
            try:
                error_data = e.response.json()
                error_detail = error_data.get("error_description", error_detail)
            except:
                error_detail = str(e)
        
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=error_detail,
        )


@router.post("/igv", response_model=IGVMarketResearchOut, status_code=status.HTTP_201_CREATED, tags=["market-research"])
def create_igv_market_research(
    payload: IGVMarketResearchCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new IGV market research record in the database
    
    Saves market research data to the database (not Podio).
    """
    try:
        igv_record = IGVMarketResearch(**payload.model_dump())
        db.add(igv_record)
        db.commit()
        db.refresh(igv_record)
        return igv_record
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database error: " + str(e),
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error: " + str(e),
        )


@router.post("/b2b", response_model=B2BMarketResearchOut, status_code=status.HTTP_201_CREATED, tags=["market-research"])
def create_b2b_market_research(
    payload: B2BMarketResearchCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new B2B market research record in the database
    
    Saves market research data to the database (not Podio).
    """
    try:
        b2b_record = B2BMarketResearch(**payload.model_dump())
        db.add(b2b_record)
        db.commit()
        db.refresh(b2b_record)
        return b2b_record
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database error: " + str(e),
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error: " + str(e),
        )

