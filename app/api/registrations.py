from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Athlete, Category, Registration
from app.schemas import RegistrationCreate, RegistrationRead

router = APIRouter(prefix="/api/v1/registrations", tags=["registrations"])


@router.post("", response_model=RegistrationRead, status_code=201)
def create_registration(payload: RegistrationCreate, db: Session = Depends(get_db)):
    athlete = db.get(Athlete, payload.athlete_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="Atleta no encontrado")
    category = db.get(Category, payload.category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    if athlete.gender != category.gender:
        raise HTTPException(
            status_code=422, detail="El género del atleta no coincide con el de la categoría"
        )
    if category.min_weight is not None and athlete.weight_kg < category.min_weight:
        raise HTTPException(
            status_code=422, detail="El peso del atleta es menor al mínimo de la categoría"
        )
    if category.max_weight is not None and athlete.weight_kg > category.max_weight:
        raise HTTPException(
            status_code=422, detail="El peso del atleta es mayor al máximo de la categoría"
        )
    existing = db.scalar(
        select(Registration).where(
            Registration.athlete_id == payload.athlete_id,
            Registration.category_id == payload.category_id,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="El atleta ya está inscrito en esta categoría")
    other_tournament_registration = db.scalar(
        select(Registration)
        .join(Category, Registration.category_id == Category.id)
        .where(
            Registration.athlete_id == payload.athlete_id,
            Category.tournament_id == category.tournament_id,
        )
    )
    if other_tournament_registration:
        raise HTTPException(
            status_code=409, detail="El atleta ya está inscrito en otra categoría de este torneo"
        )

    registration = Registration(**payload.model_dump())
    db.add(registration)
    db.commit()
    db.refresh(registration)
    return registration


@router.get("", response_model=list[RegistrationRead])
def list_registrations(category_id: int | None = None, db: Session = Depends(get_db)):
    stmt = select(Registration)
    if category_id is not None:
        stmt = stmt.where(Registration.category_id == category_id)
    return db.scalars(stmt).all()
