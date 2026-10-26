from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.athletes import WithdrawalNotConfirmed
from app.api.athletes import create_athlete as create_athlete_api
from app.api.athletes import list_athletes as list_athletes_api
from app.api.athletes import get_athlete_or_404
from app.api.athletes import update_athlete as update_athlete_api
from app.database import get_db
from app.models import Athlete, Club
from app.schemas import AthleteCreate, AthleteUpdate
from app.web.admin._shared import error_message, require_admin
from app.web.templating import templates

router = APIRouter(dependencies=[Depends(require_admin)])


def _render_athletes(
    request: Request, db: Session, error: str | None = None, status_code: int = 200, q: str = ""
):
    return templates.TemplateResponse(
        request,
        "admin/atletas.html",
        {
            "athletes": list_athletes_api(q, db),
            "clubs": db.scalars(select(Club).order_by(Club.name)).all(),
            "error": error,
            "q": q.strip(),
        },
        status_code=status_code,
    )


@router.get("/atletas")
def athletes_view(request: Request, q: str = "", db: Session = Depends(get_db)):
    return _render_athletes(request, db, q=q)


@router.post("/atletas")
def create_athlete_view(
    request: Request,
    name: str = Form(...),
    ci: str = Form(""),
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
            ci=ci,
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


def _render_athlete_edit(
    request: Request,
    db: Session,
    athlete: Athlete,
    values: dict,
    error: str | None = None,
    needs_confirmation: bool = False,
    status_code: int = 200,
):
    return templates.TemplateResponse(
        request,
        "admin/atleta_editar.html",
        {
            "athlete": athlete,
            "values": values,
            "clubs": db.scalars(select(Club).order_by(Club.name)).all(),
            "error": error,
            "needs_confirmation": needs_confirmation,
        },
        status_code=status_code,
    )


@router.get("/atletas/{athlete_id}/editar")
def edit_athlete_view(request: Request, athlete_id: int, db: Session = Depends(get_db)):
    athlete = get_athlete_or_404(db, athlete_id)
    values = {
        "name": athlete.name,
        "ci": athlete.ci or "",
        "birth_date": athlete.birth_date.isoformat(),
        "gender": athlete.gender,
        "belt_rank": athlete.belt_rank,
        "weight_kg": athlete.weight_kg,
        "club_id": athlete.club_id,
    }
    return _render_athlete_edit(request, db, athlete, values)


@router.post("/atletas/{athlete_id}/editar")
def update_athlete_view(
    request: Request,
    athlete_id: int,
    name: str = Form(...),
    ci: str = Form(""),
    birth_date: str = Form(...),
    gender: str = Form(...),
    belt_rank: str = Form(...),
    weight_kg: float = Form(...),
    club_id: int = Form(...),
    confirm_withdrawal: bool = Form(False),
    db: Session = Depends(get_db),
):
    athlete = get_athlete_or_404(db, athlete_id)
    values = {
        "name": name,
        "ci": ci,
        "birth_date": birth_date,
        "gender": gender,
        "belt_rank": belt_rank,
        "weight_kg": weight_kg,
        "club_id": club_id,
    }
    try:
        payload = AthleteUpdate(**values)
        update_athlete_api(athlete_id, payload, confirm_withdrawal, db)
    except WithdrawalNotConfirmed as exc:
        return _render_athlete_edit(request, db, athlete, values, exc.detail, needs_confirmation=True, status_code=409)
    except (HTTPException, ValidationError) as exc:
        return _render_athlete_edit(request, db, athlete, values, error_message(exc), status_code=400)
    return RedirectResponse(url="/admin/atletas", status_code=303)
