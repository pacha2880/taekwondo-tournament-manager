from datetime import datetime, timedelta, timezone

import pytest

from app.api.lifecycle import current_status
from app.models import Tournament, TournamentStatus

DEADLINE = datetime(2027, 6, 1, 12, 0)  # UTC sin zona, como se guarda


def _parse_utc(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00"))  # Python 3.10 no entiende la Z


def _future_deadline(days=30):
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


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
    assert start_with_registration_open.json()["detail"] == "Las inscripciones todavía no cerraron"
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
    match = client.post(f"/api/v1/categories/{category['id']}/bracket").json()["matches"][0]

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
    matches = client.post(f"/api/v1/categories/{category['id']}/bracket").json()["matches"]
    [bye] = [m for m in matches if m["status"] == "bye"]
    [semifinal] = [m for m in matches if m["round_number"] == 1 and m["status"] == "pending"]
    [final] = [m for m in matches if m["next_match_id"] is None]

    score_rounds(client, semifinal["id"], (10, 5), (10, 5))
    score_rounds(client, final["id"], (10, 5), (10, 5))

    assert client.get(f"/api/v1/matches/{bye['id']}").json()["status"] == "bye"
    assert client.post(f"{url}/finish").status_code == 200


@pytest.mark.parametrize("athletes,expected_status", [(1, 200), (2, 409)])
def test_a_category_without_bracket_blocks_finish_only_with_two_or_more_athletes(
    client, club, category, tournament, register_n_athletes, set_tournament_status, athletes, expected_status
):
    register_n_athletes(client, club, category, athletes)
    url = f"/api/v1/tournaments/{tournament['id']}"
    set_tournament_status(client, tournament["id"], "in_progress")

    assert client.post(f"{url}/finish").status_code == expected_status


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
    deadline = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(days=30)
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
    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()

    resp = client.patch(f"/api/v1/tournaments/{draft_tournament['id']}", json={"registration_deadline": past})

    assert resp.status_code == 422
    assert resp.json()["detail"] == "La fecha límite de inscripción debe ser futura"


def test_the_deadline_needs_a_time_zone(client, draft_tournament):
    naive = (datetime.now() + timedelta(days=30)).replace(tzinfo=None).isoformat()

    resp = client.patch(f"/api/v1/tournaments/{draft_tournament['id']}", json={"registration_deadline": naive})

    assert resp.status_code == 422


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
    assert abs(datetime.now(timezone.utc) - deadline) < timedelta(seconds=5)


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
