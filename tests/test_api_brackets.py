def _register_n_athletes(client, club, category, n):
    registrations = []
    for i in range(n):
        athlete = client.post(
            "/api/v1/athletes",
            json={
                "name": f"Atleta {i}",
                "birth_date": "2012-01-01",
                "gender": "male",
                "belt_rank": "verde",
                "weight_kg": 40,
                "club_id": club["id"],
            },
        ).json()
        resp = client.post(
            "/api/v1/registrations",
            json={"athlete_id": athlete["id"], "category_id": category["id"]},
        )
        registrations.append(resp.json())
    return registrations


def test_generate_bracket_requires_existing_category(client):
    resp = client.post("/api/v1/categories/999/bracket")
    assert resp.status_code == 404


def test_generate_bracket_requires_at_least_two_athletes(client, category):
    resp = client.post(f"/api/v1/categories/{category['id']}/bracket")
    assert resp.status_code == 400


def test_generate_bracket_with_five_athletes_has_three_byes(client, club, category):
    _register_n_athletes(client, club, category, 5)

    resp = client.post(f"/api/v1/categories/{category['id']}/bracket")
    assert resp.status_code == 201
    bracket = resp.json()

    assert bracket["size"] == 8
    matches = bracket["matches"]
    assert len(matches) == 7  # 4 + 2 + 1

    round1 = [m for m in matches if m["round_number"] == 1]
    assert len(round1) == 4
    byes = [m for m in round1 if m["status"] == "bye"]
    assert len(byes) == 3
    for bye_match in byes:
        assert bye_match["winner_id"] is not None

    pending = [m for m in round1 if m["status"] == "pending"]
    assert len(pending) == 1
    assert pending[0]["athlete_red_id"] is not None
    assert pending[0]["athlete_blue_id"] is not None


def test_bye_winners_are_already_placed_in_round_two(client, club, category):
    _register_n_athletes(client, club, category, 5)
    bracket = client.post(f"/api/v1/categories/{category['id']}/bracket").json()

    matches_by_id = {m["id"]: m for m in bracket["matches"]}
    round1_byes = [m for m in bracket["matches"] if m["round_number"] == 1 and m["status"] == "bye"]

    for bye_match in round1_byes:
        next_match = matches_by_id[bye_match["next_match_id"]]
        assert bye_match["winner_id"] in (next_match["athlete_red_id"], next_match["athlete_blue_id"])


def test_cannot_generate_bracket_twice(client, club, category):
    _register_n_athletes(client, club, category, 4)
    client.post(f"/api/v1/categories/{category['id']}/bracket")

    resp = client.post(f"/api/v1/categories/{category['id']}/bracket")
    assert resp.status_code == 409


def test_get_bracket_before_generation_404(client, category):
    resp = client.get(f"/api/v1/categories/{category['id']}/bracket")
    assert resp.status_code == 404


def test_get_bracket_after_generation(client, club, category):
    _register_n_athletes(client, club, category, 4)
    created = client.post(f"/api/v1/categories/{category['id']}/bracket").json()

    resp = client.get(f"/api/v1/categories/{category['id']}/bracket")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]
