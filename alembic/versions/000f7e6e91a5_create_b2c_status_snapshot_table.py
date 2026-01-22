"""create b2c status_snapshot_table

Revision ID: 000f7e6e91a5
Revises: b400251ef8a3
Create Date: 2026-01-20 17:35:10.179164

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '000f7e6e91a5'
down_revision: Union[str, Sequence[str], None] = 'b400251ef8a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "b2c_lead_status_snapshot",
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
    op.create_index(
        "ix_b2c_lead_status_snapshot_expa_person_id",
        "b2c_lead_status_snapshot",
        ["expa_person_id"],
    )

def downgrade() -> None:
    op.drop_index("ix_b2c_lead_status_snapshot_expa_person_id", table_name="b2c_lead_status_snapshot")
    op.drop_table("b2c_lead_status_snapshot")
