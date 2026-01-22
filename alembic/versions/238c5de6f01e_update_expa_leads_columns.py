"""update expa_leads columns

Revision ID: 238c5de6f01e
Revises: 4e69770c6f23
Create Date: 2026-01-14 16:06:47.825411

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '238c5de6f01e'
down_revision: Union[str, Sequence[str], None] = '4e69770c6f23'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Fix wrong column types (your runtime error shows home_lc_name is INTEGER in DB)
    op.alter_column(
        "expa_leads",
        "home_lc_name",
        existing_type=sa.Integer(),
        type_=sa.Text(),
        postgresql_using="home_lc_name::text",
        existing_nullable=False,
    )
    op.alter_column(
        "expa_leads",
        "home_mc_name",
        existing_type=sa.Integer(),
        type_=sa.Text(),
        postgresql_using="home_mc_name::text",
        existing_nullable=False,
    )




def downgrade() -> None:
    op.alter_column(
        "expa_leads",
        "home_mc_name",
        existing_type=sa.Text(),
        type_=sa.Integer(),
        postgresql_using="home_mc_name::integer",
        existing_nullable=False,
    )
    op.alter_column(
        "expa_leads",
        "home_lc_name",
        existing_type=sa.Text(),
        type_=sa.Integer(),
        postgresql_using="home_lc_name::integer",
        existing_nullable=False,
    )
