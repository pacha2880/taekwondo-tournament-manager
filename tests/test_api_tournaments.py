def test_create_tournament_defaults_to_draft(client, tournament):
    assert tournament["status"] == "draft"


def test_update_tournament_status(client, tournament):
    resp = client.patch(f"/api/v1/tournaments/{tournament['id']}", json={"status": "in_progress"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"


def test_get_missing_tournament_404(client):
    resp = client.get("/api/v1/tournaments/999")
    assert resp.status_code == 404
