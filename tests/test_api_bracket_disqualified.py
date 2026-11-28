"""Descalificados en la llave: ganan sin pelear los que los enfrentan, y los combates sin ganador suben en cascada."""

import pytest

from app.models import Match, MatchStatus, Registration, WeighInStatus


@pytest.fixture()
def bracket_with(client, club, category, tournament, register_n_athletes, set_tournament_status, generate_bracket, db_session):
    """Inscribe `n` atletas, descalifica a los de los índices dados y sortea la llave (los demás se pesan al iniciar)."""

    def _build(n, disqualified, status=WeighInStatus.DISQUALIFIED):
        registrations = register_n_athletes(client, club, category, n)
        set_tournament_status(client, tournament["id"], "weigh_in")
        for index in disqualified:
            db_session.get(Registration, registrations[index]["id"]).weigh_in_status = status
        db_session.commit()
        resp = generate_bracket(client, category)
        assert resp.status_code == 201
        return [r["athlete_id"] for r in registrations], resp.json()["matches"]

    return _build


def _by_status(matches, status):
    return [m for m in matches if m["status"] == status]


def test_a_disqualified_athlete_loses_by_walkover_against_an_enabled_one(bracket_with):
    athlete_ids, matches = bracket_with(4, [0])

    [walkover] = _by_status(matches, "walkover")
    assert walkover["round_number"] == 1
    assert walkover["winner_id"] in athlete_ids[1:]
    assert walkover["winner_id"] != athlete_ids[0]
    assert {walkover["athlete_red_disqualified"], walkover["athlete_blue_disqualified"]} == {True, False}


def test_the_walkover_winner_is_already_in_the_next_round(bracket_with):
    _, matches = bracket_with(4, [0])

    [walkover] = _by_status(matches, "walkover")
    final = next(m for m in matches if m["id"] == walkover["next_match_id"])
    assert walkover["winner_id"] in (final["athlete_red_id"], final["athlete_blue_id"])


def test_a_no_show_counts_as_disqualified(bracket_with):
    athlete_ids, matches = bracket_with(4, [0], status=WeighInStatus.NO_SHOW)

    [walkover] = _by_status(matches, "walkover")
    assert walkover["winner_id"] != athlete_ids[0]


def test_two_disqualified_athletes_facing_each_other_have_no_contest_and_nobody_advances(bracket_with):
    # 4 inscritos, 3 descalificados: un habilitado contra uno, los otros dos entre sí.
    athlete_ids, matches = bracket_with(4, [1, 2, 3])

    [no_contest] = _by_status(matches, "no_contest")
    assert no_contest["winner_id"] is None
    assert no_contest["athlete_red_disqualified"] and no_contest["athlete_blue_disqualified"]
    [final] = [m for m in matches if m["round_number"] == 2]
    assert final["status"] == "walkover"
    assert final["winner_id"] == athlete_ids[0]


def test_one_enabled_with_two_disqualified_wins_the_final_by_walkover(bracket_with):
    athlete_ids, matches = bracket_with(3, [1, 2])

    assert sorted(m["status"] for m in matches) == ["bye", "no_contest", "walkover"]
    [final] = [m for m in matches if m["round_number"] == 2]
    assert final["winner_id"] == athlete_ids[0]


def test_when_everyone_is_disqualified_there_is_no_winner(bracket_with):
    _, matches = bracket_with(4, [0, 1, 2, 3])

    assert {m["status"] for m in matches} == {"no_contest"}
    assert all(m["winner_id"] is None for m in matches)
    final = [m for m in matches if m["next_match_id"] is None][0]
    assert final["athlete_red_id"] is None and final["athlete_blue_id"] is None


def test_disqualified_athletes_never_reach_round_two(client, bracket_with):
    athlete_ids, matches = bracket_with(8, [0, 1, 2, 3])

    assert len(_by_status(matches, "walkover")) == 4
    round_two = {a for m in matches if m["round_number"] == 2 for a in (m["athlete_red_id"], m["athlete_blue_id"])}
    assert round_two == set(athlete_ids[4:])


def test_a_real_winner_facing_a_no_contest_advances_by_walkover(client, bracket_with, score_rounds, db_session):
    athlete_ids, matches = bracket_with(4, [])
    first, second = sorted((m for m in matches if m["round_number"] == 1), key=lambda m: m["slot"])
    db_session.get(Match, first["id"]).status = MatchStatus.NO_CONTEST
    db_session.commit()

    score_rounds(client, second["id"], (10, 5), (10, 5))

    final = client.get(f"/api/v1/matches/{first['next_match_id']}").json()
    assert final["status"] == "walkover"
    assert final["winner_id"] == second["athlete_red_id"]


def test_rounds_are_rejected_in_walkover_and_no_contest_matches(client, bracket_with, score_rounds):
    _, matches = bracket_with(4, [1, 2, 3])

    for status in ("walkover", "no_contest"):
        match = _by_status(matches, status)[0]
        resp = score_rounds(client, match["id"], (10, 5))[0]
        assert resp.status_code == 409, status


def test_the_bracket_flags_who_is_disqualified(client, bracket_with, category, anon_client):
    athlete_ids, _ = bracket_with(4, [0])

    matches = anon_client.get(f"/api/v1/categories/{category['id']}/bracket").json()["matches"]
    flagged = {
        side_id
        for m in matches
        for side_id, flag in ((m["athlete_red_id"], m["athlete_red_disqualified"]), (m["athlete_blue_id"], m["athlete_blue_disqualified"]))
        if flag
    }
    assert flagged == {athlete_ids[0]}
    match = next(m for m in matches if m["athlete_red_disqualified"] or m["athlete_blue_disqualified"])
    assert client.get(f"/api/v1/matches/{match['id']}").json()["athlete_red_disqualified"] == match["athlete_red_disqualified"]


def test_finish_counts_walkover_and_no_contest_as_played(client, bracket_with, tournament):
    bracket_with(3, [1, 2])  # bye + walkover + no_contest + final por walkover

    assert client.post(f"/api/v1/tournaments/{tournament['id']}/finish").status_code == 200


def test_a_bye_and_a_cascade_walkover_answer_409_not_400(client, bracket_with, score_rounds):
    # 5 inscritos con 4 descalificados: bye al habilitado y walkover en cascada con un lado vacío.
    athlete_ids, matches = bracket_with(5, [1, 2, 3, 4])

    [bye] = _by_status(matches, "bye")
    cascade = next(m for m in _by_status(matches, "walkover") if m["round_number"] > 1)
    assert None in (cascade["athlete_red_id"], cascade["athlete_blue_id"])
    for match in (bye, cascade):
        assert score_rounds(client, match["id"], (10, 5))[0].status_code == 409


def test_one_enabled_athlete_wins_the_final_even_when_disqualified_ones_get_byes(bracket_with):
    athlete_ids, matches = bracket_with(5, [1, 2, 3, 4])

    assert sorted(m["status"] for m in matches if m["round_number"] == 1) == ["bye", "no_contest", "no_contest", "no_contest"]
    [final] = [m for m in matches if m["next_match_id"] is None]
    assert (final["status"], final["winner_id"]) == ("walkover", athlete_ids[0])
