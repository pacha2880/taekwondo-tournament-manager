import pytest


def test_register_athlete_in_category(client, athlete, category):
    resp = client.post(
        "/api/v1/registrations", json={"athlete_id": athlete["id"], "category_id": category["id"]}
    )
    assert resp.status_code == 201
    assert resp.json()["athlete"]["id"] == athlete["id"]
    assert resp.json()["category"]["id"] == category["id"]


def test_duplicate_registration_rejected(client, athlete, category):
    payload = {"athlete_id": athlete["id"], "category_id": category["id"]}
    client.post("/api/v1/registrations", json=payload)
    resp = client.post("/api/v1/registrations", json=payload)
    assert resp.status_code == 409


def test_gender_mismatch_rejected(client, club, category):
    female_athlete = client.post(
        "/api/v1/athletes",
        json={
            "name": "Maria Lopez",
            "ci": "7654321",
            "birth_date": "2012-03-01",
            "gender": "female",
            "grade": "kup_6",
            "weight_kg": 38,
            "club_id": club["id"],
        },
    ).json()
    resp = client.post(
        "/api/v1/registrations",
        json={"athlete_id": female_athlete["id"], "category_id": category["id"]},
    )
    assert resp.status_code == 422


def test_register_missing_athlete_404(client, category):
    resp = client.post(
        "/api/v1/registrations", json={"athlete_id": 999, "category_id": category["id"]}
    )
    assert resp.status_code == 404


def test_weight_out_of_range_rejected(client, club, category):
    heavy_athlete = client.post(
        "/api/v1/athletes",
        json={
            "name": "Pedro Gomez",
            "ci": "8123456",
            "birth_date": "2012-01-01",
            "gender": "male",
            "grade": "kup_6",
            "weight_kg": 50,
            "club_id": club["id"],
        },
    ).json()
    resp = client.post(
        "/api/v1/registrations",
        json={"athlete_id": heavy_athlete["id"], "category_id": category["id"]},
    )
    assert resp.status_code == 422


def test_athlete_in_second_category_of_same_tournament_rejected(client, db_session, athlete, category, tournament, find_category):
    from app.models import Athlete, Grade

    client.post(
        "/api/v1/registrations",
        json={"athlete_id": athlete["id"], "category_id": category["id"]},
    )
    db_session.get(Athlete, athlete["id"]).grade = Grade.KUP_5  # el PATCH no lo deja con una inscripción que ya no encaja
    db_session.commit()
    other_category = find_category(tournament["id"], "male", "Cadete", "37.1–41 kg", grade_group="Novatos")
    resp = client.post(
        "/api/v1/registrations",
        json={"athlete_id": athlete["id"], "category_id": other_category["id"]},
    )
    assert resp.status_code == 409


@pytest.mark.parametrize("status", ["draft", "weigh_in", "in_progress", "finished"])
def test_registrations_are_only_open_in_registration_open(
    client, athlete, find_category, draft_tournament, status, set_tournament_status
):
    category = find_category(draft_tournament["id"], "male", "Cadete", "37.1–41 kg")
    set_tournament_status(client, draft_tournament["id"], status)

    resp = client.post("/api/v1/registrations", json={"athlete_id": athlete["id"], "category_id": category["id"]})

    assert resp.status_code == 409
    assert resp.json()["detail"] == "Las inscripciones no están abiertas"


def test_delete_registration_frees_the_athlete(client, athlete, category):
    payload = {"athlete_id": athlete["id"], "category_id": category["id"]}
    registration = client.post("/api/v1/registrations", json=payload).json()

    resp = client.delete(f"/api/v1/registrations/{registration['id']}")

    assert resp.status_code == 204
    assert client.get(f"/api/v1/registrations?category_id={category['id']}").json() == []
    assert client.post("/api/v1/registrations", json=payload).status_code == 201


def test_delete_missing_registration_404(client):
    assert client.delete("/api/v1/registrations/999").status_code == 404


@pytest.mark.parametrize("status", ["weigh_in", "in_progress", "finished"])
def test_registrations_cannot_be_deleted_once_registration_closed(
    client, athlete, category, tournament, status, set_tournament_status
):
    registration = client.post(
        "/api/v1/registrations", json={"athlete_id": athlete["id"], "category_id": category["id"]}
    ).json()
    set_tournament_status(client, tournament["id"], status)

    resp = client.delete(f"/api/v1/registrations/{registration['id']}")

    assert resp.status_code == 409
    assert resp.json()["detail"] == "Las inscripciones no están abiertas"


def test_list_registrations_without_filters_returns_all(client, athlete, category):
    client.post("/api/v1/registrations", json={"athlete_id": athlete["id"], "category_id": category["id"]})

    resp = client.get("/api/v1/registrations")

    assert resp.status_code == 200
    assert [r["athlete"]["id"] for r in resp.json()] == [athlete["id"]]


def test_list_registrations_by_tournament_excludes_other_tournaments(client, athlete, category, tournament):
    client.post("/api/v1/registrations", json={"athlete_id": athlete["id"], "category_id": category["id"]})
    other_tournament = client.post(
        "/api/v1/tournaments", json={"name": "Copa Otra", "date": "2026-12-01", "location": "La Paz"}
    ).json()

    mine = client.get("/api/v1/registrations", params={"tournament_id": tournament["id"]}).json()
    other = client.get("/api/v1/registrations", params={"tournament_id": other_tournament["id"]}).json()

    assert [r["athlete"]["id"] for r in mine] == [athlete["id"]]
    assert other == []


def _create_athlete(client, club, **fields):
    data = {
        "name": "Atleta Prueba",
        "birth_date": "2012-05-01",
        "gender": "male",
        "grade": "kup_6",
        "weight_kg": 40.5,
        "club_id": club["id"],
        **fields,
    }
    return client.post("/api/v1/athletes", json=data).json()


def _register(client, athlete, category):
    return client.post("/api/v1/registrations", json={"athlete_id": athlete["id"], "category_id": category["id"]})


def test_too_old_for_category_rejected(client, club, category):
    resp = _register(client, _create_athlete(client, club, birth_date="2010-01-01"), category)
    assert resp.status_code == 422
    assert resp.json()["detail"] == "La edad del atleta (16) no corresponde a la categoría (Cadete: 12 a 14 años)"


def test_too_young_for_category_rejected(client, club, category):
    resp = _register(client, _create_athlete(client, club, birth_date="2015-06-01"), category)
    assert resp.status_code == 422
    assert "La edad del atleta (11)" in resp.json()["detail"]


def test_age_counts_birth_year_not_exact_date(client, club, category):
    first = _register(client, _create_athlete(client, club, birth_date="2014-01-01"), category)
    last = _register(client, _create_athlete(client, club, birth_date="2014-12-31", name="Otro"), category)
    assert first.status_code == last.status_code == 201


def test_grade_outside_group_rejected(client, club, category):
    resp = _register(client, _create_athlete(client, club, grade="kup_4"), category)
    assert resp.status_code == 422
    assert resp.json()["detail"] == "El grado del atleta no corresponde al grupo «Principiantes» de la categoría"


@pytest.mark.parametrize("grade", ["kup_10", "kup_6"])
def test_grade_at_group_edge_accepted(client, club, category, grade):
    assert _register(client, _create_athlete(client, club, grade=grade), category).status_code == 201


def test_festival_checks_only_gender_and_age(client, db_session, club, tournament):
    from sqlalchemy import select

    from app.models import Category, Gender

    festival = db_session.scalars(
        select(Category).where(
            Category.tournament_id == tournament["id"], Category.age_label == "Festival", Category.gender == Gender.MALE
        )
    ).one()
    festival = {"id": festival.id}
    child = _create_athlete(client, club, birth_date="2018-03-01", grade="kup_1", weight_kg=70)
    assert _register(client, child, festival).status_code == 201
    older = _create_athlete(client, club, birth_date="2014-03-01", name="Mayor")
    assert _register(client, older, festival).status_code == 422
