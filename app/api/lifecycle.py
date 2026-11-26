from datetime import datetime

from fastapi import HTTPException

from app import clock
from app.models import Category, MatchStatus, Tournament, TournamentStatus

FINAL_MATCH_STATUSES = (MatchStatus.FINISHED, MatchStatus.BYE)


def current_status(
    stored_status: TournamentStatus, registration_deadline: datetime | None, now: datetime
) -> TournamentStatus:
    """El pesaje no se guarda: empieza solo cuando vence la fecha límite (UTC sin zona; `now`, con zona UTC)."""
    deadline_passed = registration_deadline is not None and now.replace(tzinfo=None) >= registration_deadline
    if stored_status == TournamentStatus.REGISTRATION_OPEN and deadline_passed:
        return TournamentStatus.WEIGH_IN
    return stored_status


def require_registration_deadline_in_the_future(tournament: Tournament) -> None:
    deadline = tournament.registration_deadline
    if deadline is None or deadline <= clock.utc_now().replace(tzinfo=None):
        raise HTTPException(status_code=409, detail="Primero hay que fijar una fecha límite de inscripción futura")


def require_tournament_status(
    tournament: Tournament, required: TournamentStatus | tuple[TournamentStatus, ...], detail: str
) -> None:
    allowed = required if isinstance(required, tuple) else (required,)
    if tournament.status not in allowed:
        raise HTTPException(status_code=409, detail=detail)


def _has_matches_to_play(category: Category) -> bool:
    if category.bracket is None:
        return len(category.registrations) >= 2
    return any(match.status not in FINAL_MATCH_STATUSES for match in category.bracket.matches)


def require_all_matches_played(tournament: Tournament) -> None:
    pending = [c for c in tournament.categories if _has_matches_to_play(c)]
    if pending:
        names = ", ".join(c.name for c in pending)
        raise HTTPException(status_code=409, detail=f"Quedan combates por jugar en: {names}")
