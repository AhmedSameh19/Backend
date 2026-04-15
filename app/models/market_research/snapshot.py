from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MarketResearchSnapshot(Base):
    __tablename__ = "market_research_snapshot"

    item_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    company_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True, index=True)
    product: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sub_project_igv: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    local_committee: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    local_committee_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    type_of_pr_deal: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reason_of_approach: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    size: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    website: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contact_person_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contact_position: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contact_linkedin: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    podio_last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )


class MarketResearchSyncState(Base):
    __tablename__ = "market_research_sync_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False, default=1)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    last_synced_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
