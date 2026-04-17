from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ExpaICXLeadFollowUp(Base):
    __tablename__ = "expa_icx_lead_follow_ups"

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'completed')",
            name="ck_expa_icx_lead_follow_ups_status_valid",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )

    application_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("expa_icx_leads.application_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    follow_up_text: Mapped[str] = mapped_column(Text, nullable=False)

    follow_up_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="pending",
    )

    created_by_member_id: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        index=True,
    )

    created_by_member_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    lead_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lead_phone: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    lead = relationship("ExpaICXLead", back_populates="follow_ups")
    created_by = relationship(
        "Member",
        primaryjoin="Member.expa_person_id == ExpaICXLeadFollowUp.created_by_member_id",
        foreign_keys=[created_by_member_id]
    )
