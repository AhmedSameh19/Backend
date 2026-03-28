"""add_email_column_to_members_table

Revision ID: 44c7847383b8
Revises: f3c4d5e6f7a8
Create Date: 2026-02-18 19:18:37.395310

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '44c7847383b8'
down_revision: Union[str, Sequence[str], None] = 'f3c4d5e6f7a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("members", sa.Column("email", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("members", "email")
