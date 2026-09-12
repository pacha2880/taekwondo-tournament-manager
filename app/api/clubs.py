from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Club
from app.schemas import ClubCreate, ClubRead

router = APIRouter(prefix="/api/v1/clubs", tags=["clubs"])


@router.post("", response_model=ClubRead, status_code=201)
def create_club(payload: ClubCreate, db: Session = Depends(get_db)):
    existing = db.scalar(select(Club).where(Club.name == payload.name))
    if existing:
        raise HTTPException(status_code=409, detail="Ya existe un club con ese nombre")
    club = Club(**payload.model_dump())
    db.add(club)
    db.commit()
    db.refresh(club)
    return club


@router.get("", response_model=list[ClubRead])
def list_clubs(db: Session = Depends(get_db)):
    return db.scalars(select(Club).order_by(Club.name)).all()


@router.get("/{club_id}", response_model=ClubRead)
def get_club(club_id: int, db: Session = Depends(get_db)):
    club = db.get(Club, club_id)
    if not club:
        raise HTTPException(status_code=404, detail="Club no encontrado")
    return club
