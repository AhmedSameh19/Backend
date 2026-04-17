from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import BigInteger, Date, DateTime, Integer, Text, func, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column,relationship

from app.db.base import Base


class ExpaLead(Base):
    __tablename__ = "expa_leads"

    # EXPA person id (GraphQL: data.id)
    expa_person_id: Mapped[str] = mapped_column(Text, primary_key=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)

    email: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    dob: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # EXPA status (GraphQL: data.status)
    expa_status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # academic_experiences.backgrounds[].name
    academic_backgrounds: Mapped[List[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
        server_default="{}",
    )

    # person_profile.selected_programmes
    selected_programmes: Mapped[Optional[str]] = mapped_column(Text,nullable=True,default="GV")

    home_lc_name: Mapped[str] = mapped_column(Text, nullable=False)
    home_mc_name: Mapped[str] = mapped_column(Text, nullable=False)
    home_lc_id: Mapped[int] = mapped_column(Integer, nullable=False)
    home_mc_id: Mapped[int] = mapped_column(Integer, nullable=False)

    latest_graduation_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    opportunity_applications_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    assigned_member_id: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        index=True
    )
    assigned_member_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Sync/meta
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
    status_snapshot = relationship(
        "ExpaLeadStatusSnapshot",
        back_populates="lead",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    b2c_status_snapshot = relationship(
        "B2CLeadStatusSnapshot",
        back_populates="lead",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
  
    comments = relationship(
        "ExpaLeadComment",
        back_populates="lead",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    assigned_member = relationship(
        "Member",
        back_populates="assigned_leads",
        primaryjoin="Member.expa_person_id == ExpaLead.assigned_member_id",
        foreign_keys=[assigned_member_id]
    )

    follow_ups = relationship(
        "ExpaLeadFollowUp",
        back_populates="lead",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    b2c_comments = relationship(
        "B2CComment",
        back_populates="lead"
    )

  