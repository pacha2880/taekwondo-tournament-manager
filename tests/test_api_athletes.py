import pytest


def test_create_athlete_requires_existing_club(client):
    resp = client.post(
        "/api/v1/athletes",
        json={
            "name": "Sin Club",
            "ci": "5555555",
            "birth_date": "2010-01-01",
            "gender": "female",
            "belt_rank": "amarillo",
            "weight_kg": 35,
            "club_id": 999,
        },
    )
    assert resp.status_code == 404


def test_create_and_get_athlete(client, athlete):
    assert athlete["name"] == "Juan Perez"
    assert athlete["club"]["name"] == "Dojang Central"

    resp = client.get(f"/api/v1/athletes/{athlete['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == athlete["id"]


def _athlete_payload(club, **overrides):
    payload = {
        "name": "Ana Rojas",
        "ci": "7654321",
        "birth_date": "2011-02-03",
        "gender": "female",
        "belt_rank": "azul",
        "weight_kg": 36,
        "club_id": club["id"],
    }
    return {**payload, **overrides}


def test_ci_is_optional_and_several_athletes_can_have_none(client, club):
    without_field = _athlete_payload(club)
    del without_field["ci"]

    first = client.post("/api/v1/athletes", json=without_field)
    second = client.post("/api/v1/athletes", json=_athlete_payload(club, name="Otro", ci=None))

    assert first.status_code == second.status_code == 201
    assert first.json()["ci"] is None
    assert second.json()["ci"] is None


@pytest.mark.parametrize("ci", ["1234567", "12345", "123456789", "1234567-1A", "1234567-AB", "1234567-11"])
def test_valid_ci_is_accepted(client, club, ci):
    resp = client.post("/api/v1/athletes", json=_athlete_payload(club, ci=ci))

    assert resp.status_code == 201
    assert resp.json()["ci"] == ci


@pytest.mark.parametrize(
    "ci",
    ["1234", "1234567890", "ABC1234", "1234567-", "1234567-1", "1234567-1AB", "1234567 1A", "1234567-1a-", "١٢٣٤٥٦٧", "12.345.678"],
)
def test_invalid_ci_is_rejected(client, club, ci):
    resp = client.post("/api/v1/athletes", json=_athlete_payload(club, ci=ci))

    assert resp.status_code == 422


@pytest.mark.parametrize("empty", ["", "   "])
def test_empty_ci_is_stored_as_no_ci(client, club, empty):
    first = client.post("/api/v1/athletes", json=_athlete_payload(club, ci=empty))
    second = client.post("/api/v1/athletes", json=_athlete_payload(club, name="Otro", ci=empty))

    assert first.status_code == second.status_code == 201
    assert first.json()["ci"] is None
    assert second.json()["ci"] is None


def test_ci_is_trimmed_and_uppercased(client, club):
    resp = client.post("/api/v1/athletes", json=_athlete_payload(club, ci="  1234567-1a "))

    assert resp.status_code == 201
    assert resp.json()["ci"] == "1234567-1A"


def test_duplicate_ci_is_rejected_even_with_different_case_or_spaces(client, club):
    client.post("/api/v1/athletes", json=_athlete_payload(club, ci="1234567-1A"))

    resp = client.post("/api/v1/athletes", json=_athlete_payload(club, name="Otra", ci=" 1234567-1a"))

    assert resp.status_code == 409
    assert resp.json()["detail"] == "Ya existe un atleta con ese CI"


def test_same_number_with_a_different_complement_is_another_person(client, club):
    first = client.post("/api/v1/athletes", json=_athlete_payload(club, ci="1234567"))
    second = client.post("/api/v1/athletes", json=_athlete_payload(club, name="Otra", ci="1234567-1A"))

    assert first.status_code == 201
    assert second.status_code == 201
