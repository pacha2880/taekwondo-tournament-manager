"""add grade to athletes

Revision ID: b7e2d9c41f05
Revises: a4f1c2e8b7d3
Create Date: 2026-11-13 10:00:00.000000

"""
import random
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7e2d9c41f05'
down_revision: Union[str, Sequence[str], None] = 'a4f1c2e8b7d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Nombres de Grade (app/models.py), que es lo que guarda el Enum de SQLAlchemy.
GRADES = ['KUP_10', 'KUP_9', 'KUP_8', 'KUP_7', 'KUP_6', 'KUP_5', 'KUP_4', 'KUP_3', 'KUP_2', 'KUP_1', 'DAN']
grade_enum = sa.Enum(*GRADES, name='grade')


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    grade_enum.create(bind, checkfirst=True)
    op.add_column('athletes', sa.Column('grade', grade_enum, nullable=True))

    # Los atletas que ya existen no tienen un grado comparable (belt_rank era texto libre): se les asigna uno al
    # azar, decidido con el usuario. Su belt_rank no se toca: si se vuelve a la 0.6.0, se sigue viendo el original.
    athletes = sa.table('athletes', sa.column('id', sa.Integer), sa.column('grade', grade_enum))
    for (athlete_id,) in bind.execute(sa.select(athletes.c.id)).all():
        bind.execute(athletes.update().where(athletes.c.id == athlete_id).values(grade=random.choice(GRADES)))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('athletes', 'grade')
    grade_enum.drop(op.get_bind(), checkfirst=True)
