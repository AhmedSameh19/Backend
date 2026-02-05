from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ICXRealizationsStandards(Base):
    __tablename__ = "icx_realizations_standards"

    application_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("expa_icx_realizations.application_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )

    expa_person_id: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    health_insurance: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    expectation_settings: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    visa_and_work_permit: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    communication_10_days_before: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    arrival_pickup: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    accommodation: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("false"))

    ips: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    ops: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    pgs: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("false"))

    alignment_space: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    first_day_of_work: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    job_description: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    working_hours: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    duration: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    opportunity_benefits: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    value_driven_leadership_education: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("false"))

    communication_first_10_days: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    communication_second_10_days: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    communication_third_10_days: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    communication_fourth_10_days: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("false"))

    departure_support: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    debrief: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("false"))

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )
