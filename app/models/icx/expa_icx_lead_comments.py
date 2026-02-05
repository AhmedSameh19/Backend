from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ExpaICXLeadComment(Base):
    __tablename__ = "expa_icx_lead_comments"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    application_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("expa_icx_leads.application_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    comment: Mapped[str] = mapped_column(Text, nullable=False)

    creator_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    lead = relationship("ExpaICXLead", back_populates="comments")
