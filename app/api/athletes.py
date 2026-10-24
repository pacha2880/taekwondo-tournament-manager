from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api_docs import TAG_ATHLETES, errors
from app.auth import ADMIN_ONLY
from app.database import get_db
from app.models import Athlete, Club
from app.schemas import AthleteCreate, AthleteRead

router = APIRouter(prefix="/api/v1/athletes", tags=[TAG_ATHLETES])


@router.post(
    "",
    response_model=AthleteRead,
    status_code=201,
    dependencies=ADMIN_ONLY,
    summary="Crear un atleta",
    description=(
        "Crea un atleta asignado a un club que ya existe. El CI es opcional; si se informa, no puede "
        "repetirse y, si no cumple el formato, responde 422. Requiere token."
    ),
    responses=errors({404: "El club no existe.", 409: "Ya existe un atleta con ese CI."}, auth=True),
)
def create_athlete(payload: AthleteCreate, db: Session = Depends(get_db)):
    if not db.get(Club, payload.club_id):
        raise HTTPException(status_code=404, detail="Club no encontrado")
    if payload.ci and db.scalar(select(Athlete).where(Athlete.ci == payload.ci)):
        raise HTTPException(status_code=409, detail="Ya existe un atleta con ese CI")
    athlete = Athlete(**payload.model_dump())
    db.add(athlete)
    db.commit()
    db.refresh(athlete)
    return athlete


@router.get(
    "",
    response_model=list[AthleteRead],
    dependencies=ADMIN_ONLY,
    summary="Listar atletas",
    description="Devuelve todos los atletas con su club, ordenados por nombre. Incluye fecha de nacimiento y peso, por eso requiere token.",
    responses=errors(auth=True),
)
def list_athletes(db: Session = Depends(get_db)):
    return db.scalars(select(Athlete).order_by(Athlete.name)).all()


@router.get(
    "/{athlete_id}",
    response_model=AthleteRead,
    dependencies=ADMIN_ONLY,
    summary="Obtener un atleta",
    description="Devuelve un atleta por su id. Incluye fecha de nacimiento y peso, por eso requiere token.",
    responses=errors({404: "El atleta no existe."}, auth=True),
)
def get_athlete(athlete_id: int, db: Session = Depends(get_db)):
    athlete = db.get(Athlete, athlete_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="Atleta no encontrado")
    return athlete
