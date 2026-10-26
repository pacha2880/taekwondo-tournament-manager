def test_home_lists_tournaments(client, tournament):
    resp = client.get("/")
    assert resp.status_code == 200
    assert tournament["name"] in resp.text


def test_home_colors_each_tournament_status_badge(client):
    for name, status in (("T1", "draft"), ("T2", "in_progress"), ("T3", "finished")):
        created = client.post(
            "/api/v1/tournaments", json={"name": name, "date": "2026-11-15", "location": "La Paz"}
        ).json()
        client.patch(f"/api/v1/tournaments/{created['id']}", json={"status": status})

    html = client.get("/").text

    assert '<span class="badge bg-secondary">Borrador</span>' in html
    assert '<span class="badge bg-primary">En curso</span>' in html
    assert '<span class="badge bg-success">Finalizado</span>' in html


def test_home_shows_empty_state_without_tournaments(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Todavía no hay torneos" in resp.text


def test_tournament_detail_lists_categories(client, tournament, category):
    resp = client.get(f"/torneos/{tournament['id']}")
    assert resp.status_code == 200
    assert category["age_label"] in resp.text


def test_tournament_detail_missing_404(client):
    resp = client.get("/torneos/999")
    assert resp.status_code == 404


def test_category_detail_without_bracket(client, category):
    resp = client.get(f"/categorias/{category['id']}")
    assert resp.status_code == 200
    assert "todavía no ha sido generada" in resp.text


def test_category_detail_missing_404(client):
    resp = client.get("/categorias/999")
    assert resp.status_code == 404


def test_category_detail_shows_bracket_with_athlete_names(client, club, category, register_n_athletes):
    athletes = register_n_athletes(client, club, category, 2)
    client.post(f"/api/v1/categories/{category['id']}/bracket")

    resp = client.get(f"/categorias/{category['id']}")
    assert resp.status_code == 200
    assert "Ronda 1" in resp.text
    assert athletes[0]["athlete"]["name"] in resp.text
    assert athletes[1]["athlete"]["name"] in resp.text


def test_category_detail_shows_round_scores_after_match_finishes(
    client, club, category, register_n_athletes
):
    register_n_athletes(client, club, category, 2)
    match = client.post(f"/api/v1/categories/{category['id']}/bracket").json()["matches"][0]
    client.post(
        f"/api/v1/matches/{match['id']}/rounds",
        json={"red_points": 12, "blue_points": 5},
    )
    client.post(
        f"/api/v1/matches/{match['id']}/rounds",
        json={"red_points": 9, "blue_points": 3},
    )

    resp = client.get(f"/categorias/{category['id']}")
    assert resp.status_code == 200
    assert "Ganador:" in resp.text
    assert "Round 1: 12-5" in resp.text
    assert "Round 2: 9-3" in resp.text
