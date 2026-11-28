from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api_docs import TAG_BRACKETS, errors
from app.api.categories import get_visible_category_or_404
from app.auth import ADMIN_ONLY, OPTIONAL_TOKEN, is_admin_request
from app.database import get_db
from app.api.lifecycle import require_tournament_status
from app.models import Bracket, Category, TournamentStatus
from app.schemas import BracketRead, Int4
from app.services.brackets import (
    BracketAlreadyExists,
    NotEnoughAthletes,
    fill_athlete_details,
    generate_bracket,
)

router = APIRouter(prefix="/api/v1/categories", tags=[TAG_BRACKETS])


def _bracket_read(db: Session, bracket: Bracket) -> BracketRead:
    bracket_read = BracketRead.model_validate(bracket)
    fill_athlete_details(db, bracket.category_id, bracket_read.matches)
    return bracket_read


@router.post(
    "/{category_id}/bracket",
    response_model=BracketRead,
    status_code=201,
    dependencies=ADMIN_ONLY,
    summary="Generar la llave de una categoría",
    description="Sortea a los inscritos en una llave de eliminación simple: en la primera ronda separa a los del mismo club cuando se puede, y empareja a cada descalificado (por peso o por no presentarse) con un habilitado, que gana sin pelear (`walkover`); dos descalificados juntos quedan sin combate (`no_contest`). Si el número de inscritos no es potencia de 2, se reparten pases directos (`bye`), primero a habilitados. Solo se genera con el torneo en curso (409 si todavía no empezó o ya terminó). Hacen falta al menos 2 inscritos y solo se puede generar una llave por categoría. Requiere token.",
    responses=errors({400: "La categoría tiene menos de 2 inscritos.", 404: "La categoría no existe.", 409: "El torneo no está en curso, o la categoría ya tiene una llave."}, auth=True),
)
def create_bracket(category_id: Int4, db: Session = Depends(get_db)):
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    require_tournament_status(
        category.tournament, TournamentStatus.IN_PROGRESS, "Solo se puede generar la llave con el torneo en curso"
    )
    try:
        bracket = generate_bracket(db, category)
        db.commit()
    except BracketAlreadyExists as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except NotEnoughAthletes as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _bracket_read(db, bracket)


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
