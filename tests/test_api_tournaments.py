import pytest


def test_create_tournament_defaults_to_draft(client, tournament):
    assert tournament["status"] == "draft"


def test_get_missing_tournament_404(client):
    resp = client.get("/api/v1/tournaments/999")
    assert resp.status_code == 404


def test_patch_changes_the_data_but_no_longer_accepts_a_status(client, tournament):
    url = f"/api/v1/tournaments/{tournament['id']}"

    renamed = client.patch(url, json={"name": "Copa Corregida"})
    with_status = client.patch(url, json={"status": "finished"})

    assert renamed.json()["name"] == "Copa Corregida"
    assert with_status.status_code == 422
    assert client.get(url).json()["status"] == "draft"


def test_tournament_starts_and_finishes(client, tournament):
    url = f"/api/v1/tournaments/{tournament['id']}"

    started = client.post(f"{url}/start")
    finished = client.post(f"{url}/finish")

    assert started.json()["status"] == "in_progress"
    assert finished.json()["status"] == "finished"


def test_each_action_only_works_from_its_own_status(client, tournament):
    url = f"/api/v1/tournaments/{tournament['id']}"

    finish_from_draft = client.post(f"{url}/finish")
    client.post(f"{url}/start")
    start_again = client.post(f"{url}/start")
    client.post(f"{url}/finish")
    finish_again = client.post(f"{url}/finish")

    assert finish_from_draft.status_code == 409
    assert finish_from_draft.json()["detail"] == "Solo se puede finalizar un torneo en curso"
    assert start_again.status_code == 409
    assert start_again.json()["detail"] == "El torneo ya empezó"
    assert finish_again.status_code == 409


def test_actions_require_an_existing_tournament(client):
    assert client.post("/api/v1/tournaments/999/start").status_code == 404
    assert client.post("/api/v1/tournaments/999/finish").status_code == 404


def _win_match(client, match_id):
    for _ in range(2):  # rounds_to_win por defecto
        client.post(f"/api/v1/matches/{match_id}/rounds", json={"red_points": 10, "blue_points": 5})


def test_finish_is_rejected_while_a_bracket_has_matches_to_play(client, club, category, tournament, register_n_athletes):
    register_n_athletes(client, club, category, 2)
    url = f"/api/v1/tournaments/{tournament['id']}"
    client.post(f"{url}/start")
    match = client.post(f"/api/v1/categories/{category['id']}/bracket").json()["matches"][0]

    before = client.post(f"{url}/finish")
    _win_match(client, match["id"])
    after = client.post(f"{url}/finish")

    assert before.status_code == 409
    assert before.json()["detail"] == "Quedan combates por jugar en: Cadete Hasta 45kg"
    assert after.status_code == 200


def test_finish_ignores_byes(client, club, category, tournament, register_n_athletes):
    register_n_athletes(client, club, category, 3)
    url = f"/api/v1/tournaments/{tournament['id']}"
    client.post(f"{url}/start")
    matches = client.post(f"/api/v1/categories/{category['id']}/bracket").json()["matches"]
    [bye] = [m for m in matches if m["status"] == "bye"]
    [semifinal] = [m for m in matches if m["round_number"] == 1 and m["status"] == "pending"]
    [final] = [m for m in matches if m["next_match_id"] is None]

    _win_match(client, semifinal["id"])
    _win_match(client, final["id"])

    assert client.get(f"/api/v1/matches/{bye['id']}").json()["status"] == "bye"
    assert client.post(f"{url}/finish").status_code == 200


@pytest.mark.parametrize("athletes,expected_status", [(1, 200), (2, 409)])
def test_a_category_without_bracket_blocks_finish_only_with_two_or_more_athletes(
    client, club, category, tournament, register_n_athletes, athletes, expected_status
):
    register_n_athletes(client, club, category, athletes)
    url = f"/api/v1/tournaments/{tournament['id']}"
    client.post(f"{url}/start")

    assert client.post(f"{url}/finish").status_code == expected_status
