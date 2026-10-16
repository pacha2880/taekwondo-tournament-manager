from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api_docs import TAG_CATEGORIES, errors
from app.auth import ADMIN_ONLY
from app.database import get_db
from app.models import Category, Tournament
from app.schemas import CategoryCreate, CategoryRead

router = APIRouter(prefix="/api/v1/categories", tags=[TAG_CATEGORIES])


@router.post(
    "",
    response_model=CategoryRead,
    status_code=201,
    dependencies=ADMIN_ONLY,
    summary="Crear una categoría",
    description="Crea una categoría dentro de un torneo que ya existe. `min_age` no puede ser mayor que `max_age`, ni `min_weight` mayor que `max_weight` (responde 422). Si no se envía `discipline`, es `sparring`. Requiere token.",
    responses=errors({404: "El torneo no existe."}, auth=True),
)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)):
    if not db.get(Tournament, payload.tournament_id):
        raise HTTPException(status_code=404, detail="Torneo no encontrado")
    category = Category(**payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.get(
    "",
    response_model=list[CategoryRead],
    summary="Listar categorías",
    description="Devuelve las categorías. Con el parámetro `tournament_id` devuelve solo las de ese torneo. Es público.",
    responses=errors(),
)
def list_categories(tournament_id: int | None = None, db: Session = Depends(get_db)):
    stmt = select(Category)
    if tournament_id is not None:
        stmt = stmt.where(Category.tournament_id == tournament_id)
    return db.scalars(stmt).all()


@router.get(
    "/{category_id}",
    response_model=CategoryRead,
    summary="Obtener una categoría",
    description="Devuelve una categoría por su id. Es público.",
    responses=errors({404: "La categoría no existe."}),
)
def get_category(category_id: int, db: Session = Depends(get_db)):
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return category
