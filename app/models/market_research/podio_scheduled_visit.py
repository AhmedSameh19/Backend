from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PodioScheduledVisit(Base):
    """Visit date scheduled for a Podio market research item. Used for calendar and Google sync."""
    __tablename__ = "podio_scheduled_visits"
    __table_args__ = (UniqueConstraint("podio_item_id", name="uq_podio_scheduled_visit_item"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Podio item IDs can exceed 32-bit integer range, so use BigInteger.
    podio_item_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    company_name: Mapped[str] = mapped_column(Text, nullable=False)
    visit_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
