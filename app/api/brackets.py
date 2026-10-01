from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Bracket, Category
from app.schemas import BracketRead
from app.services.brackets import (
    BracketAlreadyExists,
    NotEnoughAthletes,
    generate_bracket,
    resolve_athlete_names,
)

router = APIRouter(prefix="/api/v1/categories", tags=["brackets"])


def _bracket_read(db: Session, bracket: Bracket) -> BracketRead:
    bracket_read = BracketRead.model_validate(bracket)
    names = resolve_athlete_names(db, bracket.matches)
    for match_read in bracket_read.matches:
        match_read.athlete_red_name = names.get(match_read.athlete_red_id)
        match_read.athlete_blue_name = names.get(match_read.athlete_blue_id)
        match_read.winner_name = names.get(match_read.winner_id)
    return bracket_read


@router.post("/{category_id}/bracket", response_model=BracketRead, status_code=201)
def create_bracket(category_id: int, db: Session = Depends(get_db)):
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    try:
        bracket = generate_bracket(db, category)
    except BracketAlreadyExists as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except NotEnoughAthletes as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _bracket_read(db, bracket)


@router.get("/{category_id}/bracket", response_model=BracketRead)
def get_bracket(category_id: int, db: Session = Depends(get_db)):
    if not db.get(Category, category_id):
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    bracket = db.scalar(select(Bracket).where(Bracket.category_id == category_id))
    if not bracket:
        raise HTTPException(status_code=404, detail="Esta categoría todavía no tiene una llave")
    return _bracket_read(db, bracket)
