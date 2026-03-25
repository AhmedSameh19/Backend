"""make podio_scheduled_visits.podio_item_id bigint

Revision ID: c1d2e3f4g5h6
Revises: b2c3d4e5f6a7
Create Date: 2026-03-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c1d2e3f4g5h6"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
  op.alter_column(
      "podio_scheduled_visits",
      "podio_item_id",
      existing_type=sa.Integer(),
      type_=sa.BigInteger(),
      existing_nullable=False,
  )


def downgrade() -> None:
  op.alter_column(
      "podio_scheduled_visits",
      "podio_item_id",
      existing_type=sa.BigInteger(),
      type_=sa.Integer(),
      existing_nullable=False,
  )

