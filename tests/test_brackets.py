import random

import pytest

from app.services.brackets import (
    NotEnoughAthletes,
    build_first_round_slots,
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


def test_build_first_round_slots_rejects_fewer_than_two_athletes():
    with pytest.raises(NotEnoughAthletes):
        build_first_round_slots([1])


def test_build_first_round_slots_exact_power_of_two_has_no_byes():
    slots = build_first_round_slots([1, 2, 3, 4], rng=random.Random(0))
    assert len(slots) == 4
    assert None not in slots
    assert sorted(slots) == [1, 2, 3, 4]


def test_build_first_round_slots_pads_to_next_power_of_two_with_byes():
    athlete_ids = [10, 11, 12, 13, 14]
    slots = build_first_round_slots(athlete_ids, rng=random.Random(1))
    assert len(slots) == 8
    real = [a for a in slots if a is not None]
    assert sorted(real) == sorted(athlete_ids)
    assert slots.count(None) == 3


@pytest.mark.parametrize("n", range(2, 20))
def test_no_two_byes_ever_share_a_first_round_match(n):
    athlete_ids = list(range(n))
    for seed in range(20):
        slots = build_first_round_slots(athlete_ids, rng=random.Random(seed))
        for i in range(0, len(slots), 2):
            assert not (slots[i] is None and slots[i + 1] is None), (
                f"n={n} seed={seed} slots={slots}"
            )
