"""add status and visit_date to market research

Revision ID: e1f2a3b4c5d6
Revises: c8f3e9a1b2d4
Create Date: 2026-02-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "c8f3e9a1b2d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # IGV market research: add status and visit_date
    op.add_column(
        "igv_market_research",
        sa.Column("status", sa.String(30), nullable=False, server_default="lead"),
    )
    op.add_column(
        "igv_market_research",
        sa.Column("visit_date", sa.DateTime(timezone=True), nullable=True),
    )

    # B2B market research: add status and visit_date
    op.add_column(
        "b2b_market_research",
        sa.Column("status", sa.String(30), nullable=False, server_default="lead"),
    )
    op.add_column(
        "b2b_market_research",
        sa.Column("visit_date", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("igv_market_research", "visit_date")
    op.drop_column("igv_market_research", "status")
    op.drop_column("b2b_market_research", "visit_date")
    op.drop_column("b2b_market_research", "status")
