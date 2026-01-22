from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class B2CStatusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    expa_person_id: str

    contact_status: Optional[str] = None
    interested: Optional[str] = None
    process_status: Optional[str] = None
    reason: Optional[str] = None
    project: Optional[str] = None
    country: Optional[str] = None

    updated_at: datetime


class B2CStatusUpdate(BaseModel):
    contact_status: Optional[str] = None
    interested: Optional[str] = None
    process_status: Optional[str] = None
    reason: Optional[str] = None
    project: Optional[str] = None
    country: Optional[str] = None