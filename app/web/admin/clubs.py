from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.clubs import create_club as create_club_api
from app.database import get_db
from app.models import Club
from app.schemas import ClubCreate
from app.web.admin._shared import error_message, require_admin, templates

router = APIRouter(dependencies=[Depends(require_admin)])


def _render_clubs(request: Request, db: Session, error: str | None = None, status_code: int = 200):
    clubs = db.scalars(select(Club).order_by(Club.name)).all()
    return templates.TemplateResponse(
        request, "admin/clubes.html", {"clubs": clubs, "error": error}, status_code=status_code
    )


@router.get("/clubes")
def clubs_view(request: Request, db: Session = Depends(get_db)):
    return _render_clubs(request, db)


@router.post("/clubes")
def create_club_view(request: Request, name: str = Form(...), db: Session = Depends(get_db)):
    try:
        create_club_api(ClubCreate(name=name), db)
    except (HTTPException, ValidationError) as exc:
        return _render_clubs(request, db, error_message(exc), status_code=400)
    return RedirectResponse(url="/admin/clubes", status_code=303)
