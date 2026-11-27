from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.models import Category, Gender
from app.services.eligibility import category_mismatch, weight_mismatch


@pytest.fixture()
def registration(client, athlete, category):
    resp = client.post("/api/v1/registrations", json={"athlete_id": athlete["id"], "category_id": category["id"]})
    return resp.json()


@pytest.fixture()
def weigh_in_registration(client, registration, tournament, set_tournament_status):
    """La inscripción de la categoría 37.1-41 kg, con el torneo ya en pesaje."""
    set_tournament_status(client, tournament["id"], "weigh_in")
    return registration


@pytest.fixture()
def festival_registration(client, club, tournament, db_session, set_tournament_status):
    festival = db_session.scalars(
        select(Category).where(
            Category.tournament_id == tournament["id"], Category.age_label == "Festival", Category.gender == Gender.MALE
        )
    ).one()
    kid = client.post(
        "/api/v1/athletes",
        json={
            "name": "Beto Chico", "ci": "9990001", "birth_date": "2018-01-01", "gender": "male",
            "grade": "kup_10", "weight_kg": 25, "club_id": club["id"],
        },
    ).json()
    resp = client.post("/api/v1/registrations", json={"athlete_id": kid["id"], "category_id": festival.id})
    assert resp.status_code == 201
    set_tournament_status(client, tournament["id"], "weigh_in")
    return resp.json()


def _url(registration, action="weigh-in"):
    return f"/api/v1/registrations/{registration['id']}/{action}"


def _weigh(client, registration, weight):
    return client.post(_url(registration), json={"weight_kg": weight})


def test_new_registration_starts_pending(registration):
    assert registration["weigh_in_status"] == "pending"
    assert registration["first_weight_kg"] is None
    assert registration["second_weight_kg"] is None


def test_new_festival_registration_is_not_required(festival_registration):
    assert festival_registration["weigh_in_status"] == "not_required"


def test_first_weight_that_fits_clears(client, weigh_in_registration):
    resp = _weigh(client, weigh_in_registration, 40.5)

    assert resp.status_code == 200
    assert resp.json()["weigh_in_status"] == "cleared"
    assert resp.json()["first_weight_kg"] == 40.5


def test_first_weight_that_does_not_fit_fails_first(client, weigh_in_registration):
    resp = _weigh(client, weigh_in_registration, 42.0)

    assert resp.status_code == 200
    assert resp.json()["weigh_in_status"] == "failed_first"
    assert resp.json()["first_weight_kg"] == 42.0


def test_second_weigh_in_flow_clears(client, weigh_in_registration):
    _weigh(client, weigh_in_registration, 42.0)
    assert client.post(_url(weigh_in_registration, "second-weigh-in")).json()["weigh_in_status"] == "second_allowed"

    resp = _weigh(client, weigh_in_registration, 41.0)

    assert resp.json()["weigh_in_status"] == "cleared"
    assert resp.json()["first_weight_kg"] == 42.0
    assert resp.json()["second_weight_kg"] == 41.0


def test_second_weight_that_does_not_fit_disqualifies(client, weigh_in_registration):
    _weigh(client, weigh_in_registration, 42.0)
    client.post(_url(weigh_in_registration, "second-weigh-in"))

    resp = _weigh(client, weigh_in_registration, 41.5)

    assert resp.json()["weigh_in_status"] == "disqualified"
    assert resp.json()["second_weight_kg"] == 41.5


def test_disqualify_after_failed_first(client, weigh_in_registration):
    _weigh(client, weigh_in_registration, 36.0)

    resp = client.post(_url(weigh_in_registration, "disqualify"))

    assert resp.status_code == 200
    assert resp.json()["weigh_in_status"] == "disqualified"


@pytest.mark.parametrize("action", ["second-weigh-in", "disqualify"])
def test_decisions_need_failed_first(client, weigh_in_registration, action):
    resp = client.post(_url(weigh_in_registration, action))

    assert resp.status_code == 409
    assert resp.json()["detail"] == "No se puede hacer esto: el atleta todavía no se pesó"


def test_cannot_weigh_a_cleared_registration(client, weigh_in_registration):
    _weigh(client, weigh_in_registration, 40.5)

    resp = _weigh(client, weigh_in_registration, 40.0)

    assert resp.status_code == 409
    assert resp.json()["detail"] == "No se puede hacer esto: el atleta ya está habilitado"


def test_cannot_weigh_while_waiting_for_the_admin_decision(client, weigh_in_registration):
    _weigh(client, weigh_in_registration, 42.0)

    assert _weigh(client, weigh_in_registration, 41.0).status_code == 409


def test_delete_weigh_in_resets_status_and_weights(client, weigh_in_registration):
    _weigh(client, weigh_in_registration, 42.0)
    client.post(_url(weigh_in_registration, "second-weigh-in"))
    _weigh(client, weigh_in_registration, 41.5)

    resp = client.delete(_url(weigh_in_registration))

    assert resp.status_code == 200
    assert resp.json()["weigh_in_status"] == "pending"
    assert resp.json()["first_weight_kg"] is None
    assert resp.json()["second_weight_kg"] is None


def test_delete_weigh_in_on_pending_is_idempotent(client, weigh_in_registration):
    resp = client.delete(_url(weigh_in_registration))

    assert resp.status_code == 200
    assert resp.json()["weigh_in_status"] == "pending"


@pytest.mark.parametrize(
    ("weight", "status"), [(37.1, "cleared"), (41.0, "cleared"), (37.0, "failed_first"), (41.1, "failed_first")]
)
def test_the_category_limits_are_inclusive_and_without_tolerance(client, weigh_in_registration, weight, status):
    assert _weigh(client, weigh_in_registration, weight).json()["weigh_in_status"] == status


@pytest.mark.parametrize("weight", [40.55, 0, -1])
def test_invalid_weights_rejected(client, weigh_in_registration, weight):
    assert _weigh(client, weigh_in_registration, weight).status_code == 422


def test_unknown_registration_404(client, tournament, set_tournament_status):
    set_tournament_status(client, tournament["id"], "weigh_in")

    assert client.post("/api/v1/registrations/999/weigh-in", json={"weight_kg": 40}).status_code == 404
    assert client.post("/api/v1/registrations/999/second-weigh-in").status_code == 404
    assert client.post("/api/v1/registrations/999/disqualify").status_code == 404
    assert client.delete("/api/v1/registrations/999/weigh-in").status_code == 404


def test_weigh_in_endpoints_need_the_tournament_in_weigh_in(client, registration):
    for resp in (
        _weigh(client, registration, 40.5),
        client.post(_url(registration, "second-weigh-in")),
        client.post(_url(registration, "disqualify")),
        client.delete(_url(registration)),
    ):
        assert resp.status_code == 409
        assert resp.json()["detail"] == "El pesaje solo se carga con el torneo en pesaje"


def test_festival_needs_no_weigh_in(client, festival_registration):
    for resp in (
        _weigh(client, festival_registration, 25),
        client.post(_url(festival_registration, "second-weigh-in")),
        client.post(_url(festival_registration, "disqualify")),
        client.delete(_url(festival_registration)),
    ):
        assert resp.status_code == 409
        assert resp.json()["detail"] == "Festival no necesita pesaje"


def test_weigh_in_requires_a_token(anon_client):
    assert anon_client.post("/api/v1/registrations/1/weigh-in", json={"weight_kg": 40}).status_code == 401
    assert anon_client.post("/api/v1/registrations/1/second-weigh-in").status_code == 401
    assert anon_client.post("/api/v1/registrations/1/disqualify").status_code == 401
    assert anon_client.delete("/api/v1/registrations/1/weigh-in").status_code == 401


def test_category_mismatch_keeps_its_weight_messages(category, db_session):
    stored = db_session.get(Category, category["id"])
    athlete = SimpleNamespace(gender=stored.gender, weight_kg=30, grade=None, birth_date=None)
    assert category_mismatch(athlete, stored) == "El peso del atleta es menor al mínimo de la categoría"
    athlete.weight_kg = 50
    assert category_mismatch(athlete, stored) == "El peso del atleta es mayor al máximo de la categoría"
    assert weight_mismatch(40.5, stored) is None
