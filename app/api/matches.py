from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api_docs import TAG_MATCHES, errors
from app.auth import ADMIN_ONLY
from app.database import get_db
from app.api.lifecycle import require_tournament_status
from app.models import Match, TournamentStatus
from app.schemas import MatchRead, RoundScoreCreate, RoundScoreRead
from app.services.brackets import resolve_athlete_names
from app.services.scoring import (
    MatchAlreadyFinished,
    MatchNotReady,
    TiedRound,
    record_round,
)

router = APIRouter(prefix="/api/v1/matches", tags=[TAG_MATCHES])


@router.get(
    "/{match_id}",
    response_model=MatchRead,
    summary="Obtener un combate",
    description="Devuelve un combate con el resultado de cada round cargado. Es público.",
    responses=errors({404: "El combate no existe."}),
)
def get_match(match_id: int, db: Session = Depends(get_db)):
    match = db.get(Match, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Combate no encontrado")
    match_read = MatchRead.model_validate(match)
    names = resolve_athlete_names(db, [match])
    match_read.athlete_red_name = names.get(match_read.athlete_red_id)
    match_read.athlete_blue_name = names.get(match_read.athlete_blue_id)
    match_read.winner_name = names.get(match_read.winner_id)
    return match_read


@router.post(
    "/{match_id}/rounds",
    response_model=RoundScoreRead,
    status_code=201,
    dependencies=ADMIN_ONLY,
    summary="Cargar el resultado de un round",
    description="Solo se pueden cargar resultados con el torneo en curso (409). Solo se envían los puntos de cada lado: el servidor numera los rounds (1, 2, 3…) en el orden en que se cargan. Gana el round el lado con más puntos; un round no puede terminar en empate (422). Cuando un atleta llega a `rounds_to_win` rounds ganados, el combate pasa a `finished` y su ganador avanza a la siguiente ronda. Requiere token.",
    responses=errors({400: "El combate todavía no tiene a sus dos atletas definidos.", 404: "El combate no existe.", 409: "El torneo no está en curso, o el combate ya terminó y no admite más rounds."}, auth=True),
)
def create_round_score(match_id: int, payload: RoundScoreCreate, db: Session = Depends(get_db)):
    match = db.get(Match, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Combate no encontrado")
    require_tournament_status(
        match.bracket.category.tournament, TournamentStatus.IN_PROGRESS, "Solo se pueden cargar resultados con el torneo en curso"
    )
    try:
        return record_round(db, match, payload.red_points, payload.blue_points)
    except MatchNotReady as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MatchAlreadyFinished as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except TiedRound as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
