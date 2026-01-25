"""Add unique constraint on (expa_person_id, opp_id) for realizations

Revision ID: e8c9d7f6a5b4
Revises: d7f0a3d8c1b2
Create Date: 2026-01-25

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e8c9d7f6a5b4"
down_revision: Union[str, Sequence[str], None] = "d7f0a3d8c1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_expa_lead_realizations_person_opp",
        "expa_lead_realizations",
        ["expa_person_id", "opp_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_expa_lead_realizations_person_opp",
        "expa_lead_realizations",
        type_="unique",
    )
