import pytest


def test_create_category_requires_existing_tournament(client):
    resp = client.post(
        "/api/v1/categories",
        json={
            "tournament_id": 999,
            "gender": "male",
            "age_label": "Junior",
            "min_age": 15,
            "max_age": 17,
            "belt_group": "color",
            "weight_label": "Hasta 55kg",
        },
    )
    assert resp.status_code == 404


def test_create_category_defaults_discipline_to_sparring(client, category):
    assert category["discipline"] == "sparring"


def test_list_categories_filtered_by_tournament(client, category, tournament):
    client.post("/api/v1/tournaments", json={"name": "Otro", "date": "2026-12-01", "location": "La Paz"}).json()

    resp = client.get("/api/v1/categories", params={"tournament_id": tournament["id"]})

    assert resp.status_code == 200
    assert category["id"] in [c["id"] for c in resp.json()]
    assert {c["tournament_id"] for c in resp.json()} == {tournament["id"]}


def test_list_categories_without_filter_returns_all(client, category):
    other = client.post("/api/v1/tournaments", json={"name": "Otro", "date": "2026-12-01", "location": "La Paz"}).json()

    resp = client.get("/api/v1/categories")

    assert resp.status_code == 200
    assert {c["tournament_id"] for c in resp.json()} == {category["tournament_id"], other["id"]}


def test_create_category_rejects_min_weight_greater_than_max_weight(client, tournament):
    resp = client.post(
        "/api/v1/categories",
        json={
            "tournament_id": tournament["id"],
            "gender": "male",
            "age_label": "Junior",
            "min_age": 15,
            "max_age": 17,
            "belt_group": "color",
            "weight_label": "Hasta 55kg",
            "min_weight": 60,
            "max_weight": 55,
        },
    )
    assert resp.status_code == 422


@pytest.mark.parametrize("weights", [{"min_weight": 45.15}, {"max_weight": 55.25}])
def test_create_category_rejects_weights_with_more_than_one_decimal(client, tournament, weights):
    resp = client.post(
        "/api/v1/categories",
        json={
            "tournament_id": tournament["id"],
            "gender": "male",
            "age_label": "Junior",
            "min_age": 15,
            "max_age": 17,
            "belt_group": "color",
            "weight_label": "Hasta 55kg",
            **weights,
        },
    )
    assert resp.status_code == 422


def test_create_category_rejects_min_age_greater_than_max_age(client, tournament):
    resp = client.post(
        "/api/v1/categories",
        json={
            "tournament_id": tournament["id"],
            "gender": "male",
            "age_label": "Junior",
            "min_age": 17,
            "max_age": 15,
            "belt_group": "color",
            "weight_label": "Hasta 55kg",
        },
    )
    assert resp.status_code == 422


@pytest.mark.parametrize("status", ["in_progress", "finished"])
def test_categories_cannot_be_created_once_the_tournament_started(client, tournament, status, set_tournament_status):
    set_tournament_status(client, tournament["id"], status)

    resp = client.post(
        "/api/v1/categories",
        json={
            "tournament_id": tournament["id"],
            "gender": "male",
            "age_label": "Cadete",
            "min_age": 12,
            "belt_group": "color",
            "weight_label": "Libre",
        },
    )

    assert resp.status_code == 409
    assert resp.json()["detail"] == "Ya no se pueden crear categorías: el torneo ya empezó"


def test_registrants_are_public_sorted_by_name_and_only_with_name_and_club(
    anon_client, client, club, athlete, category, register_n_athletes
):
    register_n_athletes(client, club, category, 2)
    client.post("/api/v1/registrations", json={"athlete_id": athlete["id"], "category_id": category["id"]})

    resp = anon_client.get(f"/api/v1/categories/{category['id']}/registrants")

    assert resp.status_code == 200
    assert [r["name"] for r in resp.json()] == ["Atleta 0", "Atleta 1", "Juan Perez"]
    assert resp.json()[-1] == {"athlete_id": athlete["id"], "name": "Juan Perez", "club": "Dojang Central"}


def test_registrants_of_a_missing_category_is_404(anon_client):
    assert anon_client.get("/api/v1/categories/999/registrants").status_code == 404


def test_has_bracket_tells_whether_the_bracket_was_generated(client, club, category, register_n_athletes, generate_bracket):
    register_n_athletes(client, club, category, 2)
    url = f"/api/v1/categories/{category['id']}"

    before = client.get(url).json()["has_bracket"]
    generate_bracket(client, category)
    after = client.get(url).json()["has_bracket"]
    listed = client.get("/api/v1/categories", params={"tournament_id": category["tournament_id"]}).json()

    assert (before, after) == (False, True)
    assert [c["has_bracket"] for c in listed if c["id"] == category["id"]] == [True]
