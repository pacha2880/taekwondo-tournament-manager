"""Borra los datos de prueba que carga seed_demo_api.py, conectándose directo a la base.

Borra solo: los torneos «Copa de Prueba (...)», sus categorías, inscripciones, llaves y combates, y los
atletas de los clubes «Dojang Prueba ...» junto con esos clubes. No toca nada más.

Uso, desde la raíz del repo y con el entorno virtual activado:
    .venv/bin/python scripts/delete_demo_data.py
Pregunta de qué base borrar: local (SQLite o Docker), dev o producción. Para dev y producción pide la
DATABASE_URL (no se muestra al pegarla). Muestra qué va a borrar y pide escribir BORRAR.
Todo ocurre en una transacción: si algo falla, no se borra nada.
"""
import getpass
import sys
from pathlib import Path

from sqlalchemy import bindparam, create_engine, text
from sqlalchemy.engine import make_url

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.database import normalize_database_url  # noqa: E402

TOURNAMENT_NAMES = ["Copa de Prueba (en curso)", "Copa de Prueba (borrador)", "Copa de Prueba (50 atletas)"]
CLUB_NAMES = ["Dojang Prueba Norte", "Dojang Prueba Sur", "Dojang Prueba Este"]

DEMO_TOURNAMENTS = "SELECT id FROM tournaments WHERE name IN :tournaments"
DEMO_CATEGORIES = f"SELECT id FROM categories WHERE tournament_id IN ({DEMO_TOURNAMENTS})"
DEMO_BRACKETS = f"SELECT id FROM brackets WHERE category_id IN ({DEMO_CATEGORIES})"
DEMO_MATCHES = f"SELECT id FROM matches WHERE bracket_id IN ({DEMO_BRACKETS})"
DEMO_ATHLETES = "SELECT id FROM athletes WHERE club_id IN (SELECT id FROM clubs WHERE name IN :clubs)"

# Del más dependiente al menos dependiente, para no violar claves foráneas.
STEPS = [
    ("resultados de rounds", "round_scores", f"match_id IN ({DEMO_MATCHES})"),
    ("combates", "matches", f"bracket_id IN ({DEMO_BRACKETS})"),
    ("llaves", "brackets", f"category_id IN ({DEMO_CATEGORIES})"),
    ("inscripciones", "registrations", f"category_id IN ({DEMO_CATEGORIES}) OR athlete_id IN ({DEMO_ATHLETES})"),
    ("categorías", "categories", f"tournament_id IN ({DEMO_TOURNAMENTS})"),
    ("torneos", "tournaments", "name IN :tournaments"),
    ("atletas", "athletes", f"id IN ({DEMO_ATHLETES})"),
    ("clubes", "clubs", "name IN :clubs"),
]

TARGETS = {
    "1": ("Local (SQLite, dev.db)", "sqlite:///./dev.db"),
    "2": ("Local (PostgreSQL de Docker)", "postgresql+psycopg://taekwondo:taekwondo@localhost:5432/taekwondo"),
    "3": ("Dev (Neon, rama dev)", None),
    "4": ("Producción (Neon)", None),
}
PRODUCTION_CHOICE = "4"

ATHLETES_USED_ELSEWHERE = f"""
SELECT a.name, t.name FROM registrations r
JOIN athletes a ON a.id = r.athlete_id
JOIN categories c ON c.id = r.category_id
JOIN tournaments t ON t.id = c.tournament_id
WHERE a.id IN ({DEMO_ATHLETES}) AND t.name NOT IN :tournaments
"""


def statement(sql: str):
    return text(sql).bindparams(
        *(bindparam(name, expanding=True) for name in ("tournaments", "clubs") if f":{name}" in sql)
    )


PARAMS = {"tournaments": TOURNAMENT_NAMES, "clubs": CLUB_NAMES}


def choose_database() -> tuple[str, str, str]:
    print("¿De qué base querés borrar los datos de prueba?")
    for key, (name, _) in TARGETS.items():
        print(f"  {key}) {name}")
    choice = input("Opción: ").strip()
    if choice not in TARGETS:
        sys.exit("Opción inválida.")
    name, raw_url = TARGETS[choice]
    if raw_url is None:
        raw_url = getpass.getpass(f"DATABASE_URL de {name} (no se muestra al pegarla): ").strip()
        if not raw_url:
            sys.exit("No se ingresó ninguna URL.")
    confirmation = "BORRAR EN PRODUCCION" if choice == PRODUCTION_CHOICE else "BORRAR"
    return name, raw_url, confirmation


def main() -> None:
    name, raw_url, confirmation = choose_database()
    url = make_url(normalize_database_url(raw_url))
    location = url.database if url.drivername.startswith("sqlite") else f"{url.host} / {url.database}"
    print(f"\n{name}: {location}")

    engine = create_engine(url)
    with engine.begin() as connection:
        counts = [
            (label, table, connection.execute(statement(f"SELECT count(*) FROM {table} WHERE {condition}"), PARAMS).scalar())
            for label, table, condition in STEPS
        ]
        if not any(count for _, _, count in counts):
            sys.exit("No hay datos de prueba que borrar.")

        used_elsewhere = connection.execute(statement(ATHLETES_USED_ELSEWHERE), PARAMS).all()
        if used_elsewhere:
            lines = "\n".join(f"  - {athlete} (inscrito en «{tournament}»)" for athlete, tournament in used_elsewhere)
            sys.exit(f"No se borró nada. Estos atletas de prueba están inscritos en torneos que no son de prueba:\n{lines}")

        print("\nSe va a borrar:")
        for label, _, count in counts:
            print(f"  {count:4d} {label}")
        if input(f"\nEscribí {confirmation} para confirmar: ") != confirmation:
            sys.exit("Cancelado. No se borró nada.")

        for _, table, condition in STEPS:
            connection.execute(statement(f"DELETE FROM {table} WHERE {condition}"), PARAMS)
    print("Listo: datos de prueba borrados.")


if __name__ == "__main__":
    main()
