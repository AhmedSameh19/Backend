"""Update iCX realizations standards (add missing OGX fields)

Revision ID: f3c4d5e6f7a8
Revises: f2b3c4d5e6f7
Create Date: 2026-02-05

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f3c4d5e6f7a8"
down_revision: Union[str, Sequence[str], None] = "f2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "icx_realizations_standards",
        sa.Column("expa_person_id", sa.Text(), nullable=True),
    )

    op.add_column(
        "icx_realizations_standards",
        sa.Column("ips", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "icx_realizations_standards",
        sa.Column("ops", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "icx_realizations_standards",
        sa.Column("pgs", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "icx_realizations_standards",
        sa.Column(
            "first_day_of_work",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    op.create_index(
        "ix_icx_realizations_standards_expa_person_id",
        "icx_realizations_standards",
        ["expa_person_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_icx_realizations_standards_expa_person_id",
        table_name="icx_realizations_standards",
    )

    op.drop_column("icx_realizations_standards", "first_day_of_work")
    op.drop_column("icx_realizations_standards", "pgs")
    op.drop_column("icx_realizations_standards", "ops")
    op.drop_column("icx_realizations_standards", "ips")
    op.drop_column("icx_realizations_standards", "expa_person_id")
