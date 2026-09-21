"""Generación de llaves de eliminación simple con byes.

La parte matemática (`next_power_of_two`, `seeding_order`, `build_first_round_slots`) no
toca la base de datos a propósito, para poder testearla con casos borde sin levantar
sesiones de SQLAlchemy. `generate_bracket` es la única función que persiste.
"""

import random

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Bracket, Category, Match, MatchStatus, Registration


class BracketAlreadyExists(Exception):
    pass


class NotEnoughAthletes(Exception):
    pass


def next_power_of_two(n: int) -> int:
    power = 1
    while power < n:
        power *= 2
    return power


def seeding_order(size: int) -> list[int]:
    """Orden estándar de seeds (1..size) en posición de bracket.

    Algoritmo recursivo: para reducir a la mitad, cada seed de la mitad "buena" se
    empareja con su complemento (size + 1 - seed). Esta es la construcción clásica de
    brackets de torneo y tiene la propiedad de que, si los byes ocupan siempre los
    números de seed más altos (n+1..size), nunca quedan dos byes en el mismo
    enfrentamiento — siempre que haya más atletas reales que byes, lo cual está
    garantizado porque `size` es la potencia de 2 más chica >= n.
    """
    if size == 1:
        return [1]
    prev = seeding_order(size // 2)
    order: list[int] = []
    for seed in prev:
        order.append(seed)
        order.append(size + 1 - seed)
    return order


def build_first_round_slots(
    athlete_ids: list[int], rng: random.Random | None = None
) -> list[int | None]:
    """Mezcla los atletas y los ubica en las posiciones de primera ronda.

    Devuelve una lista de longitud `next_power_of_two(len(athlete_ids))` en el orden de
    emparejamiento de la ronda 1 (posiciones 0-1 se enfrentan, 2-3 se enfrentan, etc.).
    `None` representa un bye.
    """
    if len(athlete_ids) < 2:
        raise NotEnoughAthletes("Se necesitan al menos 2 atletas inscritos para generar una llave")

    shuffler = rng or random
    shuffled = list(athlete_ids)
    shuffler.shuffle(shuffled)

    size = next_power_of_two(len(shuffled))
    order = seeding_order(size)
    seed_to_athlete: dict[int, int | None] = {
        seed: (shuffled[seed - 1] if seed <= len(shuffled) else None)
        for seed in range(1, size + 1)
    }
    return [seed_to_athlete[seed] for seed in order]


def advance_winner(db: Session, match: Match) -> None:
    """Propaga el ganador de `match` al slot que le corresponde en la siguiente ronda.

    Reusada por el servicio de resultados (fase 4) cuando un combate real termina, y por
    `generate_bracket` para resolver los byes de la ronda 1 de inmediato.
    """
    if match.next_match_id is None or match.winner_id is None:
        return
    next_match = db.get(Match, match.next_match_id)
    if next_match is None:
        return
    if match.slot % 2 == 0:
        next_match.athlete_red_id = match.winner_id
    else:
        next_match.athlete_blue_id = match.winner_id


def generate_bracket(db: Session, category: Category, rng: random.Random | None = None) -> Bracket:
    if db.scalar(select(Bracket).where(Bracket.category_id == category.id)):
        raise BracketAlreadyExists(f"La categoría {category.id} ya tiene una llave generada")

    athlete_ids = list(
        db.scalars(select(Registration.athlete_id).where(Registration.category_id == category.id))
    )
    first_round_slots = build_first_round_slots(athlete_ids, rng=rng)
    size = len(first_round_slots)
    num_rounds = size.bit_length() - 1

    bracket = Bracket(category_id=category.id, size=size)
    db.add(bracket)
    db.flush()

    rounds: list[list[Match]] = []
    matches_in_round = size // 2
    for round_number in range(1, num_rounds + 1):
        round_matches = [
            Match(
                bracket_id=bracket.id,
                round_number=round_number,
                slot=slot,
                status=MatchStatus.PENDING,
            )
            for slot in range(matches_in_round)
        ]
        db.add_all(round_matches)
        rounds.append(round_matches)
        matches_in_round //= 2
    db.flush()

    for round_number in range(num_rounds - 1):
        current_round = rounds[round_number]
        next_round = rounds[round_number + 1]
        for slot, match in enumerate(current_round):
            match.next_match_id = next_round[slot // 2].id

    first_round = rounds[0]
    for slot, match in enumerate(first_round):
        red = first_round_slots[2 * slot]
        blue = first_round_slots[2 * slot + 1]
        match.athlete_red_id = red
        match.athlete_blue_id = blue
        if red is None or blue is None:
            match.status = MatchStatus.BYE
            match.winner_id = red if blue is None else blue
            advance_winner(db, match)

    db.commit()
    db.refresh(bracket)
    return bracket
