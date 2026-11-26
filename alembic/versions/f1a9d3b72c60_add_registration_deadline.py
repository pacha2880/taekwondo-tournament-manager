"""add registration deadline and tournament statuses

Revision ID: f1a9d3b72c60
Revises: e5c7a3f90b18
Create Date: 2026-11-26 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a9d3b72c60'
down_revision: Union[str, Sequence[str], None] = 'e5c7a3f90b18'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    if op.get_bind().dialect.name == 'postgresql':
        # SQLAlchemy guarda los NOMBRES del enum. ADD VALUE no puede correr dentro de una transacción.
        with op.get_context().autocommit_block():
            op.execute("ALTER TYPE tournamentstatus ADD VALUE IF NOT EXISTS 'REGISTRATION_OPEN'")
            op.execute("ALTER TYPE tournamentstatus ADD VALUE IF NOT EXISTS 'WEIGH_IN'")
    op.add_column('tournaments', sa.Column('registration_deadline', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Los valores nuevos del enum no se quitan: Postgres no permite borrar un valor de un enum.
    op.drop_column('tournaments', 'registration_deadline')
