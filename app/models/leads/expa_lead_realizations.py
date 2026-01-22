from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ExpaLeadRealization(Base):
	__tablename__ = "expa_lead_realizations"
	

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

	expa_person_id: Mapped[str] = mapped_column(
		Text,
		nullable=False,
		index=True,
	)

	full_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
	email: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
	created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
	contact_number: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

	home_lc_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
	host_lc_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
	host_mc_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

	assigned_member_id: Mapped[Optional[str]] = mapped_column(
		Text,
		ForeignKey("members.expa_person_id", ondelete="SET NULL"),
		nullable=True,
		index=True,
	)
	assigned_member_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

	programme: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
	opp_title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
	opp_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
	status: Mapped[Optional[str]] = mapped_column(Text, nullable=True, index=True)

	slot_start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
	slot_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		nullable=False,
	)

