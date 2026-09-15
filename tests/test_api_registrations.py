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
            "birth_date": "2012-03-01",
            "gender": "female",
            "belt_rank": "verde",
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
            "birth_date": "2012-01-01",
            "gender": "male",
            "belt_rank": "verde",
            "weight_kg": 50,
            "club_id": club["id"],
        },
    ).json()
    resp = client.post(
        "/api/v1/registrations",
        json={"athlete_id": heavy_athlete["id"], "category_id": category["id"]},
    )
    assert resp.status_code == 422


def test_athlete_in_second_category_of_same_tournament_rejected(client, athlete, category, tournament):
    client.post(
        "/api/v1/registrations",
        json={"athlete_id": athlete["id"], "category_id": category["id"]},
    )
    other_category = client.post(
        "/api/v1/categories",
        json={
            "tournament_id": tournament["id"],
            "gender": "male",
            "age_label": "Cadete",
            "min_age": 12,
            "max_age": 14,
            "belt_group": "color",
            "weight_label": "Todos los pesos",
        },
    ).json()
    resp = client.post(
        "/api/v1/registrations",
        json={"athlete_id": athlete["id"], "category_id": other_category["id"]},
    )
    assert resp.status_code == 409
