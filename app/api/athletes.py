from types import SimpleNamespace
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.clubs import get_club_or_404
from app.api.tournaments import get_tournament_or_404
from app.api_docs import TAG_ATHLETES, errors
from app.auth import ADMIN_ONLY
from app.database import get_db
from app.models import Athlete, Category, TournamentStatus
from app.schemas import AthleteCreate, AthleteRead, AthleteUpdate, CategoryRead, Int4
from app.services.athlete_search import search_athletes
from app.services.eligibility import category_mismatch

router = APIRouter(prefix="/api/v1/athletes", tags=[TAG_ATHLETES])


def get_athlete_or_404(db: Session, athlete_id: int) -> Athlete:
    athlete = db.get(Athlete, athlete_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="Atleta no encontrado")
    return athlete


def _ensure_ci_is_free(db: Session, ci: str | None, athlete_id: int | None = None) -> None:
    if not ci:
        return
    query = select(Athlete).where(Athlete.ci == ci)
    if athlete_id is not None:
        query = query.where(Athlete.id != athlete_id)
    if db.scalar(query):
        raise HTTPException(status_code=409, detail="Ya existe un atleta con ese CI")


FIELDS_THAT_AFFECT_CATEGORY = ("gender", "weight_kg", "grade", "birth_date")


def _withdraw_registrations_that_no_longer_fit(db: Session, athlete: Athlete, changes: dict, confirmed: bool):
    proposed = SimpleNamespace(
        **{field: changes.get(field, getattr(athlete, field)) for field in FIELDS_THAT_AFFECT_CATEGORY}
    )
    if all(getattr(proposed, field) == getattr(athlete, field) for field in FIELDS_THAT_AFFECT_CATEGORY):
        return

    for registration in athlete.registrations:
        tournament = registration.category.tournament
        if tournament.status in (TournamentStatus.WEIGH_IN, TournamentStatus.IN_PROGRESS) and category_mismatch(proposed, registration.category):
            raise HTTPException(
                status_code=409,
                detail="No se puede hacer este cambio: el atleta dejaría de encajar en su categoría "
                f"del torneo «{tournament.name}»",
            )

    no_longer_fit = [
        registration
        for registration in athlete.registrations
        if registration.category.tournament.status == TournamentStatus.REGISTRATION_OPEN
        and category_mismatch(proposed, registration.category)
    ]
    if not no_longer_fit:
        return
    if not confirmed:
        names = ", ".join(f"{r.category.name} ({r.category.tournament.name})" for r in no_longer_fit)
        raise HTTPException(
            status_code=409,
            detail=f"Este cambio retira al atleta de: {names}. Hay que confirmar el retiro para continuar",
        )
    for registration in no_longer_fit:
        db.delete(registration)


@router.post(
    "",
    response_model=AthleteRead,
    status_code=201,
    dependencies=ADMIN_ONLY,
    summary="Crear un atleta",
    description=(
        "Crea un atleta asignado a un club que ya existe. El CI es opcional; si se informa, no puede "
        "repetirse y, si no cumple el formato, responde 422. Requiere token."
    ),
    responses=errors({404: "El club no existe.", 409: "Ya existe un atleta con ese CI."}, auth=True),
)
def create_athlete(payload: AthleteCreate, db: Session = Depends(get_db)):
    get_club_or_404(db, payload.club_id)
    _ensure_ci_is_free(db, payload.ci)
    athlete = Athlete(**payload.model_dump())
    db.add(athlete)
    db.commit()
    db.refresh(athlete)
    return athlete


@router.get(
    "",
    response_model=list[AthleteRead],
    dependencies=ADMIN_ONLY,
    summary="Listar atletas",
    description=(
        "Devuelve los atletas con su club, ordenados por nombre. Con `q` solo devuelve los que contienen ese "
        "texto en el nombre o en el CI, sin distinguir mayúsculas ni tildes (`perez` encuentra a `Pérez`). "
        "Incluye fecha de nacimiento y peso, por eso requiere token."
    ),
    responses=errors(auth=True),
)
def list_athletes(
    q: str | None = Query(
        default=None, description="Texto a buscar en el nombre o en el CI. Si se omite o está vacío, devuelve todos."
    ),
    db: Session = Depends(get_db),
):
    return search_athletes(db, q)


@router.get(
    "/{athlete_id}",
    response_model=AthleteRead,
    dependencies=ADMIN_ONLY,
    summary="Obtener un atleta",
    description="Devuelve un atleta por su id. Incluye fecha de nacimiento y peso, por eso requiere token.",
    responses=errors({404: "El atleta no existe."}, auth=True),
)
def get_athlete(athlete_id: Int4, db: Session = Depends(get_db)):
    return get_athlete_or_404(db, athlete_id)


@router.get(
    "/{athlete_id}/eligible-categories",
    response_model=list[CategoryRead],
    dependencies=ADMIN_ONLY,
    summary="Listar las categorías en las que encaja un atleta",
    description="Devuelve, ordenadas por id, las categorías del torneo `tournament_id` que cumplen la regla de "
    "`POST /registrations` para este atleta (género, peso, edad y grupo de grado). Es la consulta inversa de "
    "`GET /categories/{id}/eligible-athletes`; la usará la inscripción pública. Con la estructura de la Copa Diamante "
    "un atleta normalmente encaja en exactamente una categoría. No mira si el atleta ya está inscrito ni el estado del "
    "torneo. Requiere token.",
    responses=errors({404: "El atleta o el torneo no existe."}, auth=True),
)
def list_eligible_categories(
    athlete_id: Int4,
    tournament_id: Annotated[Int4, Query(description="Torneo en el que se buscan las categorías.")],
    db: Session = Depends(get_db),
):
    athlete = get_athlete_or_404(db, athlete_id)
    get_tournament_or_404(db, tournament_id)
    categories = db.scalars(
        select(Category)
        .options(selectinload(Category.bracket), selectinload(Category.grade_group))
        .where(Category.tournament_id == tournament_id)
        .order_by(Category.id)
    )
    return [c for c in categories if category_mismatch(athlete, c) is None]


@router.patch(
    "/{athlete_id}",
    response_model=AthleteRead,
    dependencies=ADMIN_ONLY,
    summary="Actualizar un atleta",
    description=(
        "Modifica solo los campos que se envían (un `null` en un campo que no sea `ci` ni `height_cm` se ignora). `ci` con "
        "`null` o texto vacío lo borra; `height_cm` con `null` también. Si el cambio de **género, peso, grado o fecha de nacimiento** afecta inscripciones: en un torneo "
        "en `weigh_in` o `in_progress` se rechaza (409) si el atleta deja de cumplir las reglas de su categoría; en un torneo en "
        "`registration_open`, si el atleta deja de cumplir las reglas de la "
        "categoría hay que confirmar con `confirm_withdrawal=true`, y entonces se lo retira de ella (sin la "
        "confirmación responde 409 con las categorías afectadas y no cambia nada); en un torneo finalizado se "
        "permite y la inscripción no se toca. Requiere token."
    ),
    responses=errors(
        {
            404: "El atleta o el club no existe.",
            409: "Ya existe otro atleta con ese CI, el atleta dejaría de encajar en un torneo en pesaje o en curso, o falta "
            "confirmar el retiro de categorías.",
        },
        auth=True,
    ),
)
def update_athlete(
    athlete_id: Int4,
    payload: AthleteUpdate,
    confirm_withdrawal: bool = Query(
        default=False,
        description="Confirma que el atleta sea retirado de las categorías de torneos en `registration_open` donde ya no encaja.",
    ),
    db: Session = Depends(get_db),
):
    athlete = get_athlete_or_404(db, athlete_id)
    changes = {
        field: value
        for field, value in payload.model_dump(exclude_unset=True).items()
        if value is not None or field in ("ci", "height_cm")
    }
    if "club_id" in changes:
        get_club_or_404(db, changes["club_id"])
    _ensure_ci_is_free(db, changes.get("ci"), athlete_id)
    _withdraw_registrations_that_no_longer_fit(db, athlete, changes, confirm_withdrawal)
    for field, value in changes.items():
        setattr(athlete, field, value)
    db.commit()
    db.refresh(athlete)
    return athlete
