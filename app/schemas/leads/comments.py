from __future__ import annotations

from pydantic import BaseModel
from datetime import datetime


class CommentCreate(BaseModel):
    text: str
    created_by: str

class CommentResponse(BaseModel):
    id: int
    expa_person_id: str
    comment: str
    creator_name: str
    created_at: datetime

    class Config:
        from_attributes = True
