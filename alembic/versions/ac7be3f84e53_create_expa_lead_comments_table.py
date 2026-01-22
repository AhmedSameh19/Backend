"""create expa_lead_comments table

Revision ID: ac7be3f84e53
Revises: 3d6b5e310e1e
Create Date: 2026-01-14 04:40:18.827618

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ac7be3f84e53'
down_revision: Union[str, Sequence[str], None] = '3d6b5e310e1e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "expa_lead_comments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("expa_person_id", sa.Text(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("creator_name", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["expa_person_id"],
            ["expa_leads.expa_person_id"],
            ondelete="CASCADE",
        ),
    )

    op.create_index(
        "ix_expa_lead_comments_expa_person_id",
        "expa_lead_comments",
        ["expa_person_id"],
    )



def downgrade() -> None:
    op.drop_index("ix_expa_lead_comments_expa_person_id")
    op.drop_table("expa_lead_comments")