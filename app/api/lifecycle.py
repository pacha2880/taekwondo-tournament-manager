from fastapi import HTTPException

from app.models import Category, MatchStatus, Tournament, TournamentStatus

FINAL_MATCH_STATUSES = (MatchStatus.FINISHED, MatchStatus.BYE)


def require_tournament_status(tournament: Tournament, required: TournamentStatus, detail: str) -> None:
    if tournament.status != required:
        raise HTTPException(status_code=409, detail=detail)


def _has_matches_to_play(category: Category) -> bool:
    if category.bracket is None:
        return len(category.registrations) >= 2
    return any(match.status not in FINAL_MATCH_STATUSES for match in category.bracket.matches)


def require_all_matches_played(tournament: Tournament) -> None:
    pending = [c for c in tournament.categories if _has_matches_to_play(c)]
    if pending:
        names = ", ".join(f"{c.age_label} {c.weight_label}" for c in pending)
        raise HTTPException(status_code=409, detail=f"Quedan combates por jugar en: {names}")
