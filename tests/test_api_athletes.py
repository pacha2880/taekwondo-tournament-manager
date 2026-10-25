import pytest


def test_create_athlete_requires_existing_club(client):
    resp = client.post(
        "/api/v1/athletes",
        json={
            "name": "Sin Club",
            "ci": "5555555",
            "birth_date": "2010-01-01",
            "gender": "female",
            "belt_rank": "amarillo",
            "weight_kg": 35,
            "club_id": 999,
        },
    )
    assert resp.status_code == 404


def test_create_and_get_athlete(client, athlete):
    assert athlete["name"] == "Juan Perez"
    assert athlete["club"]["name"] == "Dojang Central"

    resp = client.get(f"/api/v1/athletes/{athlete['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == athlete["id"]


def _athlete_payload(club, **overrides):
    payload = {
        "name": "Ana Rojas",
        "ci": "7654321",
        "birth_date": "2011-02-03",
        "gender": "female",
        "belt_rank": "azul",
        "weight_kg": 36,
        "club_id": club["id"],
    }
    return {**payload, **overrides}


def test_ci_is_optional_and_several_athletes_can_have_none(client, club):
    without_field = _athlete_payload(club)
    del without_field["ci"]

    first = client.post("/api/v1/athletes", json=without_field)
    second = client.post("/api/v1/athletes", json=_athlete_payload(club, name="Otro", ci=None))

    assert first.status_code == second.status_code == 201
    assert first.json()["ci"] is None
    assert second.json()["ci"] is None


@pytest.mark.parametrize("ci", ["1234567", "12345", "123456789", "1234567-1A", "1234567-AB", "1234567-11"])
def test_valid_ci_is_accepted(client, club, ci):
    resp = client.post("/api/v1/athletes", json=_athlete_payload(club, ci=ci))

    assert resp.status_code == 201
    assert resp.json()["ci"] == ci


@pytest.mark.parametrize(
    "ci",
    ["1234", "1234567890", "ABC1234", "1234567-", "1234567-1", "1234567-1AB", "1234567 1A", "1234567-1a-", "١٢٣٤٥٦٧", "12.345.678"],
)
def test_invalid_ci_is_rejected(client, club, ci):
    resp = client.post("/api/v1/athletes", json=_athlete_payload(club, ci=ci))

    assert resp.status_code == 422


@pytest.mark.parametrize("empty", ["", "   "])
def test_empty_ci_is_stored_as_no_ci(client, club, empty):
    first = client.post("/api/v1/athletes", json=_athlete_payload(club, ci=empty))
    second = client.post("/api/v1/athletes", json=_athlete_payload(club, name="Otro", ci=empty))

    assert first.status_code == second.status_code == 201
    assert first.json()["ci"] is None
    assert second.json()["ci"] is None


def test_ci_is_trimmed_and_uppercased(client, club):
    resp = client.post("/api/v1/athletes", json=_athlete_payload(club, ci="  1234567-1a "))

    assert resp.status_code == 201
    assert resp.json()["ci"] == "1234567-1A"


def test_duplicate_ci_is_rejected_even_with_different_case_or_spaces(client, club):
    client.post("/api/v1/athletes", json=_athlete_payload(club, ci="1234567-1A"))

    resp = client.post("/api/v1/athletes", json=_athlete_payload(club, name="Otra", ci=" 1234567-1a"))

    assert resp.status_code == 409
    assert resp.json()["detail"] == "Ya existe un atleta con ese CI"


def test_same_number_with_a_different_complement_is_another_person(client, club):
    first = client.post("/api/v1/athletes", json=_athlete_payload(club, ci="1234567"))
    second = client.post("/api/v1/athletes", json=_athlete_payload(club, name="Otra", ci="1234567-1A"))

    assert first.status_code == 201
    assert second.status_code == 201


def _set_status(client, tournament, status):
    resp = client.patch(f"/api/v1/tournaments/{tournament['id']}", json={"status": status})
    assert resp.status_code == 200


def _registrations(client, category):
    return client.get("/api/v1/registrations", params={"category_id": category["id"]}).json()


def test_update_changes_only_the_sent_fields(client, athlete):
    resp = client.patch(f"/api/v1/athletes/{athlete['id']}", json={"name": "Juan Pérez Mamani"})

    assert resp.status_code == 200
    assert resp.json() == {**athlete, "name": "Juan Pérez Mamani"}


def test_update_ignores_null_in_fields_other_than_ci(client, athlete):
    resp = client.patch(f"/api/v1/athletes/{athlete['id']}", json={"name": None, "weight_kg": None})

    assert resp.status_code == 200
    assert resp.json() == athlete


def test_update_sets_normalizes_and_clears_the_ci(client, athlete):
    url = f"/api/v1/athletes/{athlete['id']}"

    assert client.patch(url, json={"ci": " 7654321-1a "}).json()["ci"] == "7654321-1A"
    assert client.patch(url, json={"ci": None}).json()["ci"] is None
    assert client.patch(url, json={"ci": "7654321"}).json()["ci"] == "7654321"
    assert client.patch(url, json={"ci": ""}).json()["ci"] is None


def test_update_rejects_an_invalid_ci(client, athlete):
    resp = client.patch(f"/api/v1/athletes/{athlete['id']}", json={"ci": "12AB"})

    assert resp.status_code == 422


def test_update_rejects_the_ci_of_another_athlete_but_accepts_its_own(client, club, athlete):
    other = client.post("/api/v1/athletes", json=_athlete_payload(club, ci="7654321")).json()

    own = client.patch(f"/api/v1/athletes/{athlete['id']}", json={"ci": athlete["ci"]})
    taken = client.patch(f"/api/v1/athletes/{athlete['id']}", json={"ci": other["ci"]})

    assert own.status_code == 200
    assert taken.status_code == 409
    assert taken.json()["detail"] == "Ya existe un atleta con ese CI"


def test_update_moves_the_athlete_to_another_club(client, athlete):
    other_club = client.post("/api/v1/clubs", json={"name": "Dojang Norte"}).json()

    resp = client.patch(f"/api/v1/athletes/{athlete['id']}", json={"club_id": other_club["id"]})

    assert resp.status_code == 200
    assert resp.json()["club"]["name"] == "Dojang Norte"


def test_update_requires_existing_athlete_and_club(client, athlete):
    assert client.patch("/api/v1/athletes/999", json={"name": "X"}).status_code == 404
    assert client.patch(f"/api/v1/athletes/{athlete['id']}", json={"club_id": 999}).status_code == 404


def test_update_keeps_the_registration_when_the_athlete_still_fits(client, athlete, category):
    client.post("/api/v1/registrations", json={"athlete_id": athlete["id"], "category_id": category["id"]})

    resp = client.patch(f"/api/v1/athletes/{athlete['id']}", json={"weight_kg": 44})

    assert resp.status_code == 200
    assert len(_registrations(client, category)) == 1


@pytest.mark.parametrize("change", [{"weight_kg": 50}, {"gender": "female"}])
def test_update_that_no_longer_fits_needs_confirmation_and_changes_nothing(client, athlete, category, change):
    client.post("/api/v1/registrations", json={"athlete_id": athlete["id"], "category_id": category["id"]})

    resp = client.patch(f"/api/v1/athletes/{athlete['id']}", json=change)

    assert resp.status_code == 409
    assert "Este cambio retira al atleta de: Cadete Hasta 45kg (Copa Nacional)" in resp.json()["detail"]
    assert client.get(f"/api/v1/athletes/{athlete['id']}").json() == athlete
    assert len(_registrations(client, category)) == 1


@pytest.mark.parametrize("change", [{"weight_kg": 50}, {"gender": "female"}])
def test_confirmed_update_withdraws_the_athlete_from_the_categories_where_it_no_longer_fits(
    client, athlete, category, change
):
    client.post("/api/v1/registrations", json={"athlete_id": athlete["id"], "category_id": category["id"]})

    resp = client.patch(f"/api/v1/athletes/{athlete['id']}", params={"confirm_withdrawal": True}, json=change)

    assert resp.status_code == 200
    assert resp.json() == {**athlete, **change}
    assert _registrations(client, category) == []


@pytest.mark.parametrize("change", [{"weight_kg": 50}, {"gender": "female"}])
def test_update_that_no_longer_fits_is_rejected_while_the_tournament_is_in_progress(
    client, athlete, category, tournament, change
):
    client.post("/api/v1/registrations", json={"athlete_id": athlete["id"], "category_id": category["id"]})
    _set_status(client, tournament, "in_progress")
    url = f"/api/v1/athletes/{athlete['id']}"

    resp = client.patch(url, params={"confirm_withdrawal": True}, json=change)

    assert resp.status_code == 409
    assert "torneo en curso «Copa Nacional»" in resp.json()["detail"]
    assert client.get(url).json() == athlete
    assert len(_registrations(client, category)) == 1


def test_update_that_still_fits_is_allowed_while_the_tournament_is_in_progress(client, athlete, category, tournament):
    client.post("/api/v1/registrations", json={"athlete_id": athlete["id"], "category_id": category["id"]})
    _set_status(client, tournament, "in_progress")

    resp = client.patch(f"/api/v1/athletes/{athlete['id']}", json={"weight_kg": 44})

    assert resp.status_code == 200
    assert resp.json() == {**athlete, "weight_kg": 44}
    assert len(_registrations(client, category)) == 1


def test_other_fields_can_still_be_edited_while_the_tournament_is_in_progress(client, athlete, category, tournament):
    client.post("/api/v1/registrations", json={"athlete_id": athlete["id"], "category_id": category["id"]})
    _set_status(client, tournament, "in_progress")

    resp = client.patch(
        f"/api/v1/athletes/{athlete['id']}",
        json={"name": "Juan P.", "belt_rank": "azul", "weight_kg": athlete["weight_kg"], "gender": "male"},
    )

    assert resp.status_code == 200
    assert resp.json()["belt_rank"] == "azul"


def test_update_is_allowed_after_the_tournament_finished_and_keeps_the_registration(
    client, athlete, category, tournament
):
    client.post("/api/v1/registrations", json={"athlete_id": athlete["id"], "category_id": category["id"]})
    _set_status(client, tournament, "finished")

    resp = client.patch(f"/api/v1/athletes/{athlete['id']}", json={"weight_kg": 50})

    assert resp.status_code == 200
    assert len(_registrations(client, category)) == 1


def test_only_draft_tournaments_withdraw_the_athlete(client, athlete, category, tournament):
    client.post("/api/v1/registrations", json={"athlete_id": athlete["id"], "category_id": category["id"]})
    _set_status(client, tournament, "finished")
    next_tournament = client.post(
        "/api/v1/tournaments", json={"name": "Copa Siguiente", "date": "2027-03-01", "location": "La Paz"}
    ).json()
    next_category = client.post(
        "/api/v1/categories",
        json={
            "tournament_id": next_tournament["id"],
            "gender": "male",
            "age_label": "Cadete",
            "min_age": 12,
            "max_age": 14,
            "belt_group": "color",
            "weight_label": "Hasta 45kg",
            "max_weight": 45,
        },
    ).json()
    client.post("/api/v1/registrations", json={"athlete_id": athlete["id"], "category_id": next_category["id"]})

    resp = client.patch(f"/api/v1/athletes/{athlete['id']}", params={"confirm_withdrawal": True}, json={"weight_kg": 50})

    assert resp.status_code == 200
    assert len(_registrations(client, category)) == 1
    assert _registrations(client, next_category) == []
