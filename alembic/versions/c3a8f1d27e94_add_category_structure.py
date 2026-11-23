"""add category structure

Revision ID: c3a8f1d27e94
Revises: b7e2d9c41f05
Create Date: 2026-11-16 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c3a8f1d27e94'
down_revision: Union[str, Sequence[str], None] = 'b7e2d9c41f05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def existing_enum(name: str, *values: str):
    """Enum que ya existe en Postgres (lo crearon migraciones anteriores): no se vuelve a crear."""
    return sa.Enum(*values, name=name).with_variant(postgresql.ENUM(*values, name=name, create_type=False), 'postgresql')


GRADE = existing_enum('grade', 'KUP_10', 'KUP_9', 'KUP_8', 'KUP_7', 'KUP_6', 'KUP_5', 'KUP_4', 'KUP_3', 'KUP_2', 'KUP_1', 'DAN')
GENDER = existing_enum('gender', 'MALE', 'FEMALE')


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'grade_groups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tournament_id', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=60), nullable=False),
        sa.Column('from_grade', GRADE, nullable=False),
        sa.ForeignKeyConstraint(['tournament_id'], ['tournaments.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'age_divisions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tournament_id', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=60), nullable=False),
        sa.Column('from_age', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['tournament_id'], ['tournaments.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'weight_limits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('age_division_id', sa.Integer(), nullable=False),
        sa.Column('gender', GENDER, nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('upper_limit', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['age_division_id'], ['age_divisions.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    # Columnas opcionales: las categorías que ya existen quedan como históricas (sin estructura).
    with op.batch_alter_table('categories') as batch:
        batch.add_column(sa.Column('grade_group_id', sa.Integer(), nullable=True))
        batch.add_column(sa.Column('age_division_id', sa.Integer(), nullable=True))
        batch.add_column(sa.Column('weight_position', sa.Integer(), nullable=True))
        batch.create_foreign_key('fk_categories_grade_group_id', 'grade_groups', ['grade_group_id'], ['id'])
        batch.create_foreign_key('fk_categories_age_division_id', 'age_divisions', ['age_division_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('categories') as batch:
        batch.drop_constraint('fk_categories_age_division_id', type_='foreignkey')
        batch.drop_constraint('fk_categories_grade_group_id', type_='foreignkey')
        batch.drop_column('weight_position')
        batch.drop_column('age_division_id')
        batch.drop_column('grade_group_id')
    op.drop_table('weight_limits')
    op.drop_table('age_divisions')
    op.drop_table('grade_groups')
