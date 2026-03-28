from __future__ import annotations

from pydantic import BaseModel, Field
class MemberCreate(BaseModel):
    member_id: str = Field(..., min_length=1)
    full_name: str = Field(..., min_length=1)


class MemberOut(BaseModel):
    expa_person_id: str
    member_id: str
    full_name: str = Field(..., min_length=1)
    role: str | None = None
    function: str | None = None
    email: str | None = None

    class Config:
        from_attributes = True
        
class OkResponse(BaseModel):
    ok: bool