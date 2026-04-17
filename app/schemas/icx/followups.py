from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


ICXFollowUpStatus = Literal["pending", "completed"]


class ICXFollowUpCreate(BaseModel):
    application_id: str
    follow_up_text: str = Field(..., min_length=1)
    follow_up_at: datetime
    created_by: Optional[str] = None


class ICXFollowUpOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: str
    follow_up_text: str
    follow_up_at: datetime
    status: ICXFollowUpStatus
    created_by_member_id: Optional[str] = None
    created_by_member_name: Optional[str] = None
    created_at: datetime


class ICXFollowUpStatusUpdate(BaseModel):
    status: ICXFollowUpStatus
