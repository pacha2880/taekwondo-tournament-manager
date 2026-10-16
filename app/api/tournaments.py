from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api_docs import TAG_TOURNAMENTS, errors
from app.auth import ADMIN_ONLY
from app.database import get_db
from app.models import Tournament
from app.schemas import TournamentCreate, TournamentRead, TournamentUpdate

router = APIRouter(prefix="/api/v1/tournaments", tags=[TAG_TOURNAMENTS])


@router.post(
    "",
    response_model=TournamentRead,
    status_code=201,
    dependencies=ADMIN_ONLY,
    summary="Crear un torneo",
    description="Crea un torneo en estado `draft` (borrador). Requiere token.",
    responses=errors(auth=True),
)
def create_tournament(payload: TournamentCreate, db: Session = Depends(get_db)):
    tournament = Tournament(**payload.model_dump())
    db.add(tournament)
    db.commit()
    db.refresh(tournament)
    return tournament


@router.get(
    "",
    response_model=list[TournamentRead],
    summary="Listar torneos",
    description="Devuelve los torneos, del más reciente al más antiguo. Es público.",
    responses=errors(),
)
def list_tournaments(db: Session = Depends(get_db)):
    return db.scalars(select(Tournament).order_by(Tournament.date.desc())).all()


@router.get(
    "/{tournament_id}",
    response_model=TournamentRead,
    summary="Obtener un torneo",
    description="Devuelve un torneo por su id. Es público.",
    responses=errors({404: "El torneo no existe."}),
)
def get_tournament(tournament_id: int, db: Session = Depends(get_db)):
    tournament = db.get(Tournament, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Torneo no encontrado")
    return tournament


@router.patch(
    "/{tournament_id}",
    response_model=TournamentRead,
    dependencies=ADMIN_ONLY,
    summary="Actualizar un torneo",
    description="Modifica solo los campos que se envían (nombre, fecha, lugar o estado). Requiere token.",
    responses=errors({404: "El torneo no existe."}, auth=True),
)
def update_tournament(tournament_id: int, payload: TournamentUpdate, db: Session = Depends(get_db)):
    tournament = db.get(Tournament, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Torneo no encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(tournament, field, value)
    db.commit()
    db.refresh(tournament)
    return tournament
