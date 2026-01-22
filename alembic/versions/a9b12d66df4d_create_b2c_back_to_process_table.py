"""create b2c_back_to_process Table

Revision ID: a9b12d66df4d
Revises: 000f7e6e91a5
Create Date: 2026-01-20 18:15:13.900664

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9b12d66df4d'
down_revision: Union[str, Sequence[str], None] = '000f7e6e91a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "b2c_back_to_process",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("expa_person_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("expa_status", sa.Text(), nullable=True),
        sa.Column("selected_programmes", sa.Text(), nullable=True, server_default="GV"),
        sa.Column("home_lc_name", sa.Text(), nullable=False),
        sa.Column("home_mc_name", sa.Text(), nullable=False),
        sa.Column("home_lc_id", sa.Integer(), nullable=False),
        sa.Column("home_mc_id", sa.Integer(), nullable=False),
        sa.Column(
            "inserted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["expa_person_id"],
            ["expa_leads.expa_person_id"],
            ondelete="CASCADE",
        ),
    )

    op.create_index(
        "ix_b2c_back_to_process_home_lc_id_inserted_at",
        "b2c_back_to_process",
        ["home_lc_id","inserted_at"],
    )
    op.create_index(
        "ix_b2c_back_to_process_expa_person_id",
        "b2c_back_to_process",
        ["expa_person_id"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_b2c_back_to_process_home_lc_id_inserted_at",
        table_name="b2c_back_to_process",
    )
    op.drop_index("ix_b2c_back_to_process_expa_person_id", table_name="b2c_back_to_process")
    op.drop_table("b2c_back_to_process")
