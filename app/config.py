import logging
import os
from collections.abc import Mapping

from app.cors import parse_origins

INSECURE_DEFAULTS = {"SECRET_KEY": "dev-secret-key", "ADMIN_PASSWORD": "admin"}
DEFAULT_ADMIN_USERNAME = "admin"
MIN_SECRET_KEY_BYTES = 32

logger = logging.getLogger(__name__)


def secret_key() -> str:
    return os.environ.get("SECRET_KEY", INSECURE_DEFAULTS["SECRET_KEY"])


def cors_origins() -> list[str]:
    return parse_origins(os.environ.get("CORS_ORIGINS", ""))


def admin_credentials() -> tuple[str, str]:
    return (
        os.environ.get("ADMIN_USERNAME", DEFAULT_ADMIN_USERNAME),
        os.environ.get("ADMIN_PASSWORD", INSECURE_DEFAULTS["ADMIN_PASSWORD"]),
    )


def check_production_settings(env: Mapping[str, str] = os.environ) -> None:
    if env.get("APP_ENV") != "production":
        return
    insecure = [name for name, default in INSECURE_DEFAULTS.items() if env.get(name, default) == default]
    if insecure:
        raise RuntimeError(
            f"APP_ENV=production requiere configurar {', '.join(insecure)} "
            "(no pueden quedar con el valor por defecto)"
        )
    if "*" in parse_origins(env.get("CORS_ORIGINS", "")):
        raise RuntimeError(
            "APP_ENV=production no admite CORS_ORIGINS=*; lista los orígenes permitidos separados por comas"
        )


def warn_if_short_secret_key(env: Mapping[str, str] = os.environ) -> None:
    if env.get("APP_ENV") != "production":
        return
    length = len(env.get("SECRET_KEY", INSECURE_DEFAULTS["SECRET_KEY"]).encode())
    if length < MIN_SECRET_KEY_BYTES:
        logger.warning("SECRET_KEY tiene %d bytes; se recomiendan %d o más", length, MIN_SECRET_KEY_BYTES)
