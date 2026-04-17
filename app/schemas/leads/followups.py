from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


FollowUpStatus = Literal["pending", "completed"]


class FollowUpCreate(BaseModel):
	follow_up_text: str = Field(..., min_length=1)
	follow_up_at: datetime
	created_by: Optional[str] = None
	status: FollowUpStatus = "pending"
	lead_name: Optional[str] = None
	lead_phone: Optional[str] = None


class FollowUpOut(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: int
	expa_person_id: str
	lead_name: Optional[str] = None
	lead_phone: Optional[str] = None
	follow_up_text: str
	follow_up_at: datetime
	status: FollowUpStatus
	created_by_member_id: Optional[str] = None
	created_by_member_name: Optional[str] = None
	created_at: datetime


class FollowUpStatusUpdate(BaseModel):
	status: FollowUpStatus

