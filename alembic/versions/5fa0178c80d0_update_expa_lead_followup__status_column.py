"""update expa_lead_followup_ status_column

Revision ID: 5fa0178c80d0
Revises: 6da9e63f510e
Create Date: 2026-01-15 15:37:07.254720

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5fa0178c80d0'
down_revision: Union[str, Sequence[str], None] = '6da9e63f510e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
    "expa_lead_follow_ups",
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
    )

    op.execute(
        sa.text(
            """
        DO $$
        BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_expa_lead_follow_ups_status_valid') THEN
            ALTER TABLE expa_lead_follow_ups
            ADD CONSTRAINT ck_expa_lead_follow_ups_status_valid
            CHECK (status IN ('pending', 'completed'));
        END IF;

        END $$;
        """
        )
    )



def downgrade():
    op.execute("""
    ALTER TABLE expa_lead_follow_ups
    DROP CONSTRAINT IF EXISTS ck_expa_lead_follow_ups_status_valid;
    """)

    op.drop_column("expa_lead_follow_ups", "status")
