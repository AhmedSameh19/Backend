"""Create iCX realizations standards table

Revision ID: f2b3c4d5e6f7
Revises: e3f4a5b6c7d8
Create Date: 2026-02-05

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "e3f4a5b6c7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "icx_realizations_standards",
        sa.Column(
            "application_id",
            sa.Text(),
            sa.ForeignKey("expa_icx_realizations.application_id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("health_insurance", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("expectation_settings", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("visa_and_work_permit", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("communication_10_days_before", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("arrival_pickup", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("accommodation", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("alignment_space", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("job_description", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("working_hours", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("duration", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("opportunity_benefits", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "value_driven_leadership_education",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("communication_first_10_days", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("communication_second_10_days", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("communication_third_10_days", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("communication_fourth_10_days", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("departure_support", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("debrief", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_index(
        "ix_icx_realizations_standards_application_id",
        "icx_realizations_standards",
        ["application_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_icx_realizations_standards_application_id", table_name="icx_realizations_standards")
    op.drop_table("icx_realizations_standards")
