from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import exists, select
from sqlalchemy.orm import Session, selectinload

from app.api.lifecycle import is_hidden_from_public, registrants_are_public
from app.api_docs import TAG_CATEGORIES, errors
from app.auth import ADMIN_ONLY, OPTIONAL_TOKEN, is_admin_request
from app.database import get_db
from app.models import Category, Gender, Registration, Tournament, TournamentStatus
from app.schemas import AthleteRead, CategoryRead, Int4, RegistrantRead
from app.services.athlete_search import search_athletes
from app.services.eligibility import category_mismatch
from app.services.registrants import list_registrants

router = APIRouter(prefix="/api/v1/categories", tags=[TAG_CATEGORIES])

REGISTRANTS_NOT_PUBLIC_YET = "La lista de inscritos se publica al cerrar las inscripciones"


def get_visible_category_or_404(db: Session, category_id: int, is_admin: bool) -> Category:
    category = db.get(Category, category_id)
    if not category or (is_hidden_from_public(category.tournament) and not is_admin):
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return category


@router.get(
    "",
    response_model=list[CategoryRead],
    summary="Listar categorías",
    description=(
        "Devuelve las categorías en el orden en que se crearon. Filtros opcionales, combinables entre sí: "
        "`tournament_id` (solo las de ese torneo), `grade_group_id` (solo las de ese grupo de grado), `gender` "
        "(`male` o `female`) y `has_registrants` (`true`: con al menos un inscrito; `false`: sin ninguno). "
        "Es público, pero sin token no incluye las categorías de torneos en preparación (`draft`), y el filtro "
        "`has_registrants` solo se acepta junto con un `tournament_id` cuyo torneo ya cerró las inscripciones "
        "(`weigh_in`, `in_progress` o `finished`); en otro caso responde 403. Con token no hay estas restricciones."
    ),
    responses=errors(
        {403: "Sin token, `has_registrants` sin un `tournament_id` cuya lista de inscritos ya sea pública."},
        auth=True,
    ),
    openapi_extra=OPTIONAL_TOKEN,
)
def list_categories(
    tournament_id: Int4 | None = None,
    grade_group_id: Int4 | None = None,
    gender: Gender | None = None,
    has_registrants: bool | None = None,
    is_admin: bool = Depends(is_admin_request),
    db: Session = Depends(get_db),
):
    if not is_admin and has_registrants is not None:
        tournament = db.get(Tournament, tournament_id) if tournament_id is not None else None
        if tournament is None or not registrants_are_public(tournament):
            raise HTTPException(status_code=403, detail=REGISTRANTS_NOT_PUBLIC_YET)
    query = (
        select(Category)
        .options(selectinload(Category.bracket), selectinload(Category.grade_group))
        .order_by(Category.id)
    )
    if not is_admin:
        query = query.where(Category.tournament.has(Tournament.stored_status != TournamentStatus.DRAFT))
    if tournament_id is not None:
        query = query.where(Category.tournament_id == tournament_id)
    if grade_group_id is not None:
        query = query.where(Category.grade_group_id == grade_group_id)
    if gender is not None:
        query = query.where(Category.gender == gender)
    if has_registrants is not None:
        has_any = exists().where(Registration.category_id == Category.id)
        query = query.where(has_any if has_registrants else ~has_any)
    return db.scalars(query).all()


@router.get(
    "/{category_id}",
    response_model=CategoryRead,
    summary="Obtener una categoría",
    description="Devuelve una categoría por su id. Es público, pero la de un torneo en preparación (`draft`) solo "
    "existe para quien manda token: sin token responde 404.",
    responses=errors({404: "La categoría no existe (o su torneo está en preparación y no se envió token)."}, auth=True),
    openapi_extra=OPTIONAL_TOKEN,
)
def get_category(category_id: Int4, is_admin: bool = Depends(is_admin_request), db: Session = Depends(get_db)):
    return get_visible_category_or_404(db, category_id, is_admin)


@router.get(
    "/{category_id}/registrants",
    response_model=list[RegistrantRead],
    summary="Listar los inscritos de una categoría",
    description="Devuelve los atletas inscritos en la categoría, ordenados por nombre, solo con datos públicos: "
    "nombre y club (nunca CI, fecha de nacimiento ni peso). Mientras la categoría no tiene llave "
    "(`has_bracket: false`) es lo que se muestra al público. Es público desde el Pesaje (`weigh_in`): sin token, "
    "con las inscripciones abiertas responde 403 y con el torneo en preparación (`draft`), 404. Con token, siempre.",
    responses=errors(
        {
            403: "Sin token, las inscripciones siguen abiertas: la lista se publica al llegar al Pesaje.",
            404: "La categoría no existe (o su torneo está en preparación y no se envió token).",
        },
        auth=True,
    ),
    openapi_extra=OPTIONAL_TOKEN,
)
def list_category_registrants(
    category_id: Int4, is_admin: bool = Depends(is_admin_request), db: Session = Depends(get_db)
):
    category = get_visible_category_or_404(db, category_id, is_admin)
    if not is_admin and not registrants_are_public(category.tournament):
        raise HTTPException(status_code=403, detail=REGISTRANTS_NOT_PUBLIC_YET)
    return list_registrants(db, category_id)


@router.get(
    "/{category_id}/eligible-athletes",
    response_model=list[AthleteRead],
    dependencies=ADMIN_ONLY,
    summary="Listar los atletas que encajan en una categoría",
    description="Devuelve, ordenados por nombre, los atletas que cumplen la regla de `POST /registrations` para esta "
    "categoría (género, peso, y en las categorías con estructura, edad y grupo de grado). Incluye a los que ya "
    "están inscritos, en esta o en otra categoría; para saber quién ya está inscrito usá "
    "`GET /registrations?category_id=`. Requiere token.",
    responses=errors({404: "La categoría no existe."}, auth=True),
)
def list_eligible_athletes(category_id: Int4, db: Session = Depends(get_db)):
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return [a for a in search_athletes(db, None) if category_mismatch(a, category) is None]
