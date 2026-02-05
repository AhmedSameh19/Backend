from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ICXCommentCreate(BaseModel):
    text: str = Field(..., min_length=1)
    created_by: str = Field(..., min_length=1)


class ICXCommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: str
    comment: str
    creator_name: str | None = None
    created_at: datetime
