from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class CompanyProfileStatus(str, Enum):
    """Company profile lifecycle status in market research"""
    lead = "lead"
    contacted = "contacted"
    visited = "visited"


class MarketResearchItem(BaseModel):
    """Market research data from Podio"""
    company_name: Optional[str] = Field(None, description="Company name")
    product: Optional[str] = Field(None, description="Product")
    sub_project_igv: Optional[str] = Field(None, description="Sub-project (IGV)")
    local_committee: Optional[str] = Field(None, description="Local committee (display name)")
    local_committee_id: Optional[int] = Field(None, description="Local committee Podio option id for filtering")
    type_of_pr_deal: Optional[str] = Field(None, description="Type of PR deal")
    reason_of_approach: Optional[str] = Field(None, description="Reason of approach")
    item_id: Optional[int] = Field(None, description="Podio item ID")
    # Company info (try common Podio field external IDs)
    industry: Optional[str] = Field(None, description="Industry")
    size: Optional[str] = Field(None, description="Company size")
    address: Optional[str] = Field(None, description="Address")
    website: Optional[str] = Field(None, description="Website")
    # Contact person
    contact_person_name: Optional[str] = Field(None, description="Contact person name")
    contact_position: Optional[str] = Field(None, description="Contact position")
    contact_email: Optional[str] = Field(None, description="Contact email")
    contact_phone: Optional[str] = Field(None, description="Contact phone")
    contact_linkedin: Optional[str] = Field(None, description="Contact LinkedIn")

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


class CompanyAssignRequest(BaseModel):
    """Request body for assigning a market research company to a member (EXPA person ID)."""
    member_id: str = Field(..., min_length=1, description="EXPA person ID of the member to assign")


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
    status: CompanyProfileStatus = Field(CompanyProfileStatus.lead, description="Profile status (lead/contacted/visited)")
    visit_date: Optional[datetime] = Field(None, description="Date of company visit (when status is visited)")
    
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
    status: CompanyProfileStatus = Field(CompanyProfileStatus.lead, description="Profile status (lead/contacted/visited)")
    visit_date: Optional[datetime] = Field(None, description="Date of company visit (when status is visited)")
    
    class Config:
        from_attributes = True


class MarketResearchStatusUpdate(BaseModel):
    """Partial update for status and visit date"""
    status: Optional[CompanyProfileStatus] = Field(None, description="Profile status (lead/contacted/visited)")
    visit_date: Optional[datetime] = Field(None, description="Date of company visit (when status is visited)")


class ScheduledVisitOut(BaseModel):
    """Scheduled company visit for calendar (IGV, B2B, or Podio with visit_date set)."""
    id: int
    company_name: Optional[str] = None
    visit_date: datetime
    source: str = Field(..., description="'igv', 'b2b', or 'podio'")

    class Config:
        from_attributes = True


class PodioScheduledVisitCreate(BaseModel):
    """Create or update a scheduled visit for a Podio market research item."""
    podio_item_id: int = Field(..., description="Podio item ID")
    company_name: str = Field(..., min_length=1, description="Company name")
    visit_date: datetime = Field(..., description="Scheduled visit date")


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
    status: str = "lead"
    visit_date: Optional[datetime] = None
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
    status: str = "lead"
    visit_date: Optional[datetime] = None
    created_at: datetime
    inserted_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True