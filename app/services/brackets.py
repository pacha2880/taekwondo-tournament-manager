"""Generación de llaves de eliminación simple con byes.

La parte matemática (`next_power_of_two`, `seeding_order`, `draw_first_round_slots`) no
toca la base de datos a propósito, para poder testearla con casos borde sin levantar
sesiones de SQLAlchemy. `generate_bracket` es la única función que arma la llave.
"""

import random
from collections import Counter
from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import FINAL_MATCH_STATUSES, Athlete, Bracket, Category, Match, MatchStatus, Registration, WeighInStatus

DISQUALIFIED_STATUSES = (WeighInStatus.DISQUALIFIED, WeighInStatus.NO_SHOW)


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


class Participant(NamedTuple):
    athlete_id: int
    club_id: int
    disqualified: bool


def _take_from_largest_clubs(pool: list[Participant], count: int, rng: random.Random) -> list[Participant]:
    """Saca `count` participantes de `pool`, siempre del club que más tiene en ese momento (empate: al azar).

    Así queda lo más parejo posible entre clubes, que es lo que minimiza los choques del resto."""
    by_club: dict[int, list[Participant]] = {}
    for participant in pool:
        by_club.setdefault(participant.club_id, []).append(participant)
    taken = []
    for _ in range(count):
        biggest = max(len(members) for members in by_club.values())
        club = rng.choice([c for c, members in by_club.items() if len(members) == biggest])
        taken.append(by_club[club].pop())
        if not by_club[club]:
            del by_club[club]
    return taken


def _pair_avoiding_same_club(pool: list[Participant], rng: random.Random) -> list[tuple[Participant, Participant]]:
    """Empareja un número par de habilitados con la menor cantidad posible de parejas del mismo club.

    Se ordenan agrupados por club (el más grande primero) y el i-ésimo se empareja con el i-ésimo + m/2. Un club de
    a lo sumo m/2 atletas es contiguo y nunca abarca i e i + m/2, así que no choca; solo el más grande, si pasa de
    m/2, choca c - m/2 veces, que es el mínimo posible (cada pareja admite a lo sumo uno de ese club sin choque).
    """
    pool = list(pool)
    rng.shuffle(pool)
    club_size = Counter(p.club_id for p in pool)
    club_tiebreak = {club: rng.random() for club in club_size}
    pool.sort(key=lambda p: (-club_size[p.club_id], club_tiebreak[p.club_id]))
    half = len(pool) // 2
    pairs = [[a, b] for a, b in zip(pool[:half], pool[half:])]
    # Mezcla sin subir los choques: intercambia atletas entre parejas y deshace el cambio si empeora.
    clashes = lambda pair: pair[0].club_id == pair[1].club_id  # noqa: E731
    for _ in range(len(pairs) * 4):
        if len(pairs) < 2:
            break
        first, second = rng.sample(pairs, 2)
        side_a, side_b = rng.randrange(2), rng.randrange(2)
        before = clashes(first) + clashes(second)
        first[side_a], second[side_b] = second[side_b], first[side_a]
        if clashes(first) + clashes(second) > before:
            first[side_a], second[side_b] = second[side_b], first[side_a]
    return [(a, b) for a, b in pairs]


def draw_first_round_slots(participants: list[Participant], rng: random.Random | None = None) -> list[int | None]:
    """Sortea la primera ronda y devuelve los slots en orden de emparejamiento (0-1 se enfrentan, 2-3, etc.).

    Largo `next_power_of_two(n)`; `None` es un bye. Prioridades: (a) los byes van a habilitados (a los de los clubes
    con más habilitados primero; a un descalificado solo si faltan habilitados); (b) cada descalificado se empareja
    con un habilitado, y solo los que sobran se enfrentan entre sí; (c) entre habilitados, la menor cantidad de
    parejas del mismo club; (d) el resto, al azar. Un descalificado con bye queda solo en su combate.
    """
    if len(participants) < 2:
        raise NotEnoughAthletes("Se necesitan al menos 2 atletas inscritos para generar una llave")
    rng = rng or random.Random()
    size = next_power_of_two(len(participants))
    bye_count = size - len(participants)

    enabled = [p for p in participants if not p.disqualified]
    disqualified = [p for p in participants if p.disqualified]
    rng.shuffle(enabled)
    rng.shuffle(disqualified)

    with_bye = _take_from_largest_clubs(enabled, min(bye_count, len(enabled)), rng)
    with_bye += disqualified[: bye_count - len(with_bye)]
    disqualified = [p for p in disqualified if p not in with_bye]
    enabled = [p for p in enabled if p not in with_bye]

    against_disqualified = _take_from_largest_clubs(enabled, min(len(enabled), len(disqualified)), rng)
    enabled = [p for p in enabled if p not in against_disqualified]
    pairs = list(zip(against_disqualified, disqualified))
    pairs += _pair_avoiding_same_club(enabled, rng)
    leftover = disqualified[len(against_disqualified) :]
    pairs += list(zip(leftover[::2], leftover[1::2]))

    # Los combates con bye son los que tienen un seed > n (nunca dos juntos); el resto son combates reales.
    order = seeding_order(size)
    bye_positions = [i for i in range(size // 2) if max(order[2 * i], order[2 * i + 1]) > len(participants)]
    real_positions = [i for i in range(size // 2) if i not in bye_positions]
    rng.shuffle(with_bye)
    rng.shuffle(pairs)
    matches: dict[int, tuple[Participant | None, Participant | None]] = {}
    for position, participant in zip(bye_positions, with_bye):
        matches[position] = (participant, None)
    for position, pair in zip(real_positions, pairs):
        matches[position] = pair if rng.random() < 0.5 else pair[::-1]
    return [p.athlete_id if p else None for i in range(size // 2) for p in matches[i]]


def resolve_athlete_names(db: Session, matches: list[Match]) -> dict[int, str]:
    """Nombres de los atletas referenciados (rojo/azul/ganador) en `matches`, en una sola
    consulta batch -- evita N+1 queries al mostrar una llave o un combate."""
    athlete_ids = {
        athlete_id
        for match in matches
        for athlete_id in (match.athlete_red_id, match.athlete_blue_id, match.winner_id)
        if athlete_id is not None
    }
    if not athlete_ids:
        return {}
    return {a.id: a.name for a in db.scalars(select(Athlete).where(Athlete.id.in_(athlete_ids)))}


def advance_winner(db: Session, match: Match) -> None:
    """Propaga el ganador de `match` al slot que le corresponde en la siguiente ronda.

    Reusada por el servicio de resultados cuando un combate real termina, y por
    `generate_bracket` y `resolve_pending_walkovers` para los combates que no se pelean.
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


def resolve_pending_walkovers(db: Session, bracket_id: int) -> None:
    """Resuelve los combates que ya no se pueden pelear porque sus dos combates de origen están resueltos y
    al menos uno no mandó ganador (`no_contest`): con un ganador es `walkover`, sin ninguno, `no_contest`.

    Recorre las rondas en orden, así la resolución sube en cascada. Se llama al generar la llave y cada vez que un
    combate real termina. No hace commit."""
    db.flush()
    matches = db.scalars(select(Match).where(Match.bracket_id == bracket_id).order_by(Match.round_number)).all()
    sources: dict[int, list[Match]] = {}
    for match in matches:
        if match.next_match_id is not None:
            sources.setdefault(match.next_match_id, []).append(match)
    for match in matches:
        origins = sources.get(match.id, [])
        if match.status != MatchStatus.PENDING or not origins:
            continue
        if any(origin.status not in FINAL_MATCH_STATUSES for origin in origins):
            continue
        winners = [origin.winner_id for origin in origins if origin.winner_id is not None]
        if len(winners) == 2:
            continue
        match.status = MatchStatus.WALKOVER if winners else MatchStatus.NO_CONTEST
        match.winner_id = winners[0] if winners else None
        advance_winner(db, match)


def disqualified_athlete_ids(db: Session, category_id: int) -> set[int]:
    """Atletas descalificados (`disqualified` o `no_show`) de la categoría, en una sola consulta."""
    return set(
        db.scalars(
            select(Registration.athlete_id).where(
                Registration.category_id == category_id, Registration.weigh_in_status.in_(DISQUALIFIED_STATUSES)
            )
        )
    )


def fill_athlete_details(db: Session, category_id: int, match_reads: list) -> None:
    """Completa en los `MatchRead` los nombres de los atletas y si cada lado está descalificado."""
    names = resolve_athlete_names(db, match_reads)
    disqualified = disqualified_athlete_ids(db, category_id)
    for match_read in match_reads:
        match_read.athlete_red_name = names.get(match_read.athlete_red_id)
        match_read.athlete_blue_name = names.get(match_read.athlete_blue_id)
        match_read.winner_name = names.get(match_read.winner_id)
        match_read.athlete_red_disqualified = match_read.athlete_red_id in disqualified
        match_read.athlete_blue_disqualified = match_read.athlete_blue_id in disqualified


def generate_bracket(db: Session, category: Category, rng: random.Random | None = None) -> Bracket:
    """Sortea la llave y resuelve la primera ronda y su cascada. Hace flush, no commit: lo hace quien llama."""
    if db.scalar(select(Bracket).where(Bracket.category_id == category.id)):
        raise BracketAlreadyExists(f"La categoría {category.id} ya tiene una llave generada")

    participants = [
        Participant(athlete_id, club_id, status in DISQUALIFIED_STATUSES)
        for athlete_id, club_id, status in db.execute(
            select(Registration.athlete_id, Athlete.club_id, Registration.weigh_in_status)
            .join(Athlete, Registration.athlete_id == Athlete.id)
            .where(Registration.category_id == category.id)
        )
    ]
    first_round_slots = draw_first_round_slots(participants, rng=rng)
    disqualified = {p.athlete_id for p in participants if p.disqualified}
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
        sides = [side for side in (red, blue) if side is not None]
        fighters = [side for side in sides if side not in disqualified]
        if len(sides) == 1 and fighters:
            match.status = MatchStatus.BYE
        elif len(fighters) == 1:
            match.status = MatchStatus.WALKOVER
        elif len(fighters) == 0:
            match.status = MatchStatus.NO_CONTEST
        if fighters and len(fighters) < 2:
            match.winner_id = fighters[0]
            advance_winner(db, match)

    resolve_pending_walkovers(db, bracket.id)
    return bracket
