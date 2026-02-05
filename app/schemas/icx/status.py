from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict





class ICXLeadStatusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    application_id: str

    contacted: Optional[str] = None
    interviewed: Optional[str] = None
    expectations_email_status: Optional[str] = None
    out_of_process: Optional[str] = None
    reason: Optional[str] = None

    updated_at: datetime


class ICXLeadStatusUpdate(BaseModel):
    contacted: Optional[str] = None
    interviewed: Optional[str] = None
    expectations_email_status: Optional[str] = None
    out_of_process: Optional[str] = None
    reason: Optional[str] = None
