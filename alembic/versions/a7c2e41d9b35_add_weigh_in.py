"""add weigh-in status and weights to registrations

Revision ID: a7c2e41d9b35
Revises: f1a9d3b72c60
Create Date: 2026-11-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7c2e41d9b35'
down_revision: Union[str, Sequence[str], None] = 'f1a9d3b72c60'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# SQLAlchemy guarda los NOMBRES del enum (en mayúscula).
weigh_in_status = sa.Enum(
    'PENDING', 'FAILED_FIRST', 'SECOND_ALLOWED', 'CLEARED', 'DISQUALIFIED', 'NO_SHOW', 'NOT_REQUIRED',
    name='weighinstatus',
)


def upgrade() -> None:
    """Upgrade schema."""
    weigh_in_status.create(op.get_bind(), checkfirst=True)
    with op.batch_alter_table('registrations') as batch:
        batch.add_column(sa.Column('weigh_in_status', weigh_in_status, nullable=False, server_default='PENDING'))
        batch.add_column(sa.Column('first_weight_kg', sa.Float(), nullable=True))
        batch.add_column(sa.Column('second_weight_kg', sa.Float(), nullable=True))
    # Festival (la primera división de edad, position 0) no se pesa.
    op.execute(
        "UPDATE registrations SET weigh_in_status = 'NOT_REQUIRED' WHERE category_id IN ("
        "SELECT c.id FROM categories c JOIN age_divisions a ON c.age_division_id = a.id WHERE a.position = 0)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('registrations') as batch:
        batch.drop_column('second_weight_kg')
        batch.drop_column('first_weight_kg')
        batch.drop_column('weigh_in_status')
    weigh_in_status.drop(op.get_bind(), checkfirst=True)
