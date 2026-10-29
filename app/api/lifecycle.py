from fastapi import HTTPException

from app.models import Tournament, TournamentStatus


def require_tournament_status(tournament: Tournament, required: TournamentStatus, detail: str) -> None:
    if tournament.status != required:
        raise HTTPException(status_code=409, detail=detail)
