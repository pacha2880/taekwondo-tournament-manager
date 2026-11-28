from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api_docs import TAG_BRACKETS, errors
from app.api.categories import get_visible_category_or_404
from app.auth import OPTIONAL_TOKEN, is_admin_request
from app.database import get_db
from app.models import Bracket
from app.schemas import BracketRead, Int4
from app.services.brackets import fill_athlete_details

router = APIRouter(prefix="/api/v1/categories", tags=[TAG_BRACKETS])


def _bracket_read(db: Session, bracket: Bracket) -> BracketRead:
    bracket_read = BracketRead.model_validate(bracket)
    fill_athlete_details(db, bracket.category_id, bracket_read.matches)
    return bracket_read


@router.get(
    "/{category_id}/bracket",
    response_model=BracketRead,
    summary="Obtener la llave de una categoría",
    description="Devuelve todos los combates de todas las rondas. Cada combate indica el combate de la siguiente ronda al que avanza su ganador (`next_match_id`). Es público, pero con el torneo en preparación (`draft`) sin token responde 404.",
    responses=errors({404: "La categoría no existe (o su torneo está en preparación y no se envió token) o todavía no tiene llave."}, auth=True),
    openapi_extra=OPTIONAL_TOKEN,
)
def get_bracket(category_id: Int4, is_admin: bool = Depends(is_admin_request), db: Session = Depends(get_db)):
    get_visible_category_or_404(db, category_id, is_admin)
    bracket = db.scalar(select(Bracket).where(Bracket.category_id == category_id))
    if not bracket:
        raise HTTPException(status_code=404, detail="Esta categoría todavía no tiene una llave")
    return _bracket_read(db, bracket)
