"""create b2c comments table

Revision ID: b400251ef8a3
Revises: 933dc07d1926
Create Date: 2026-01-20 16:59:33.750067

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b400251ef8a3'
down_revision: Union[str, Sequence[str], None] = '933dc07d1926'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "b2c_comments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
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
        "ix_b2c_comments_expa_person_id",
        "b2c_comments",
        ["expa_person_id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_b2c_comments_expa_person_id", table_name="b2c_comments")
    op.drop_table("b2c_comments")
