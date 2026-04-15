"""create market research snapshot and sync state tables

Revision ID: g1h2i3j4k5l6
Revises: f5e6f7g8h9i0
Create Date: 2026-04-15 20:15:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "g1h2i3j4k5l6"
down_revision: Union[str, Sequence[str], None] = "f5e6f7g8h9i0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "market_research_snapshot",
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("company_name", sa.Text(), nullable=True),
        sa.Column("product", sa.Text(), nullable=True),
        sa.Column("sub_project_igv", sa.Text(), nullable=True),
        sa.Column("local_committee", sa.Text(), nullable=True),
        sa.Column("local_committee_id", sa.Integer(), nullable=True),
        sa.Column("type_of_pr_deal", sa.Text(), nullable=True),
        sa.Column("reason_of_approach", sa.Text(), nullable=True),
        sa.Column("industry", sa.Text(), nullable=True),
        sa.Column("size", sa.Text(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("website", sa.Text(), nullable=True),
        sa.Column("contact_person_name", sa.Text(), nullable=True),
        sa.Column("contact_position", sa.Text(), nullable=True),
        sa.Column("contact_email", sa.Text(), nullable=True),
        sa.Column("contact_phone", sa.Text(), nullable=True),
        sa.Column("contact_linkedin", sa.Text(), nullable=True),
        sa.Column("podio_last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("item_id"),
    )
    op.create_index("ix_market_research_snapshot_company_name", "market_research_snapshot", ["company_name"])
    op.create_index("ix_market_research_snapshot_local_committee_id", "market_research_snapshot", ["local_committee_id"])
    op.create_index("ix_market_research_snapshot_podio_last_seen_at", "market_research_snapshot", ["podio_last_seen_at"])
    op.create_index("ix_market_research_snapshot_synced_at", "market_research_snapshot", ["synced_at"])

    op.create_table(
        "market_research_sync_state",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("last_synced_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        "INSERT INTO market_research_sync_state (id, last_synced_items) VALUES (1, 0) ON CONFLICT (id) DO NOTHING"
    )


def downgrade() -> None:
    op.drop_table("market_research_sync_state")
    op.drop_index("ix_market_research_snapshot_synced_at", table_name="market_research_snapshot")
    op.drop_index("ix_market_research_snapshot_podio_last_seen_at", table_name="market_research_snapshot")
    op.drop_index("ix_market_research_snapshot_local_committee_id", table_name="market_research_snapshot")
    op.drop_index("ix_market_research_snapshot_company_name", table_name="market_research_snapshot")
    op.drop_table("market_research_snapshot")
