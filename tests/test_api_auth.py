from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.auth import ALGORITHM, TOKEN_TTL, create_access_token
from app.config import secret_key
from app.main import app

PUBLIC_ENDPOINTS = {
    ("POST", "/api/v1/auth/login"),
    ("GET", "/api/v1/clubs"),
    ("GET", "/api/v1/clubs/{club_id}"),
    ("GET", "/api/v1/tournaments"),
    ("GET", "/api/v1/tournaments/{tournament_id}"),
    ("GET", "/api/v1/categories"),
    ("GET", "/api/v1/categories/{category_id}"),
    ("GET", "/api/v1/categories/{category_id}/bracket"),
    ("GET", "/api/v1/matches/{match_id}"),
}


def _token(secret=None, algorithm=ALGORITHM, **claims):
    now = datetime.now(timezone.utc)
    payload = {"sub": "admin", "iat": now, "exp": now + timedelta(hours=1), **claims}
    payload = {key: value for key, value in payload.items() if value is not None}
    return jwt.encode(payload, secret if secret is not None else secret_key(), algorithm=algorithm)


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


def _api_operations_by_protection():
    protected, unprotected = set(), set()
    for path, operations in app.openapi()["paths"].items():
        if not path.startswith("/api/v1"):
            continue
        for method, operation in operations.items():
            (protected if operation.get("security") else unprotected).add((method.upper(), path))
    return protected, unprotected


def test_every_api_endpoint_requires_login_unless_explicitly_public():
    protected, unprotected = _api_operations_by_protection()

    assert ("POST", "/api/v1/clubs") in protected, "el inventario no está viendo las rutas de la API"
    assert unprotected == PUBLIC_ENDPOINTS


def test_login_returns_a_bearer_token(anon_client):
    resp = anon_client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == int(TOKEN_TTL.total_seconds()) == 8 * 3600
    claims = jwt.decode(body["access_token"], secret_key(), algorithms=[ALGORITHM])
    assert claims["sub"] == "admin"
    assert claims["exp"] - claims["iat"] == body["expires_in"]


@pytest.mark.parametrize(
    "credentials",
    [
        {"username": "admin", "password": "incorrecta"},
        {"username": "otro", "password": "admin"},
    ],
)
def test_login_rejects_wrong_credentials(anon_client, credentials):
    resp = anon_client.post("/api/v1/auth/login", data=credentials)

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Usuario o contraseña incorrectos"
    assert resp.headers["www-authenticate"] == "Bearer"


def test_issued_token_can_be_used_on_a_protected_endpoint(anon_client):
    login = anon_client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin"})

    resp = anon_client.post(
        "/api/v1/clubs", json={"name": "Dojang Token"}, headers=_bearer(login.json()["access_token"])
    )

    assert resp.status_code == 201


@pytest.mark.parametrize(
    "method,path",
    [
        ("post", "/api/v1/clubs"),
        ("post", "/api/v1/athletes"),
        ("patch", "/api/v1/athletes/1"),
        ("patch", "/api/v1/clubs/1"),
        ("post", "/api/v1/tournaments"),
        ("patch", "/api/v1/tournaments/1"),
        ("post", "/api/v1/categories"),
        ("post", "/api/v1/registrations"),
        ("post", "/api/v1/categories/1/bracket"),
        ("post", "/api/v1/matches/1/rounds"),
        ("get", "/api/v1/athletes"),
        ("get", "/api/v1/athletes/1"),
        ("get", "/api/v1/registrations"),
    ],
)
def test_protected_endpoints_reject_requests_without_a_token(anon_client, method, path):
    resp = getattr(anon_client, method)(path)

    assert resp.status_code == 401
    assert resp.headers["www-authenticate"] == "Bearer"
    assert "autenticado" in resp.json()["detail"]


def test_garbage_token_is_rejected(anon_client):
    resp = anon_client.get("/api/v1/athletes", headers=_bearer("esto-no-es-un-jwt"))

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Token inválido"


def test_token_signed_with_another_secret_is_rejected(anon_client):
    resp = anon_client.get(
        "/api/v1/athletes", headers=_bearer(_token(secret="otra-clave-distinta-de-32-bytes-o-mas!!"))
    )

    assert resp.status_code == 401


def test_unsigned_token_with_alg_none_is_rejected(anon_client):
    unsigned = jwt.encode(
        {"sub": "admin", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}, key=None, algorithm="none"
    )

    resp = anon_client.get("/api/v1/athletes", headers=_bearer(unsigned))

    assert resp.status_code == 401


def test_expired_token_is_rejected_with_a_specific_message(anon_client):
    past = datetime.now(timezone.utc) - timedelta(hours=1)

    resp = anon_client.get("/api/v1/athletes", headers=_bearer(_token(exp=past)))

    assert resp.status_code == 401
    assert "venció" in resp.json()["detail"]


def test_token_without_expiration_is_rejected(anon_client):
    no_exp = jwt.encode({"sub": "admin"}, secret_key(), algorithm=ALGORITHM)

    resp = anon_client.get("/api/v1/athletes", headers=_bearer(no_exp))

    assert resp.status_code == 401


def test_token_for_another_user_is_rejected(anon_client):
    resp = anon_client.get("/api/v1/athletes", headers=_bearer(_token(sub="otro")))

    assert resp.status_code == 401


def test_small_clock_skew_is_tolerated(anon_client):
    issued_slightly_in_the_future = datetime.now(timezone.utc) + timedelta(seconds=10)

    resp = anon_client.get("/api/v1/athletes", headers=_bearer(_token(iat=issued_slightly_in_the_future)))

    assert resp.status_code == 200


def test_token_created_by_the_app_round_trips():
    token = create_access_token("admin")

    claims = jwt.decode(token, secret_key(), algorithms=[ALGORITHM])

    assert claims["sub"] == "admin"


def test_public_reads_work_without_a_token(anon_client, club, tournament, category):
    assert anon_client.get("/api/v1/clubs").status_code == 200
    assert anon_client.get(f"/api/v1/clubs/{club['id']}").status_code == 200
    assert anon_client.get("/api/v1/tournaments").status_code == 200
    assert anon_client.get(f"/api/v1/tournaments/{tournament['id']}").status_code == 200
    assert anon_client.get("/api/v1/categories").status_code == 200
    assert anon_client.get(f"/api/v1/categories/{category['id']}").status_code == 200


def test_bracket_and_match_are_public(anon_client, client, club, category, register_n_athletes):
    register_n_athletes(client, club, category, 2)
    bracket = client.post(f"/api/v1/categories/{category['id']}/bracket").json()
    match_id = bracket["matches"][0]["id"]

    assert anon_client.get(f"/api/v1/categories/{category['id']}/bracket").status_code == 200
    assert anon_client.get(f"/api/v1/matches/{match_id}").status_code == 200
