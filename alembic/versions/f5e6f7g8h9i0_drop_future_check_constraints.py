"""drop future check constraints from follow ups

Revision ID: f5e6f7g8h9i0
Revises: 616e7ccfdef5
Create Date: 2026-03-30 02:10:00

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f5e6f7g8h9i0"
down_revision: Union[str, Sequence[str], None] = "616e7ccfdef5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop OGX check constraint
    op.drop_constraint(
        "ck_expa_lead_follow_ups_follow_up_at_future",
        "expa_lead_follow_ups",
        type_="check",
    )
    # Drop ICX check constraint
    op.drop_constraint(
        "ck_expa_icx_lead_follow_ups_follow_up_at_future",
        "expa_icx_lead_follow_ups",
        type_="check",
    )


def downgrade() -> None:
    # Re-add OGX check constraint
    op.create_check_constraint(
        "ck_expa_lead_follow_ups_follow_up_at_future",
        "expa_lead_follow_ups",
        "follow_up_at > now()",
    )
    # Re-add ICX check constraint
    op.create_check_constraint(
        "ck_expa_icx_lead_follow_ups_follow_up_at_future",
        "expa_icx_lead_follow_ups",
        "follow_up_at > now()",
    )
