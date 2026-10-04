import pytest

from app.config import check_production_settings


def test_defaults_are_allowed_outside_production():
    check_production_settings({})
    check_production_settings({"APP_ENV": "development"})


def test_production_rejects_missing_secrets():
    with pytest.raises(RuntimeError, match="SECRET_KEY, ADMIN_PASSWORD"):
        check_production_settings({"APP_ENV": "production"})


def test_production_rejects_default_values():
    env = {"APP_ENV": "production", "SECRET_KEY": "dev-secret-key", "ADMIN_PASSWORD": "admin"}
    with pytest.raises(RuntimeError):
        check_production_settings(env)


def test_production_rejects_only_the_insecure_one():
    env = {"APP_ENV": "production", "SECRET_KEY": "clave-larga-aleatoria", "ADMIN_PASSWORD": "admin"}
    with pytest.raises(RuntimeError, match="ADMIN_PASSWORD") as exc:
        check_production_settings(env)
    assert "SECRET_KEY" not in str(exc.value)


def test_production_accepts_custom_values():
    env = {"APP_ENV": "production", "SECRET_KEY": "clave-larga-aleatoria", "ADMIN_PASSWORD": "otra-clave"}
    check_production_settings(env)
