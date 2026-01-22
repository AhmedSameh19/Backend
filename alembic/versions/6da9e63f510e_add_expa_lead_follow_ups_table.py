"""add expa lead follow ups table

Revision ID: 6da9e63f510e
Revises: 9343f1b7e665
Create Date: 2026-01-15 06:23:08.617576

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6da9e63f510e'
down_revision: Union[str, Sequence[str], None] = '9343f1b7e665'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "expa_lead_follow_ups",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "expa_person_id",
            sa.Text,
            sa.ForeignKey("expa_leads.expa_person_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "follow_up_text",
            sa.Text,
            nullable=False,
        ),
        sa.Column(
            "follow_up_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "created_by_member_id",
            sa.Text,
            sa.ForeignKey("members.member_id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "created_by_member_name",
            sa.Text,
            nullable=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )




def downgrade() -> None:
    op.drop_table("follow_ups")
