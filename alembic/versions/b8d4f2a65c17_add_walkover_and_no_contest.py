"""add walkover and no_contest match statuses

Revision ID: b8d4f2a65c17
Revises: a7c2e41d9b35
Create Date: 2026-11-27 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b8d4f2a65c17'
down_revision: Union[str, Sequence[str], None] = 'a7c2e41d9b35'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    if op.get_bind().dialect.name == 'postgresql':
        # SQLAlchemy guarda los NOMBRES del enum. ADD VALUE no puede correr dentro de una transacción.
        with op.get_context().autocommit_block():
            op.execute("ALTER TYPE matchstatus ADD VALUE IF NOT EXISTS 'WALKOVER'")
            op.execute("ALTER TYPE matchstatus ADD VALUE IF NOT EXISTS 'NO_CONTEST'")
    # En SQLite el enum es un VARCHAR sin CHECK: no hace falta nada.


def downgrade() -> None:
    """Downgrade schema."""
    # Los valores nuevos del enum no se quitan: Postgres no permite borrar un valor de un enum.
