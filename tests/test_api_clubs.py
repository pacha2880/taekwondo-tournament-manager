def test_create_and_list_club(client):
    resp = client.post("/api/v1/clubs", json={"name": "Tigres TKD"})
    assert resp.status_code == 201
    assert resp.json()["name"] == "Tigres TKD"

    resp = client.get("/api/v1/clubs")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_duplicate_club_name_rejected(client, club):
    resp = client.post("/api/v1/clubs", json={"name": club["name"]})
    assert resp.status_code == 409


def test_get_missing_club_404(client):
    resp = client.get("/api/v1/clubs/999")
    assert resp.status_code == 404
