"""Borra todos los datos de una base (torneos, clubes, atletas y todo lo que cuelga de ellos) y, con --seed, carga
los datos de prueba de seed_demo_api.py.

Uso, desde la raíz del repo:
    .venv/bin/python scripts/reset_data.py {local,dev,prod} [--seed] [--yes]
En dev y prod, la URL de la base y el admin salen de `.env` (ver `.env.example`); en local, la base es la misma que
usa la app (`DATABASE_URL` o `dev.db`). Muestra la base y pide escribir el nombre del ambiente para confirmar, salvo
con --yes. No toca `alembic_version`: las migraciones quedan como están.
"""
import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.database import Base, normalize_database_url  # noqa: E402
import app.models  # noqa: E402,F401  (registra las tablas en Base.metadata)
from seed_demo_api import API_URLS, env_setting, seed  # noqa: E402


def database_url(env: str) -> URL:
    if env == "local":
        raw = os.environ.get("DATABASE_URL", "sqlite:///./dev.db")
    else:
        raw = env_setting(env, "DATABASE_URL")
    url = make_url(normalize_database_url(raw))
    # Un DEV_DATABASE_URL copiado de la fila equivocada vaciaría producción.
    if env == "dev" and url.host == make_url(normalize_database_url(env_setting("prod", "DATABASE_URL"))).host:
        sys.exit("DEV_DATABASE_URL apunta al mismo servidor que PROD_DATABASE_URL: no se borró nada.")
    return url


def describe(url: URL) -> str:
    return url.database if url.drivername.startswith("sqlite") else f"{url.host} / {url.database}"


def delete_everything(url: URL) -> None:
    tables = [table.name for table in reversed(Base.metadata.sorted_tables)]
    with create_engine(url).begin() as connection:
        if url.drivername.startswith("sqlite"):
            for table in tables:
                connection.execute(text(f"DELETE FROM {table}"))
        else:
            connection.execute(text(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY"))
    print(f"Borrado todo en {describe(url)}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Borra todos los datos de una base.")
    parser.add_argument("env", choices=API_URLS)
    parser.add_argument("--seed", action="store_true", help="después de borrar, carga los datos de prueba")
    parser.add_argument("--yes", action="store_true", help="no pedir confirmación")
    args = parser.parse_args()

    url = database_url(args.env)
    prompt = f"Se borran TODOS los datos de {args.env} ({describe(url)}). Escribí {args.env} para confirmar: "
    if not args.yes and input(prompt) != args.env:
        sys.exit("Cancelado. No se borró nada.")
    delete_everything(url)
    if args.seed:
        seed(args.env)


if __name__ == "__main__":
    main()
