from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Match, MatchStatus, RoundScore
from app.services.brackets import advance_winner


class MatchNotReady(Exception):
    pass


class MatchAlreadyFinished(Exception):
    pass


class DuplicateRound(Exception):
    pass


class TiedRound(Exception):
    pass


def _rounds_won(db: Session, match_id: int, athlete_id: int) -> int:
    return db.scalar(
        select(func.count())
        .select_from(RoundScore)
        .where(RoundScore.match_id == match_id, RoundScore.round_winner_id == athlete_id)
    )


def record_round(
    db: Session, match: Match, round_number: int, red_points: int, blue_points: int
) -> RoundScore:
    if match.athlete_red_id is None or match.athlete_blue_id is None:
        raise MatchNotReady("El combate todavía no tiene ambos atletas definidos")
    if match.status == MatchStatus.FINISHED:
        raise MatchAlreadyFinished("El combate ya está finalizado")
    if red_points == blue_points:
        raise TiedRound("Un round no puede terminar en empate")
    if db.scalar(
        select(RoundScore).where(
            RoundScore.match_id == match.id, RoundScore.round_number == round_number
        )
    ):
        raise DuplicateRound(f"Ya existe un resultado para el round {round_number} de este combate")

    round_winner_id = match.athlete_red_id if red_points > blue_points else match.athlete_blue_id
    round_score = RoundScore(
        match_id=match.id,
        round_number=round_number,
        red_points=red_points,
        blue_points=blue_points,
        round_winner_id=round_winner_id,
    )
    db.add(round_score)
    db.flush()

    rounds_to_win = match.bracket.category.rounds_to_win
    red_wins = _rounds_won(db, match.id, match.athlete_red_id)
    blue_wins = _rounds_won(db, match.id, match.athlete_blue_id)
    if red_wins >= rounds_to_win or blue_wins >= rounds_to_win:
        match.status = MatchStatus.FINISHED
        match.winner_id = match.athlete_red_id if red_wins > blue_wins else match.athlete_blue_id
        advance_winner(db, match)

    db.commit()
    db.refresh(round_score)
    return round_score
