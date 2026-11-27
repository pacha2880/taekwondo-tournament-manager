"""Ningún endpoint público devuelve datos personales de los atletas (hay menores)."""

import re

from tests.test_api_auth import OPTIONAL_TOKEN_ENDPOINTS, PUBLIC_ENDPOINTS

SENSITIVE_FIELDS = {"birth_date", "weight_kg", "first_weight_kg", "second_weight_kg", "ci", "height_cm"}


def _keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _keys(item)


def test_public_endpoints_never_return_sensitive_athlete_fields(
    client, anon_client, club, category, register_n_athletes, generate_bracket
):
    register_n_athletes(client, club, category, 2)
    bracket = generate_bracket(client, category).json()
    path_values = {
        "club_id": club["id"],
        "tournament_id": category["tournament_id"],
        "category_id": category["id"],
        "match_id": bracket["matches"][0]["id"],
    }

    for method, path in sorted(PUBLIC_ENDPOINTS | OPTIONAL_TOKEN_ENDPOINTS):
        if method != "GET":
            continue
        params = re.findall(r"\{(\w+)\}", path)
        missing = [p for p in params if p not in path_values]
        assert not missing, f"Agregar un valor de prueba para {missing} ({path})"
        resp = anon_client.get(path.format(**path_values))

        assert resp.status_code == 200, (path, resp.status_code)
        exposed = SENSITIVE_FIELDS & set(_keys(resp.json()))
        assert not exposed, f"{path} devuelve datos personales: {sorted(exposed)}"


def test_public_registrants_show_the_weigh_in_status_but_never_the_weights(
    client, anon_client, club, category, register_n_athletes, set_tournament_status
):
    (registration,) = register_n_athletes(client, club, category, 1)
    set_tournament_status(client, category["tournament_id"], "weigh_in")
    client.post(f"/api/v1/registrations/{registration['id']}/weigh-in", json={"weight_kg": 40})

    (registrant,) = anon_client.get(f"/api/v1/categories/{category['id']}/registrants").json()

    assert registrant["weigh_in_status"] == "cleared"
    assert not {"first_weight_kg", "second_weight_kg", "weight_kg"} & registrant.keys()
