"""create market research tables

Revision ID: c8f3e9a1b2d4
Revises: a9b12d66df4d
Create Date: 2026-01-21 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8f3e9a1b2d4'
down_revision: Union[str, Sequence[str], None] = 'a9b12d66df4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create IGV and B2B market research tables"""
    
    # Create IGV Market Research table
    op.create_table(
        "igv_market_research",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("podio_id", sa.Integer(), nullable=True),
        sa.Column("company_name", sa.Text(), nullable=True),
        sa.Column("product", sa.Text(), nullable=True),
        sa.Column("sub_project", sa.Text(), nullable=True),
        sa.Column("home_lc_id", sa.Integer(), nullable=False),
        sa.Column("socialmedia_acc", sa.Text(), nullable=True),
        sa.Column("website", sa.Text(), nullable=True),
        sa.Column("phone_number", sa.Text(), nullable=True),
        sa.Column("acc_submitted_by", sa.Text(), nullable=True),
        sa.Column("industry", sa.Text(), nullable=True),
        sa.Column("company_employee_size", sa.Text(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("person_name", sa.Text(), nullable=True),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("position", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
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
    
    # Create indexes for IGV table
    op.create_index(
        "idx_igv_market_research_home_lc_id",
        "igv_market_research",
        ["home_lc_id"],
    )
    op.create_index(
        "idx_igv_market_research_home_lc_created_at",
        "igv_market_research",
        ["home_lc_id", "created_at"],
    )
    op.create_index(
        "ix_igv_market_research_podio_id",
        "igv_market_research",
        ["podio_id"],
    )
    
    # Create B2B Market Research table
    op.create_table(
        "b2b_market_research",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("podio_id", sa.Integer(), nullable=True),
        sa.Column("company_name", sa.Text(), nullable=True),
        sa.Column("product", sa.Text(), nullable=True),
        sa.Column("reason_for_approach", sa.Text(), nullable=True),
        sa.Column("home_lc_id", sa.Integer(), nullable=False),
        sa.Column("socialmedia_acc", sa.Text(), nullable=True),
        sa.Column("website", sa.Text(), nullable=True),
        sa.Column("phone_number", sa.Text(), nullable=True),
        sa.Column("acc_submitted_by", sa.Text(), nullable=True),
        sa.Column("industry", sa.Text(), nullable=True),
        sa.Column("company_employee_size", sa.Text(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("person_name", sa.Text(), nullable=True),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("position", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
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
    
    # Create indexes for B2B table
    op.create_index(
        "idx_b2b_market_research_home_lc_id",
        "b2b_market_research",
        ["home_lc_id"],
    )
    op.create_index(
        "idx_b2b_market_research_home_lc_created_at",
        "b2b_market_research",
        ["home_lc_id", "created_at"],
    )
    op.create_index(
        "ix_b2b_market_research_podio_id",
        "b2b_market_research",
        ["podio_id"],
    )


def downgrade() -> None:
    """Drop market research tables"""
    # Drop indexes
    op.drop_index("ix_b2b_market_research_podio_id", table_name="b2b_market_research")
    op.drop_index("idx_b2b_market_research_home_lc_created_at", table_name="b2b_market_research")
    op.drop_index("idx_b2b_market_research_home_lc_id", table_name="b2b_market_research")
    op.drop_index("ix_igv_market_research_podio_id", table_name="igv_market_research")
    op.drop_index("idx_igv_market_research_home_lc_created_at", table_name="igv_market_research")
    op.drop_index("idx_igv_market_research_home_lc_id", table_name="igv_market_research")
    
    # Drop tables
    op.drop_table("b2b_market_research")
    op.drop_table("igv_market_research")

