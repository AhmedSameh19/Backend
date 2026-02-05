"""Create expa_icx_leads table

Revision ID: f1c2d3e4a5b6
Revises: e8c9d7f6a5b4
Create Date: 2026-02-05

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1c2d3e4a5b6"
down_revision: Union[str, Sequence[str], None] = "b5f2a0c9d3e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "expa_icx_leads",
        sa.Column("application_id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("expa_person_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("person_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("gender", sa.Text(), nullable=True),
        sa.Column("opportunity_host_mc_id", sa.Text(), nullable=True),
        sa.Column("opportunity_host_mc_name", sa.Text(), nullable=True),
        sa.Column("home_lc_id", sa.Text(), nullable=True),
        sa.Column("home_lc_name", sa.Text(), nullable=True),
        sa.Column("home_mc_id", sa.Text(), nullable=True),
        sa.Column("home_mc_name", sa.Text(), nullable=True),
        sa.Column("cv_url", sa.Text(), nullable=True),
        sa.Column("opportunity_id", sa.Text(), nullable=True),
        sa.Column("opportunity_title", sa.Text(), nullable=True),
        sa.Column("programme", sa.Text(), nullable=True),
        sa.Column("opportunity_duration_type", sa.Text(), nullable=True),
        sa.Column("host_lc_id", sa.Text(), nullable=True),
        sa.Column("host_lc_name", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("date_approved", sa.DateTime(timezone=True), nullable=True),
        sa.Column("date_approval_broken", sa.DateTime(timezone=True), nullable=True),
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
        sa.Column("inserted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_index("ix_expa_icx_leads_expa_person_id", "expa_icx_leads", ["expa_person_id"], unique=False)
    op.create_index("ix_expa_icx_leads_host_lc_id_created_at", "expa_icx_leads", ["host_lc_id", "created_at"], unique=False)
    op.create_index("ix_expa_icx_leads_assigned_member_id", "expa_icx_leads", ["assigned_member_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_expa_icx_leads_assigned_member_id", table_name="expa_icx_leads")
    op.drop_index("ix_expa_icx_leads_host_lc_id_created_at", table_name="expa_icx_leads")
    op.drop_index("ix_expa_icx_leads_expa_person_id", table_name="expa_icx_leads")
    op.drop_table("expa_icx_leads")
