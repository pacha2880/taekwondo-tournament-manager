from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.categories import create_category as create_category_api
from app.api.tournaments import create_tournament as create_tournament_api
from app.api.tournaments import finish_tournament as finish_tournament_api
from app.api.tournaments import start_tournament as start_tournament_api
from app.database import get_db
from app.models import Category, Tournament
from app.schemas import CategoryCreate, TournamentCreate
from app.web.admin._shared import echo_form, error_message, require_admin
from app.web.templating import templates

router = APIRouter(dependencies=[Depends(require_admin)])


def _render_dashboard(
    request: Request, db: Session, error: str | None = None, status_code: int = 200, form: dict | None = None
):
    tournaments = db.scalars(select(Tournament).order_by(Tournament.date.desc())).all()
    return templates.TemplateResponse(
        request,
        "admin/dashboard.html",
        {"tournaments": tournaments, "error": error, "form": form or {}},
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
        form = echo_form(name=name, date=date, location=location)
        return _render_dashboard(request, db, error_message(exc), status_code=400, form=form)
    return RedirectResponse(url=f"/admin/torneos/{tournament.id}", status_code=303)


def _render_tournament_detail(
    request: Request,
    db: Session,
    tournament_id: int,
    error: str | None = None,
    status_code: int = 200,
    form: dict | None = None,
):
    tournament = db.get(Tournament, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Torneo no encontrado")
    categories = db.scalars(select(Category).where(Category.tournament_id == tournament_id)).all()
    return templates.TemplateResponse(
        request,
        "admin/tournament_detail.html",
        {
            "tournament": tournament,
            "categories": categories,
            "error": error,
            "form": form or {},
        },
        status_code=status_code,
    )


def _submit_and_redirect(request: Request, db: Session, tournament_id: int, action, form: dict | None = None):
    try:
        action()
    except (HTTPException, ValidationError) as exc:
        return _render_tournament_detail(request, db, tournament_id, error_message(exc), status_code=400, form=form)
    return RedirectResponse(url=f"/admin/torneos/{tournament_id}", status_code=303)


@router.get("/torneos/{tournament_id}")
def tournament_detail(tournament_id: int, request: Request, db: Session = Depends(get_db)):
    return _render_tournament_detail(request, db, tournament_id)


@router.post("/torneos/{tournament_id}/iniciar")
def start_tournament_view(tournament_id: int, request: Request, db: Session = Depends(get_db)):
    return _submit_and_redirect(request, db, tournament_id, lambda: start_tournament_api(tournament_id, db))


@router.post("/torneos/{tournament_id}/finalizar")
def finish_tournament_view(tournament_id: int, request: Request, db: Session = Depends(get_db)):
    return _submit_and_redirect(request, db, tournament_id, lambda: finish_tournament_api(tournament_id, db))


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
        form=echo_form(
            age_label=age_label,
            min_age=min_age,
            max_age=max_age,
            gender=gender,
            belt_group=belt_group,
            weight_label=weight_label,
            min_weight=min_weight,
            max_weight=max_weight,
        ),
        action=lambda: create_category_api(
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
