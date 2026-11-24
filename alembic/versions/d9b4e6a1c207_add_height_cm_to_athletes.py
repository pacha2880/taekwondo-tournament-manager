"""add height_cm to athletes

Revision ID: d9b4e6a1c207
Revises: c3a8f1d27e94
Create Date: 2026-11-23 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd9b4e6a1c207'
down_revision: Union[str, Sequence[str], None] = 'c3a8f1d27e94'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('athletes', sa.Column('height_cm', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('athletes', 'height_cm')
