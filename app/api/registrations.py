from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.athletes import get_athlete_or_404
from app.api.lifecycle import require_tournament_status
from app.api_docs import TAG_REGISTRATIONS, errors
from app.auth import ADMIN_ONLY
from app.database import get_db
from app.models import Category, Registration, TournamentStatus
from app.schemas import RegistrationCreate, RegistrationRead
from app.services.eligibility import category_mismatch

router = APIRouter(prefix="/api/v1/registrations", tags=[TAG_REGISTRATIONS])


@router.post(
    "",
    response_model=RegistrationRead,
    status_code=201,
    dependencies=ADMIN_ONLY,
    summary="Inscribir un atleta en una categoría",
    description="Reglas: el torneo debe estar en `draft`: al pasar a `in_progress` las inscripciones se cierran (409); el género del atleta debe coincidir con el de la categoría (422); su peso debe estar dentro de `min_weight`/`max_weight` si la categoría los define (422); no puede inscribirse dos veces en la misma categoría (409) ni en más de una categoría del mismo torneo (409). Requiere token.",
    responses=errors({404: "El atleta o la categoría no existe.", 409: "Las inscripciones están cerradas (el torneo ya empezó), o el atleta ya está inscrito en esa categoría o en otra del mismo torneo."}, auth=True),
)
def create_registration(payload: RegistrationCreate, db: Session = Depends(get_db)):
    athlete = get_athlete_or_404(db, payload.athlete_id)
    category = db.get(Category, payload.category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    require_tournament_status(
        category.tournament, TournamentStatus.DRAFT, "Las inscripciones están cerradas: el torneo ya empezó"
    )
    mismatch = category_mismatch(athlete.gender, athlete.weight_kg, category)
    if mismatch:
        raise HTTPException(status_code=422, detail=mismatch)
    existing = db.scalar(
        select(Registration).where(
            Registration.athlete_id == payload.athlete_id,
            Registration.category_id == payload.category_id,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="El atleta ya está inscrito en esta categoría")
    other_tournament_registration = db.scalar(
        select(Registration)
        .join(Category, Registration.category_id == Category.id)
        .where(
            Registration.athlete_id == payload.athlete_id,
            Category.tournament_id == category.tournament_id,
        )
    )
    if other_tournament_registration:
        raise HTTPException(
            status_code=409, detail="El atleta ya está inscrito en otra categoría de este torneo"
        )

    registration = Registration(**payload.model_dump())
    db.add(registration)
    db.commit()
    db.refresh(registration)
    return registration


@router.get(
    "",
    response_model=list[RegistrationRead],
    dependencies=ADMIN_ONLY,
    summary="Listar inscripciones",
    description="Devuelve las inscripciones con los datos del atleta y de la categoría. Con el parámetro `category_id` devuelve solo las de esa categoría. Incluye fecha de nacimiento y peso de los atletas, por eso requiere token.",
    responses=errors(auth=True),
)
def list_registrations(category_id: int | None = None, db: Session = Depends(get_db)):
    stmt = select(Registration)
    if category_id is not None:
        stmt = stmt.where(Registration.category_id == category_id)
    return db.scalars(stmt).all()
