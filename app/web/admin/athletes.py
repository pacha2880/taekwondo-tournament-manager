from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.athletes import create_athlete as create_athlete_api
from app.database import get_db
from app.models import Athlete, Club
from app.schemas import AthleteCreate
from app.web.admin._shared import error_message, require_admin, templates

router = APIRouter(dependencies=[Depends(require_admin)])


def _render_athletes(request: Request, db: Session, error: str | None = None, status_code: int = 200):
    return templates.TemplateResponse(
        request,
        "admin/atletas.html",
        {
            "athletes": db.scalars(select(Athlete).order_by(Athlete.name)).all(),
            "clubs": db.scalars(select(Club).order_by(Club.name)).all(),
            "error": error,
        },
        status_code=status_code,
    )


@router.get("/atletas")
def athletes_view(request: Request, db: Session = Depends(get_db)):
    return _render_athletes(request, db)


@router.post("/atletas")
def create_athlete_view(
    request: Request,
    name: str = Form(...),
    birth_date: str = Form(...),
    gender: str = Form(...),
    belt_rank: str = Form(...),
    weight_kg: float = Form(...),
    club_id: int = Form(...),
    db: Session = Depends(get_db),
):
    try:
        payload = AthleteCreate(
            name=name,
            birth_date=birth_date,
            gender=gender,
            belt_rank=belt_rank,
            weight_kg=weight_kg,
            club_id=club_id,
        )
        create_athlete_api(payload, db)
    except (HTTPException, ValidationError) as exc:
        return _render_athletes(request, db, error_message(exc), status_code=400)
    return RedirectResponse(url="/admin/atletas", status_code=303)
