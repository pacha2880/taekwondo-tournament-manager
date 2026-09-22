from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Match
from app.schemas import MatchRead, RoundScoreCreate, RoundScoreRead
from app.services.scoring import (
    DuplicateRound,
    MatchAlreadyFinished,
    MatchNotReady,
    TiedRound,
    record_round,
)

router = APIRouter(prefix="/api/v1/matches", tags=["matches"])


@router.get("/{match_id}", response_model=MatchRead)
def get_match(match_id: int, db: Session = Depends(get_db)):
    match = db.get(Match, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Combate no encontrado")
    return match


@router.post("/{match_id}/rounds", response_model=RoundScoreRead, status_code=201)
def create_round_score(match_id: int, payload: RoundScoreCreate, db: Session = Depends(get_db)):
    match = db.get(Match, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Combate no encontrado")
    try:
        return record_round(db, match, payload.round_number, payload.red_points, payload.blue_points)
    except MatchNotReady as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (MatchAlreadyFinished, DuplicateRound) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except TiedRound as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
