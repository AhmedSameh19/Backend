"""create_members_and_assign_leads table

Revision ID: 4e69770c6f23
Revises: 4219ec4ce561
Create Date: 2026-01-14 05:42:32.509787
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4e69770c6f23"
down_revision: Union[str, Sequence[str], None] = "4219ec4ce561"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "members",
        sa.Column("member_id", sa.Text(), primary_key=True),
        sa.Column("full_name", sa.Text(), nullable=False),
    )

    # Columns already exist on `expa_leads` from the initial migration;
    # add the FK constraint only after `members` exists.
    op.create_foreign_key(
        "fk_expa_leads_assigned_member_id_members",
        "expa_leads",
        "members",
        ["assigned_member_id"],
        ["member_id"],
        ondelete="SET NULL",
    )

    op.create_index(
        "ix_expa_leads_assigned_member_id",
        "expa_leads",
        ["assigned_member_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_expa_leads_assigned_member_id", table_name="expa_leads")
    op.drop_constraint(
        "fk_expa_leads_assigned_member_id_members",
        "expa_leads",
        type_="foreignkey",
    )
    op.drop_table("members")
