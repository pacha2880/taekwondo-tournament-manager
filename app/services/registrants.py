from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Athlete, Club, Registration


def list_registrants(db: Session, category_id: int):
    """Inscritos de una categoría con solo datos públicos (nombre y club), ordenados por nombre.

    Nunca agregar acá CI, fecha de nacimiento ni peso: el resultado se muestra sin token y hay menores.
    """
    return db.execute(
        select(Athlete.id.label("athlete_id"), Athlete.name.label("name"), Club.name.label("club"))
        .join(Registration, Registration.athlete_id == Athlete.id)
        .join(Club, Athlete.club_id == Club.id)
        .where(Registration.category_id == category_id)
        .order_by(Athlete.name, Athlete.id)
    ).all()
