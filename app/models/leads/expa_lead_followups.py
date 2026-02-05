from datetime import datetime
from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ExpaLeadFollowUp(Base):
    __tablename__ = "expa_lead_follow_ups"

    __table_args__ = (
        CheckConstraint(
            "follow_up_at > now()",
            name="ck_expa_lead_follow_ups_follow_up_at_future",
        ),
        CheckConstraint(
            "status IN ('pending', 'completed')",
            name="ck_expa_lead_follow_ups_status_valid",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )

    expa_person_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("expa_leads.expa_person_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    follow_up_text: Mapped[str] = mapped_column(Text, nullable=False)

    follow_up_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="pending",
    )

    created_by_member_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("members.expa_person_id", ondelete="SET NULL"),
        nullable=True
    )

    created_by_member_name: Mapped[Text] = mapped_column(
        Text,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    lead = relationship("ExpaLead", back_populates="follow_ups")
    created_by = relationship(
        "Member",
        back_populates="follow_ups_created",
        foreign_keys=[created_by_member_id],
    )
