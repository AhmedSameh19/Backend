"""update members table adding all other fields

Revision ID: b0e31a323dbc
Revises: 5fa0178c80d0
Create Date: 2026-01-15 16:22:12.610627

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b0e31a323dbc'
down_revision: Union[str, Sequence[str], None] = '5fa0178c80d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns
    op.add_column(
        "members",
        sa.Column("role", sa.Text(), nullable=False),
    )
    op.add_column(
        "members",
        sa.Column("function", sa.Text(), nullable=True),
    )
    op.add_column(
        "members",
        sa.Column(
            "reports_to_member_id",
            sa.Text(),
            sa.ForeignKey("members.member_id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "members",
        sa.Column("home_lc_id", sa.Text(), nullable=False),
    )
    op.add_column(
        "members",
        sa.Column(
            "home_mc_id",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'1609'"),
        ),
    )
    op.add_column(
        "members",
        sa.Column("home_lc_name", sa.Text(), nullable=True),
    )
    op.add_column(
        "members",
        sa.Column(
            "home_mc_name",
            sa.Text(),
            nullable=True,
            server_default=sa.text("'MC Egypt'"),
        ),
    )

    # Index for FK lookups
    op.create_index(
        "ix_members_reports_to_member_id",
        "members",
        ["reports_to_member_id"],
    )

    # 🔥 Composite index for filtering (explained below)
    op.create_index(
        "ix_members_function_home_lc_id",
        "members",
        ["function", "home_lc_id"],
    )

def downgrade() -> None:
    op.drop_index("ix_members_function_home_lc_id", table_name="members")
    op.drop_index("ix_members_reports_to_member_id", table_name="members")

    op.drop_column("members", "home_mc_name")
    op.drop_column("members", "home_lc_name")
    op.drop_column("members", "home_mc_id")
    op.drop_column("members", "home_lc_id")
    op.drop_column("members", "reports_to_member_id")
    op.drop_column("members", "function")
    op.drop_column("members", "role")