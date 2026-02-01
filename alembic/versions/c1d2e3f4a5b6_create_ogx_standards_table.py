"""Create ogx_standards table

Revision ID: c1d2e3f4a5b6
Revises: e8c9d7f6a5b4
Create Date: 2026-02-01

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, Sequence[str], None] = "e8c9d7f6a5b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ogx_standards",
        sa.Column(
            "expa_person_id",
            sa.Text(),
            sa.ForeignKey("expa_leads.expa_person_id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("health_insurance", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("expectation_settings", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("visa_and_work_permit", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "communication_10_days_before",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
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
        sa.Column(
            "communication_first_10_days",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "communication_second_10_days",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "communication_third_10_days",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "communication_fourth_10_days",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("departure_support", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("debrief", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index(
        "ix_ogx_standards_expa_person_id",
        "ogx_standards",
        ["expa_person_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_ogx_standards_expa_person_id", table_name="ogx_standards")
    op.drop_table("ogx_standards")
