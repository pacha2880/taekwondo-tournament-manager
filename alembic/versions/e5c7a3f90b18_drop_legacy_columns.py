"""drop legacy columns

Revision ID: e5c7a3f90b18
Revises: d9b4e6a1c207
Create Date: 2026-11-26 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e5c7a3f90b18'
down_revision: Union[str, Sequence[str], None] = 'd9b4e6a1c207'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def existing_enum(name: str, *values: str):
    """Enum que ya existe en Postgres (lo crearon migraciones anteriores): no se vuelve a crear."""
    return sa.Enum(*values, name=name).with_variant(postgresql.ENUM(*values, name=name, create_type=False), 'postgresql')


GRADE = existing_enum('grade', 'KUP_10', 'KUP_9', 'KUP_8', 'KUP_7', 'KUP_6', 'KUP_5', 'KUP_4', 'KUP_3', 'KUP_2', 'KUP_1', 'DAN')


def upgrade() -> None:
    """Upgrade schema."""
    # Las bases se vaciaron el 2026-11-26: ya no hay datos de versiones anteriores, así que se puede borrar.
    with op.batch_alter_table('athletes') as batch:
        batch.drop_column('belt_rank')
        batch.alter_column('grade', existing_type=GRADE, nullable=False)
    with op.batch_alter_table('categories') as batch:
        batch.drop_column('belt_group')
        batch.alter_column('age_division_id', existing_type=sa.Integer(), nullable=False)
    if op.get_bind().dialect.name == 'postgresql':
        op.execute('DROP TYPE beltgroup')


def downgrade() -> None:
    """Downgrade schema."""
    belt_group = sa.Enum('COLOR', 'BLACK', name='beltgroup')
    belt_group.create(op.get_bind(), checkfirst=True)
    with op.batch_alter_table('categories') as batch:
        batch.alter_column('age_division_id', existing_type=sa.Integer(), nullable=True)
        batch.add_column(sa.Column('belt_group', belt_group, nullable=False, server_default='COLOR'))
    with op.batch_alter_table('athletes') as batch:
        batch.alter_column('grade', existing_type=GRADE, nullable=True)
        batch.add_column(sa.Column('belt_rank', sa.String(length=60), nullable=False, server_default=''))
