def test_list_categories_filtered_by_tournament(client, category, tournament):
    client.post("/api/v1/tournaments", json={"name": "Otro", "date": "2026-12-01", "location": "La Paz"}).json()

    resp = client.get("/api/v1/categories", params={"tournament_id": tournament["id"]})

    assert resp.status_code == 200
    assert category["id"] in [c["id"] for c in resp.json()]
    assert {c["tournament_id"] for c in resp.json()} == {tournament["id"]}


def test_list_categories_without_filter_returns_all(client, category):
    other = client.post("/api/v1/tournaments", json={"name": "Otro", "date": "2026-12-01", "location": "La Paz"}).json()

    resp = client.get("/api/v1/categories")

    assert resp.status_code == 200
    assert {c["tournament_id"] for c in resp.json()} == {category["tournament_id"], other["id"]}


def test_registrants_are_public_sorted_by_name_and_only_with_name_and_club(
    anon_client, client, club, athlete, category, register_n_athletes, set_tournament_status
):
    register_n_athletes(client, club, category, 2)
    client.post("/api/v1/registrations", json={"athlete_id": athlete["id"], "category_id": category["id"]})
    set_tournament_status(client, category["tournament_id"], "weigh_in")

    resp = anon_client.get(f"/api/v1/categories/{category['id']}/registrants")

    assert resp.status_code == 200
    assert [r["name"] for r in resp.json()] == ["Atleta 0", "Atleta 1", "Juan Perez"]
    assert resp.json()[-1] == {
        "athlete_id": athlete["id"], "name": "Juan Perez", "club": "Dojang Central", "weigh_in_status": "pending"
    }


def test_registrants_of_a_missing_category_is_404(anon_client):
    assert anon_client.get("/api/v1/categories/999/registrants").status_code == 404


def test_is_festival_is_true_only_in_the_festival_categories(client, tournament, category):
    listed = client.get("/api/v1/categories", params={"tournament_id": tournament["id"]}).json()

    assert {c["is_festival"] for c in listed if c["age_label"] == "Festival"} == {True}
    assert {c["is_festival"] for c in listed if c["age_label"] != "Festival"} == {False}
    assert client.get(f"/api/v1/categories/{category['id']}").json()["is_festival"] is False


def test_has_bracket_tells_whether_the_bracket_was_generated(client, club, category, register_n_athletes, generate_bracket):
    register_n_athletes(client, club, category, 2)
    url = f"/api/v1/categories/{category['id']}"

    before = client.get(url).json()["has_bracket"]
    generate_bracket(client, category)
    after = client.get(url).json()["has_bracket"]
    listed = client.get("/api/v1/categories", params={"tournament_id": category["tournament_id"]}).json()

    assert (before, after) == (False, True)
    assert [c["has_bracket"] for c in listed if c["id"] == category["id"]] == [True]


def _athlete_payload(club, name, **changes):
    return {
        "name": name,
        "birth_date": "2012-05-01",
        "gender": "male",
        "grade": "kup_6",
        "weight_kg": 40.5,
        "club_id": club["id"],
        **changes,
    }


def test_eligible_athletes_only_those_that_fit_sorted_by_name(client, club, athlete, category):
    client.post("/api/v1/athletes", json=_athlete_payload(club, "Ana Zeta"))
    client.post("/api/v1/athletes", json=_athlete_payload(club, "Abel Alto"))
    for name, change in [
        ("Otro genero", {"gender": "female"}),
        ("Otra edad", {"birth_date": "2000-05-01"}),
        ("Otro grado", {"grade": "kup_1"}),
        ("Otro peso", {"weight_kg": 60}),
    ]:
        assert client.post("/api/v1/athletes", json=_athlete_payload(club, name, **change)).status_code == 201

    resp = client.get(f"/api/v1/categories/{category['id']}/eligible-athletes")

    assert resp.status_code == 200
    assert [a["name"] for a in resp.json()] == ["Abel Alto", "Ana Zeta", "Juan Perez"]
    assert resp.json()[0]["club"]["id"] == club["id"]


def test_eligible_athletes_includes_already_registered(client, athlete, category):
    client.post("/api/v1/registrations", json={"athlete_id": athlete["id"], "category_id": category["id"]})

    resp = client.get(f"/api/v1/categories/{category['id']}/eligible-athletes")

    assert [a["id"] for a in resp.json()] == [athlete["id"]]


def test_eligible_athletes_category_not_found(client):
    resp = client.get("/api/v1/categories/9999/eligible-athletes")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Categoría no encontrada"


def test_eligible_athletes_requires_token(anon_client, category):
    resp = anon_client.get(f"/api/v1/categories/{category['id']}/eligible-athletes")

    assert resp.status_code == 401


def test_categories_that_differ_only_in_grade_group_have_different_names(tournament, find_category):
    beginners = find_category(tournament["id"], "male", "Cadete", "37.1–41 kg", grade_group="Principiantes")
    novices = find_category(tournament["id"], "male", "Cadete", "37.1–41 kg", grade_group="Novatos")

    assert beginners["name"] == "Principiantes · Cadete · Masculino · 37.1–41 kg"
    assert novices["name"] == "Novatos · Cadete · Masculino · 37.1–41 kg"
    assert (beginners["grade_group_name"], novices["grade_group_name"]) == ("Principiantes", "Novatos")
    assert beginners["grade_group_id"] != novices["grade_group_id"]


def test_festival_name_has_no_grade_group(client, tournament):
    festival = [
        c for c in client.get("/api/v1/categories", params={"tournament_id": tournament["id"]}).json()
        if c["age_label"] == "Festival" and c["gender"] == "male"
    ]

    assert [(c["name"], c["grade_group_id"], c["grade_group_name"]) for c in festival] == [
        ("Festival · Masculino · Todos los pesos", None, None)
    ]



def test_list_categories_filtered_by_grade_group_and_gender(client, tournament, find_category):
    novices = find_category(tournament["id"], "male", "Cadete", "37.1–41 kg", grade_group="Novatos")
    params = {"tournament_id": tournament["id"], "grade_group_id": novices["grade_group_id"]}

    by_group = client.get("/api/v1/categories", params=params).json()
    by_group_and_gender = client.get("/api/v1/categories", params={**params, "gender": "female"}).json()

    assert {c["grade_group_name"] for c in by_group} == {"Novatos"}
    assert {c["gender"] for c in by_group} == {"male", "female"}
    assert {(c["grade_group_name"], c["gender"]) for c in by_group_and_gender} == {("Novatos", "female")}
    assert novices["id"] in [c["id"] for c in by_group]
    assert novices["id"] not in [c["id"] for c in by_group_and_gender]


def test_list_categories_with_an_invalid_gender_is_422(client):
    assert client.get("/api/v1/categories", params={"gender": "otro"}).status_code == 422


def test_list_categories_filtered_by_having_registrants(client, club, tournament, category, register_n_athletes):
    register_n_athletes(client, club, category, 1)
    params = {"tournament_id": tournament["id"]}

    with_registrants = client.get("/api/v1/categories", params={**params, "has_registrants": True}).json()
    without_registrants = client.get("/api/v1/categories", params={**params, "has_registrants": False}).json()
    everything = client.get("/api/v1/categories", params=params).json()

    assert [c["id"] for c in with_registrants] == [category["id"]]
    assert category["id"] not in [c["id"] for c in without_registrants]
    assert len(with_registrants) + len(without_registrants) == len(everything)
