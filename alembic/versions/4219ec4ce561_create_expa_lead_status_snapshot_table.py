"""create expa_lead_status_snapshot table

Revision ID: 4219ec4ce561
Revises: b26e9ffff6f8
Create Date: 2026-01-14 05:04:14.373558

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4219ec4ce561'
down_revision: Union[str, Sequence[str], None] = 'ac7be3f84e53'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
   op.create_table(
        "expa_lead_status_snapshot",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("expa_person_id", sa.Text(), sa.ForeignKey("expa_leads.expa_person_id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("contact_status", sa.Text(), nullable=True),
        sa.Column("interested", sa.Text(), nullable=True),
        sa.Column("process_status", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("project", sa.Text(), nullable=True),
        sa.Column("country", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now())
    )


def downgrade() -> None:
    op.drop_table("expa_lead_status_snapshot")

