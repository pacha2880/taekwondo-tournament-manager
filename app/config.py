import os
from collections.abc import Mapping

from app.cors import parse_origins

INSECURE_DEFAULTS = {"SECRET_KEY": "dev-secret-key", "ADMIN_PASSWORD": "admin"}
DEFAULT_ADMIN_USERNAME = "admin"
MIN_SECRET_KEY_BYTES = 32
# Ambientes desplegados (alcanzables desde internet) y por lo tanto con credenciales propias
# obligatorias. "staging" es como "production" para esto, pero no para el chequeo de CORS: ahí
# sí puede querer aceptar cualquier origen (CORS_ORIGINS=*) mientras se prueba un frontend
# externo sin actualizar la lista a mano.
DEPLOYED_ENVIRONMENTS = {"production", "staging"}


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
    app_env = env.get("APP_ENV")
    if app_env not in DEPLOYED_ENVIRONMENTS:
        return
    insecure = [name for name, default in INSECURE_DEFAULTS.items() if env.get(name, default) == default]
    if insecure:
        raise RuntimeError(
            f"APP_ENV={app_env} requiere configurar {', '.join(insecure)} "
            "(no pueden quedar con el valor por defecto)"
        )
    if app_env == "production" and "*" in parse_origins(env.get("CORS_ORIGINS", "")):
        raise RuntimeError(
            "APP_ENV=production no admite CORS_ORIGINS=*; lista los orígenes permitidos separados por comas"
        )
    secret_key_bytes = len(env["SECRET_KEY"].encode())
    if secret_key_bytes < MIN_SECRET_KEY_BYTES:
        raise RuntimeError(
            f"APP_ENV={app_env} requiere un SECRET_KEY de {MIN_SECRET_KEY_BYTES} bytes o más "
            f"(tiene {secret_key_bytes})"
        )
