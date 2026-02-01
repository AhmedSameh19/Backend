from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class MarketResearchItem(BaseModel):
    """Market research data from Podio"""
    company_name: Optional[str] = Field(None, description="Company name")
    product: Optional[str] = Field(None, description="Product")
    sub_project_igv: Optional[str] = Field(None, description="Sub-project (IGV)")
    local_committee: Optional[str] = Field(None, description="Local committee")
    type_of_pr_deal: Optional[str] = Field(None, description="Type of PR deal")
    reason_of_approach: Optional[str] = Field(None, description="Reason of approach")
    item_id: Optional[int] = Field(None, description="Podio item ID")
    
    class Config:
        from_attributes = True


class MarketResearchListResponse(BaseModel):
    """Response containing list of market research items"""
    items: list[MarketResearchItem]
    total: int


class IGVMarketResearchSubmit(BaseModel):
    """IGV market research submission data"""
    company_name: str = Field(..., description="Company name")
    product: Optional[str] = Field(None, description="Product")
    sub_project: Optional[str] = Field(None, description="Sub-project")
    home_lc_id: int = Field(..., description="Home local committee ID")


class B2BMarketResearchSubmit(BaseModel):
    """B2B market research submission data"""
    company_name: str = Field(..., description="Company name")
    product: Optional[str] = Field(None, description="Product")
    reason_for_approach: Optional[str] = Field(None, description="Reason for approach")
    home_lc_id: int = Field(..., description="Home local committee ID")


class MarketResearchSubmitResponse(BaseModel):
    """Response after submitting market research data to Podio"""
    item_id: int = Field(..., description="Podio item ID")
    success: bool = Field(True, description="Whether submission was successful")
    message: str = Field("Successfully submitted to Podio", description="Response message")


class IGVMarketResearchCreate(BaseModel):
    """IGV market research data for database storage"""
    podio_id: Optional[int] = Field(None, description="Podio item ID")
    company_name: Optional[str] = Field(None, description="Company name")
    product: Optional[str] = Field(None, description="Product")
    sub_project: Optional[str] = Field(None, description="Sub-project")
    home_lc_id: int = Field(..., description="Home local committee ID")
    socialmedia_acc: Optional[str] = Field(None, description="Social media account")
    website: Optional[str] = Field(None, description="Website")
    phone_number: Optional[str] = Field(None, description="Phone number")
    acc_submitted_by: Optional[str] = Field(None, description="Account submitted by")
    industry: Optional[str] = Field(None, description="Industry")
    company_employee_size: Optional[str] = Field(None, description="Company employee size")
    address: Optional[str] = Field(None, description="Address")
    person_name: Optional[str] = Field(None, description="Contact person name")
    email: Optional[str] = Field(None, description="Contact email")
    position: Optional[str] = Field(None, description="Contact position")
    
    class Config:
        from_attributes = True


class B2BMarketResearchCreate(BaseModel):
    """B2B market research data for database storage"""
    podio_id: Optional[int] = Field(None, description="Podio item ID")
    company_name: Optional[str] = Field(None, description="Company name")
    product: Optional[str] = Field(None, description="Product")
    reason_for_approach: Optional[str] = Field(None, description="Reason for approach")
    home_lc_id: int = Field(..., description="Home local committee ID")
    socialmedia_acc: Optional[str] = Field(None, description="Social media account")
    website: Optional[str] = Field(None, description="Website")
    phone_number: Optional[str] = Field(None, description="Phone number")
    acc_submitted_by: Optional[str] = Field(None, description="Account submitted by")
    industry: Optional[str] = Field(None, description="Industry")
    company_employee_size: Optional[str] = Field(None, description="Company employee size")
    address: Optional[str] = Field(None, description="Address")
    person_name: Optional[str] = Field(None, description="Contact person name")
    email: Optional[str] = Field(None, description="Contact email")
    position: Optional[str] = Field(None, description="Contact position")
    
    class Config:
        from_attributes = True


class IGVMarketResearchOut(BaseModel):
    """IGV market research response model"""
    id: int
    podio_id: Optional[int] = None
    company_name: Optional[str] = None
    product: Optional[str] = None
    sub_project: Optional[str] = None
    home_lc_id: int
    socialmedia_acc: Optional[str] = None
    website: Optional[str] = None
    phone_number: Optional[str] = None
    acc_submitted_by: Optional[str] = None
    industry: Optional[str] = None
    company_employee_size: Optional[str] = None
    address: Optional[str] = None
    person_name: Optional[str] = None
    email: Optional[str] = None
    position: Optional[str] = None
    created_at: datetime
    inserted_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class B2BMarketResearchOut(BaseModel):
    """B2B market research response model"""
    id: int
    podio_id: Optional[int] = None
    company_name: Optional[str] = None
    product: Optional[str] = None
    reason_for_approach: Optional[str] = None
    home_lc_id: int
    socialmedia_acc: Optional[str] = None
    website: Optional[str] = None
    phone_number: Optional[str] = None
    acc_submitted_by: Optional[str] = None
    industry: Optional[str] = None
    company_employee_size: Optional[str] = None
    address: Optional[str] = None
    person_name: Optional[str] = None
    email: Optional[str] = None
    position: Optional[str] = None
    created_at: datetime
    inserted_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True