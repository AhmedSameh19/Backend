"""Create iCX lead comments and follow-ups tables

Revision ID: c9d8e7f6a5b4
Revises: f1c2d3e4a5b6
Create Date: 2026-02-05

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c9d8e7f6a5b4"
down_revision: Union[str, Sequence[str], None] = "f1c2d3e4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "expa_icx_lead_comments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "application_id",
            sa.Text(),
            sa.ForeignKey("expa_icx_leads.application_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("creator_name", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_expa_icx_lead_comments_application_id",
        "expa_icx_lead_comments",
        ["application_id"],
    )

    op.create_table(
        "expa_icx_lead_follow_ups",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column(
            "application_id",
            sa.Text(),
            sa.ForeignKey("expa_icx_leads.application_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("follow_up_text", sa.Text(), nullable=False),
        sa.Column("follow_up_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Text(), server_default="pending", nullable=False),
        sa.Column(
            "created_by_member_id",
            sa.Text(),
            sa.ForeignKey("members.expa_person_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_by_member_name", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "follow_up_at > now()",
            name="ck_expa_icx_lead_follow_ups_follow_up_at_future",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'completed')",
            name="ck_expa_icx_lead_follow_ups_status_valid",
        ),
    )
    op.create_index(
        "ix_expa_icx_lead_follow_ups_application_id",
        "expa_icx_lead_follow_ups",
        ["application_id"],
    )
    op.create_index(
        "ix_expa_icx_lead_follow_ups_created_by_member_id",
        "expa_icx_lead_follow_ups",
        ["created_by_member_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_expa_icx_lead_follow_ups_created_by_member_id", table_name="expa_icx_lead_follow_ups")
    op.drop_index("ix_expa_icx_lead_follow_ups_application_id", table_name="expa_icx_lead_follow_ups")
    op.drop_table("expa_icx_lead_follow_ups")

    op.drop_index("ix_expa_icx_lead_comments_application_id", table_name="expa_icx_lead_comments")
    op.drop_table("expa_icx_lead_comments")
