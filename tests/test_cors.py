import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import check_production_settings
from app.cors import add_cors, parse_origins

ALLOWED = "https://frontend-amigo.example"
OTHER = "https://sitio-ajeno.example"


def _client(origins):
    app = FastAPI()

    @app.get("/ping")
    def ping():
        return {"ok": True}

    add_cors(app, origins)
    return TestClient(app)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("", []),
        ("   ", []),
        ("https://a.example", ["https://a.example"]),
        ("https://a.example, https://b.example ,,", ["https://a.example", "https://b.example"]),
        ("https://a.example/", ["https://a.example"]),
    ],
)
def test_parse_origins(raw, expected):
    assert parse_origins(raw) == expected


def test_allowed_origin_gets_cors_headers():
    resp = _client([ALLOWED]).get("/ping", headers={"Origin": ALLOWED})

    assert resp.headers["access-control-allow-origin"] == ALLOWED
    assert "access-control-allow-credentials" not in resp.headers


def test_other_origin_gets_no_cors_headers():
    resp = _client([ALLOWED]).get("/ping", headers={"Origin": OTHER})

    assert "access-control-allow-origin" not in resp.headers


def test_without_configured_origins_cors_is_off():
    resp = _client([]).get("/ping", headers={"Origin": ALLOWED})

    assert "access-control-allow-origin" not in resp.headers


def test_preflight_allows_authorization_header_and_patch():
    resp = _client([ALLOWED]).options(
        "/ping",
        headers={
            "Origin": ALLOWED,
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )

    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == ALLOWED
    assert "PATCH" in resp.headers["access-control-allow-methods"]
    assert "authorization" in resp.headers["access-control-allow-headers"].lower()


def test_preflight_from_other_origin_is_rejected():
    resp = _client([ALLOWED]).options(
        "/ping", headers={"Origin": OTHER, "Access-Control-Request-Method": "POST"}
    )

    assert resp.status_code == 400
    assert "access-control-allow-origin" not in resp.headers


def test_production_refuses_wildcard_origin():
    env = {
        "APP_ENV": "production",
        "SECRET_KEY": "clave-larga-aleatoria",
        "ADMIN_PASSWORD": "otra-clave",
        "CORS_ORIGINS": f"{ALLOWED}, *",
    }

    with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
        check_production_settings(env)


def test_production_accepts_explicit_origins():
    env = {
        "APP_ENV": "production",
        "SECRET_KEY": "clave-larga-aleatoria",
        "ADMIN_PASSWORD": "otra-clave",
        "CORS_ORIGINS": f"{ALLOWED},http://localhost:5173",
    }

    check_production_settings(env)


def test_wildcard_is_allowed_outside_production():
    check_production_settings({"CORS_ORIGINS": "*"})


def test_staging_also_allows_wildcard_origin():
    env = {
        "APP_ENV": "staging",
        "SECRET_KEY": "clave-larga-aleatoria",
        "ADMIN_PASSWORD": "otra-clave",
        "CORS_ORIGINS": "*",
    }

    check_production_settings(env)
