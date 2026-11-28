from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.athletes import get_athlete_or_404
from app.api.lifecycle import require_tournament_status
from app.api_docs import TAG_REGISTRATIONS, errors
from app.auth import ADMIN_ONLY
from app.database import get_db
from app.models import Category, Registration, TournamentStatus, WeighInStatus
from app.schemas import Int4, RegistrationCreate, RegistrationRead, WeighInCreate
from app.services.eligibility import category_mismatch, weight_mismatch

router = APIRouter(prefix="/api/v1/registrations", tags=[TAG_REGISTRATIONS])


@router.post(
    "",
    response_model=RegistrationRead,
    status_code=201,
    dependencies=ADMIN_ONLY,
    summary="Inscribir un atleta en una categoría",
    description="Reglas: el torneo debe estar en `registration_open` (409); el género del atleta debe coincidir con el de la categoría (422); su peso debe estar dentro de `min_weight`/`max_weight` si la categoría los define (422); su edad (año del torneo menos año de nacimiento) debe estar entre `min_age` y `max_age` y, si la categoría tiene grupo de grado, su grado debe pertenecer al grupo (422); no puede inscribirse dos veces en la misma categoría (409) ni en más de una categoría del mismo torneo (409). Requiere token.",
    responses=errors({404: "El atleta o la categoría no existe.", 409: "Las inscripciones no están abiertas, o el atleta ya está inscrito en esa categoría o en otra del mismo torneo."}, auth=True),
)
def create_registration(payload: RegistrationCreate, db: Session = Depends(get_db)):
    athlete = get_athlete_or_404(db, payload.athlete_id)
    category = db.get(Category, payload.category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    require_tournament_status(
        category.tournament, TournamentStatus.REGISTRATION_OPEN, "Las inscripciones no están abiertas"
    )
    mismatch = category_mismatch(athlete, category)
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
    if category.is_festival:
        registration.weigh_in_status = WeighInStatus.NOT_REQUIRED
    db.add(registration)
    db.commit()
    db.refresh(registration)
    return registration


@router.get(
    "",
    response_model=list[RegistrationRead],
    dependencies=ADMIN_ONLY,
    summary="Listar inscripciones",
    description="Devuelve las inscripciones con los datos del atleta y de la categoría, en el orden en que se hicieron. Con `category_id` devuelve solo las de esa categoría y con `tournament_id` solo las de ese torneo; si se envían ambos, se aplican los dos filtros. Incluye fecha de nacimiento y peso de los atletas, por eso requiere token.",
    responses=errors(auth=True),
)
def list_registrations(
    category_id: Int4 | None = None, tournament_id: Int4 | None = None, db: Session = Depends(get_db)
):
    query = (
        select(Registration)
        .options(
            selectinload(Registration.category).options(
                selectinload(Category.bracket), selectinload(Category.grade_group), selectinload(Category.age_division)
            )
        )
        .order_by(Registration.id)
    )
    if category_id is not None:
        query = query.where(Registration.category_id == category_id)
    if tournament_id is not None:
        query = query.join(Registration.category).where(Category.tournament_id == tournament_id)
    return db.scalars(query).all()


@router.delete(
    "/{registration_id}",
    status_code=204,
    dependencies=ADMIN_ONLY,
    summary="Retirar a un atleta de una categoría",
    description="Borra la inscripción. Solo mientras el torneo está en `registration_open`; en otro estado responde 409. Requiere token.",
    responses=errors({404: "La inscripción no existe.", 409: "Las inscripciones no están abiertas."}, auth=True),
)
def delete_registration(registration_id: Int4, db: Session = Depends(get_db)):
    registration = db.get(Registration, registration_id)
    if not registration:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")
    require_tournament_status(
        registration.category.tournament, TournamentStatus.REGISTRATION_OPEN, "Las inscripciones no están abiertas"
    )
    db.delete(registration)
    db.commit()
    return Response(status_code=204)


def get_registration_for_weigh_in(db: Session, registration_id: int) -> Registration:
    registration = db.get(Registration, registration_id)
    if not registration:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")
    require_tournament_status(
        registration.category.tournament, TournamentStatus.WEIGH_IN, "El pesaje solo se carga con el torneo en pesaje"
    )
    if registration.weigh_in_status == WeighInStatus.NOT_REQUIRED:
        raise HTTPException(status_code=409, detail="Festival no necesita pesaje")
    return registration


# El `detail` del 409 se muestra tal cual en el frontend: el estado va en palabras, no como valor del enum.
WEIGH_IN_STATUS_TEXT = {
    WeighInStatus.PENDING: "todavía no se pesó",
    WeighInStatus.FAILED_FIRST: "no entró en el primer pesaje y espera la decisión",
    WeighInStatus.SECOND_ALLOWED: "tiene habilitado el segundo pesaje",
    WeighInStatus.CLEARED: "ya está habilitado",
    WeighInStatus.DISQUALIFIED: "ya está descalificado",
    WeighInStatus.NO_SHOW: "no se presentó",
}


def require_weigh_in_status(registration: Registration, *allowed: WeighInStatus) -> None:
    if registration.weigh_in_status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"No se puede hacer esto: el atleta {WEIGH_IN_STATUS_TEXT[registration.weigh_in_status]}",
        )


@router.post(
    "/{registration_id}/weigh-in",
    response_model=RegistrationRead,
    dependencies=ADMIN_ONLY,
    summary="Cargar el peso de un atleta",
    description="Con la inscripción en `pending` guarda el primer peso (un decimal como máximo, 422 si no); si entra en la categoría pasa a `cleared` y si no, a `failed_first` (queda esperando la decisión del admin). Con la inscripción en `second_allowed` guarda el segundo peso; si entra pasa a `cleared` y si no, a `disqualified`. Que el atleta no entre no es un error: responde 200 y el estado lo dice. Solo con el torneo en `weigh_in`; en otro estado de la inscripción, o en Festival (no se pesa), responde 409. Requiere token.",
    responses=errors({404: "La inscripción no existe.", 409: "El torneo no está en pesaje, la inscripción no admite un peso en su estado actual o es de Festival."}, auth=True),
)
def record_weigh_in(registration_id: Int4, payload: WeighInCreate, db: Session = Depends(get_db)):
    registration = get_registration_for_weigh_in(db, registration_id)
    require_weigh_in_status(registration, WeighInStatus.PENDING, WeighInStatus.SECOND_ALLOWED)
    fits = weight_mismatch(payload.weight_kg, registration.category) is None
    if registration.weigh_in_status == WeighInStatus.PENDING:
        registration.first_weight_kg = payload.weight_kg
        registration.weigh_in_status = WeighInStatus.CLEARED if fits else WeighInStatus.FAILED_FIRST
    else:
        registration.second_weight_kg = payload.weight_kg
        registration.weigh_in_status = WeighInStatus.CLEARED if fits else WeighInStatus.DISQUALIFIED
    db.commit()
    db.refresh(registration)
    return registration


@router.post(
    "/{registration_id}/second-weigh-in",
    response_model=RegistrationRead,
    dependencies=ADMIN_ONLY,
    summary="Habilitar el segundo pesaje",
    description="Pasa la inscripción de `failed_first` a `second_allowed`, para que se pueda cargar un segundo peso. Solo con el torneo en `weigh_in`; desde cualquier otro estado de la inscripción, o en Festival, responde 409. Requiere token.",
    responses=errors({404: "La inscripción no existe.", 409: "El torneo no está en pesaje, la inscripción no está en `failed_first` o es de Festival."}, auth=True),
)
def allow_second_weigh_in(registration_id: Int4, db: Session = Depends(get_db)):
    registration = get_registration_for_weigh_in(db, registration_id)
    require_weigh_in_status(registration, WeighInStatus.FAILED_FIRST)
    registration.weigh_in_status = WeighInStatus.SECOND_ALLOWED
    db.commit()
    db.refresh(registration)
    return registration


@router.post(
    "/{registration_id}/disqualify",
    response_model=RegistrationRead,
    dependencies=ADMIN_ONLY,
    summary="Descalificar a un atleta por peso",
    description="Pasa la inscripción de `failed_first` a `disqualified`. Solo con el torneo en `weigh_in`; desde cualquier otro estado de la inscripción, o en Festival, responde 409. Requiere token.",
    responses=errors({404: "La inscripción no existe.", 409: "El torneo no está en pesaje, la inscripción no está en `failed_first` o es de Festival."}, auth=True),
)
def disqualify_for_weight(registration_id: Int4, db: Session = Depends(get_db)):
    registration = get_registration_for_weigh_in(db, registration_id)
    require_weigh_in_status(registration, WeighInStatus.FAILED_FIRST)
    registration.weigh_in_status = WeighInStatus.DISQUALIFIED
    db.commit()
    db.refresh(registration)
    return registration


@router.delete(
    "/{registration_id}/weigh-in",
    response_model=RegistrationRead,
    dependencies=ADMIN_ONLY,
    summary="Borrar el pesaje de un atleta",
    description="Para corregir un error de carga: vuelve la inscripción a `pending` y borra los dos pesos. Sobre una inscripción ya en `pending` no cambia nada. Solo con el torneo en `weigh_in`; en Festival responde 409. Requiere token.",
    responses=errors({404: "La inscripción no existe.", 409: "El torneo no está en pesaje o la inscripción es de Festival."}, auth=True),
)
def clear_weigh_in(registration_id: Int4, db: Session = Depends(get_db)):
    registration = get_registration_for_weigh_in(db, registration_id)
    registration.weigh_in_status = WeighInStatus.PENDING
    registration.first_weight_kg = None
    registration.second_weight_kg = None
    db.commit()
    db.refresh(registration)
    return registration
