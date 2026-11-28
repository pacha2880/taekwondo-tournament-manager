from fastapi import HTTPException

from app import clock
from app.models import FINAL_MATCH_STATUSES, Category, Tournament, TournamentStatus


# Un torneo en preparación solo lo ve el admin. La misma regla en Python y como condición SQL para las listas.
VISIBLE_TO_PUBLIC = Tournament.stored_status != TournamentStatus.DRAFT


def is_hidden_from_public(tournament: Tournament) -> bool:
    return tournament.stored_status == TournamentStatus.DRAFT


def registrants_are_public(tournament: Tournament) -> bool:
    """La lista de inscritos se publica desde el Pesaje."""
    return tournament.status in (TournamentStatus.WEIGH_IN, TournamentStatus.IN_PROGRESS, TournamentStatus.FINISHED)


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
    return category.bracket is not None and any(
        match.status not in FINAL_MATCH_STATUSES for match in category.bracket.matches
    )


def require_all_matches_played(tournament: Tournament) -> None:
    pending = [c for c in tournament.categories if _has_matches_to_play(c)]
    if pending:
        names = ", ".join(c.name for c in pending)
        raise HTTPException(status_code=409, detail=f"Quedan combates por jugar en: {names}")
