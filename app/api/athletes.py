from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.clubs import get_club_or_404
from app.api_docs import TAG_ATHLETES, errors
from app.auth import ADMIN_ONLY
from app.database import get_db
from app.models import Athlete, TournamentStatus
from app.schemas import AthleteCreate, AthleteRead, AthleteUpdate
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


class WithdrawalNotConfirmed(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=409, detail=detail)


def _withdraw_registrations_that_no_longer_fit(db: Session, athlete: Athlete, changes: dict, confirmed: bool):
    gender = changes.get("gender", athlete.gender)
    weight_kg = changes.get("weight_kg", athlete.weight_kg)
    if (gender, weight_kg) == (athlete.gender, athlete.weight_kg):
        return

    for registration in athlete.registrations:
        tournament = registration.category.tournament
        if tournament.status == TournamentStatus.IN_PROGRESS and category_mismatch(
            gender, weight_kg, registration.category
        ):
            raise HTTPException(
                status_code=409,
                detail="No se puede cambiar el género ni el peso: el atleta dejaría de encajar en su categoría "
                f"del torneo en curso «{tournament.name}»",
            )

    no_longer_fit = [
        registration
        for registration in athlete.registrations
        if registration.category.tournament.status == TournamentStatus.DRAFT
        and category_mismatch(gender, weight_kg, registration.category)
    ]
    if not no_longer_fit:
        return
    if not confirmed:
        names = ", ".join(
            f"{r.category.age_label} {r.category.weight_label} ({r.category.tournament.name})" for r in no_longer_fit
        )
        raise WithdrawalNotConfirmed(f"Este cambio retira al atleta de: {names}. Hay que confirmar el retiro para continuar")
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
    description="Devuelve todos los atletas con su club, ordenados por nombre. Incluye fecha de nacimiento y peso, por eso requiere token.",
    responses=errors(auth=True),
)
def list_athletes(db: Session = Depends(get_db)):
    return db.scalars(select(Athlete).order_by(Athlete.name)).all()


@router.get(
    "/{athlete_id}",
    response_model=AthleteRead,
    dependencies=ADMIN_ONLY,
    summary="Obtener un atleta",
    description="Devuelve un atleta por su id. Incluye fecha de nacimiento y peso, por eso requiere token.",
    responses=errors({404: "El atleta no existe."}, auth=True),
)
def get_athlete(athlete_id: int, db: Session = Depends(get_db)):
    return get_athlete_or_404(db, athlete_id)


@router.patch(
    "/{athlete_id}",
    response_model=AthleteRead,
    dependencies=ADMIN_ONLY,
    summary="Actualizar un atleta",
    description=(
        "Modifica solo los campos que se envían (un `null` en un campo que no sea `ci` se ignora). `ci` con "
        "`null` o texto vacío lo borra. Si el cambio de **género o peso** afecta inscripciones: en un torneo "
        "en curso se rechaza (409) si el atleta deja de cumplir las reglas de su categoría; en un torneo en "
        "borrador, si el atleta deja de cumplir las reglas de la "
        "categoría hay que confirmar con `confirm_withdrawal=true`, y entonces se lo retira de ella (sin la "
        "confirmación responde 409 con las categorías afectadas y no cambia nada); en un torneo finalizado se "
        "permite y la inscripción no se toca. Requiere token."
    ),
    responses=errors(
        {
            404: "El atleta o el club no existe.",
            409: "Ya existe otro atleta con ese CI, el atleta dejaría de encajar en un torneo en curso, o falta "
            "confirmar el retiro de categorías.",
        },
        auth=True,
    ),
)
def update_athlete(
    athlete_id: int,
    payload: AthleteUpdate,
    confirm_withdrawal: bool = Query(
        default=False,
        description="Confirma que el atleta sea retirado de las categorías de torneos en borrador donde ya no encaja.",
    ),
    db: Session = Depends(get_db),
):
    athlete = get_athlete_or_404(db, athlete_id)
    changes = {
        field: value
        for field, value in payload.model_dump(exclude_unset=True).items()
        if value is not None or field == "ci"
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
