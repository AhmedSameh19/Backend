from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class B2CLeadStatusSnapshot(Base):
    __tablename__ = "b2c_lead_status_snapshot"


    expa_person_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("expa_leads.expa_person_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )

    contact_status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    interested: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    process_status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    project: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    country: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    lead = relationship(
        "ExpaLead",
        back_populates="b2c_status_snapshot",
        uselist=False,
    )

