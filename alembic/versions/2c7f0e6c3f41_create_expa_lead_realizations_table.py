"""create expa_lead_realizations table

Revision ID: 2c7f0e6c3f41
Revises: a9b12d66df4d
Create Date: 2026-01-22

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2c7f0e6c3f41"
down_revision: Union[str, Sequence[str], None] = "a9b12d66df4d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "expa_lead_realizations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "expa_person_id",
            sa.Text(),
            sa.ForeignKey("expa_leads.expa_person_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("full_name", sa.Text(), nullable=True),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("contact_number", sa.Text(), nullable=True),
        sa.Column("home_lc_id", sa.Integer(), nullable=True),
        sa.Column("host_lc_name", sa.Text(), nullable=True),
        sa.Column("host_mc_name", sa.Text(), nullable=True),
        sa.Column("programme", sa.Text(), nullable=True),
        sa.Column("opp_title", sa.Text(), nullable=True),
        sa.Column("opp_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("slot_start_date", sa.Date(), nullable=True),
        sa.Column("slot_end_date", sa.Date(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),

    )

    op.create_index(
        "ix_expa_lead_realizations_expa_person_id",
        "expa_lead_realizations",
        ["expa_person_id"],
        unique=False,
    )
    op.create_index(
        "ix_expa_lead_realizations_opp_id",
        "expa_lead_realizations",
        ["opp_id"],
        unique=False,
    )
    op.create_index(
        "ix_expa_lead_realizations_home_lc_id",
        "expa_lead_realizations",
        ["home_lc_id"],
        unique=False,
    )
    op.create_index(
        "ix_expa_lead_realizations_status",
        "expa_lead_realizations",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_expa_lead_realizations_status", table_name="expa_lead_realizations")
    op.drop_index("ix_expa_lead_realizations_home_lc_id", table_name="expa_lead_realizations")
    op.drop_index("ix_expa_lead_realizations_opp_id", table_name="expa_lead_realizations")
    op.drop_index("ix_expa_lead_realizations_expa_person_id", table_name="expa_lead_realizations")
    op.drop_table("expa_lead_realizations")
