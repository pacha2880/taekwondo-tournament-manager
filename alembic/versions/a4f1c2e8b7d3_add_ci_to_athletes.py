"""add ci to athletes

Revision ID: a4f1c2e8b7d3
Revises: d63c6c668bd4
Create Date: 2026-10-23 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4f1c2e8b7d3'
down_revision: Union[str, Sequence[str], None] = 'd63c6c668bd4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('athletes', sa.Column('ci', sa.String(length=12), nullable=True))
    op.create_index(op.f('ix_athletes_ci'), 'athletes', ['ci'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_athletes_ci'), table_name='athletes')
    op.drop_column('athletes', 'ci')
