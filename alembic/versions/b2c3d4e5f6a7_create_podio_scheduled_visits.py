"""create podio_scheduled_visits table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "podio_scheduled_visits",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("podio_item_id", sa.Integer(), nullable=False),
        sa.Column("company_name", sa.Text(), nullable=False),
        sa.Column("visit_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
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
    op.create_index("ix_podio_scheduled_visits_podio_item_id", "podio_scheduled_visits", ["podio_item_id"])
    op.create_unique_constraint("uq_podio_scheduled_visit_item", "podio_scheduled_visits", ["podio_item_id"])


def downgrade() -> None:
    op.drop_constraint("uq_podio_scheduled_visit_item", "podio_scheduled_visits", type_="unique")
    op.drop_index("ix_podio_scheduled_visits_podio_item_id", table_name="podio_scheduled_visits")
    op.drop_table("podio_scheduled_visits")
