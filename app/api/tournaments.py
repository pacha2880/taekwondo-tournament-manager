from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import clock
from app.api.lifecycle import (
    VISIBLE_TO_PUBLIC,
    is_hidden_from_public,
    require_all_matches_played,
    require_registration_deadline_in_the_future,
    require_tournament_status,
)
from app.api_docs import TAG_TOURNAMENTS, errors
from app.auth import ADMIN_ONLY, OPTIONAL_TOKEN, is_admin_request
from app.database import get_db
from app.models import Category, Registration, Tournament, TournamentStatus
from app.schemas import Int4, TournamentCreate, TournamentRead, TournamentStartRead, TournamentUpdate
from app.services.brackets import generate_bracket
from app.services.category_structure import add_default_structure, sync_categories
from app.services.registrants import close_weigh_in

router = APIRouter(prefix="/api/v1/tournaments", tags=[TAG_TOURNAMENTS])


def get_tournament_or_404(db: Session, tournament_id: int) -> Tournament:
    tournament = db.get(Tournament, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Torneo no encontrado")
    return tournament


def get_visible_tournament_or_404(db: Session, tournament_id: int, is_admin: bool) -> Tournament:
    tournament = get_tournament_or_404(db, tournament_id)
    if is_hidden_from_public(tournament) and not is_admin:
        raise HTTPException(status_code=404, detail="Torneo no encontrado")
    return tournament


@router.post(
    "",
    response_model=TournamentRead,
    status_code=201,
    dependencies=ADMIN_ONLY,
    summary="Crear un torneo",
    description="Crea un torneo en estado `draft` (en preparación: todavía no admite inscripciones). Nace con la estructura de categorías "
    "de la Copa Diamante y todas sus categorías ya creadas (ver `GET /tournaments/{id}/category-structure`). "
    "Requiere token.",
    responses=errors(auth=True),
)
def create_tournament(payload: TournamentCreate, db: Session = Depends(get_db)):
    tournament = Tournament(**payload.model_dump())
    db.add(tournament)
    add_default_structure(tournament)
    sync_categories(db, tournament)
    db.commit()
    db.refresh(tournament)
    return tournament


@router.get(
    "",
    response_model=list[TournamentRead],
    summary="Listar torneos",
    description="Devuelve los torneos, del más reciente al más antiguo. Es público, pero sin token no incluye los "
    "torneos en preparación (`draft`); con token los devuelve todos.",
    responses=errors(auth=True),
    openapi_extra=OPTIONAL_TOKEN,
)
def list_tournaments(is_admin: bool = Depends(is_admin_request), db: Session = Depends(get_db)):
    query = select(Tournament).order_by(Tournament.date.desc())
    if not is_admin:
        query = query.where(VISIBLE_TO_PUBLIC)
    return db.scalars(query).all()


@router.get(
    "/{tournament_id}",
    response_model=TournamentRead,
    summary="Obtener un torneo",
    description="Devuelve un torneo por su id. Es público, pero un torneo en preparación (`draft`) solo existe "
    "para quien manda token: sin token responde 404.",
    responses=errors({404: "El torneo no existe (o está en preparación y no se envió token)."}, auth=True),
    openapi_extra=OPTIONAL_TOKEN,
)
def get_tournament(tournament_id: Int4, is_admin: bool = Depends(is_admin_request), db: Session = Depends(get_db)):
    return get_visible_tournament_or_404(db, tournament_id, is_admin)


@router.patch(
    "/{tournament_id}",
    response_model=TournamentRead,
    dependencies=ADMIN_ONLY,
    summary="Actualizar un torneo",
    description="Modifica solo los campos que se envían (nombre, fecha, lugar o fecha límite de inscripción). El "
    "estado no se cambia acá: ver `open-registration`, `close-registration`, `start` y `finish`. La fecha límite "
    "(`registration_deadline`) solo se puede cambiar en `draft` o `registration_open` (409 en otro estado, incluido "
    "`weigh_in`); debe ser futura (422), llevar zona horaria y caer antes del día del torneo, contando el día en UTC "
    "(422; con el torneo en `draft` o `registration_open` tampoco se puede mover la fecha del torneo a ese día o "
    "antes); `null` la borra, pero solo en `draft` (422 con las inscripciones abiertas). Requiere token.",
    responses=errors(
        {404: "El torneo no existe.", 409: "La fecha límite solo se cambia en `draft` o `registration_open`."},
        auth=True,
    ),
)
def update_tournament(tournament_id: Int4, payload: TournamentUpdate, db: Session = Depends(get_db)):
    tournament = get_tournament_or_404(db, tournament_id)
    changes = payload.model_dump(exclude_unset=True)
    emptied = [field for field in ("name", "date", "location") if field in changes and changes[field] is None]
    if emptied:
        raise HTTPException(status_code=422, detail=f"Estos campos no pueden quedar vacíos: {', '.join(emptied)}")
    if "registration_deadline" in changes:
        changes["registration_deadline"] = _checked_deadline(tournament, changes["registration_deadline"])
    if changes.keys() & {"date", "registration_deadline"}:
        _require_deadline_before_tournament_day(tournament, changes)
    for field, value in changes.items():
        setattr(tournament, field, value)
    db.commit()
    db.refresh(tournament)
    return tournament


def _checked_deadline(tournament: Tournament, deadline: datetime | None) -> datetime | None:
    """Valida la fecha límite nueva y la devuelve como se guarda: UTC sin zona."""
    require_tournament_status(
        tournament,
        (TournamentStatus.DRAFT, TournamentStatus.REGISTRATION_OPEN),
        "La fecha límite de inscripción solo se cambia en preparación o con las inscripciones abiertas",
    )
    if deadline is None:
        if tournament.status == TournamentStatus.REGISTRATION_OPEN:
            raise HTTPException(
                status_code=422, detail="Con las inscripciones abiertas la fecha límite no puede quedar vacía"
            )
        return None
    if deadline <= clock.utc_now():
        raise HTTPException(status_code=422, detail="La fecha límite de inscripción debe ser futura")
    return deadline.astimezone(timezone.utc).replace(tzinfo=None)


def _require_deadline_before_tournament_day(tournament: Tournament, changes: dict) -> None:
    # Once registration closed the deadline is history: a postponed tournament can still change its date.
    if tournament.status not in (TournamentStatus.DRAFT, TournamentStatus.REGISTRATION_OPEN):
        return
    deadline = changes.get("registration_deadline", tournament.registration_deadline)
    day = changes.get("date", tournament.date)
    if deadline is not None and deadline.date() >= day:
        raise HTTPException(
            status_code=422, detail="La fecha límite de inscripción debe ser anterior al día del torneo (en UTC)"
        )


@router.post(
    "/{tournament_id}/open-registration",
    response_model=TournamentRead,
    dependencies=ADMIN_ONLY,
    summary="Abrir las inscripciones",
    description="Pasa el torneo de `draft` a `registration_open`. Exige que ya tenga una fecha límite de "
    "inscripción futura (`registration_deadline`); al vencer, el torneo pasa solo a `weigh_in`. Requiere token.",
    responses=errors(
        {
            404: "El torneo no existe.",
            409: "El torneo no está en `draft`, o no tiene una fecha límite de inscripción futura.",
        },
        auth=True,
    ),
)
def open_registration(tournament_id: Int4, db: Session = Depends(get_db)):
    tournament = get_tournament_or_404(db, tournament_id)
    require_tournament_status(
        tournament, TournamentStatus.DRAFT, "Solo se pueden abrir las inscripciones de un torneo en preparación"
    )
    require_registration_deadline_in_the_future(tournament)
    tournament.stored_status = TournamentStatus.REGISTRATION_OPEN
    db.commit()
    db.refresh(tournament)
    return tournament


@router.post(
    "/{tournament_id}/close-registration",
    response_model=TournamentRead,
    dependencies=ADMIN_ONLY,
    summary="Pasar a Pesaje",
    description="Cierra las inscripciones antes de la fecha límite: la fecha límite pasa a ser ahora y el torneo "
    "queda en `weigh_in`. Solo desde `registration_open`; es irreversible. Requiere token.",
    responses=errors(
        {404: "El torneo no existe.", 409: "Las inscripciones no están abiertas (o ya vencieron)."}, auth=True
    ),
)
def close_registration(tournament_id: Int4, db: Session = Depends(get_db)):
    tournament = get_tournament_or_404(db, tournament_id)
    require_tournament_status(tournament, TournamentStatus.REGISTRATION_OPEN, "Las inscripciones no están abiertas")
    tournament.registration_deadline = clock.utc_now().replace(tzinfo=None)
    db.commit()
    db.refresh(tournament)
    return tournament


@router.post(
    "/{tournament_id}/start",
    response_model=TournamentStartRead,
    dependencies=ADMIN_ONLY,
    summary="Iniciar un torneo",
    description="Pasa el torneo de `weigh_in` a `in_progress`: se cargan los resultados. "
    "Cierra el pesaje: las inscripciones en `pending` pasan a `no_show` (no se presentaron) y las que quedaron en "
    "`failed_first` o `second_allowed` pasan a `disqualified`; las demás no cambian. Después sortea las llaves de "
    "todas las categorías con 2 o más inscritos, salvo Festival (que no tiene llave), con los descalificados ya "
    "marcados: ganan sin pelear (`walkover`) los que los enfrentan. La respuesta suma `not_weighed_in`, los que "
    "quedaron en `no_show` con este inicio, ordenados por categoría y nombre. Es irreversible. Requiere token.",
    responses=errors({404: "El torneo no existe.", 409: "El torneo no está en `weigh_in`."}, auth=True),
)
def start_tournament(tournament_id: Int4, db: Session = Depends(get_db)):
    tournament = get_tournament_or_404(db, tournament_id)
    if tournament.status in (TournamentStatus.IN_PROGRESS, TournamentStatus.FINISHED):
        raise HTTPException(status_code=409, detail="El torneo ya empezó")
    require_tournament_status(tournament, TournamentStatus.WEIGH_IN, "El torneo solo se inicia desde el pesaje")
    tournament.stored_status = TournamentStatus.IN_PROGRESS
    not_weighed_in = close_weigh_in(db, tournament_id)
    db.flush()  # el sorteo lee los estados de pesaje desde la base
    # Un solo conteo: un torneo tiene ~200 categorías y la mayoría quedan con 0 o 1 inscrito.
    registrations_per_category = dict(
        db.execute(
            select(Registration.category_id, func.count())
            .join(Category)
            .where(Category.tournament_id == tournament_id)
            .group_by(Registration.category_id)
        ).all()
    )
    for category in sorted(tournament.categories, key=lambda c: c.id):
        if not category.is_festival and registrations_per_category.get(category.id, 0) >= 2:
            generate_bracket(db, category)
    db.commit()
    db.refresh(tournament)
    started = TournamentRead.model_validate(tournament).model_dump()
    return TournamentStartRead(**started, not_weighed_in=not_weighed_in)


@router.post(
    "/{tournament_id}/finish",
    response_model=TournamentRead,
    dependencies=ADMIN_ONLY,
    summary="Finalizar un torneo",
    description="Pasa el torneo de `in_progress` a `finished`: sus resultados quedan como definitivos. Exige que "
    "no queden combates por jugar: toda llave terminada. Festival no tiene llave y no lo impide. Es irreversible. Requiere token.",
    responses=errors(
        {404: "El torneo no existe.", 409: "El torneo no está en curso, o quedan combates por jugar."}, auth=True
    ),
)
def finish_tournament(tournament_id: Int4, db: Session = Depends(get_db)):
    tournament = get_tournament_or_404(db, tournament_id)
    require_tournament_status(tournament, TournamentStatus.IN_PROGRESS, "Solo se puede finalizar un torneo en curso")
    require_all_matches_played(tournament)
    tournament.stored_status = TournamentStatus.FINISHED
    db.commit()
    db.refresh(tournament)
    return tournament
