"""Add assigned member fields to realizations

Revision ID: d7f0a3d8c1b2
Revises: 2c7f0e6c3f41
Create Date: 2026-01-22

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d7f0a3d8c1b2"
down_revision: Union[str, Sequence[str], None] = "2c7f0e6c3f41"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "expa_lead_realizations",
        sa.Column("assigned_member_id", sa.Text(), nullable=True),
    )
    op.add_column(
        "expa_lead_realizations",
        sa.Column("assigned_member_name", sa.Text(), nullable=True),
    )

    op.create_index(
        "ix_expa_lead_realizations_assigned_member_id",
        "expa_lead_realizations",
        ["assigned_member_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_expa_lead_realizations_assigned_member_id",
        "expa_lead_realizations",
        "members",
        ["assigned_member_id"],
        ["expa_person_id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_expa_lead_realizations_assigned_member_id",
        "expa_lead_realizations",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_expa_lead_realizations_assigned_member_id",
        table_name="expa_lead_realizations",
    )
    op.drop_column("expa_lead_realizations", "assigned_member_name")
    op.drop_column("expa_lead_realizations", "assigned_member_id")
