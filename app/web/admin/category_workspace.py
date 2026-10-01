from collections import defaultdict

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.brackets import create_bracket as create_bracket_api
from app.api.matches import create_round_score as create_round_score_api
from app.api.registrations import create_registration as create_registration_api
from app.database import get_db
from app.models import Athlete, Bracket, Category, Match, Registration
from app.schemas import RegistrationCreate, RoundScoreCreate
from app.services.brackets import resolve_athlete_names
from app.web.admin._shared import error_message, require_admin, templates

router = APIRouter(dependencies=[Depends(require_admin)])


def _category_detail_context(db: Session, category_id: int) -> dict:
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")

    registrations = db.scalars(
        select(Registration).where(Registration.category_id == category_id)
    ).all()
    all_athletes = db.scalars(select(Athlete).order_by(Athlete.name)).all()

    bracket = db.scalar(select(Bracket).where(Bracket.category_id == category_id))
    rounds = []
    athletes: dict[int, str] = {}
    if bracket:
        athletes = resolve_athlete_names(db, bracket.matches)
        matches_by_round = defaultdict(list)
        for match in bracket.matches:
            matches_by_round[match.round_number].append(match)
        rounds = [
            (round_number, sorted(matches, key=lambda m: m.slot))
            for round_number, matches in sorted(matches_by_round.items())
        ]

    return {
        "category": category,
        "tournament": category.tournament,
        "registrations": registrations,
        "all_athletes": all_athletes,
        "bracket": bracket,
        "rounds": rounds,
        "athletes": athletes,
    }


def _render_category_detail(
    request: Request, db: Session, category_id: int, error: str | None = None, status_code: int = 200
):
    context = _category_detail_context(db, category_id)
    return templates.TemplateResponse(
        request,
        "admin/category_detail.html",
        {**context, "error": error},
        status_code=status_code,
    )


def _submit_and_redirect(request: Request, db: Session, category_id: int, action):
    try:
        action()
    except (HTTPException, ValidationError) as exc:
        return _render_category_detail(request, db, category_id, error_message(exc), status_code=400)
    return RedirectResponse(url=f"/admin/categorias/{category_id}", status_code=303)


@router.get("/categorias/{category_id}")
def category_detail(category_id: int, request: Request, db: Session = Depends(get_db)):
    return _render_category_detail(request, db, category_id)


@router.post("/categorias/{category_id}/inscripciones")
def create_registration_view(
    category_id: int, request: Request, athlete_id: int = Form(...), db: Session = Depends(get_db)
):
    return _submit_and_redirect(
        request,
        db,
        category_id,
        lambda: create_registration_api(RegistrationCreate(athlete_id=athlete_id, category_id=category_id), db),
    )


@router.post("/categorias/{category_id}/llave")
def create_bracket_view(category_id: int, request: Request, db: Session = Depends(get_db)):
    return _submit_and_redirect(request, db, category_id, lambda: create_bracket_api(category_id, db))


@router.post("/combates/{match_id}/rounds")
def create_round_score_view(
    match_id: int,
    request: Request,
    round_number: int = Form(...),
    red_points: int = Form(...),
    blue_points: int = Form(...),
    db: Session = Depends(get_db),
):
    match = db.get(Match, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Combate no encontrado")
    category_id = match.bracket.category_id
    payload = RoundScoreCreate(round_number=round_number, red_points=red_points, blue_points=blue_points)
    return _submit_and_redirect(
        request, db, category_id, lambda: create_round_score_api(match_id, payload, db)
    )
