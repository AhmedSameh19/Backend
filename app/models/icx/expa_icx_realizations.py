from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ExpaICXRealization(Base):
    __tablename__ = "expa_icx_realizations"

    # Opportunity application id
    application_id: Mapped[str] = mapped_column(Text, primary_key=True)

    expa_person_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True, index=True)

    full_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    contact_number: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    home_lc_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True, index=True)
    home_lc_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    home_mc_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    home_mc_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    host_lc_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True, index=True)
    host_lc_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    programme: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    opp_title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    opp_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True, index=True)

    status: Mapped[Optional[str]] = mapped_column(Text, nullable=True, index=True)

    slot_start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    slot_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    date_approved: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    date_realized: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    experience_end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    assigned_member_id: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        index=True,
    )
    assigned_member_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    assigned_member = relationship(
        "Member",
        primaryjoin="Member.expa_person_id == ExpaICXRealization.assigned_member_id",
        foreign_keys=[assigned_member_id]
    )

    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
