from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.categories import create_category as create_category_api
from app.api.tournaments import create_tournament as create_tournament_api
from app.api.tournaments import update_tournament as update_tournament_api
from app.database import get_db
from app.models import Category, Tournament, TournamentStatus
from app.schemas import CategoryCreate, TournamentCreate, TournamentUpdate
from app.web.admin._shared import error_message, require_admin, templates
from app.web.labels import es_label

router = APIRouter(dependencies=[Depends(require_admin)])


def _render_dashboard(request: Request, db: Session, error: str | None = None, status_code: int = 200):
    tournaments = db.scalars(select(Tournament).order_by(Tournament.date.desc())).all()
    return templates.TemplateResponse(
        request,
        "admin/dashboard.html",
        {"tournaments": tournaments, "error": error},
        status_code=status_code,
    )


@router.get("")
def dashboard(request: Request, db: Session = Depends(get_db)):
    return _render_dashboard(request, db)


@router.post("/torneos")
def create_tournament_view(
    request: Request,
    name: str = Form(...),
    date: str = Form(...),
    location: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        tournament = create_tournament_api(TournamentCreate(name=name, date=date, location=location), db)
    except (HTTPException, ValidationError) as exc:
        return _render_dashboard(request, db, error_message(exc), status_code=400)
    return RedirectResponse(url=f"/admin/torneos/{tournament.id}", status_code=303)


def _render_tournament_detail(
    request: Request, db: Session, tournament_id: int, error: str | None = None, status_code: int = 200
):
    tournament = db.get(Tournament, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Torneo no encontrado")
    categories = db.scalars(select(Category).where(Category.tournament_id == tournament_id)).all()
    status_options = [(s.value, es_label(s)) for s in TournamentStatus]
    return templates.TemplateResponse(
        request,
        "admin/tournament_detail.html",
        {
            "tournament": tournament,
            "categories": categories,
            "status_options": status_options,
            "error": error,
        },
        status_code=status_code,
    )


def _submit_and_redirect(request: Request, db: Session, tournament_id: int, action):
    try:
        action()
    except (HTTPException, ValidationError) as exc:
        return _render_tournament_detail(request, db, tournament_id, error_message(exc), status_code=400)
    return RedirectResponse(url=f"/admin/torneos/{tournament_id}", status_code=303)


@router.get("/torneos/{tournament_id}")
def tournament_detail(tournament_id: int, request: Request, db: Session = Depends(get_db)):
    return _render_tournament_detail(request, db, tournament_id)


@router.post("/torneos/{tournament_id}/estado")
def update_tournament_status(
    tournament_id: int, request: Request, status: str = Form(...), db: Session = Depends(get_db)
):
    return _submit_and_redirect(
        request, db, tournament_id, lambda: update_tournament_api(tournament_id, TournamentUpdate(status=status), db)
    )


@router.post("/torneos/{tournament_id}/categorias")
def create_category_view(
    tournament_id: int,
    request: Request,
    age_label: str = Form(...),
    min_age: int = Form(...),
    max_age: int | None = Form(None),
    gender: str = Form(...),
    belt_group: str = Form(...),
    weight_label: str = Form(...),
    min_weight: float | None = Form(None),
    max_weight: float | None = Form(None),
    db: Session = Depends(get_db),
):
    return _submit_and_redirect(
        request,
        db,
        tournament_id,
        lambda: create_category_api(
            CategoryCreate(
                tournament_id=tournament_id,
                age_label=age_label,
                min_age=min_age,
                max_age=max_age,
                gender=gender,
                belt_group=belt_group,
                weight_label=weight_label,
                min_weight=min_weight,
                max_weight=max_weight,
            ),
            db,
        ),
    )
