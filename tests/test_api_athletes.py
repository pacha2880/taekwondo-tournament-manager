def test_create_athlete_requires_existing_club(client):
    resp = client.post(
        "/api/v1/athletes",
        json={
            "name": "Sin Club",
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
