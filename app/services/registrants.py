from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Athlete, Category, Club, Registration, WeighInStatus

# Hay menores: en público no se ve que alguien no entró en el primer pesaje mientras todavía puede entrar en el
# segundo. Se ve solo el resultado (habilitado o descalificado).
UNDECIDED_WEIGH_IN = (WeighInStatus.FAILED_FIRST, WeighInStatus.SECOND_ALLOWED)


def list_registrants(db: Session, category_id: int) -> list[dict]:
    """Inscritos de una categoría con solo datos públicos (nombre, club y estado del pesaje), ordenados por nombre.

    Nunca agregar acá CI, fecha de nacimiento ni kilos (tampoco los del pesaje): el resultado se
    muestra sin token y hay menores.
    """
    rows = db.execute(
        select(Athlete.id.label("athlete_id"), Athlete.name.label("name"), Club.name.label("club"), Registration.weigh_in_status)
        .join(Registration, Registration.athlete_id == Athlete.id)
        .join(Club, Athlete.club_id == Club.id)
        .where(Registration.category_id == category_id)
        .order_by(Athlete.name, Athlete.id)
    ).all()
    return [
        {**row._asdict(), "weigh_in_status": WeighInStatus.PENDING if row.weigh_in_status in UNDECIDED_WEIGH_IN else row.weigh_in_status}
        for row in rows
    ]


def close_weigh_in(db: Session, tournament_id: int) -> list[dict]:
    """Resuelve las inscripciones sin decidir al empezar el torneo (sin commit) y devuelve las que no se presentaron.

    `pending` pasa a `no_show`; `failed_first` y `second_allowed` pasan a `disqualified`.
    """
    registrations = db.scalars(
        select(Registration).join(Category).where(Category.tournament_id == tournament_id)
    ).all()
    not_weighed_in = []
    for registration in registrations:
        if registration.weigh_in_status == WeighInStatus.PENDING:
            registration.weigh_in_status = WeighInStatus.NO_SHOW
            not_weighed_in.append(
                {
                    "registration_id": registration.id,
                    "athlete_id": registration.athlete_id,
                    "name": registration.athlete.name,
                    "club": registration.athlete.club.name,
                    "category_id": registration.category_id,
                    "category_name": registration.category.name,
                }
            )
        elif registration.weigh_in_status in (WeighInStatus.FAILED_FIRST, WeighInStatus.SECOND_ALLOWED):
            registration.weigh_in_status = WeighInStatus.DISQUALIFIED
    return sorted(not_weighed_in, key=lambda row: (row["category_name"], row["name"], row["registration_id"]))
