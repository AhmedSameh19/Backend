"""update members table primary key to expa_person_id

Revision ID: 933dc07d1926
Revises: 7a57a8863ed7
Create Date: 2026-01-18 20:27:24.058182

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '933dc07d1926'
down_revision: Union[str, Sequence[str], None] = '7a57a8863ed7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
   

    # 3. Create index on expa_person_id
    op.create_index(
        index_name="ix_members_expa_person_id",
        table_name="members",
        columns=["expa_person_id"],
        unique=True
    )

def downgrade() -> None:
     # 1. Drop index
    op.drop_index(
        index_name="ix_members_expa_person_id",
        table_name="members"
    )

 
