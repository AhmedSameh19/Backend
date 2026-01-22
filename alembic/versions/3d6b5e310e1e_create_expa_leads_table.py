"""create expa_leads table

Revision ID: 3d6b5e310e1e
Revises: 
Create Date: 2026-01-13 19:35:43.053560

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql



# revision identifiers, used by Alembic.
revision: str = '3d6b5e310e1e'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "expa_leads",
        sa.Column("expa_person_id", sa.Text(), primary_key=True),

        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("full_name", sa.Text(), nullable=False),

        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("gender", sa.Text(), nullable=True),

        sa.Column("dob", sa.Date(), nullable=True),

        sa.Column("expa_status", sa.Text(), nullable=True),

        sa.Column(
            "academic_backgrounds",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),

        sa.Column(
            "selected_programmes",
            sa.Text(),
            nullable=True,
            server_default="GV",
        ),

        sa.Column("home_lc_name", sa.Text(), nullable=False),
        sa.Column("home_mc_name", sa.Text(), nullable=False),
        sa.Column("home_lc_id", sa.Integer(), nullable=False),
        sa.Column("home_mc_id", sa.Integer(), nullable=False),

        sa.Column("latest_graduation_date", sa.Date(), nullable=True),

        sa.Column(
            "opportunity_applications_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        # Keep assignment columns in the initial table, but add the FK later
        # after the `members` table exists.
        sa.Column(
            "assigned_member_id",
            sa.Text(),
            nullable=True,
        ),
        sa.Column("assigned_member_name", sa.Text(), nullable=True),
        sa.Column(
            "last_synced_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "inserted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    
    # Indexes optimized for LC filtering + list pagination
    op.create_index(
        "idx_expa_leads_home_lc_created_at",
        "expa_leads",
        ["home_lc_name", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_expa_leads_created_at",
        "expa_leads",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "idx_expa_leads_status",
        "expa_leads",
        ["expa_status"],
        unique=False,
    )
    op.create_index(
        "idx_expa_leads_last_synced_at",
        "expa_leads",
        ["last_synced_at"],
        unique=False,
    )



def downgrade() -> None:
    op.drop_index("idx_expa_leads_last_synced_at", table_name="expa_leads")
    op.drop_index("idx_expa_leads_status", table_name="expa_leads")
    op.drop_index("idx_expa_leads_created_at", table_name="expa_leads")
    op.drop_index("idx_expa_leads_home_lc_created_at", table_name="expa_leads")
    op.drop_table("expa_leads")