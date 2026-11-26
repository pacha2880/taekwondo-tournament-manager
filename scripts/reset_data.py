"""Borra todos los datos de una base (torneos, clubes, atletas y todo lo que cuelga de ellos) y, con --seed, carga
los datos de prueba de seed_demo_api.py.

Uso, desde la raíz del repo:
    .venv/bin/python scripts/reset_data.py {local,dev,prod} [--seed] [--yes]
La URL de la base y el admin salen de `.env` (ver `.env.example`). Pide escribir el nombre del ambiente para
confirmar, salvo con --yes. No toca `alembic_version`: las migraciones quedan como están.
"""
import argparse
import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.database import Base, normalize_database_url  # noqa: E402
import app.models  # noqa: E402,F401  (registra las tablas en Base.metadata)
from seed_demo_api import API_URLS, env_setting, seed  # noqa: E402


def delete_everything(database_url: str) -> None:
    url = make_url(normalize_database_url(database_url))
    location = url.database if url.drivername.startswith("sqlite") else f"{url.host} / {url.database}"
    tables = [table.name for table in reversed(Base.metadata.sorted_tables)]
    with create_engine(url).begin() as connection:
        if url.drivername.startswith("sqlite"):
            for table in tables:
                connection.execute(text(f"DELETE FROM {table}"))
        else:
            connection.execute(text(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY"))
    print(f"Borrado todo en {location}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Borra todos los datos de una base.")
    parser.add_argument("env", choices=API_URLS)
    parser.add_argument("--seed", action="store_true", help="después de borrar, carga los datos de prueba")
    parser.add_argument("--yes", action="store_true", help="no pedir confirmación")
    args = parser.parse_args()

    database_url = env_setting(args.env, "DATABASE_URL")
    if not args.yes and input(f"Se borran TODOS los datos de {args.env}. Escribí {args.env} para confirmar: ") != args.env:
        sys.exit("Cancelado. No se borró nada.")
    delete_everything(database_url)
    if args.seed:
        seed(args.env)


if __name__ == "__main__":
    main()
