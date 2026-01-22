"""update members table add global expa ID

Revision ID: 7a57a8863ed7
Revises: b0e31a323dbc
Create Date: 2026-01-15 19:29:12.298193

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a57a8863ed7'
down_revision: Union[str, Sequence[str], None] = 'b0e31a323dbc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'members',
        sa.Column('expa_person_id', sa.Text(), nullable=True, unique=True)
    )
    


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('members', 'expa_person_id')
