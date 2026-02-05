from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ExpaICXLeadStatusSnapshot(Base):
    __tablename__ = "expa_icx_lead_status_snapshot"


    application_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("expa_icx_leads.application_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )

    contacted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    interviewed: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expectations_email_status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    out_of_process: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    lead = relationship("ExpaICXLead", back_populates="status_snapshot")
