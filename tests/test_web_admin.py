def test_dashboard_requires_login(client):
    resp = client.get("/admin", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin/login"


def test_login_with_wrong_credentials_shows_error(client):
    resp = client.post("/admin/login", data={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401
    assert "incorrectos" in resp.text


def test_login_then_access_dashboard(client):
    resp = client.post("/admin/login", data={"username": "admin", "password": "admin"}, follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin"

    resp = client.get("/admin")
    assert resp.status_code == 200
    assert "Torneos" in resp.text


def test_logout_requires_login_again(client):
    client.post("/admin/login", data={"username": "admin", "password": "admin"})
    client.post("/admin/logout")

    resp = client.get("/admin", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin/login"


def _login(client):
    client.post("/admin/login", data={"username": "admin", "password": "admin"})


def test_create_club_via_admin(client):
    _login(client)
    resp = client.post("/admin/clubes", data={"name": "Dojang Admin"}, follow_redirects=False)
    assert resp.status_code == 303

    resp = client.get("/admin/clubes")
    assert "Dojang Admin" in resp.text


def test_create_duplicate_club_shows_error(client):
    _login(client)
    client.post("/admin/clubes", data={"name": "Dojang Admin"})
    resp = client.post("/admin/clubes", data={"name": "Dojang Admin"})
    assert resp.status_code == 400
    assert "ya existe" in resp.text.lower()


def test_create_category_with_invalid_weight_range_shows_error(client, tournament):
    _login(client)
    resp = client.post(
        f"/admin/torneos/{tournament['id']}/categorias",
        data={
            "age_label": "Junior",
            "min_age": "15",
            "max_age": "17",
            "gender": "male",
            "belt_group": "color",
            "weight_label": "Hasta 55kg",
            "min_weight": "60",
            "max_weight": "55",
        },
    )
    assert resp.status_code == 400
    assert "min_weight no puede ser mayor que max_weight" in resp.text


def test_create_athlete_requires_a_club_first(client):
    _login(client)
    resp = client.get("/admin/atletas")
    assert "Primero tenés que crear un club" in resp.text


def test_full_admin_workflow_creates_bracket_and_scores_a_match(client):
    _login(client)
    club_resp = client.post("/admin/clubes", data={"name": "Dojang Flujo"}, follow_redirects=False)
    assert club_resp.status_code == 303

    tournament_resp = client.post(
        "/admin/torneos",
        data={"name": "Copa Admin", "date": "2026-12-01", "location": "San Salvador"},
        follow_redirects=False,
    )
    assert tournament_resp.status_code == 303
    tournament_id = tournament_resp.headers["location"].rsplit("/", 1)[-1]

    clubs_page = client.get("/admin/atletas")
    assert "Dojang Flujo" in clubs_page.text

    club_id = _extract_first_option_value(clubs_page.text, 'name="club_id"')

    athlete1 = client.post(
        "/admin/atletas",
        data={
            "name": "Atleta Uno",
            "birth_date": "2012-01-01",
            "gender": "male",
            "belt_rank": "verde",
            "weight_kg": "40",
            "club_id": club_id,
        },
        follow_redirects=False,
    )
    assert athlete1.status_code == 303
    client.post(
        "/admin/atletas",
        data={
            "name": "Atleta Dos",
            "birth_date": "2012-01-01",
            "gender": "male",
            "belt_rank": "verde",
            "weight_kg": "40",
            "club_id": club_id,
        },
    )

    category_resp = client.post(
        f"/admin/torneos/{tournament_id}/categorias",
        data={
            "age_label": "Cadete",
            "min_age": "12",
            "max_age": "14",
            "gender": "male",
            "belt_group": "color",
            "weight_label": "Hasta 45kg",
        },
        follow_redirects=False,
    )
    assert category_resp.status_code == 303

    tournament_page = client.get(f"/admin/torneos/{tournament_id}")
    assert "Cadete" in tournament_page.text
    category_id = _extract_category_id(tournament_page.text)

    category_page = client.get(f"/admin/categorias/{category_id}")
    athlete_ids = _extract_all_option_values(category_page.text, 'name="athlete_id"')
    assert len(athlete_ids) == 2

    for athlete_id in athlete_ids:
        resp = client.post(
            f"/admin/categorias/{category_id}/inscripciones",
            data={"athlete_id": athlete_id},
            follow_redirects=False,
        )
        assert resp.status_code == 303

    bracket_resp = client.post(f"/admin/categorias/{category_id}/llave", follow_redirects=False)
    assert bracket_resp.status_code == 303

    category_page = client.get(f"/admin/categorias/{category_id}")
    assert "Pendiente" in category_page.text
    match_id = _extract_match_id(category_page.text)

    score_resp = client.post(
        f"/admin/combates/{match_id}/rounds",
        data={"round_number": "1", "red_points": "12", "blue_points": "5"},
        follow_redirects=False,
    )
    assert score_resp.status_code == 303
    score_resp = client.post(
        f"/admin/combates/{match_id}/rounds",
        data={"round_number": "2", "red_points": "9", "blue_points": "3"},
        follow_redirects=False,
    )
    assert score_resp.status_code == 303

    category_page = client.get(f"/admin/categorias/{category_id}")
    assert "Finalizado" in category_page.text
    assert "Ganador:" in category_page.text


def _extract_first_option_value(html: str, select_marker: str) -> str:
    return _extract_all_option_values(html, select_marker)[0]


def _extract_all_option_values(html: str, select_marker: str) -> list[str]:
    start = html.index(select_marker)
    select_end = html.index("</select>", start)
    chunk = html[start:select_end]
    values = []
    pos = 0
    while True:
        idx = chunk.find('value="', pos)
        if idx == -1:
            break
        idx += len('value="')
        end = chunk.index('"', idx)
        values.append(chunk[idx:end])
        pos = end
    return values


def _extract_category_id(tournament_page_html: str) -> str:
    marker = '/admin/categorias/'
    start = tournament_page_html.index(marker) + len(marker)
    end = tournament_page_html.index('"', start)
    return tournament_page_html[start:end]


def _extract_match_id(category_page_html: str) -> str:
    marker = "/admin/combates/"
    start = category_page_html.index(marker) + len(marker)
    end = category_page_html.index("/rounds", start)
    return category_page_html[start:end]
