"""add status and visit_date to market research tables if missing

Revision ID: a1b2c3d4e5f6
Revises: f2a3b4c5d6e7
Create Date: 2026-02-19

Use ADD COLUMN IF NOT EXISTS so this is safe when the columns were never
added (e.g. migration e1f2a3b4c5d6 was marked applied but not run).
"""
from typing import Sequence, Union

from alembic import op


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f2a3b4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL: ADD COLUMN IF NOT EXISTS (safe when columns already exist)
    op.execute("""
        ALTER TABLE igv_market_research
        ADD COLUMN IF NOT EXISTS status VARCHAR(30) NOT NULL DEFAULT 'lead'
    """)
    op.execute("""
        ALTER TABLE igv_market_research
        ADD COLUMN IF NOT EXISTS visit_date TIMESTAMP WITH TIME ZONE
    """)
    op.execute("""
        ALTER TABLE b2b_market_research
        ADD COLUMN IF NOT EXISTS status VARCHAR(30) NOT NULL DEFAULT 'lead'
    """)
    op.execute("""
        ALTER TABLE b2b_market_research
        ADD COLUMN IF NOT EXISTS visit_date TIMESTAMP WITH TIME ZONE
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE igv_market_research DROP COLUMN IF EXISTS visit_date")
    op.execute("ALTER TABLE igv_market_research DROP COLUMN IF EXISTS status")
    op.execute("ALTER TABLE b2b_market_research DROP COLUMN IF EXISTS visit_date")
    op.execute("ALTER TABLE b2b_market_research DROP COLUMN IF EXISTS status")
