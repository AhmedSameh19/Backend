from typing import Optional
from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Member(Base):
    __tablename__ = "members"

    member_id: Mapped[str] = mapped_column(Text, primary_key=True, unique=True, nullable=False)
    expa_person_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    function: Mapped[str] = mapped_column(Text, nullable=True)
    reports_to_member_id: Mapped[Optional[str]] = mapped_column(
        Text,
        ForeignKey("members.member_id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    reports_to_person_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True, index=True)
    home_lc_id: Mapped[Optional[str]] = mapped_column(Text, nullable=False)
    home_mc_id: Mapped[Optional[str]] = mapped_column(Text, nullable=False, server_default="1609")
    home_lc_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    home_mc_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True, server_default="MC Egypt")    
    # Relationship: all leads assigned to this member
    assigned_leads = relationship(
        "ExpaLead",
        back_populates="assigned_member",
    )
    follow_ups_created = relationship(
        "ExpaLeadFollowUp",
        back_populates="created_by",
        foreign_keys="ExpaLeadFollowUp.created_by_member_id",
        passive_deletes=True
    )
