def test_home_lists_tournaments(client, tournament):
    resp = client.get("/")
    assert resp.status_code == 200
    assert tournament["name"] in resp.text


def test_home_colors_each_tournament_status_badge(client, set_tournament_status):
    for name, status in (("T1", "draft"), ("T2", "in_progress"), ("T3", "finished")):
        created = client.post(
            "/api/v1/tournaments", json={"name": name, "date": "2026-11-15", "location": "La Paz"}
        ).json()
        set_tournament_status(client, created["id"], status)

    html = client.get("/").text

    assert '<span class="badge bg-secondary">Inscripciones abiertas</span>' in html
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


def test_category_detail_shows_bracket_with_athlete_names(client, club, category, register_n_athletes, generate_bracket):
    athletes = register_n_athletes(client, club, category, 2)
    generate_bracket(client, category)

    resp = client.get(f"/categorias/{category['id']}")
    assert resp.status_code == 200
    assert "Ronda 1" in resp.text
    assert athletes[0]["athlete"]["name"] in resp.text
    assert athletes[1]["athlete"]["name"] in resp.text


def test_category_detail_shows_round_scores_after_match_finishes(
    client, club, category, register_n_athletes, generate_bracket, score_rounds
):
    register_n_athletes(client, club, category, 2)
    match = generate_bracket(client, category).json()["matches"][0]
    score_rounds(client, match["id"], (12, 5), (9, 3))

    resp = client.get(f"/categorias/{category['id']}")
    assert resp.status_code == 200
    assert "Ganador:" in resp.text
    assert "Round 1: 12-5" in resp.text
    assert "Round 2: 9-3" in resp.text


def test_home_lists_draft_tournaments_as_open_registrations(client, tournament):
    html = client.get("/").text

    assert tournament["name"] in html
    assert "Inscripciones abiertas" in html


def test_category_without_bracket_lists_registrants_with_only_name_and_club(client, athlete, category):
    client.post("/api/v1/registrations", json={"athlete_id": athlete["id"], "category_id": category["id"]})

    html = client.get(f"/categorias/{category['id']}").text

    assert "<td>Juan Perez</td><td>Dojang Central</td>" in html
    for private in (athlete["ci"], athlete["birth_date"], str(athlete["weight_kg"])):
        assert private not in html


def test_category_without_registrants_says_so(client, category):
    assert "Todavía no hay inscritos" in client.get(f"/categorias/{category['id']}").text


def test_registrants_are_listed_until_the_bracket_is_generated_and_then_the_bracket_shows_the_club(
    client, club, category, register_n_athletes, generate_bracket, set_tournament_status
):
    register_n_athletes(client, club, category, 2)
    set_tournament_status(client, category["tournament_id"], "in_progress")
    page = f"/categorias/{category['id']}"

    before = client.get(page).text
    generate_bracket(client, category)
    after = client.get(page).text

    assert "<td>Atleta 0</td><td>Dojang Central</td>" in before
    assert "<td>Atleta 0</td>" not in after
    assert "Atleta 0 (Dojang Central)" in after
