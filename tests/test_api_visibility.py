"""Sin token se ocultan los torneos en preparación y la lista de inscritos antes del Pesaje."""

import pytest


@pytest.fixture()
def draft_category(client, draft_tournament):
    return client.get("/api/v1/categories", params={"tournament_id": draft_tournament["id"]}).json()[0]


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/tournaments/{t}",
        "/api/v1/tournaments/{t}/category-structure",
        "/api/v1/categories/{c}",
        "/api/v1/categories/{c}/registrants",
        "/api/v1/categories/{c}/bracket",
    ],
)
def test_draft_tournament_endpoints_are_404_without_token(anon_client, draft_tournament, draft_category, path):
    resp = anon_client.get(path.format(t=draft_tournament["id"], c=draft_category["id"]))

    assert resp.status_code == 404


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/tournaments/{t}",
        "/api/v1/tournaments/{t}/category-structure",
        "/api/v1/categories/{c}",
        "/api/v1/categories/{c}/registrants",
    ],
)
def test_draft_tournament_endpoints_work_with_token(client, draft_tournament, draft_category, path):
    assert client.get(path.format(t=draft_tournament["id"], c=draft_category["id"])).status_code == 200


def test_draft_tournament_is_hidden_from_lists_without_token(anon_client, client, tournament):
    draft_tournament = client.post(
        "/api/v1/tournaments", json={"name": "Otra", "date": "2026-12-01", "location": "La Paz"}
    ).json()
    ids = [t["id"] for t in anon_client.get("/api/v1/tournaments").json()]
    assert ids == [tournament["id"]]
    assert draft_tournament["id"] in [t["id"] for t in client.get("/api/v1/tournaments").json()]

    visible = {c["tournament_id"] for c in anon_client.get("/api/v1/categories").json()}
    assert visible == {tournament["id"]}
    assert anon_client.get("/api/v1/categories", params={"tournament_id": draft_tournament["id"]}).json() == []
    assert draft_tournament["id"] in {c["tournament_id"] for c in client.get("/api/v1/categories").json()}


@pytest.mark.parametrize("status,public", [("registration_open", False), ("weigh_in", True), ("in_progress", True), ("finished", True)])
def test_registrants_are_published_from_weigh_in(
    anon_client, client, club, category, register_n_athletes, set_tournament_status, status, public
):
    register_n_athletes(client, club, category, 1)
    set_tournament_status(client, category["tournament_id"], status)
    url = f"/api/v1/categories/{category['id']}/registrants"

    anonymous = anon_client.get(url)

    assert anonymous.status_code == (200 if public else 403)
    if not public:
        assert anonymous.json()["detail"] == "La lista de inscritos se publica al cerrar las inscripciones"
    assert len(client.get(url).json()) == 1


def test_has_registrants_without_token_needs_a_tournament_past_registration(
    anon_client, client, club, category, register_n_athletes, set_tournament_status
):
    register_n_athletes(client, club, category, 2)
    tournament_id = category["tournament_id"]
    url = "/api/v1/categories"

    assert anon_client.get(url, params={"has_registrants": True}).status_code == 403
    assert anon_client.get(url, params={"has_registrants": True, "tournament_id": tournament_id}).status_code == 403
    assert client.get(url, params={"has_registrants": True}).status_code == 200

    set_tournament_status(client, tournament_id, "weigh_in")
    resp = anon_client.get(url, params={"has_registrants": True, "tournament_id": tournament_id})

    assert [c["id"] for c in resp.json()] == [category["id"]]
