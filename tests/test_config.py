import pytest

from app.config import check_production_settings, warn_if_short_secret_key


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


def test_staging_also_rejects_default_values():
    env = {"APP_ENV": "staging", "SECRET_KEY": "dev-secret-key", "ADMIN_PASSWORD": "admin"}
    with pytest.raises(RuntimeError, match="SECRET_KEY, ADMIN_PASSWORD"):
        check_production_settings(env)


def test_short_secret_key_is_warned_about_in_production(caplog):
    short_key = "clave-corta-de-20-bs"
    assert len(short_key) == 20

    warn_if_short_secret_key({"APP_ENV": "production", "SECRET_KEY": short_key})

    assert "SECRET_KEY tiene 20 bytes; se recomiendan 32 o más" in caplog.text
    assert short_key not in caplog.text


def test_long_secret_key_is_not_warned_about(caplog):
    warn_if_short_secret_key({"APP_ENV": "production", "SECRET_KEY": "x" * 32})

    assert caplog.text == ""


def test_short_secret_key_is_ignored_outside_production(caplog):
    warn_if_short_secret_key({"SECRET_KEY": "corta"})
    warn_if_short_secret_key({"APP_ENV": "development", "SECRET_KEY": "corta"})

    assert caplog.text == ""


def test_short_secret_key_is_also_warned_about_in_staging(caplog):
    warn_if_short_secret_key({"APP_ENV": "staging", "SECRET_KEY": "clave-corta-de-20-bs"})

    assert "SECRET_KEY tiene 20 bytes; se recomiendan 32 o más" in caplog.text
