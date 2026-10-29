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
    resp = client.get("/api/v1/categories", params={"tournament_id": tournament["id"]})
    assert resp.status_code == 200
    assert len(resp.json()) == 1


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
