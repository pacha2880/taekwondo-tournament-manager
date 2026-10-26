"""Carga datos de prueba por la API (pide usuario y contraseña):

- «Copa de Prueba (en curso)»: 7 categorías con 47 inscritos, todas con llave generada y en distintos
  momentos: dos terminadas, cuatro a medias (con combates terminados y alguno con 1 o 2 rounds cargados)
  y una sin empezar.
- «Copa de Prueba (borrador)»: una categoría con 5 inscritos y sin llave.

Uso, desde la raíz del repo (no necesita instalar nada):
    python3 scripts/seed_demo_api.py
Pregunta dónde cargar: local (tu servidor en el puerto 8000), dev o producción.
Es idempotente: si los torneos ya existen, no hace nada. Nunca borra datos.
"""
import getpass
import json
import random
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date

ENVIRONMENTS = {
    "1": ("Local", "http://localhost:8000"),
    "2": ("Dev", "https://taekwondo-tournament-manager-dev.onrender.com"),
    "3": ("Producción", "https://taekwondo-tournament-manager.onrender.com"),
}
PRODUCTION_CHOICE = "3"
TIMEOUT_SECONDS = 90  # el primer request del plan gratis de Render puede tardar 30-50 s

IN_PROGRESS_TOURNAMENT = {"name": "Copa de Prueba (en curso)", "date": "2026-11-15", "location": "Cochabamba, Bolivia"}
DRAFT_TOURNAMENT = {"name": "Copa de Prueba (borrador)", "date": "2027-01-30", "location": "La Paz, Bolivia"}
CLUB_NAMES = ["Dojang Prueba Norte", "Dojang Prueba Sur", "Dojang Prueba Este"]

MALE_NAMES = ["Mateo", "Santiago", "Diego", "Luis", "Carlos", "Andrés", "Bruno", "Marcelo", "Sebastián", "Joaquín", "Rodrigo", "Gabriel"]
FEMALE_NAMES = ["Valentina", "Camila", "Sofía", "Lucía", "Daniela", "Fernanda", "Paola", "Andrea", "Mariana", "Isabella", "Carla", "Gabriela"]
SURNAMES = ["Quispe", "Mamani", "Flores", "Condori", "Rojas", "Vargas", "Gutiérrez", "Choque", "Pérez", "Fernández", "Torrico", "Salazar", "Arce", "Cabrera", "Villarroel", "Rivera"]
BELTS = {
    "color": ["blanco", "amarillo", "verde", "azul", "rojo"],
    "black": ["negro 1er dan", "negro 2do dan", "negro 3er dan"],
}

# Qué se juega en cada llave, en orden:
#   ("all",)                        todos los combates hasta terminar la llave
#   ("rounds", n)                   todos los combates de las rondas 1 a n
#   ("some", ronda, k)              k combates listos de esa ronda, terminados
#   ("half", ronda, k, rounds)      k combates listos de esa ronda con `rounds` rounds cargados y sin terminar
# (género, grupo de edad, edad mín., edad máx., cinturón, etiqueta de peso, peso mín., peso máx.,
#  años de nacimiento, rango de pesos de los atletas, atletas, inscritos, qué se juega)
CATEGORY_SPECS = [
    ("male", "Cadete", 12, 14, "color", "Hasta 45 kg", None, 45, (2012, 2014), (30, 45), 7, 7, [("all",)]),
    ("male", "Cadete", 12, 14, "color", "45 a 55 kg", 45, 55, (2012, 2014), (45.5, 55), 6, 6, [("all",)]),
    ("female", "Cadete", 12, 14, "color", "Hasta 45 kg", None, 45, (2012, 2014), (30, 45), 5, 5, [("rounds", 1), ("half", 2, 1, 1)]),
    ("male", "Juvenil", 15, 17, "color", "Hasta 60 kg", None, 60, (2009, 2011), (45, 60), 10, 10, [("rounds", 1), ("some", 2, 2), ("half", 2, 1, 2)]),
    ("female", "Juvenil", 15, 17, "color", "Hasta 55 kg", None, 55, (2009, 2011), (40, 55), 6, 6, [("some", 1, 1), ("half", 1, 1, 1)]),
    ("male", "Adulto", 18, 35, "black", "Hasta 68 kg", None, 68, (1992, 2008), (55, 68), 8, 8, [("rounds", 1), ("some", 2, 1), ("half", 2, 1, 1)]),
    ("female", "Adulto", 18, 35, "black", "Hasta 57 kg", None, 57, (1992, 2008), (45, 57), 8, 5, []),
]
DRAFT_CATEGORY_SPEC = ("female", "Juvenil", 15, 17, "color", "Hasta 55 kg", None, 55, (2009, 2011), (40, 55), 5, 5, [])


def build_category(spec, rng: random.Random, used_cis: set[str]) -> dict:
    """Devuelve el payload de la categoría, sus atletas (con `club` por nombre y `register`) y qué se juega."""
    gender, age_label, min_age, max_age, belt_group, weight_label, min_weight, max_weight, years, weights, count, registered, plan = spec
    first_names = MALE_NAMES if gender == "male" else FEMALE_NAMES
    athletes = []
    for i in range(count):
        ci = None
        if not (age_label == "Cadete" and rng.random() < 0.3):
            while ci is None or ci in used_cis:
                ci = str(rng.randint(4_000_000, 9_000_000))
                if rng.random() < 0.1:
                    ci += "-1A"
            used_cis.add(ci)
        athletes.append(
            {
                "name": f"{rng.choice(first_names)} {rng.choice(SURNAMES)} {rng.choice(SURNAMES)}",
                "ci": ci,
                "birth_date": date(rng.randint(*years), rng.randint(1, 12), rng.randint(1, 28)).isoformat(),
                "gender": gender,
                "belt_rank": rng.choice(BELTS[belt_group]),
                "weight_kg": round(rng.uniform(*weights), 1),
                "club": rng.choice(CLUB_NAMES),
                "register": i < registered,
            }
        )
    return {
        "category": {
            "gender": gender,
            "age_label": age_label,
            "min_age": min_age,
            "max_age": max_age,
            "belt_group": belt_group,
            "weight_label": weight_label,
            "min_weight": min_weight,
            "max_weight": max_weight,
        },
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
    category = api("POST", "/api/v1/categories", {**entry["category"], "tournament_id": tournament_id})
    print(f"  {category['age_label']} {category['weight_label']} ({category['gender']}): ", end="", flush=True)
    for data in entry["athletes"]:
        payload = {k: v for k, v in data.items() if k not in ("club", "register")}
        athlete = api("POST", "/api/v1/athletes", {**payload, "club_id": club_ids[data["club"]]})
        if data["register"]:
            api("POST", "/api/v1/registrations", {"athlete_id": athlete["id"], "category_id": category["id"]})
        print(".", end="", flush=True)
    print()
    return category["id"]


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
    for number, red_wins in enumerate(red_wins_round, start=1):
        winner_points = rng.randint(6, 14)
        loser_points = rng.randint(0, winner_points - 1)
        red, blue = (winner_points, loser_points) if red_wins else (loser_points, winner_points)
        api("POST", f"/api/v1/matches/{match['id']}/rounds", {"round_number": number, "red_points": red, "blue_points": blue})


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


def choose_environment() -> str:
    print("¿Dónde querés cargar los datos?")
    for key, (name, url) in ENVIRONMENTS.items():
        print(f"  {key}) {name:<11} {url}")
    choice = input("Opción: ").strip()
    if choice not in ENVIRONMENTS:
        sys.exit("Opción inválida.")
    if choice == PRODUCTION_CHOICE and input("Vas a cargar datos de prueba en PRODUCCIÓN. Escribí PRODUCCION para continuar: ") != "PRODUCCION":
        sys.exit("Cancelado.")
    return ENVIRONMENTS[choice][1]


def main() -> None:
    base_url = choose_environment()
    print(f"\nServicio: {base_url}")
    username = input("Usuario: ")
    password = getpass.getpass("Contraseña: ")

    print("Iniciando sesión (si el servicio estaba dormido, tarda hasta 1 minuto)...")
    token = call(base_url, "POST", "/api/v1/auth/login", form={"username": username, "password": password})["access_token"]

    def api(method: str, path: str, body=None):
        return call(base_url, method, path, token=token, body=body)

    existing = {t["name"] for t in api("GET", "/api/v1/tournaments")}
    for tournament in (IN_PROGRESS_TOURNAMENT, DRAFT_TOURNAMENT):
        if tournament["name"] in existing:
            sys.exit(f"Ya existe «{tournament['name']}»: no se hizo nada.")

    club_ids = {c["name"]: c["id"] for c in api("GET", "/api/v1/clubs")}
    for name in CLUB_NAMES:
        if name not in club_ids:
            club_ids[name] = api("POST", "/api/v1/clubs", {"name": name})["id"]

    used_cis = {a["ci"] for a in api("GET", "/api/v1/athletes") if a["ci"]}
    data_rng = random.Random(2026)
    in_progress_entries = [build_category(spec, data_rng, used_cis) for spec in CATEGORY_SPECS]
    draft_entry = build_category(DRAFT_CATEGORY_SPEC, data_rng, used_cis)

    print(f"\n«{IN_PROGRESS_TOURNAMENT['name']}»")
    tournament_id = api("POST", "/api/v1/tournaments", IN_PROGRESS_TOURNAMENT)["id"]
    category_ids = [load_category(api, tournament_id, club_ids, entry) for entry in in_progress_entries]

    print("  Pasando el torneo a «en curso», sorteando las llaves y cargando resultados...")
    api("PATCH", f"/api/v1/tournaments/{tournament_id}", {"status": "in_progress"})
    match_rng = random.Random(7)
    for category_id, entry in zip(category_ids, in_progress_entries):
        api("POST", f"/api/v1/categories/{category_id}/bracket")
        play(api, match_rng, category_id, entry["plan"])

    print(f"\n«{DRAFT_TOURNAMENT['name']}»")
    draft_id = api("POST", "/api/v1/tournaments", DRAFT_TOURNAMENT)["id"]
    load_category(api, draft_id, club_ids, draft_entry)

    print("\nListo. Torneo en curso: 2 llaves terminadas, 4 a medias y 1 sin empezar. Torneo en borrador: 1 categoría, 5 inscritos.")


if __name__ == "__main__":
    main()
