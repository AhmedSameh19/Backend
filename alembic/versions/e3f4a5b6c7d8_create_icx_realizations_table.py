"""Create iCX realizations table

Revision ID: e3f4a5b6c7d8
Revises: d1a2b3c4d5e6
Create Date: 2026-02-05

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, Sequence[str], None] = "d1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "expa_icx_realizations",
        sa.Column("application_id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("expa_person_id", sa.Text(), nullable=True),
        sa.Column("full_name", sa.Text(), nullable=True),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("contact_number", sa.Text(), nullable=True),
        sa.Column("home_lc_id", sa.Text(), nullable=True),
        sa.Column("home_lc_name", sa.Text(), nullable=True),
        sa.Column("home_mc_id", sa.Text(), nullable=True),
        sa.Column("home_mc_name", sa.Text(), nullable=True),
        sa.Column("host_lc_id", sa.Text(), nullable=True),
        sa.Column("host_lc_name", sa.Text(), nullable=True),
        sa.Column("programme", sa.Text(), nullable=True),
        sa.Column("opp_title", sa.Text(), nullable=True),
        sa.Column("opp_id", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("slot_start_date", sa.Date(), nullable=True),
        sa.Column("slot_end_date", sa.Date(), nullable=True),
        sa.Column("date_approved", sa.DateTime(timezone=True), nullable=True),
        sa.Column("date_realized", sa.DateTime(timezone=True), nullable=True),
        sa.Column("experience_end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "assigned_member_id",
            sa.Text(),
            sa.ForeignKey("members.expa_person_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("assigned_member_name", sa.Text(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_index("ix_expa_icx_realizations_expa_person_id", "expa_icx_realizations", ["expa_person_id"])
    op.create_index("ix_expa_icx_realizations_home_lc_id", "expa_icx_realizations", ["home_lc_id"])
    op.create_index("ix_expa_icx_realizations_host_lc_id", "expa_icx_realizations", ["host_lc_id"])
    op.create_index("ix_expa_icx_realizations_opp_id", "expa_icx_realizations", ["opp_id"])
    op.create_index("ix_expa_icx_realizations_status", "expa_icx_realizations", ["status"])
    op.create_index("ix_expa_icx_realizations_date_realized", "expa_icx_realizations", ["date_realized"])
    op.create_index("ix_expa_icx_realizations_assigned_member_id", "expa_icx_realizations", ["assigned_member_id"])


def downgrade() -> None:
    op.drop_index("ix_expa_icx_realizations_assigned_member_id", table_name="expa_icx_realizations")
    op.drop_index("ix_expa_icx_realizations_date_realized", table_name="expa_icx_realizations")
    op.drop_index("ix_expa_icx_realizations_status", table_name="expa_icx_realizations")
    op.drop_index("ix_expa_icx_realizations_opp_id", table_name="expa_icx_realizations")
    op.drop_index("ix_expa_icx_realizations_host_lc_id", table_name="expa_icx_realizations")
    op.drop_index("ix_expa_icx_realizations_home_lc_id", table_name="expa_icx_realizations")
    op.drop_index("ix_expa_icx_realizations_expa_person_id", table_name="expa_icx_realizations")
    op.drop_table("expa_icx_realizations")
