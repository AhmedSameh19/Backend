"""drop unique constraint on expa_person_id in members

Revision ID: f6e7f8g9h0i1
Revises: f5e6f7g8h9i0
Create Date: 2026-03-30 02:15:00

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f6e7f8g9h0i1"
down_revision: Union[str, Sequence[str], None] = "f5e6f7g8h9i0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop unique constraint on members.expa_person_id if it exists
    op.execute(
        "ALTER TABLE members DROP CONSTRAINT IF EXISTS members_expa_person_id_key"
    )


def downgrade() -> None:
    # Re-add unique constraint
    op.create_unique_constraint(
        "members_expa_person_id_key",
        "members",
        ["expa_person_id"]
    )
