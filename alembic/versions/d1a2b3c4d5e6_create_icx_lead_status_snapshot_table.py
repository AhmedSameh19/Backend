"""Create iCX lead status snapshot table

Revision ID: d1a2b3c4d5e6
Revises: c9d8e7f6a5b4
Create Date: 2026-02-05

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "c9d8e7f6a5b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "expa_icx_lead_status_snapshot",
        sa.Column(
            "application_id",
            sa.Text(),
            sa.ForeignKey("expa_icx_leads.application_id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("contacted", sa.Text(), nullable=True),
        sa.Column("interviewed", sa.Text(), nullable=True),
        sa.Column("expectations_email_status", sa.Text(), nullable=True),
        sa.Column("out_of_process", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
       
    )
    op.create_index(
        "ix_expa_icx_lead_status_snapshot_application_id",
        "expa_icx_lead_status_snapshot",
        ["application_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_expa_icx_lead_status_snapshot_application_id", table_name="expa_icx_lead_status_snapshot")
    op.drop_table("expa_icx_lead_status_snapshot")
