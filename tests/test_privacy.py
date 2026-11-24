"""Ningún endpoint público devuelve datos personales de los atletas (hay menores)."""

import re

from tests.test_api_auth import PUBLIC_ENDPOINTS

SENSITIVE_FIELDS = {"birth_date", "weight_kg", "ci", "height_cm"}


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

    for method, path in sorted(PUBLIC_ENDPOINTS):
        if method != "GET":
            continue
        params = re.findall(r"\{(\w+)\}", path)
        missing = [p for p in params if p not in path_values]
        assert not missing, f"Agregar un valor de prueba para {missing} ({path})"
        resp = anon_client.get(path.format(**path_values))

        assert resp.status_code == 200, (path, resp.status_code)
        exposed = SENSITIVE_FIELDS & set(_keys(resp.json()))
        assert not exposed, f"{path} devuelve datos personales: {sorted(exposed)}"
