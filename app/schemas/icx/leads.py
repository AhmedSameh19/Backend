from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class ICXLeadBulkAssignRequest(BaseModel):
    member_id: str = Field(..., min_length=1)
    application_ids: List[str] = Field(..., min_length=1)
