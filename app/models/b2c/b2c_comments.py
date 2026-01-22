from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column,relationship

from app.db.base import Base


class B2CComment(Base):
	__tablename__ = "b2c_comments"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

	expa_person_id: Mapped[str] = mapped_column(
		Text,
		ForeignKey("expa_leads.expa_person_id", ondelete="CASCADE"),
		nullable=False,
		index=True,
	)

	comment: Mapped[str] = mapped_column(Text, nullable=False)

	creator_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		nullable=False,
		server_default=func.now(),
	)
	lead= relationship("ExpaLead", back_populates="b2c_comments")
