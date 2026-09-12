from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Tournament
from app.schemas import TournamentCreate, TournamentRead, TournamentUpdate

router = APIRouter(prefix="/api/v1/tournaments", tags=["tournaments"])


@router.post("", response_model=TournamentRead, status_code=201)
def create_tournament(payload: TournamentCreate, db: Session = Depends(get_db)):
    tournament = Tournament(**payload.model_dump())
    db.add(tournament)
    db.commit()
    db.refresh(tournament)
    return tournament


@router.get("", response_model=list[TournamentRead])
def list_tournaments(db: Session = Depends(get_db)):
    return db.scalars(select(Tournament).order_by(Tournament.date.desc())).all()


@router.get("/{tournament_id}", response_model=TournamentRead)
def get_tournament(tournament_id: int, db: Session = Depends(get_db)):
    tournament = db.get(Tournament, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Torneo no encontrado")
    return tournament


@router.patch("/{tournament_id}", response_model=TournamentRead)
def update_tournament(tournament_id: int, payload: TournamentUpdate, db: Session = Depends(get_db)):
    tournament = db.get(Tournament, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Torneo no encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(tournament, field, value)
    db.commit()
    db.refresh(tournament)
    return tournament
