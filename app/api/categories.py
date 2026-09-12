from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Category, Tournament
from app.schemas import CategoryCreate, CategoryRead

router = APIRouter(prefix="/api/v1/categories", tags=["categories"])


@router.post("", response_model=CategoryRead, status_code=201)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)):
    if not db.get(Tournament, payload.tournament_id):
        raise HTTPException(status_code=404, detail="Torneo no encontrado")
    category = Category(**payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.get("", response_model=list[CategoryRead])
def list_categories(tournament_id: int | None = None, db: Session = Depends(get_db)):
    stmt = select(Category)
    if tournament_id is not None:
        stmt = stmt.where(Category.tournament_id == tournament_id)
    return db.scalars(stmt).all()


@router.get("/{category_id}", response_model=CategoryRead)
def get_category(category_id: int, db: Session = Depends(get_db)):
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return category
