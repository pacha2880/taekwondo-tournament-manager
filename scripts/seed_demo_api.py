"""Carga datos de prueba por la API: un torneo en cada estado del ciclo, con casos borde a la vista.

- «Copa de Prueba (en preparación)» (`draft`): fecha futura, fecha límite fijada sin abrir y estructura retocada (el
  grupo «Principiantes» se llama «Iniciación» y Junior masculino suma la división 63.1–68 kg). Sin inscritos.
- «Copa de Prueba (inscripciones abiertas)» (`registration_open`): fecha límite en 1 año y torneo después. 6 categorías
  con 23 inscritos, una con un solo inscrito, dos de Festival (niños sin CI) y un atleta sin inscribir.
- «Copa de Prueba (pesaje)» (`weigh_in`): 6 categorías con 19 inscritos, una con un solo inscrito y dos de Festival.
  Los primeros inscritos no Festival quedan uno en cada estado del pesaje (sin pesar, no entró en el primer pesaje,
  segundo pesaje habilitado, descalificado y habilitado en el segundo pesaje); el resto, habilitado. Festival no se pesa.
- «Copa de Prueba (en curso)» (`in_progress`): 7 categorías con 47 inscritos, todos pesados y habilitados, todas con
  llave generada y en distintos momentos: dos terminadas, cuatro a medias (con combates terminados y alguno con 1 o 2
  rounds cargados) y una sin empezar.
- «Copa de Prueba (finalizado)» (`finished`): 5 categorías, todos los inscritos pesados y habilitados, cuatro con la llave jugada hasta el final (de 3, 4, 5 y 8
  inscritos: dos con pases directos) y una con un solo inscrito, sin llave.
El resto de las categorías de cada torneo (la estructura de la Copa Diamante) queda vacía.

Uso, desde la raíz del repo:
    .venv/bin/python scripts/seed_demo_api.py {local,dev,prod}
local es tu servidor en el puerto 8000. El usuario y la clave del admin salen de `.env` (ver `.env.example`).
Si alguno de los torneos ya existe, no hace nada. Nunca borra datos: para empezar de cero, `scripts/reset_data.py`.
"""
import json
import random
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from dotenv import dotenv_values

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
API_URLS = {
    "local": "http://localhost:8000",
    "dev": "https://taekwondo-tournament-manager-dev.onrender.com",
    "prod": "https://taekwondo-tournament-manager.onrender.com",
}
TIMEOUT_SECONDS = 90  # el primer request del plan gratis de Render puede tardar 30-50 s

CLUB_NAMES = ["Dojang Prueba Norte", "Dojang Prueba Sur", "Dojang Prueba Este"]
MALE_NAMES = ["Mateo", "Santiago", "Diego", "Luis", "Carlos", "Andrés", "Bruno", "Marcelo", "Sebastián", "Joaquín", "Rodrigo", "Gabriel"]
FEMALE_NAMES = ["Valentina", "Camila", "Sofía", "Lucía", "Daniela", "Fernanda", "Paola", "Andrea", "Mariana", "Isabella", "Carla", "Gabriela"]
SURNAMES = ["Quispe", "Mamani", "Flores", "Condori", "Rojas", "Vargas", "Gutiérrez", "Choque", "Pérez", "Fernández", "Torrico", "Salazar", "Arce", "Cabrera", "Villarroel", "Rivera"]
BEGINNERS = [f"kup_{n}" for n in range(10, 5, -1)]
ADVANCED = ["kup_1", "dan"]

# Qué se juega en cada llave, en orden:
#   ("all",)                        todos los combates hasta terminar la llave
#   ("rounds", n)                   todos los combates de las rondas 1 a n
#   ("some", ronda, k)              k combates listos de esa ronda, terminados
#   ("half", ronda, k, rounds)      k combates listos de esa ronda con `rounds` rounds cargados y sin terminar
# (género, división de edad y de peso que le toca (solo para mostrar), grados, edades (la edad es el año del torneo menos
#  el de nacimiento), rango de pesos, atletas, inscritos, qué se juega)
# La categoría no se crea: es la de la estructura del torneo en la que encajan esos atletas, así que sus grados, edades y
# pesos tienen que caer todos en la misma (ver COPA_DIAMANTE_* en app/services/category_structure.py). Festival (hasta
# 9 años) no tiene grupo de grado ni pesos; sus atletas van sin CI.
# Una llave se sortea con 2 o más inscritos; con uno solo la categoría queda sin llave.
IN_PROGRESS_SPECS = [
    ("male", "Cadete 41.1–45 kg", BEGINNERS, (12, 14), (41.1, 45), 7, 7, [("all",)]),
    ("male", "Cadete 49.1–53 kg", BEGINNERS, (12, 14), (49.1, 53), 6, 6, [("all",)]),
    ("female", "Cadete 37.1–41 kg", BEGINNERS, (12, 14), (37.1, 41), 5, 5, [("rounds", 1), ("half", 2, 1, 1)]),
    ("male", "Junior 55.1–63 kg", BEGINNERS, (15, 17), (55.1, 63), 10, 10, [("rounds", 1), ("some", 2, 2), ("half", 2, 1, 2)]),
    ("female", "Junior 49.1–55 kg", BEGINNERS, (15, 17), (49.1, 55), 6, 6, [("some", 1, 1), ("half", 1, 1, 1)]),
    ("male", "Mayores 58.1–68 kg", ADVANCED, (18, 29), (58.1, 68), 8, 8, [("rounds", 1), ("some", 2, 1), ("half", 2, 1, 1)]),
    ("female", "Mayores 49.1–57 kg", ADVANCED, (18, 29), (49.1, 57), 8, 5, []),
]
FINISHED_SPECS = [
    ("male", "Cadete 41.1–45 kg", BEGINNERS, (12, 14), (41.1, 45), 3, 3, [("all",)]),
    ("female", "Cadete 37.1–41 kg", BEGINNERS, (12, 14), (37.1, 41), 4, 4, [("all",)]),
    ("female", "Junior 49.1–55 kg", BEGINNERS, (15, 17), (49.1, 55), 5, 5, [("all",)]),
    ("male", "Mayores 58.1–68 kg", ADVANCED, (18, 29), (58.1, 68), 8, 8, [("all",)]),
    ("female", "Mayores 49.1–57 kg", ADVANCED, (18, 29), (49.1, 57), 1, 1, []),
]
WEIGH_IN_SPECS = [
    ("male", "Cadete 49.1–53 kg", BEGINNERS, (12, 14), (49.1, 53), 5, 5, []),
    ("female", "Cadete 37.1–41 kg", BEGINNERS, (12, 14), (37.1, 41), 1, 1, []),
    ("female", "Junior 49.1–55 kg", BEGINNERS, (15, 17), (49.1, 55), 4, 4, []),
    ("male", "Mayores 58.1–68 kg", ADVANCED, (18, 29), (58.1, 68), 3, 3, []),
    ("male", "Festival", BEGINNERS, (5, 9), (20, 35), 4, 4, []),
    ("female", "Festival", BEGINNERS, (5, 9), (20, 35), 2, 2, []),
]
REGISTRATION_OPEN_SPECS = [
    ("male", "Cadete 41.1–45 kg", BEGINNERS, (12, 14), (41.1, 45), 6, 6, []),
    ("female", "Cadete 37.1–41 kg", BEGINNERS, (12, 14), (37.1, 41), 4, 4, []),
    ("male", "Junior 55.1–63 kg", BEGINNERS, (15, 17), (55.1, 63), 6, 5, []),
    ("female", "Mayores 49.1–57 kg", ADVANCED, (18, 29), (49.1, 57), 1, 1, []),
    ("male", "Festival", BEGINNERS, (5, 9), (20, 35), 4, 4, []),
    ("female", "Festival", BEGINNERS, (5, 9), (20, 35), 3, 3, []),
]

# Cómo queda el pesaje de los primeros inscritos no Festival del torneo en pesaje, en orden; el resto queda `cleared`.
# `second_cleared`: no entró en el primer pesaje, se le habilitó el segundo y entró.
WEIGH_IN_CASES = ["pending", "failed_first", "second_allowed", "disqualified", "second_cleared"]
OVERWEIGHT_KG = 0.6  # cuánto se pasa del máximo de su categoría quien no entra

STAGES = ["draft", "registration_open", "weigh_in", "in_progress", "finished"]
# `days_to_date`: cuántos días desde hoy es el torneo (negativo: ya se jugó). `deadline_days`: la fecha límite de
# inscripción, en días desde hoy; desde el Pesaje se la adelanta a ahora con close-registration.
TOURNAMENTS = [
    {
        "name": "Copa de Prueba (en preparación)", "location": "La Paz, Bolivia", "stage": "draft",
        "days_to_date": 120, "deadline_days": 90, "seed": 1, "specs": [],
        "summary": "estructura retocada, fecha límite fijada, sin inscritos",
    },
    {
        "name": "Copa de Prueba (inscripciones abiertas)", "location": "Santa Cruz, Bolivia", "stage": "registration_open",
        "days_to_date": 386, "deadline_days": 365, "seed": 2, "specs": REGISTRATION_OPEN_SPECS,
        "summary": "6 categorías, 23 inscritos (una con 1, dos de Festival sin CI) y 1 atleta sin inscribir",
    },
    {
        "name": "Copa de Prueba (pesaje)", "location": "Sucre, Bolivia", "stage": "weigh_in",
        "days_to_date": 14, "deadline_days": 7, "seed": 3, "specs": WEIGH_IN_SPECS,
        "summary": "6 categorías, 19 inscritos (una con 1, dos de Festival sin CI), lista pública; pesaje: 1 sin pesar, "
        "1 no entró, 1 con segundo pesaje habilitado, 1 descalificado, 1 habilitado en el segundo y el resto habilitado",
    },
    {
        "name": "Copa de Prueba (en curso)", "location": "Cochabamba, Bolivia", "stage": "in_progress",
        "days_to_date": -11, "deadline_days": 7, "seed": 2026, "specs": IN_PROGRESS_SPECS,
        "summary": "7 categorías, 47 inscritos, todos pesados: 2 llaves terminadas, 4 a medias y 1 sin empezar",
    },
    {
        "name": "Copa de Prueba (finalizado)", "location": "Tarija, Bolivia", "stage": "finished",
        "days_to_date": -60, "deadline_days": 7, "seed": 4, "specs": FINISHED_SPECS,
        "summary": "5 categorías, 21 inscritos, todos pesados: 4 llaves terminadas (3, 4, 5 y 8 inscritos) y 1 categoría con 1 inscrito",
    },
]


def build_category(spec, rng: random.Random, used_cis: set[str], tournament_year: int) -> dict:
    """Devuelve el nombre de la categoría, sus atletas (con `club` por nombre y `register`) y qué se juega."""
    gender, label, grades, ages, weights, count, registered, plan = spec
    first_names = MALE_NAMES if gender == "male" else FEMALE_NAMES
    birth_years = (tournament_year - ages[1], tournament_year - ages[0])
    athletes = []
    for i in range(count):
        ci = None
        if not (label == "Festival" or (label.startswith("Cadete") and rng.random() < 0.3)):
            while ci is None or ci in used_cis:
                ci = str(rng.randint(4_000_000, 9_000_000))
                if rng.random() < 0.1:
                    ci += "-1A"
            used_cis.add(ci)
        athletes.append(
            {
                "name": f"{rng.choice(first_names)} {rng.choice(SURNAMES)} {rng.choice(SURNAMES)}",
                "ci": ci,
                "birth_date": date(rng.randint(*birth_years), rng.randint(1, 12), rng.randint(1, 28)).isoformat(),
                "gender": gender,
                "grade": rng.choice(grades),
                "weight_kg": round(rng.uniform(*weights), 1),
                "club": rng.choice(CLUB_NAMES),
                "register": i < registered,
            }
        )
    return {
        "label": f"{label} ({gender})",
        "athletes": athletes,
        "plan": plan,
    }


def call(base_url: str, method: str, path: str, token: str | None = None, body=None, form=None):
    headers = {}
    data = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
    request = urllib.request.Request(base_url + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors="replace")
        sys.exit(f"\nError {error.code} en {method} {path}: {detail}")
    except urllib.error.URLError as error:
        sys.exit(f"\nNo se pudo conectar con {base_url}: {error.reason}")


def load_category(api, tournament_id: int, club_ids: dict, entry: dict) -> int:
    print(f"  {entry['label']}: ", end="", flush=True)
    category_id = None
    for data in entry["athletes"]:
        payload = {k: v for k, v in data.items() if k not in ("club", "register")}
        athlete = api("POST", "/api/v1/athletes", {**payload, "club_id": club_ids[data["club"]]})
        if category_id is None:
            [category] = api("GET", f"/api/v1/athletes/{athlete['id']}/eligible-categories?tournament_id={tournament_id}")
            category_id = category["id"]
        if data["register"]:
            api("POST", "/api/v1/registrations", {"athlete_id": athlete["id"], "category_id": category_id})
        print(".", end="", flush=True)
    print()
    return category_id


def weigh_in_registrations(api, tournament_id: int, cases: list[str] = ()) -> None:
    """Pesa a los inscritos no Festival con su peso declarado; a los primeros, según `cases` (ver WEIGH_IN_CASES)."""
    registrations = api("GET", f"/api/v1/registrations?tournament_id={tournament_id}")
    weighed = [r for r in registrations if r["weigh_in_status"] != "not_required"]
    for registration, case in zip(weighed, [*cases, *["cleared"] * len(weighed)]):
        path = f"/api/v1/registrations/{registration['id']}"
        declared = {"weight_kg": registration["athlete"]["weight_kg"]}
        if case == "pending":
            continue
        if case == "cleared":
            api("POST", f"{path}/weigh-in", declared)
            continue
        api("POST", f"{path}/weigh-in", {"weight_kg": round(registration["category"]["max_weight"] + OVERWEIGHT_KG, 1)})
        if case == "disqualified":
            api("POST", f"{path}/disqualify")
        elif case in ("second_allowed", "second_cleared"):
            api("POST", f"{path}/second-weigh-in")
            if case == "second_cleared":
                api("POST", f"{path}/weigh-in", declared)


def ready_matches(api, category_id: int, round_number: int) -> list[dict]:
    matches = api("GET", f"/api/v1/categories/{category_id}/bracket")["matches"]
    return sorted(
        (
            m
            for m in matches
            if m["round_number"] == round_number
            and m["status"] == "pending"
            and m["athlete_red_id"]
            and m["athlete_blue_id"]
            and not m["round_scores"]
        ),
        key=lambda m: m["slot"],
    )


def total_rounds(api, category_id: int) -> int:
    return max(m["round_number"] for m in api("GET", f"/api/v1/categories/{category_id}/bracket")["matches"])


def record_rounds(api, rng: random.Random, match: dict, red_wins_round: list[bool]) -> None:
    for round_number, red_wins in enumerate(red_wins_round, start=1):
        winner_points = rng.randint(6, 14)
        loser_points = rng.randint(0, winner_points - 1)
        red, blue = (winner_points, loser_points) if red_wins else (loser_points, winner_points)
        api(
            "POST",
            f"/api/v1/matches/{match['id']}/rounds",
            {"round_number": round_number, "red_points": red, "blue_points": blue},
        )


def finish_match(api, rng: random.Random, match: dict) -> None:
    winner_is_red = rng.random() < 0.5
    sequence = rng.choice([[True, True], [True, False, True], [False, True, True]])
    record_rounds(api, rng, match, [winner_is_red == won for won in sequence])


def leave_half_played(api, rng: random.Random, match: dict, rounds: int) -> None:
    record_rounds(api, rng, match, [True, False][:rounds])


def play(api, rng: random.Random, category_id: int, plan: list[tuple]) -> None:
    for step in plan:
        if step[0] == "all":
            for round_number in range(1, total_rounds(api, category_id) + 1):
                for match in ready_matches(api, category_id, round_number):
                    finish_match(api, rng, match)
        elif step[0] == "rounds":
            for round_number in range(1, step[1] + 1):
                for match in ready_matches(api, category_id, round_number):
                    finish_match(api, rng, match)
        elif step[0] == "some":
            for match in ready_matches(api, category_id, step[1])[: step[2]]:
                finish_match(api, rng, match)
        elif step[0] == "half":
            for match in ready_matches(api, category_id, step[1])[: step[2]]:
                leave_half_played(api, rng, match, step[3])


def retouch_structure(api, tournament_id: int) -> None:
    """Renombra el primer grupo de grado y agrega a Junior masculino la división 63.1–68 kg."""
    path = f"/api/v1/tournaments/{tournament_id}/category-structure"
    structure = api("GET", path)
    groups = [{k: g[k] for k in ("id", "name", "from_grade")} for g in structure["grade_groups"]]
    groups[0]["name"] = "Iniciación"
    divisions = [{k: d[k] for k in ("id", "name", "from_age", "weight_limits")} for d in structure["age_divisions"][1:]]
    junior = next(d for d in divisions if d["name"] == "Junior")
    junior["weight_limits"]["male"] = [48, 55, 63, 68, 73]
    result = api("PUT", path, {"grade_groups": groups, "age_divisions": divisions})
    print(f"  Estructura retocada: {len(result['categories'])} categorías.")


def env_setting(env: str, name: str) -> str:
    """Valor de `.env` para el ambiente: `DEV_ADMIN_PASSWORD`, `PROD_DATABASE_URL`… (local usa los nombres de la app,
    sin prefijo)."""
    key = name if env == "local" else f"{env.upper()}_{name}"
    value = dotenv_values(ENV_FILE).get(key)
    if not value:
        sys.exit(f"Falta {key} en {ENV_FILE} (ver .env.example).")
    return value


def seed(env: str) -> None:
    base_url = API_URLS[env]
    print(f"\nServicio: {base_url}")
    username = env_setting(env, "ADMIN_USERNAME")
    password = env_setting(env, "ADMIN_PASSWORD")

    print("Iniciando sesión (si el servicio estaba dormido, tarda hasta 1 minuto)...")
    token = call(base_url, "POST", "/api/v1/auth/login", form={"username": username, "password": password})["access_token"]

    def api(method: str, path: str, body=None):
        return call(base_url, method, path, token=token, body=body)

    existing = {t["name"] for t in api("GET", "/api/v1/tournaments")}
    for tournament in TOURNAMENTS:
        if tournament["name"] in existing:
            sys.exit(f"Ya existe «{tournament['name']}»: no se hizo nada.")

    club_ids = {c["name"]: c["id"] for c in api("GET", "/api/v1/clubs")}
    for name in CLUB_NAMES:
        if name not in club_ids:
            club_ids[name] = api("POST", "/api/v1/clubs", {"name": name})["id"]

    used_cis = {a["ci"] for a in api("GET", "/api/v1/athletes") if a["ci"]}
    now = datetime.now(timezone.utc)
    for tournament in TOURNAMENTS:
        stage = STAGES.index(tournament["stage"])
        tournament_date = now.date() + timedelta(days=tournament["days_to_date"])
        deadline = now + timedelta(days=tournament["deadline_days"])
        # La fecha límite cae antes del día del torneo: uno ya jugado se crea con una fecha provisoria posterior y
        # recibe la real en el Pesaje, cuando la fecha límite ya no cuenta. Las edades salen del año provisorio, que es
        # el que valida la inscripción: si la fecha real cae en otro año, quedan corridas un año (solo es la demo).
        provisional_date = max(tournament_date, deadline.date() + timedelta(days=1))
        print(f"\n«{tournament['name']}»")
        tournament_id = api(
            "POST",
            "/api/v1/tournaments",
            {"name": tournament["name"], "date": provisional_date.isoformat(), "location": tournament["location"]},
        )["id"]
        api("PATCH", f"/api/v1/tournaments/{tournament_id}", {"registration_deadline": deadline.isoformat()})
        if tournament["stage"] == "draft":
            retouch_structure(api, tournament_id)
            continue

        api("POST", f"/api/v1/tournaments/{tournament_id}/open-registration")
        data_rng = random.Random(tournament["seed"])
        entries = [build_category(spec, data_rng, used_cis, provisional_date.year) for spec in tournament["specs"]]
        category_ids = [load_category(api, tournament_id, club_ids, entry) for entry in entries]
        if stage == STAGES.index("registration_open"):
            continue

        api("POST", f"/api/v1/tournaments/{tournament_id}/close-registration")
        if provisional_date != tournament_date:
            api("PATCH", f"/api/v1/tournaments/{tournament_id}", {"date": tournament_date.isoformat()})
        if stage == STAGES.index("weigh_in"):
            weigh_in_registrations(api, tournament_id, WEIGH_IN_CASES)
            continue

        print("  Pesando a los inscritos, pasando el torneo a «en curso», sorteando las llaves y cargando resultados...")
        weigh_in_registrations(api, tournament_id)
        api("POST", f"/api/v1/tournaments/{tournament_id}/start")
        match_rng = random.Random(7)
        for category_id, entry in zip(category_ids, entries):
            if sum(a["register"] for a in entry["athletes"]) >= 2:
                api("POST", f"/api/v1/categories/{category_id}/bracket")
                play(api, match_rng, category_id, entry["plan"])
        if stage == STAGES.index("finished"):
            api("POST", f"/api/v1/tournaments/{tournament_id}/finish")

    print("\nListo:")
    for tournament in TOURNAMENTS:
        print(f"  {tournament['name']}: {tournament['summary']}.")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in API_URLS:
        sys.exit(f"Uso: {sys.argv[0]} {{{','.join(API_URLS)}}}")
    if sys.argv[1] == "prod" and input("Vas a cargar datos de prueba en PRODUCCIÓN. Escribí prod para continuar: ") != "prod":
        sys.exit("Cancelado.")
    seed(sys.argv[1])
