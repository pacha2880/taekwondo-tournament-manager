from datetime import datetime, timedelta, timezone

import pytest

from app import clock as app_clock
from app.models import current_status
from app.models import Tournament, TournamentStatus

DEADLINE = datetime(2027, 6, 1, 12, 0)  # UTC sin zona, como se guarda


def _parse_utc(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00"))  # Python 3.10 no entiende la Z


def _future_deadline(days=30):
    return (app_clock.utc_now() + timedelta(days=days)).isoformat()


def test_create_tournament_defaults_to_draft(client, draft_tournament):
    assert draft_tournament["status"] == "draft"
    assert draft_tournament["registration_deadline"] is None


def test_get_missing_tournament_404(client):
    resp = client.get("/api/v1/tournaments/999")
    assert resp.status_code == 404


def test_patch_changes_the_data_but_no_longer_accepts_a_status(client, draft_tournament):
    url = f"/api/v1/tournaments/{draft_tournament['id']}"

    renamed = client.patch(url, json={"name": "Copa Corregida"})
    with_status = client.patch(url, json={"status": "finished"})

    assert renamed.json()["name"] == "Copa Corregida"
    assert with_status.status_code == 422
    assert client.get(url).json()["status"] == "draft"


def test_tournament_goes_through_the_whole_cycle(client, tournament):
    url = f"/api/v1/tournaments/{tournament['id']}"

    assert tournament["status"] == "registration_open"
    assert client.post(f"{url}/close-registration").json()["status"] == "weigh_in"
    started = client.post(f"{url}/start")
    finished = client.post(f"{url}/finish")

    assert started.json()["status"] == "in_progress"
    assert finished.json()["status"] == "finished"


def test_each_action_only_works_from_its_own_status(client, tournament, set_tournament_status):
    url = f"/api/v1/tournaments/{tournament['id']}"

    finish_from_draft = client.post(f"{url}/finish")
    start_with_registration_open = client.post(f"{url}/start")
    set_tournament_status(client, tournament["id"], "in_progress")
    start_again = client.post(f"{url}/start")
    client.post(f"{url}/finish")
    finish_again = client.post(f"{url}/finish")

    assert finish_from_draft.status_code == 409
    assert finish_from_draft.json()["detail"] == "Solo se puede finalizar un torneo en curso"
    assert start_with_registration_open.status_code == 409
    assert start_with_registration_open.json()["detail"] == "El torneo solo se inicia desde el pesaje"
    assert start_again.status_code == 409
    assert start_again.json()["detail"] == "El torneo ya empezó"
    assert finish_again.status_code == 409


def test_actions_require_an_existing_tournament(client):
    assert client.post("/api/v1/tournaments/999/start").status_code == 404
    assert client.post("/api/v1/tournaments/999/finish").status_code == 404
    assert client.post("/api/v1/tournaments/999/open-registration").status_code == 404
    assert client.post("/api/v1/tournaments/999/close-registration").status_code == 404


def test_finish_is_rejected_while_a_bracket_has_matches_to_play(
    client, club, category, tournament, register_n_athletes, score_rounds, set_tournament_status
):
    register_n_athletes(client, club, category, 2)
    url = f"/api/v1/tournaments/{tournament['id']}"
    set_tournament_status(client, tournament["id"], "in_progress")
    match = client.get(f"/api/v1/categories/{category['id']}/bracket").json()["matches"][0]

    before = client.post(f"{url}/finish")
    score_rounds(client, match["id"], (10, 5), (10, 5))
    after = client.post(f"{url}/finish")

    assert before.status_code == 409
    assert before.json()["detail"] == "Quedan combates por jugar en: Principiantes · Cadete · Masculino · 37.1–41 kg"
    assert after.status_code == 200


def test_finish_ignores_byes(client, club, category, tournament, register_n_athletes, score_rounds, set_tournament_status):
    register_n_athletes(client, club, category, 3)
    url = f"/api/v1/tournaments/{tournament['id']}"
    set_tournament_status(client, tournament["id"], "in_progress")
    matches = client.get(f"/api/v1/categories/{category['id']}/bracket").json()["matches"]
    [bye] = [m for m in matches if m["status"] == "bye"]
    [semifinal] = [m for m in matches if m["round_number"] == 1 and m["status"] == "pending"]
    [final] = [m for m in matches if m["next_match_id"] is None]

    score_rounds(client, semifinal["id"], (10, 5), (10, 5))
    score_rounds(client, final["id"], (10, 5), (10, 5))

    assert client.get(f"/api/v1/matches/{bye['id']}").json()["status"] == "bye"
    assert client.post(f"{url}/finish").status_code == 200


def _festival_category(client, tournament):
    categories = client.get("/api/v1/categories", params={"tournament_id": tournament["id"]}).json()
    return next(c for c in categories if c["age_label"] == "Festival" and c["gender"] == "male")


def _register_children(client, club, festival, n):
    for i in range(n):
        athlete = client.post(
            "/api/v1/athletes",
            json={
                "name": f"Niño {i}", "ci": str(8000000 + i), "birth_date": "2018-03-01", "gender": "male",
                "grade": "kup_10", "weight_kg": 20, "club_id": club["id"],
            },
        ).json()
        resp = client.post("/api/v1/registrations", json={"athlete_id": athlete["id"], "category_id": festival["id"]})
        assert resp.status_code == 201


def test_start_draws_every_category_with_two_or_more_athletes_except_festival(
    client, club, category, tournament, register_n_athletes, find_category, set_tournament_status
):
    lone = find_category(tournament["id"], "male", "Cadete", "41.1–45 kg")
    empty = find_category(tournament["id"], "male", "Cadete", "45.1–49 kg")
    festival = _festival_category(client, tournament)
    register_n_athletes(client, club, category, 2)
    solo = client.post(
        "/api/v1/athletes",
        json={"name": "Solo", "ci": "9000000", "birth_date": "2012-01-01", "gender": "male", "grade": "kup_6",
              "weight_kg": 43, "club_id": club["id"]},
    ).json()
    client.post("/api/v1/registrations", json={"athlete_id": solo["id"], "category_id": lone["id"]})
    _register_children(client, club, festival, 2)

    set_tournament_status(client, tournament["id"], "in_progress")

    listed = client.get("/api/v1/categories", params={"tournament_id": tournament["id"]}).json()
    with_bracket = {c["id"] for c in listed if c["has_bracket"]}
    assert with_bracket == {category["id"]}
    assert {lone["id"], empty["id"], festival["id"]}.isdisjoint(with_bracket)


def test_start_draws_with_the_disqualified_already_marked(
    client, club, category, tournament, register_n_athletes, set_tournament_status
):
    register_n_athletes(client, club, category, 2)
    set_tournament_status(client, tournament["id"], "in_progress", weigh_everyone=False)

    [match] = client.get(f"/api/v1/categories/{category['id']}/bracket").json()["matches"]

    assert match["status"] == "no_contest"  # los dos quedaron en no_show al iniciar


def test_a_festival_with_registrants_does_not_block_finish(client, club, tournament, set_tournament_status):
    festival = _festival_category(client, tournament)
    _register_children(client, club, festival, 2)
    set_tournament_status(client, tournament["id"], "in_progress")

    assert client.get(f"/api/v1/categories/{festival['id']}/bracket").status_code == 404
    assert client.post(f"/api/v1/tournaments/{tournament['id']}/finish").status_code == 200


@pytest.mark.parametrize(
    "stored_status, deadline, now, expected",
    [
        (TournamentStatus.REGISTRATION_OPEN, DEADLINE, DEADLINE - timedelta(seconds=1), TournamentStatus.REGISTRATION_OPEN),
        (TournamentStatus.REGISTRATION_OPEN, DEADLINE, DEADLINE, TournamentStatus.WEIGH_IN),
        (TournamentStatus.REGISTRATION_OPEN, DEADLINE, DEADLINE + timedelta(days=1), TournamentStatus.WEIGH_IN),
        (TournamentStatus.DRAFT, DEADLINE, DEADLINE + timedelta(days=1), TournamentStatus.DRAFT),
        (TournamentStatus.IN_PROGRESS, DEADLINE, DEADLINE + timedelta(days=1), TournamentStatus.IN_PROGRESS),
        (TournamentStatus.REGISTRATION_OPEN, None, DEADLINE, TournamentStatus.REGISTRATION_OPEN),
    ],
)
def test_current_status_turns_into_weigh_in_only_once_the_deadline_passes(stored_status, deadline, now, expected):
    assert current_status(stored_status, deadline, now.replace(tzinfo=timezone.utc)) == expected


def test_the_deadline_is_returned_in_utc_with_offset(client, draft_tournament):
    url = f"/api/v1/tournaments/{draft_tournament['id']}"
    deadline = app_clock.utc_now().replace(microsecond=0) + timedelta(days=30)
    bolivia = timezone(timedelta(hours=-4))

    resp = client.patch(url, json={"registration_deadline": deadline.astimezone(bolivia).isoformat()})

    assert resp.status_code == 200
    assert _parse_utc(resp.json()["registration_deadline"]) == deadline
    assert resp.json()["registration_deadline"].endswith(("Z", "+00:00"))
    assert client.get(url).json()["registration_deadline"] == resp.json()["registration_deadline"]


def test_the_deadline_can_be_set_and_cleared_in_draft(client, draft_tournament):
    url = f"/api/v1/tournaments/{draft_tournament['id']}"

    client.patch(url, json={"registration_deadline": _future_deadline()})
    cleared = client.patch(url, json={"registration_deadline": None})

    assert cleared.status_code == 200
    assert cleared.json()["registration_deadline"] is None


def test_the_deadline_must_be_in_the_future(client, draft_tournament):
    past = (app_clock.utc_now() - timedelta(minutes=1)).isoformat()

    resp = client.patch(f"/api/v1/tournaments/{draft_tournament['id']}", json={"registration_deadline": past})

    assert resp.status_code == 422
    assert resp.json()["detail"] == "La fecha límite de inscripción debe ser futura"


def test_the_deadline_needs_a_time_zone(client, draft_tournament):
    naive = (app_clock.utc_now() + timedelta(days=30)).replace(tzinfo=None).isoformat()

    resp = client.patch(f"/api/v1/tournaments/{draft_tournament['id']}", json={"registration_deadline": naive})

    assert resp.status_code == 422


@pytest.mark.parametrize(
    ("deadline", "status_code"),
    [("2026-11-14T23:59:00+00:00", 200), ("2026-11-15T00:00:00+00:00", 422), ("2026-11-14T21:00:00-04:00", 422)],
)
def test_the_deadline_must_fall_before_the_tournament_day_in_utc(client, draft_tournament, deadline, status_code):
    resp = client.patch(f"/api/v1/tournaments/{draft_tournament['id']}", json={"registration_deadline": deadline})

    assert resp.status_code == status_code
    if status_code == 422:
        assert resp.json()["detail"] == "La fecha límite de inscripción debe ser anterior al día del torneo (en UTC)"


def test_the_tournament_date_cannot_move_onto_the_deadline_while_registration_is_open(client, tournament):
    url = f"/api/v1/tournaments/{tournament['id']}"

    resp = client.patch(url, json={"date": "2026-11-01"})

    assert resp.status_code == 422
    assert client.get(url).json()["date"] == "2026-11-15"


def test_patch_rejects_emptying_a_required_field(client, draft_tournament):
    resp = client.patch(f"/api/v1/tournaments/{draft_tournament['id']}", json={"date": None, "name": None})

    assert resp.status_code == 422
    assert resp.json()["detail"] == "Estos campos no pueden quedar vacíos: name, date"


def test_date_and_deadline_are_checked_together_in_the_same_patch(client, tournament):
    resp = client.patch(
        f"/api/v1/tournaments/{tournament['id']}",
        json={"date": "2027-01-10", "registration_deadline": "2027-01-09T12:00:00+00:00"},
    )

    assert resp.status_code == 200


def test_a_postponed_tournament_can_change_its_date_after_registration_closed(
    client, tournament, set_tournament_status
):
    set_tournament_status(client, tournament["id"], "weigh_in")

    resp = client.patch(f"/api/v1/tournaments/{tournament['id']}", json={"date": "2025-10-01"})

    assert resp.status_code == 200


def test_the_deadline_can_move_but_not_be_cleared_while_registration_is_open(client, tournament):
    url = f"/api/v1/tournaments/{tournament['id']}"

    moved = client.patch(url, json={"registration_deadline": _future_deadline(60)})
    cleared = client.patch(url, json={"registration_deadline": None})

    assert moved.status_code == 200
    assert cleared.status_code == 422
    assert client.get(url).json()["registration_deadline"] == moved.json()["registration_deadline"]


@pytest.mark.parametrize("status", ["weigh_in", "in_progress", "finished"])
def test_the_deadline_cannot_change_after_registration_closed(client, tournament, set_tournament_status, status):
    set_tournament_status(client, tournament["id"], status)

    resp = client.patch(
        f"/api/v1/tournaments/{tournament['id']}", json={"registration_deadline": _future_deadline()}
    )

    assert resp.status_code == 409


def test_the_other_fields_stay_editable_after_registration_closed(client, tournament, set_tournament_status):
    set_tournament_status(client, tournament["id"], "weigh_in")

    resp = client.patch(f"/api/v1/tournaments/{tournament['id']}", json={"location": "Sucre"})

    assert resp.status_code == 200
    assert resp.json()["location"] == "Sucre"


def test_open_registration_needs_a_future_deadline(client, draft_tournament):
    url = f"/api/v1/tournaments/{draft_tournament['id']}/open-registration"

    without_deadline = client.post(url)
    client.patch(f"/api/v1/tournaments/{draft_tournament['id']}", json={"registration_deadline": _future_deadline()})
    opened = client.post(url)

    assert without_deadline.status_code == 409
    assert opened.status_code == 200
    assert opened.json()["status"] == "registration_open"


def test_open_registration_is_rejected_with_an_expired_deadline(client, draft_tournament, clock):
    client.patch(f"/api/v1/tournaments/{draft_tournament['id']}", json={"registration_deadline": _future_deadline(1)})
    clock.advance(days=2)

    resp = client.post(f"/api/v1/tournaments/{draft_tournament['id']}/open-registration")

    assert resp.status_code == 409


@pytest.mark.parametrize("status", ["registration_open", "weigh_in", "in_progress", "finished"])
def test_open_registration_only_works_from_draft(client, tournament, set_tournament_status, status):
    set_tournament_status(client, tournament["id"], status)

    assert client.post(f"/api/v1/tournaments/{tournament['id']}/open-registration").status_code == 409


def test_close_registration_moves_to_weigh_in_and_the_deadline_to_now(client, tournament):
    resp = client.post(f"/api/v1/tournaments/{tournament['id']}/close-registration")

    assert resp.status_code == 200
    assert resp.json()["status"] == "weigh_in"
    deadline = _parse_utc(resp.json()["registration_deadline"])
    assert abs(app_clock.utc_now() - deadline) < timedelta(seconds=5)


def test_close_registration_is_rejected_from_draft(client, draft_tournament):
    assert client.post(f"/api/v1/tournaments/{draft_tournament['id']}/close-registration").status_code == 409


def test_close_registration_is_rejected_when_repeated(client, tournament):
    url = f"/api/v1/tournaments/{tournament['id']}/close-registration"
    client.post(url)

    assert client.post(url).status_code == 409


def test_the_tournament_enters_weigh_in_when_the_deadline_passes_without_writing_it(
    client, tournament, clock, db_session
):
    url = f"/api/v1/tournaments/{tournament['id']}"
    clock.advance(days=366)

    assert client.get(url).json()["status"] == "weigh_in"
    assert client.post(f"{url}/close-registration").status_code == 409
    assert client.patch(url, json={"registration_deadline": _future_deadline()}).status_code == 409
    assert db_session.get(Tournament, tournament["id"]).stored_status == TournamentStatus.REGISTRATION_OPEN
    assert client.post(f"{url}/start").status_code == 200
