def test_match_not_ready_rejects_round_score(client, club, category, register_n_athletes):
    register_n_athletes(client, club, category, 5)
    bracket = client.post(f"/api/v1/categories/{category['id']}/bracket").json()
    not_ready = next(
        m
        for m in bracket["matches"]
        if m["status"] == "pending" and (m["athlete_red_id"] is None or m["athlete_blue_id"] is None)
    )

    resp = client.post(
        f"/api/v1/matches/{not_ready['id']}/rounds",
        json={"round_number": 1, "red_points": 10, "blue_points": 5},
    )
    assert resp.status_code == 400


def test_tied_round_rejected(client, club, category, register_n_athletes):
    register_n_athletes(client, club, category, 2)
    match = client.post(f"/api/v1/categories/{category['id']}/bracket").json()["matches"][0]

    resp = client.post(
        f"/api/v1/matches/{match['id']}/rounds",
        json={"round_number": 1, "red_points": 5, "blue_points": 5},
    )
    assert resp.status_code == 422


def test_duplicate_round_number_rejected(client, club, category, register_n_athletes):
    register_n_athletes(client, club, category, 2)
    match = client.post(f"/api/v1/categories/{category['id']}/bracket").json()["matches"][0]
    client.post(
        f"/api/v1/matches/{match['id']}/rounds",
        json={"round_number": 1, "red_points": 10, "blue_points": 5},
    )

    resp = client.post(
        f"/api/v1/matches/{match['id']}/rounds",
        json={"round_number": 1, "red_points": 3, "blue_points": 9},
    )
    assert resp.status_code == 409


def test_match_finishes_after_two_round_wins(client, club, category, register_n_athletes):
    register_n_athletes(client, club, category, 2)
    match = client.post(f"/api/v1/categories/{category['id']}/bracket").json()["matches"][0]

    client.post(
        f"/api/v1/matches/{match['id']}/rounds",
        json={"round_number": 1, "red_points": 10, "blue_points": 5},
    )
    resp = client.post(
        f"/api/v1/matches/{match['id']}/rounds",
        json={"round_number": 2, "red_points": 8, "blue_points": 3},
    )
    assert resp.status_code == 201

    finished = client.get(f"/api/v1/matches/{match['id']}").json()
    assert finished["status"] == "finished"
    assert finished["winner_id"] == match["athlete_red_id"]
    assert len(finished["round_scores"]) == 2


def test_match_can_go_to_a_third_round(client, club, category, register_n_athletes):
    register_n_athletes(client, club, category, 2)
    match = client.post(f"/api/v1/categories/{category['id']}/bracket").json()["matches"][0]

    client.post(
        f"/api/v1/matches/{match['id']}/rounds",
        json={"round_number": 1, "red_points": 10, "blue_points": 5},
    )
    client.post(
        f"/api/v1/matches/{match['id']}/rounds",
        json={"round_number": 2, "red_points": 3, "blue_points": 8},
    )
    mid_match = client.get(f"/api/v1/matches/{match['id']}").json()
    assert mid_match["status"] == "pending"

    resp = client.post(
        f"/api/v1/matches/{match['id']}/rounds",
        json={"round_number": 3, "red_points": 2, "blue_points": 7},
    )
    assert resp.status_code == 201
    finished = client.get(f"/api/v1/matches/{match['id']}").json()
    assert finished["status"] == "finished"
    assert finished["winner_id"] == match["athlete_blue_id"]


def test_finished_match_rejects_more_rounds(client, club, category, register_n_athletes):
    register_n_athletes(client, club, category, 2)
    match = client.post(f"/api/v1/categories/{category['id']}/bracket").json()["matches"][0]
    client.post(
        f"/api/v1/matches/{match['id']}/rounds",
        json={"round_number": 1, "red_points": 10, "blue_points": 5},
    )
    client.post(
        f"/api/v1/matches/{match['id']}/rounds",
        json={"round_number": 2, "red_points": 8, "blue_points": 3},
    )

    resp = client.post(
        f"/api/v1/matches/{match['id']}/rounds",
        json={"round_number": 3, "red_points": 1, "blue_points": 9},
    )
    assert resp.status_code == 409


def test_winner_propagates_to_next_round(client, club, category, register_n_athletes):
    register_n_athletes(client, club, category, 4)
    bracket = client.post(f"/api/v1/categories/{category['id']}/bracket").json()
    semis = [m for m in bracket["matches"] if m["round_number"] == 1]
    final = next(m for m in bracket["matches"] if m["round_number"] == 2)

    winners = []
    for semi in semis:
        client.post(
            f"/api/v1/matches/{semi['id']}/rounds",
            json={"round_number": 1, "red_points": 10, "blue_points": 2},
        )
        client.post(
            f"/api/v1/matches/{semi['id']}/rounds",
            json={"round_number": 2, "red_points": 10, "blue_points": 2},
        )
        winners.append(client.get(f"/api/v1/matches/{semi['id']}").json()["winner_id"])

    updated_final = client.get(f"/api/v1/matches/{final['id']}").json()
    assert updated_final["athlete_red_id"] in winners
    assert updated_final["athlete_blue_id"] in winners


def test_get_missing_match_404(client):
    resp = client.get("/api/v1/matches/999")
    assert resp.status_code == 404
