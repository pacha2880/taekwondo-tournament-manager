import os
from collections.abc import Mapping

INSECURE_DEFAULTS = {"SECRET_KEY": "dev-secret-key", "ADMIN_PASSWORD": "admin"}


def check_production_settings(env: Mapping[str, str] = os.environ) -> None:
    if env.get("APP_ENV") != "production":
        return
    insecure = [name for name, default in INSECURE_DEFAULTS.items() if env.get(name, default) == default]
    if insecure:
        raise RuntimeError(
            f"APP_ENV=production requiere configurar {', '.join(insecure)} "
            "(no pueden quedar con el valor por defecto)"
        )
