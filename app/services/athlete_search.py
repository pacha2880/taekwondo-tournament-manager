import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Athlete


def _fold(text: str) -> str:
    without_accents = "".join(c for c in unicodedata.normalize("NFD", text) if not unicodedata.combining(c))
    return without_accents.casefold()


def search_athletes(db: Session, query: str | None) -> list[Athlete]:
    athletes = db.scalars(select(Athlete).order_by(Athlete.name)).all()
    needle = _fold((query or "").strip())
    if not needle:
        return athletes
    return [a for a in athletes if needle in _fold(a.name) or needle in _fold(a.ci or "")]
