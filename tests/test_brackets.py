import random

import pytest

from app.services.brackets import (
    NotEnoughAthletes,
    Participant,
    draw_first_round_slots,
    next_power_of_two,
    seeding_order,
)


@pytest.mark.parametrize(
    "n,expected",
    [(1, 1), (2, 2), (3, 4), (4, 4), (5, 8), (7, 8), (8, 8), (9, 16)],
)
def test_next_power_of_two(n, expected):
    assert next_power_of_two(n) == expected


def test_seeding_order_size_8_matches_standard_bracket_order():
    assert seeding_order(8) == [1, 8, 4, 5, 2, 7, 3, 6]


@pytest.mark.parametrize("size", [1, 2, 4, 8, 16, 32])
def test_seeding_order_is_a_permutation_of_all_seeds(size):
    order = seeding_order(size)
    assert sorted(order) == list(range(1, size + 1))




def _people(*clubs, disqualified=()):
    """Un participante por club listado (ids desde 1);  son los ids descalificados."""
    return [Participant(i, club, i in disqualified) for i, club in enumerate(clubs, start=1)]


def _matches(slots):
    return [(slots[i], slots[i + 1]) for i in range(0, len(slots), 2)]


def _same_club_fights(slots, participants):
    club = {p.athlete_id: p.club_id for p in participants}
    off = {p.athlete_id for p in participants if p.disqualified}
    return sum(
        1
        for a, b in _matches(slots)
        if a is not None and b is not None and not {a, b} & off and club[a] == club[b]
    )


def _draw(participants, seed=0):
    return draw_first_round_slots(participants, rng=random.Random(seed))


def test_draw_rejects_fewer_than_two_athletes():
    with pytest.raises(NotEnoughAthletes):
        _draw(_people("A"))


@pytest.mark.parametrize("n", range(2, 20))
def test_draw_places_everyone_once_and_never_puts_two_byes_together(n):
    participants = _people(*[i % 3 for i in range(n)], disqualified={1, 4})
    for seed in range(20):
        slots = _draw(participants, seed)
        assert len(slots) == next_power_of_two(n)
        assert sorted(s for s in slots if s is not None) == list(range(1, n + 1))
        assert all(a is not None or b is not None for a, b in _matches(slots))


def test_draw_is_the_same_with_the_same_seed_and_varies_with_others():
    participants = _people(*range(8))
    assert _draw(participants, 1) == _draw(participants, 1)
    assert len({tuple(_draw(participants, seed)) for seed in range(10)}) > 1


@pytest.mark.parametrize(
    "clubs,unavoidable",
    [
        (("A", "A", "B", "B"), 0),
        (("A", "A", "A", "B"), 1),
        (("A", "A", "A", "B", "C"), 0),  # 5 atletas, 3 byes: los 3 byes van al club grande
        (("A", "A", "A", "B", "B", "B"), 0),  # 2 byes repartidos entre los dos clubes
        (("A", "A", "A", "A", "B", "C"), 0),
        (("A", "A", "A", "A", "A", "B", "C", "D"), 1),
    ],
)
def test_draw_has_the_fewest_same_club_fights_possible(clubs, unavoidable):
    participants = _people(*clubs)
    assert all(_same_club_fights(_draw(participants, seed), participants) == unavoidable for seed in range(30))


def test_byes_go_to_enabled_athletes_while_there_are_enough():
    participants = _people("A", "B", "C", "D", "E", disqualified={1, 2})  # 3 byes, 3 habilitados
    for seed in range(20):
        byes = [a or b for a, b in _matches(_draw(participants, seed)) if None in (a, b)]
        assert sorted(byes) == [3, 4, 5]


def test_a_disqualified_athlete_gets_a_bye_only_when_enabled_ones_run_out():
    participants = _people("A", "B", "C", "D", "E", disqualified={1, 2, 3})  # 3 byes, 2 habilitados
    for seed in range(20):
        byes = [a or b for a, b in _matches(_draw(participants, seed)) if None in (a, b)]
        assert {4, 5} < set(byes) and len(byes) == 3


def test_each_disqualified_athlete_faces_an_enabled_one_before_facing_another_disqualified():
    participants = _people("A", "B", "C", "D", "E", "F", disqualified={1, 2})
    for seed in range(20):
        fights = [m for m in _matches(_draw(participants, seed)) if None not in m]
        assert sorted(sum(1 for a in m if a in (1, 2)) for m in fights) == [1, 1]


def test_disqualified_athletes_face_each_other_only_when_there_are_leftovers():
    participants = _people("A", "B", "C", "D", disqualified={2, 3, 4})
    for seed in range(20):
        fights = [set(m) for m in _matches(_draw(participants, seed))]
        assert any(f <= {2, 3, 4} and len(f) == 2 for f in fights)


def test_fights_against_a_disqualified_athlete_are_not_counted_as_clashes():
    participants = _people("A", "A", "A", disqualified={3})  # 3 atletas: 1 bye, dos van juntos (uno es DSQ)
    for seed in range(20):
        assert _same_club_fights(_draw(participants, seed), participants) == 0
