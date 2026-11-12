from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Match, MatchStatus, RoundScore
from app.services.brackets import advance_winner


class MatchNotReady(Exception):
    pass


class MatchAlreadyFinished(Exception):
    pass


class TiedRound(Exception):
    pass


class RoundOutOfOrder(Exception):
    pass


def _rounds_won(db: Session, match_id: int, athlete_id: int) -> int:
    return db.scalar(
        select(func.count())
        .select_from(RoundScore)
        .where(RoundScore.match_id == match_id, RoundScore.round_winner_id == athlete_id)
    )


def record_round(db: Session, match: Match, round_number: int, red_points: int, blue_points: int) -> RoundScore:
    """Registra un round (no puede empatar). El combate pasa a FINISHED, y el ganador avanza,
    recién al llegar a `category.rounds_to_win` rounds ganados.

    `round_number` tiene que ser el siguiente: así un reenvío (la respuesta se perdió por mala señal) se rechaza
    en vez de guardarse como el round siguiente."""
    if match.athlete_red_id is None or match.athlete_blue_id is None:
        raise MatchNotReady("El combate todavía no tiene ambos atletas definidos")
    if match.status == MatchStatus.FINISHED:
        raise MatchAlreadyFinished("El combate ya está finalizado")
    next_round = db.scalar(select(func.count()).select_from(RoundScore).where(RoundScore.match_id == match.id)) + 1
    if round_number != next_round:
        raise RoundOutOfOrder(f"El round que sigue es el {next_round}, no el {round_number}; recargá el combate")
    if red_points == blue_points:
        raise TiedRound("Un round no puede terminar en empate")

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
