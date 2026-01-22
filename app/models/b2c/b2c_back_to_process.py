from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class B2CBackToProcess(Base):
    __tablename__ = "b2c_back_to_process"

    __table_args__ = (
        UniqueConstraint("expa_person_id", name="uq_b2c_back_to_process_expa_person_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    expa_person_id: Mapped[str] = mapped_column(
		Text,
		ForeignKey("expa_leads.expa_person_id", ondelete="CASCADE"),
		nullable=False,
		index=True,
	)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)

    email: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # EXPA status (GraphQL: data.status)
    expa_status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # person_profile.selected_programmes
    selected_programmes: Mapped[Optional[str]] = mapped_column(Text,nullable=True,default="GV")

    home_lc_name: Mapped[str] = mapped_column(Text, nullable=False)
    home_mc_name: Mapped[str] = mapped_column(Text, nullable=False)
    home_lc_id: Mapped[int] = mapped_column(Integer, nullable=False)
    home_mc_id: Mapped[int] = mapped_column(Integer, nullable=False)

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
    