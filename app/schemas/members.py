from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional
class MemberCreate(BaseModel):
    member_id: str = Field(..., min_length=1)
    full_name: str = Field(..., min_length=1)


class MemberOut(BaseModel):
    expa_person_id: Optional[str] = None
    member_id: Optional[str] = None
    full_name: str = Field(..., min_length=1)
    role: str | None = None
    function: str | None = None
    email: str | None = None

    class Config:
        from_attributes = True
        
class OkResponse(BaseModel):
    ok: bool