"""Add IPS/OPS/PGS + first_day_of_work to ogx_standards

Revision ID: b5f2a0c9d3e1
Revises: c1d2e3f4a5b6
Create Date: 2026-02-01

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b5f2a0c9d3e1"
down_revision: Union[str, Sequence[str], None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ogx_standards",
        sa.Column("ips", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "ogx_standards",
        sa.Column("ops", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "ogx_standards",
        sa.Column("pgs", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "ogx_standards",
        sa.Column(
            "first_day_of_work",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("ogx_standards", "first_day_of_work")
    op.drop_column("ogx_standards", "pgs")
    op.drop_column("ogx_standards", "ops")
    op.drop_column("ogx_standards", "ips")
