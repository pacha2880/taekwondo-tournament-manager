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


def test_admin_athlete_list_shows_the_ci_only_when_there_is_one(client, club):
    _login(client)
    form = {"birth_date": "2012-01-01", "gender": "male", "belt_rank": "verde", "weight_kg": "40", "club_id": club["id"]}
    client.post("/admin/atletas", data={**form, "name": "Ana Con Cedula", "ci": "1234567"})
    client.post("/admin/atletas", data={**form, "name": "Beto Sin Cedula", "ci": "  "})

    rows = client.get("/admin/atletas").text.split("</li>")
    [ana] = [row for row in rows if "Ana Con Cedula" in row]
    [beto] = [row for row in rows if "Beto Sin Cedula" in row]

    assert "CI 1234567" in ana
    assert "CI" not in beto


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
        data={"red_points": "12", "blue_points": "5"},
        follow_redirects=False,
    )
    assert score_resp.status_code == 303
    score_resp = client.post(
        f"/admin/combates/{match_id}/rounds",
        data={"red_points": "9", "blue_points": "3"},
        follow_redirects=False,
    )
    assert score_resp.status_code == 303

    category_page = client.get(f"/admin/categorias/{category_id}")
    assert "Finalizado" in category_page.text
    assert "Ganador:" in category_page.text


def test_dashboard_colors_each_tournament_status_badge(client):
    for name, status in (("T1", "draft"), ("T2", "in_progress"), ("T3", "finished")):
        created = client.post(
            "/api/v1/tournaments", json={"name": name, "date": "2026-11-15", "location": "La Paz"}
        ).json()
        client.patch(f"/api/v1/tournaments/{created['id']}", json={"status": status})
    _login(client)

    html = client.get("/admin").text

    assert '<span class="badge bg-secondary">Borrador</span>' in html
    assert '<span class="badge bg-primary">En curso</span>' in html
    assert '<span class="badge bg-success">Finalizado</span>' in html


def test_admin_navbar_has_torneos_button_before_clubes_and_atletas(client):
    _login(client)

    for path in ("/admin", "/admin/clubes", "/admin/atletas"):
        html = client.get(path).text
        torneos = html.index('href="/admin">Torneos</a>')
        clubes = html.index('href="/admin/clubes">Clubes</a>')
        atletas = html.index('href="/admin/atletas">Atletas</a>')
        assert torneos < clubes < atletas


def test_registration_select_excludes_athletes_already_in_the_category(
    client, club, category, athlete, register_n_athletes
):
    _login(client)
    register_n_athletes(client, club, category, 2)

    page = client.get(f"/admin/categorias/{category['id']}")

    assert _extract_all_option_values(page.text, 'name="athlete_id"') == [str(athlete["id"])]


def test_registration_select_excludes_athletes_registered_in_another_category_of_the_tournament(
    client, club, category, athlete
):
    _login(client)
    other_category = client.post(
        "/api/v1/categories",
        json={
            "tournament_id": category["tournament_id"],
            "gender": "male",
            "age_label": "Juvenil",
            "min_age": 15,
            "max_age": 17,
            "belt_group": "color",
            "weight_label": "Hasta 55kg",
        },
    ).json()
    client.post(
        f"/admin/categorias/{other_category['id']}/inscripciones",
        data={"athlete_id": athlete["id"]},
    )

    page = client.get(f"/admin/categorias/{category['id']}")

    assert 'name="athlete_id"' not in page.text
    assert "No quedan atletas para inscribir" in page.text


def test_registration_form_is_replaced_by_a_message_when_everyone_is_registered(
    client, club, category, register_n_athletes
):
    _login(client)
    register_n_athletes(client, club, category, 2)

    page = client.get(f"/admin/categorias/{category['id']}")

    assert 'name="athlete_id"' not in page.text
    assert "No quedan atletas para inscribir" in page.text


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


def _edit_athlete_form(athlete, **overrides):
    form = {
        "name": athlete["name"],
        "ci": athlete["ci"] or "",
        "birth_date": athlete["birth_date"],
        "gender": athlete["gender"],
        "belt_rank": athlete["belt_rank"],
        "weight_kg": str(athlete["weight_kg"]),
        "club_id": str(athlete["club"]["id"]),
    }
    return {**form, **overrides}


def test_edit_athlete_page_is_linked_from_the_list_and_prefilled(client, athlete):
    _login(client)

    assert f'href="/admin/atletas/{athlete["id"]}/editar"' in client.get("/admin/atletas").text
    page = client.get(f"/admin/atletas/{athlete['id']}/editar").text

    for field in ('value="Juan Perez"', 'value="1234567"', 'value="2012-05-01"', 'value="verde"', 'value="40.5"'):
        assert field in page
    assert '<option value="male" selected>' in page
    assert 'data-confirm="Guardar cambios del atleta"' in page
    assert f'<option value="{athlete["club"]["id"]}" selected>' in page
    assert client.get("/admin/atletas/999/editar").status_code == 404


def test_edit_athlete_asks_for_confirmation_before_withdrawing_it_from_a_category(client, athlete, category):
    _login(client)
    client.post("/api/v1/registrations", json={"athlete_id": athlete["id"], "category_id": category["id"]})
    url = f"/admin/atletas/{athlete['id']}/editar"

    asked = client.post(url, data=_edit_athlete_form(athlete, weight_kg="50"), follow_redirects=False)

    assert asked.status_code == 409
    assert "Este cambio retira al atleta de: Cadete Hasta 45kg (Copa Nacional)" in asked.text
    assert '<input type="hidden" name="confirm_withdrawal" value="true">' in asked.text
    assert 'value="50.0"' in asked.text
    assert 'data-confirm="Guardar cambios del atleta"' not in asked.text

    confirmed = client.post(
        url, data=_edit_athlete_form(athlete, weight_kg="50", confirm_withdrawal="true"), follow_redirects=False
    )

    assert confirmed.status_code == 303


def test_edit_athlete_in_a_tournament_in_progress_shows_the_reason_without_a_confirm_button(
    client, athlete, category, tournament
):
    _login(client)
    client.post("/api/v1/registrations", json={"athlete_id": athlete["id"], "category_id": category["id"]})
    client.patch(f"/api/v1/tournaments/{tournament['id']}", json={"status": "in_progress"})

    resp = client.post(f"/admin/atletas/{athlete['id']}/editar", data=_edit_athlete_form(athlete, weight_kg="50"))

    assert resp.status_code == 400
    assert "torneo en curso «Copa Nacional»" in resp.text
    assert "Confirmar y retirar" not in resp.text


def test_edit_club_via_admin(client, club):
    _login(client)
    client.post("/api/v1/clubs", json={"name": "Dojang Norte"})

    assert f'href="/admin/clubes/{club["id"]}/editar"' in client.get("/admin/clubes").text
    assert f'value="{club["name"]}"' in client.get(f"/admin/clubes/{club['id']}/editar").text

    saved = client.post(f"/admin/clubes/{club['id']}/editar", data={"name": "Dojang Renovado"}, follow_redirects=False)
    duplicate = client.post(f"/admin/clubes/{club['id']}/editar", data={"name": "Dojang Norte"})

    assert saved.status_code == 303
    assert duplicate.status_code == 400
    assert "Ya existe un club con ese nombre" in duplicate.text
    assert client.get("/admin/clubes/999/editar").status_code == 404


def _admin_search(client, q):
    return client.get("/admin/atletas", params={"q": q}).text


def test_admin_search_passes_the_text_to_the_api_keeps_it_and_offers_to_clear(client, club):
    _login(client)
    for name, ci in [("Ana Pérez", "1234567"), ("Luis Núñez", "7654321")]:
        client.post("/api/v1/athletes", json={**_athlete_json(club), "name": name, "ci": ci})

    searched = _admin_search(client, "perez")
    unfiltered = client.get("/admin/atletas").text

    assert "Ana Pérez" in searched
    assert "Luis Núñez" not in searched
    assert 'value="perez"' in searched
    assert ">Limpiar</a>" in searched
    assert "Luis Núñez" in unfiltered
    assert "Limpiar" not in unfiltered


def test_admin_search_without_matches_says_so_and_escapes_the_text(client):
    _login(client)

    page = _admin_search(client, "<b>x</b>")

    assert "Ningún atleta coincide con «&lt;b&gt;x&lt;/b&gt;»" in page
    assert "<b>x</b>" not in page


def _athlete_json(club):
    return {
        "name": "X",
        "birth_date": "2012-01-01",
        "gender": "male",
        "belt_rank": "verde",
        "weight_kg": 40,
        "club_id": club["id"],
    }


def test_round_form_shows_the_next_round_number_without_an_editable_field(client, club, category, register_n_athletes):
    register_n_athletes(client, club, category, 2)
    match = client.post(f"/api/v1/categories/{category['id']}/bracket").json()["matches"][0]
    _login(client)
    page_url = f"/admin/categorias/{category['id']}"

    first = client.get(page_url).text
    client.post(f"/admin/combates/{match['id']}/rounds", data={"red_points": "10", "blue_points": "5"})
    second = client.get(page_url).text

    assert 'data-confirm="Cargar round 1"' in first
    assert 'data-confirm-note="Una vez cargado, el resultado de un round no se puede editar."' in first
    assert 'name="round_number"' not in first
    assert 'data-confirm="Cargar round 2"' in second


def test_admin_pages_include_the_confirmation_modal(client):
    _login(client)

    assert 'id="confirm-modal"' in client.get("/admin").text

