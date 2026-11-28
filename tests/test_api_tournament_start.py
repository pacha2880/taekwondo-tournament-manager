"""Al empezar el torneo se cierra el pesaje: los que no se presentaron o no decidieron quedan fuera."""

import pytest


@pytest.fixture()
def register(client, club, category):
    def _register(name, ci, target=None, **athlete_fields):
        athlete = client.post(
            "/api/v1/athletes",
            json={
                "name": name, "ci": ci, "birth_date": "2012-01-01", "gender": "male", "grade": "kup_6",
                "weight_kg": 40, "club_id": club["id"], **athlete_fields,
            },
        ).json()
        resp = client.post(
            "/api/v1/registrations", json={"athlete_id": athlete["id"], "category_id": (target or category)["id"]}
        )
        assert resp.status_code == 201
        return resp.json()

    return _register


def _weigh(client, registration, weight):
    assert client.post(f"/api/v1/registrations/{registration['id']}/weigh-in", json={"weight_kg": weight}).status_code == 200


def _status_of(client, registration):
    listed = client.get("/api/v1/registrations", params={"category_id": registration["category_id"]}).json()
    return next(r["weigh_in_status"] for r in listed if r["id"] == registration["id"])


def _start(client, tournament):
    resp = client.post(f"/api/v1/tournaments/{tournament['id']}/start")
    assert resp.status_code == 200
    return resp.json()


def test_start_resolves_every_registration_left_undecided(client, tournament, register, set_tournament_status):
    cleared, failed_first, second_allowed, second_failed, pending = (
        register(name, ci) for name, ci in [("A", "9000001"), ("B", "9000002"), ("C", "9000003"), ("D", "9000004"), ("E", "9000005")]
    )
    set_tournament_status(client, tournament["id"], "weigh_in")
    _weigh(client, cleared, 40)
    _weigh(client, failed_first, 50)
    _weigh(client, second_allowed, 50)
    client.post(f"/api/v1/registrations/{second_allowed['id']}/second-weigh-in")
    _weigh(client, second_failed, 50)
    client.post(f"/api/v1/registrations/{second_failed['id']}/second-weigh-in")
    _weigh(client, second_failed, 50)

    _start(client, tournament)

    assert [_status_of(client, r) for r in (cleared, failed_first, second_allowed, second_failed, pending)] == [
        "cleared", "disqualified", "disqualified", "disqualified", "no_show",
    ]


def test_start_lists_who_did_not_show_up_by_category_and_name(client, tournament, category, register, set_tournament_status):
    zoe = register("Zoe", "9000001")
    ana = register("Ana", "9000002")
    set_tournament_status(client, tournament["id"], "weigh_in")

    not_weighed_in = _start(client, tournament)["not_weighed_in"]

    assert not_weighed_in == [
        {
            "registration_id": r["id"], "athlete_id": r["athlete_id"], "name": name, "club": "Dojang Central",
            "category_id": category["id"], "category_name": category["name"],
        }
        for r, name in ((ana, "Ana"), (zoe, "Zoe"))
    ]


def test_start_with_everyone_weighed_in_lists_nobody(client, tournament, register, set_tournament_status):
    registration = register("Ana", "9000001")
    set_tournament_status(client, tournament["id"], "weigh_in")
    _weigh(client, registration, 40)

    assert _start(client, tournament)["not_weighed_in"] == []


def test_start_leaves_festival_alone(client, tournament, register, set_tournament_status):
    categories = client.get("/api/v1/categories", params={"tournament_id": tournament["id"]}).json()
    festival = next(c for c in categories if c["age_label"] == "Festival" and c["gender"] == "male")
    registration = register("Beto", "9000001", target=festival, birth_date="2018-01-01", grade="kup_10", weight_kg=25)
    set_tournament_status(client, tournament["id"], "weigh_in")

    started = _start(client, tournament)

    assert _status_of(client, registration) == "not_required"
    assert started["not_weighed_in"] == []


def test_start_does_not_touch_another_tournament(client, tournament, category, register, find_category, set_tournament_status):
    other = client.post(
        "/api/v1/tournaments", json={"name": "Otra Copa", "date": "2026-11-20", "location": "Santa Ana"}
    ).json()
    set_tournament_status(client, other["id"], "registration_open")
    other_registration = register("Otro", "9000009", target=find_category(other["id"], "male", "Cadete", "37.1–41 kg"))
    own = register("Propio", "9000001")
    assert client.post(f"/api/v1/tournaments/{tournament['id']}/close-registration").status_code == 200

    started = _start(client, tournament)

    assert [r["registration_id"] for r in started["not_weighed_in"]] == [own["id"]]
    assert _status_of(client, other_registration) == "pending"
