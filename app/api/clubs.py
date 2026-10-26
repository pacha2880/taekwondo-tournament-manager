from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api_docs import TAG_CLUBS, errors
from app.auth import ADMIN_ONLY
from app.database import get_db
from app.models import Club
from app.schemas import ClubCreate, ClubRead, ClubUpdate

router = APIRouter(prefix="/api/v1/clubs", tags=[TAG_CLUBS])


def get_club_or_404(db: Session, club_id: int) -> Club:
    club = db.get(Club, club_id)
    if not club:
        raise HTTPException(status_code=404, detail="Club no encontrado")
    return club


def _ensure_name_is_free(db: Session, name: str, club_id: int | None = None) -> None:
    query = select(Club).where(Club.name == name)
    if club_id is not None:
        query = query.where(Club.id != club_id)
    if db.scalar(query):
        raise HTTPException(status_code=409, detail="Ya existe un club con ese nombre")


@router.post(
    "",
    response_model=ClubRead,
    status_code=201,
    dependencies=ADMIN_ONLY,
    summary="Crear un club",
    description="Crea un club. El nombre debe ser único. Requiere token.",
    responses=errors({409: "Ya existe un club con ese nombre."}, auth=True),
)
def create_club(payload: ClubCreate, db: Session = Depends(get_db)):
    _ensure_name_is_free(db, payload.name)
    club = Club(**payload.model_dump())
    db.add(club)
    db.commit()
    db.refresh(club)
    return club


@router.get(
    "",
    response_model=list[ClubRead],
    summary="Listar clubes",
    description="Devuelve todos los clubes ordenados por nombre. Es público.",
    responses=errors(),
)
def list_clubs(db: Session = Depends(get_db)):
    return db.scalars(select(Club).order_by(Club.name)).all()


@router.get(
    "/{club_id}",
    response_model=ClubRead,
    summary="Obtener un club",
    description="Devuelve un club por su id. Es público.",
    responses=errors({404: "El club no existe."}),
)
def get_club(club_id: int, db: Session = Depends(get_db)):
    return get_club_or_404(db, club_id)


@router.patch(
    "/{club_id}",
    response_model=ClubRead,
    dependencies=ADMIN_ONLY,
    summary="Actualizar un club",
    description="Modifica el nombre del club, que debe seguir siendo único. Requiere token.",
    responses=errors({404: "El club no existe.", 409: "Ya existe otro club con ese nombre."}, auth=True),
)
def update_club(club_id: int, payload: ClubUpdate, db: Session = Depends(get_db)):
    club = get_club_or_404(db, club_id)
    if payload.name is not None:
        _ensure_name_is_free(db, payload.name, club_id)
        club.name = payload.name
    db.commit()
    db.refresh(club)
    return club
