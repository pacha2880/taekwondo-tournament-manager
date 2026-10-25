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


def test_update_club_name(client, club):
    resp = client.patch(f"/api/v1/clubs/{club['id']}", json={"name": "Dojang Renovado"})

    assert resp.status_code == 200
    assert resp.json() == {"id": club["id"], "name": "Dojang Renovado"}
    assert client.get(f"/api/v1/clubs/{club['id']}").json()["name"] == "Dojang Renovado"


def test_update_club_without_name_changes_nothing(client, club):
    resp = client.patch(f"/api/v1/clubs/{club['id']}", json={"name": None})

    assert resp.status_code == 200
    assert resp.json() == club


def test_update_club_rejects_the_name_of_another_club_but_accepts_its_own(client, club):
    client.post("/api/v1/clubs", json={"name": "Dojang Norte"})

    own = client.patch(f"/api/v1/clubs/{club['id']}", json={"name": club["name"]})
    taken = client.patch(f"/api/v1/clubs/{club['id']}", json={"name": "Dojang Norte"})

    assert own.status_code == 200
    assert taken.status_code == 409
    assert taken.json()["detail"] == "Ya existe un club con ese nombre"


def test_update_missing_club_returns_404(client):
    assert client.patch("/api/v1/clubs/999", json={"name": "X"}).status_code == 404
