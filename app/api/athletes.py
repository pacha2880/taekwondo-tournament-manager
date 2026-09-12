from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Athlete, Club
from app.schemas import AthleteCreate, AthleteRead

router = APIRouter(prefix="/api/v1/athletes", tags=["athletes"])


@router.post("", response_model=AthleteRead, status_code=201)
def create_athlete(payload: AthleteCreate, db: Session = Depends(get_db)):
    if not db.get(Club, payload.club_id):
        raise HTTPException(status_code=404, detail="Club no encontrado")
    athlete = Athlete(**payload.model_dump())
    db.add(athlete)
    db.commit()
    db.refresh(athlete)
    return athlete


@router.get("", response_model=list[AthleteRead])
def list_athletes(db: Session = Depends(get_db)):
    return db.scalars(select(Athlete).order_by(Athlete.name)).all()


@router.get("/{athlete_id}", response_model=AthleteRead)
def get_athlete(athlete_id: int, db: Session = Depends(get_db)):
    athlete = db.get(Athlete, athlete_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="Atleta no encontrado")
    return athlete
