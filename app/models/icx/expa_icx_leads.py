from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ExpaICXLead(Base):
    __tablename__ = "expa_icx_leads"

    # EXPA opportunity application id (GraphQL: data.id)
    application_id: Mapped[str] = mapped_column(Text, primary_key=True)

    expa_person_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)

    # Opportunity application timestamps
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    # Person
    person_created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)

    email: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    home_lc_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True, index=True)
    home_lc_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    home_mc_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    home_mc_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    cv_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Opportunity
    opportunity_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    opportunity_title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    programme: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    opportunity_duration_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    host_lc_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    host_lc_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    opportunity_host_mc_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    opportunity_host_mc_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Application status & dates
    status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    date_approved: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    date_approval_broken: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    date_realized: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    experience_end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    assigned_member_id: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        index=True,
    )
    assigned_member_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    inserted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    assigned_member = relationship(
        "Member",
        primaryjoin="Member.expa_person_id == ExpaICXLead.assigned_member_id",
        foreign_keys=[assigned_member_id]
    )

    comments = relationship(
        "ExpaICXLeadComment",
        back_populates="lead",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    follow_ups = relationship(
        "ExpaICXLeadFollowUp",
        back_populates="lead",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    status_snapshot = relationship(
        "ExpaICXLeadStatusSnapshot",
        back_populates="lead",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
