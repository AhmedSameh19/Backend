from __future__ import annotations

from pydantic import BaseModel,Field

from typing import List

class LeadAssignRequest(BaseModel):
    member_id: str

class LeadBulkAssignRequest(BaseModel):
    member_id: str = Field(..., min_length=1)
    expa_person_ids: List[str] = Field(..., min_length=1)