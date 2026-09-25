from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Athlete, Bracket, Category, Tournament

router = APIRouter(tags=["public"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def list_tournaments(request: Request, db: Session = Depends(get_db)):
    tournaments = db.scalars(select(Tournament).order_by(Tournament.date.desc())).all()
    return templates.TemplateResponse(request, "index.html", {"tournaments": tournaments})


@router.get("/torneos/{tournament_id}")
def tournament_detail(tournament_id: int, request: Request, db: Session = Depends(get_db)):
    tournament = db.get(Tournament, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Torneo no encontrado")
    categories = db.scalars(select(Category).where(Category.tournament_id == tournament_id)).all()
    return templates.TemplateResponse(
        request, "tournament_detail.html", {"tournament": tournament, "categories": categories}
    )


@router.get("/categorias/{category_id}")
def category_detail(category_id: int, request: Request, db: Session = Depends(get_db)):
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")

    bracket = db.scalar(select(Bracket).where(Bracket.category_id == category_id))
    rounds = []
    athletes: dict[int, str] = {}
    if bracket:
        athlete_ids = {
            athlete_id
            for match in bracket.matches
            for athlete_id in (match.athlete_red_id, match.athlete_blue_id, match.winner_id)
            if athlete_id is not None
        }
        if athlete_ids:
            athletes = {
                a.id: a.name for a in db.scalars(select(Athlete).where(Athlete.id.in_(athlete_ids)))
            }

        matches_by_round = defaultdict(list)
        for match in bracket.matches:
            matches_by_round[match.round_number].append(match)
        rounds = [
            (round_number, sorted(matches, key=lambda m: m.slot))
            for round_number, matches in sorted(matches_by_round.items())
        ]

    return templates.TemplateResponse(
        request,
        "category_detail.html",
        {
            "category": category,
            "tournament": category.tournament,
            "bracket": bracket,
            "rounds": rounds,
            "athletes": athletes,
        },
    )
