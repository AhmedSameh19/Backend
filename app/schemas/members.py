from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional
class MemberCreate(BaseModel):
    member_id: str = Field(..., min_length=1)
    full_name: str = Field(..., min_length=1)


class MemberOut(BaseModel):
    member_id: Optional[str] = None
    expa_person_id: Optional[str] = None
    full_name: str = Field(..., min_length=1)
    role: Optional[str] = None
    function: Optional[str] = None
    email: Optional[str] = None
    reports_to_member_id: Optional[str] = None
    reports_to_person_id: Optional[str] = None
    home_lc_id: Optional[str] = None
    home_mc_id: Optional[str] = None
    home_lc_name: Optional[str] = None

    class Config:
        from_attributes = True
        
class OkResponse(BaseModel):
    ok: bool