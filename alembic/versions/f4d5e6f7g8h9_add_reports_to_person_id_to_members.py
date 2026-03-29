"""add reports_to_person_id to members

Revision ID: f4d5e6f7g8h9
Revises: f3c4d5e6f7a8
Create Date: 2026-03-30 01:50:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f4d5e6f7g8h9"
down_revision: Union[str, Sequence[str], None] = "f3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "members",
        sa.Column("reports_to_person_id", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("members", "reports_to_person_id")
