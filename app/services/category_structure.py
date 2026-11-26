"""Estructura de categorías de un torneo y las categorías que se derivan de ella.

Ver docs/DECISIONS.md, 2026-11-16: grupos de grado y divisiones de edad son cortes (cada uno empieza donde termina
el anterior), los pesos son límites superiores por edad y género, y cada categoría es grupo × género × edad ×
división de peso. Las categorías no se crean a mano: `sync_categories` las crea, conserva o borra.
"""

from collections import Counter

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.schemas import CategoryStructureUpdate
from app.models import AgeDivision, Category, Gender, Grade, GradeGroup, Tournament, WeightLimit

GRADES = list(Grade)

# Copa Diamante 2026 (convocatoria real del club, ver la plantilla en Notion). Es la estructura con la que nace todo
# torneo nuevo hasta que existan plantillas editables.
COPA_DIAMANTE_GRADE_GROUPS = [
    ("Principiantes", Grade.KUP_10),
    ("Novatos", Grade.KUP_5),
    ("Avanzados", Grade.KUP_1),
]
# Festival (los más chicos) está siempre y es fijo: primera división de edad, hasta FESTIVAL_MAX_AGE años contados por
# año de nacimiento, sin pesos ni grupos de grado; una lista general por género.
FESTIVAL_NAME = "Festival"
FESTIVAL_MAX_AGE = 9
COPA_DIAMANTE_AGE_DIVISIONS = [
    # nombre, desde qué edad, límites de peso masculinos, femeninos (None: sin divisiones de peso)
    (FESTIVAL_NAME, 0, None, None),
    ("Infantil", FESTIVAL_MAX_AGE + 1, [26, 29, 32, 35, 38, 41, 44, 47, 50, 53, 56], [26, 29, 32, 35, 38, 41, 44, 47, 50, 53, 56]),
    ("Cadete", 12, [33, 37, 41, 45, 49, 53, 57, 61, 65], [29, 33, 37, 41, 44, 47, 51, 55, 59]),
    ("Junior", 15, [48, 55, 63, 73], [44, 49, 55, 63]),
    ("Mayores", 18, [58, 68, 80], [49, 57, 67]),
    ("Senior", 30, [58, 68, 80], [49, 57, 67]),
]


def add_default_structure(tournament: Tournament) -> None:
    tournament.grade_groups = [
        GradeGroup(position=i, name=name, from_grade=from_grade)
        for i, (name, from_grade) in enumerate(COPA_DIAMANTE_GRADE_GROUPS)
    ]
    tournament.age_divisions = []
    for i, (name, from_age, male_limits, female_limits) in enumerate(COPA_DIAMANTE_AGE_DIVISIONS):
        division = AgeDivision(position=i, name=name, from_age=from_age)
        for gender, limits in ((Gender.MALE, male_limits), (Gender.FEMALE, female_limits)):
            division.weight_limits += [
                WeightLimit(gender=gender, position=j, upper_limit=limit) for j, limit in enumerate(limits or [])
            ]
        tournament.age_divisions.append(division)


def is_festival(division: AgeDivision) -> bool:
    return division.position == 0


def grade_range(groups: list[GradeGroup], index: int) -> tuple[Grade, Grade]:
    """Primer y último grado del grupo en `index` (los grupos van ordenados por `position`)."""
    if index + 1 < len(groups):
        last = GRADES[GRADES.index(groups[index + 1].from_grade) - 1]
    else:
        last = GRADES[-1]
    return groups[index].from_grade, last


def age_range(divisions: list[AgeDivision], index: int) -> tuple[int, int | None]:
    """Edad mínima y máxima de la división en `index`; la última no tiene tope (None)."""
    if index + 1 < len(divisions):
        return divisions[index].from_age, divisions[index + 1].from_age - 1
    return divisions[index].from_age, None


def weight_limits(division: AgeDivision, gender: Gender) -> list[float]:
    return [limit.upper_limit for limit in division.weight_limits if limit.gender == gender]


def weight_range(limits: list[float], position: int) -> tuple[float | None, float | None]:
    """Peso mínimo y máximo (ambos incluidos, en décimas como el reglamento WT) de la división en `position`."""
    lower = round(limits[position - 1] + 0.1, 1) if position > 0 else None
    upper = limits[position] if position < len(limits) else None
    return lower, upper


def weight_label(limits: list[float], position: int) -> str:
    lower, upper = weight_range(limits, position)
    if not limits:
        return "Todos los pesos"
    if lower is None:
        return f"Hasta {upper:g} kg"
    if upper is None:
        return f"Más de {limits[-1]:g} kg"
    return f"{lower:g}–{upper:g} kg"


def describe_structure(tournament: Tournament) -> dict:
    """La estructura en la forma de `CategoryStructureRead`, con los rangos ya calculados."""
    groups = tournament.grade_groups
    divisions = tournament.age_divisions
    return {
        "grade_groups": [
            {"id": group.id, "name": group.name, "from_grade": grade_range(groups, i)[0], "to_grade": grade_range(groups, i)[1]}
            for i, group in enumerate(groups)
        ],
        "age_divisions": [
            {
                "id": division.id,
                "name": division.name,
                "from_age": age_range(divisions, i)[0],
                "to_age": age_range(divisions, i)[1],
                "has_weight_divisions": not is_festival(division),
                "weight_limits": {gender.value: weight_limits(division, gender) for gender in Gender},
            }
            for i, division in enumerate(divisions)
        ],
    }


def _desired_categories(tournament: Tournament) -> dict[tuple, dict]:
    """Categorías que corresponden a la estructura, por clave (grupo, género, edad, posición de peso)."""
    desired = {}
    groups = tournament.grade_groups
    divisions = tournament.age_divisions
    for d, division in enumerate(divisions):
        min_age, max_age = age_range(divisions, d)
        # Festival es una lista general por género: sin grupos de grado ni pesos.
        division_groups = [None] if is_festival(division) else groups
        for group in division_groups:
            for gender in Gender:
                limits = weight_limits(division, gender)
                for position in range(len(limits) + 1):
                    min_weight, max_weight = weight_range(limits, position)
                    desired[(group.id if group else None, gender, division.id, position)] = {
                        "age_label": division.name,
                        "min_age": min_age,
                        "max_age": max_age,
                        "weight_label": weight_label(limits, position),
                        "min_weight": min_weight,
                        "max_weight": max_weight,
                    }
    return desired


def _reject(detail: str):
    raise HTTPException(status_code=422, detail=detail)


def _check_names(names: list[str], what: str) -> None:
    if any(not name.strip() for name in names):
        _reject(f"Hay {what} sin nombre")
    repeated = {name for name, count in Counter(n.strip() for n in names).items() if count > 1}
    if repeated:
        _reject(f"Hay {what} con el mismo nombre: {', '.join(sorted(repeated))}")


def _check_ids(ids: list[int | None], allowed: set[int], what: str) -> None:
    given = [i for i in ids if i is not None]
    if len(given) != len(set(given)):
        _reject(f"Hay {what} repetidos")
    foreign = set(given) - allowed
    if foreign:
        _reject(f"Estos ids de {what} no son de este torneo: {', '.join(map(str, sorted(foreign)))}")


def validate_structure(tournament: Tournament, payload: CategoryStructureUpdate) -> None:
    groups = payload.grade_groups
    if not groups:
        _reject("Tiene que haber al menos un grupo de grado")
    _check_names([g.name for g in groups], "grupos de grado")
    _check_ids([g.id for g in groups], {g.id for g in tournament.grade_groups}, "grupos de grado")
    if groups[0].from_grade != Grade.KUP_10:
        _reject("El primer grupo de grado tiene que empezar en 10mo Kup")
    for previous, group in zip(groups, groups[1:]):
        if GRADES.index(group.from_grade) <= GRADES.index(previous.from_grade):
            _reject(f"El grupo «{group.name}» tiene que empezar en un grado mayor que «{previous.name}»")
    last_group = tournament.grade_groups[-1]
    if groups[-1].id != last_group.id:
        _reject(f"El último grupo («{last_group.name}») no se puede quitar: tiene que seguir último, con su id")

    divisions = payload.age_divisions
    if not divisions:
        _reject("Tiene que haber al menos una división de edad después de Festival")
    _check_names([d.name for d in divisions], "divisiones de edad")
    if any(d.name.strip().casefold() == FESTIVAL_NAME.casefold() for d in divisions):
        _reject("Festival es fijo: no se envía en la estructura")
    _check_ids([d.id for d in divisions], {d.id for d in tournament.age_divisions[1:]}, "divisiones de edad")
    if divisions[0].from_age != FESTIVAL_MAX_AGE + 1:
        _reject(f"La primera división de edad tiene que empezar en {FESTIVAL_MAX_AGE + 1} (Festival llega hasta {FESTIVAL_MAX_AGE})")
    for previous, division in zip(divisions, divisions[1:]):
        if division.from_age <= previous.from_age:
            _reject(f"La división «{division.name}» tiene que empezar en una edad mayor que «{previous.name}»")
    for division in divisions:
        for gender, limits in (("masculinos", division.weight_limits.male), ("femeninos", division.weight_limits.female)):
            if any(limit <= 0 for limit in limits) or any(b <= a for a, b in zip(limits, limits[1:])):
                _reject(f"Los pesos {gender} de «{division.name}» tienen que ser positivos, de menor a mayor y sin repetir")


def apply_structure(db: Session, tournament: Tournament, payload: CategoryStructureUpdate) -> None:
    """Valida y aplica una estructura completa (sin Festival) y recalcula las categorías."""
    validate_structure(tournament, payload)
    kept_groups = {g.id for g in payload.grade_groups if g.id is not None}
    festival = tournament.age_divisions[0]
    kept_divisions = {festival.id} | {d.id for d in payload.age_divisions if d.id is not None}

    # Primero se van las categorías de los grupos y divisiones que se quitan, para que ninguna quede apuntando a una
    # fila borrada.
    for category in list(tournament.categories):
        if category.age_division_id not in kept_divisions or (
            category.grade_group_id is not None and category.grade_group_id not in kept_groups
        ):
            tournament.categories.remove(category)
    db.flush()

    existing_groups = {g.id: g for g in tournament.grade_groups}
    groups = []
    for position, data in enumerate(payload.grade_groups):
        group = existing_groups.get(data.id) or GradeGroup()
        group.position, group.name, group.from_grade = position, data.name.strip(), data.from_grade
        groups.append(group)
    tournament.grade_groups = groups

    existing_divisions = {d.id: d for d in tournament.age_divisions[1:]}
    divisions = [festival]
    for position, data in enumerate(payload.age_divisions, start=1):
        division = existing_divisions.get(data.id) or AgeDivision()
        division.position, division.name, division.from_age = position, data.name.strip(), data.from_age
        division.weight_limits = [
            WeightLimit(gender=gender, position=j, upper_limit=limit)
            for gender, limits in ((Gender.MALE, data.weight_limits.male), (Gender.FEMALE, data.weight_limits.female))
            for j, limit in enumerate(limits)
        ]
        divisions.append(division)
    tournament.age_divisions = divisions

    sync_categories(db, tournament)
    db.flush()


def preview_categories(tournament: Tournament) -> list[dict]:
    group_names = {g.id: g.name for g in tournament.grade_groups}
    return [
        {
            "grade_group_name": group_names.get(c.grade_group_id),
            "gender": c.gender,
            "age_label": c.age_label,
            "weight_label": c.weight_label,
        }
        for c in tournament.categories
    ]


def sync_categories(db: Session, tournament: Tournament) -> None:
    """Deja las categorías del torneo iguales a su estructura: conserva (con su id) las que siguen
    correspondiendo, crea las que faltan y borra las que sobran."""
    db.flush()  # para que grupos y divisiones nuevos tengan id
    desired = _desired_categories(tournament)
    for category in list(tournament.categories):
        key = (category.grade_group_id, category.gender, category.age_division_id, category.weight_position)
        values = desired.pop(key, None)
        if values is None:
            tournament.categories.remove(category)
        else:
            for field, value in values.items():
                setattr(category, field, value)
    for (group_id, gender, division_id, position), values in desired.items():
        tournament.categories.append(
            Category(
                grade_group_id=group_id,
                gender=gender,
                age_division_id=division_id,
                weight_position=position,
                **values,
            )
        )
