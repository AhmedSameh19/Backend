from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IGVMarketResearch(Base):
    __tablename__ = "igv_market_research"

    __table_args__ = (
        Index("idx_igv_market_research_home_lc_id", "home_lc_id"),
        Index("idx_igv_market_research_home_lc_created_at", "home_lc_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    podio_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    company_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    product: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sub_project: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    home_lc_id: Mapped[int] = mapped_column(Integer, nullable=False)
    socialmedia_acc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    website: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    acc_submitted_by: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    company_employee_size: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    person_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    position: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
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

