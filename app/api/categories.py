from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api_docs import TAG_CATEGORIES, errors
from app.auth import ADMIN_ONLY
from app.database import get_db
from app.models import Category
from app.schemas import AthleteRead, CategoryRead, Int4, RegistrantRead
from app.services.athlete_search import search_athletes
from app.services.eligibility import category_mismatch
from app.services.registrants import list_registrants

router = APIRouter(prefix="/api/v1/categories", tags=[TAG_CATEGORIES])


@router.get(
    "",
    response_model=list[CategoryRead],
    summary="Listar categorías",
    description=(
        "Devuelve las categorías en el orden en que se crearon. Con el parámetro `tournament_id` devuelve solo las de "
        "ese torneo. Es público."
    ),
    responses=errors(),
)
def list_categories(tournament_id: Int4 | None = None, db: Session = Depends(get_db)):
    query = select(Category).options(selectinload(Category.bracket)).order_by(Category.id)
    if tournament_id is not None:
        query = query.where(Category.tournament_id == tournament_id)
    return db.scalars(query).all()


@router.get(
    "/{category_id}",
    response_model=CategoryRead,
    summary="Obtener una categoría",
    description="Devuelve una categoría por su id. Es público.",
    responses=errors({404: "La categoría no existe."}),
)
def get_category(category_id: Int4, db: Session = Depends(get_db)):
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return category


@router.get(
    "/{category_id}/registrants",
    response_model=list[RegistrantRead],
    summary="Listar los inscritos de una categoría",
    description="Devuelve los atletas inscritos en la categoría, ordenados por nombre, solo con datos públicos: "
    "nombre y club (nunca CI, fecha de nacimiento ni peso). Sirve en cualquier estado del torneo; mientras la "
    "categoría no tiene llave (`has_bracket: false`) es lo que se muestra al público. Es público.",
    responses=errors({404: "La categoría no existe."}),
)
def list_category_registrants(category_id: Int4, db: Session = Depends(get_db)):
    if not db.get(Category, category_id):
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
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
