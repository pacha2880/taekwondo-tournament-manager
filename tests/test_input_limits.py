"""Valores que no caben en la columna de Postgres: SQLite los guarda igual, así que sin estos límites la suite pasaba
y en producción la API respondía 500 en vez de 422."""

import pytest
from pydantic import ValidationError

from app.schemas import INT4_MAX, RoundScoreCreate

TOO_BIG = INT4_MAX + 1

ATHLETE = {"name": "Ana Rojas", "birth_date": "2011-02-03", "gender": "female", "grade": "kup_4", "weight_kg": 36}
TOURNAMENT = {"name": "Copa", "date": "2026-11-15", "location": "Cochabamba"}


@pytest.mark.parametrize(
    "method, path, body",
    [
        ("post", "/api/v1/clubs", lambda ids: {"name": "x" * 121}),
        ("patch", "/api/v1/clubs/{club}", lambda ids: {"name": "x" * 121}),
        ("post", "/api/v1/athletes", lambda ids: {**ATHLETE, "club_id": ids["club"], "name": "x" * 121}),
        ("patch", "/api/v1/athletes/{athlete}", lambda ids: {"name": "x" * 121}),
        ("post", "/api/v1/tournaments", lambda ids: {**TOURNAMENT, "name": "x" * 151}),
        ("post", "/api/v1/tournaments", lambda ids: {**TOURNAMENT, "location": "x" * 151}),
        ("patch", "/api/v1/tournaments/{tournament}", lambda ids: {"name": "x" * 151}),
        ("patch", "/api/v1/tournaments/{tournament}", lambda ids: {"location": "x" * 151}),
        ("post", "/api/v1/athletes", lambda ids: {**ATHLETE, "club_id": TOO_BIG}),
        ("patch", "/api/v1/athletes/{athlete}", lambda ids: {"club_id": TOO_BIG}),
        ("post", "/api/v1/registrations", lambda ids: {"athlete_id": TOO_BIG, "category_id": ids["category"]}),
        ("post", "/api/v1/registrations", lambda ids: {"athlete_id": ids["athlete"], "category_id": TOO_BIG}),
    ],
)
def test_values_that_do_not_fit_the_column_are_rejected(client, club, athlete, tournament, category, method, path, body):
    ids = {"club": club["id"], "athlete": athlete["id"], "tournament": tournament["id"], "category": category["id"]}

    resp = getattr(client, method)(path.format(**ids), json=body(ids))

    assert resp.status_code == 422


def test_a_name_exactly_as_long_as_the_column_is_accepted(client):
    assert client.post("/api/v1/clubs", json={"name": "x" * 120}).status_code == 201


@pytest.mark.parametrize("points", [{"red_points": TOO_BIG}, {"blue_points": TOO_BIG}, {"round_number": TOO_BIG}, {"round_number": 0}])
def test_round_points_must_fit_the_column(points):
    with pytest.raises(ValidationError):
        RoundScoreCreate(**{"round_number": 1, "red_points": 0, "blue_points": 0, **points})
