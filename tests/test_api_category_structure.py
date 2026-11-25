import copy
import json

import pytest

from app.models import Tournament
from app.services.category_structure import sync_categories


def _structure(client, tournament):
    return client.get(f"/api/v1/tournaments/{tournament['id']}/category-structure")


def _categories(client, tournament):
    return client.get("/api/v1/categories", params={"tournament_id": tournament["id"]}).json()


def test_a_new_tournament_starts_with_the_copa_diamante_grade_groups(client, tournament):
    groups = _structure(client, tournament).json()["grade_groups"]

    assert [(g["name"], g["from_grade"], g["to_grade"]) for g in groups] == [
        ("Principiantes", "kup_10", "kup_6"),
        ("Novatos", "kup_5", "kup_2"),
        ("Avanzados", "kup_1", "dan"),
    ]


def test_a_new_tournament_starts_with_the_copa_diamante_age_and_weight_divisions(client, tournament):
    divisions = _structure(client, tournament).json()["age_divisions"]

    assert [(d["name"], d["from_age"], d["to_age"]) for d in divisions] == [
        ("Festival", 0, 9),
        ("Infantil", 10, 11),
        ("Cadete", 12, 14),
        ("Junior", 15, 17),
        ("Mayores", 18, 29),
        ("Senior", 30, None),
    ]
    assert [d["has_weight_divisions"] for d in divisions] == [False, True, True, True, True, True]
    # Escritos a mano a propósito (plantilla de Notion): importar la constante no detectaría un error de tipeo.
    assert {d["name"]: d["weight_limits"] for d in divisions} == {
        "Festival": {"male": [], "female": []},
        "Infantil": {"male": [26, 29, 32, 35, 38, 41, 44, 47, 50, 53, 56], "female": [26, 29, 32, 35, 38, 41, 44, 47, 50, 53, 56]},
        "Cadete": {"male": [33, 37, 41, 45, 49, 53, 57, 61, 65], "female": [29, 33, 37, 41, 44, 47, 51, 55, 59]},
        "Junior": {"male": [48, 55, 63, 73], "female": [44, 49, 55, 63]},
        "Mayores": {"male": [58, 68, 80], "female": [49, 57, 67]},
        "Senior": {"male": [58, 68, 80], "female": [49, 57, 67]},
    }


def test_every_combination_of_the_structure_is_a_category(client, tournament):
    categories = _categories(client, tournament)

    # Festival: 1 por género. El resto: 3 grupos × 2 géneros × (Infantil 12 + Cadete 10 + Junior 5 + Mayores 4 + Senior 4)
    assert len(categories) == 2 + 210


def test_generated_categories_carry_their_age_and_weight_range(client, tournament):
    junior_male = [
        c for c in _categories(client, tournament)
        if c["age_label"] == "Junior" and c["gender"] == "male" and c["grade_group_name"] == "Principiantes"
    ]

    assert [(c["weight_label"], c["min_weight"], c["max_weight"]) for c in junior_male] == [
        ("Hasta 48 kg", None, 48),
        ("48.1–55 kg", 48.1, 55),
        ("55.1–63 kg", 55.1, 63),
        ("63.1–73 kg", 63.1, 73),
        ("Más de 73 kg", 73.1, None),
    ]
    assert {(c["min_age"], c["max_age"], c["rounds_to_win"]) for c in junior_male} == {(15, 17, 2)}


def test_festival_is_one_general_list_per_gender(client, tournament):
    festival = [c for c in _categories(client, tournament) if c["age_label"] == "Festival"]

    assert sorted(c["gender"] for c in festival) == ["female", "male"]
    assert {(c["min_age"], c["max_age"], c["weight_label"], c["min_weight"], c["max_weight"]) for c in festival} == {
        (0, 9, "Todos los pesos", None, None)
    }


def test_syncing_again_keeps_every_category_and_its_id(client, tournament, db_session):
    before = sorted(c["id"] for c in _categories(client, tournament))

    sync_categories(db_session, db_session.get(Tournament, tournament["id"]))
    db_session.commit()

    assert sorted(c["id"] for c in _categories(client, tournament)) == before


def test_the_structure_is_public(client, anon_client, tournament):
    assert anon_client.get(f"/api/v1/tournaments/{tournament['id']}/category-structure").status_code == 200


def test_structure_of_a_missing_tournament_is_404(client):
    assert client.get("/api/v1/tournaments/999/category-structure").status_code == 404


def test_tournaments_from_before_the_structure_have_none(client, tournament, db_session):
    old = db_session.get(Tournament, tournament["id"])
    old.categories = []
    db_session.flush()
    old.grade_groups = []
    old.age_divisions = []
    db_session.commit()

    resp = _structure(client, tournament)

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Este torneo no tiene estructura de categorías"


def _editable(structure):
    """La estructura actual en la forma que recibe el PUT (sin Festival)."""
    return {
        "grade_groups": [{"id": g["id"], "name": g["name"], "from_grade": g["from_grade"]} for g in structure["grade_groups"]],
        "age_divisions": [
            {"id": d["id"], "name": d["name"], "from_age": d["from_age"], "weight_limits": copy.deepcopy(d["weight_limits"])}
            for d in structure["age_divisions"][1:]
        ],
    }


def _put(client, tournament, body, **params):
    # json.dumps (not httpx's json=) so a test can send the non-standard `Infinity` token.
    return client.put(
        f"/api/v1/tournaments/{tournament['id']}/category-structure",
        content=json.dumps(body),
        headers={"Content-Type": "application/json"},
        params=params,
    )


def test_moving_a_grade_cut_keeps_every_category_id(client, tournament):
    before = sorted(c["id"] for c in _categories(client, tournament))
    body = _editable(_structure(client, tournament).json())
    body["grade_groups"][1]["from_grade"] = "kup_4"

    resp = _put(client, tournament, body)

    assert resp.status_code == 200
    assert [(g["from_grade"], g["to_grade"]) for g in resp.json()["grade_groups"]] == [
        ("kup_10", "kup_5"), ("kup_4", "kup_2"), ("kup_1", "dan")
    ]
    assert sorted(c["id"] for c in _categories(client, tournament)) == before


def test_changing_a_weight_limit_keeps_the_category_and_updates_its_range(client, tournament):
    body = _editable(_structure(client, tournament).json())
    junior = next(d for d in body["age_divisions"] if d["name"] == "Junior")
    junior["weight_limits"]["male"] = [50, 55, 63, 73]

    _put(client, tournament, body)

    labels = [c["weight_label"] for c in _categories(client, tournament) if c["age_label"] == "Junior" and c["gender"] == "male"]
    assert labels.count("Hasta 50 kg") == 3 and "Hasta 48 kg" not in labels
    assert len(_categories(client, tournament)) == 212


def test_removing_a_group_and_adding_an_age_recalculates_the_categories(client, tournament):
    body = _editable(_structure(client, tournament).json())
    del body["grade_groups"][1]  # Novatos
    body["age_divisions"].append({"name": "Master", "from_age": 40, "weight_limits": {"male": [70], "female": []}})

    resp = _put(client, tournament, body)

    assert resp.status_code == 200
    # Festival 2 + 2 grupos × (Infantil 24 + Cadete 20 + Junior 10 + Mayores 8 + Senior 8 + Master 2 + 1)
    assert len(_categories(client, tournament)) == 2 + 2 * 73
    assert len(resp.json()["categories"]) == 2 + 2 * 73
    assert resp.json()["age_divisions"][-2]["to_age"] == 39
    assert resp.json()["age_divisions"][-1]["to_age"] is None


def test_validate_only_returns_the_result_without_saving(client, tournament):
    before = _structure(client, tournament).json()
    body = _editable(before)
    del body["age_divisions"][-1]

    resp = _put(client, tournament, body, validate_only="true")

    assert resp.status_code == 200
    assert len(resp.json()["categories"]) == 212 - 3 * 2 * 4
    assert _structure(client, tournament).json() == before
    assert len(_categories(client, tournament)) == 212


@pytest.mark.parametrize(
    "change, detail",
    [
        (lambda b: b["grade_groups"][0].update(from_grade="kup_9"), "El primer grupo de grado tiene que empezar en 10mo Kup"),
        (lambda b: b["grade_groups"][1].update(from_grade="kup_10"), "El grupo «Novatos» tiene que empezar en un grado mayor"),
        (lambda b: b["grade_groups"].pop(), "El último grupo («Avanzados») no se puede quitar"),
        (lambda b: b["grade_groups"][1].update(name="Principiantes"), "Hay grupos de grado con el mismo nombre"),
        (lambda b: b["age_divisions"][0].update(from_age=8), "La primera división de edad tiene que empezar en 10"),
        (lambda b: b["age_divisions"][2].update(from_age=12), "La división «Junior» tiene que empezar en una edad mayor"),
        (lambda b: b["age_divisions"].append({"name": "Festival", "from_age": 50, "weight_limits": {"male": [], "female": []}}),
         "Festival es fijo"),
        (lambda b: b["age_divisions"][0]["weight_limits"].update(male=[30, 26]), "Los pesos masculinos de «Infantil»"),
        (lambda b: b["grade_groups"][0].update(id=999), "Estos ids de grupos de grado no son de este torneo: 999"),
    ],
)
def test_an_invalid_structure_is_rejected_without_changes(client, tournament, change, detail):
    before = _structure(client, tournament).json()
    body = _editable(before)
    change(body)

    resp = _put(client, tournament, body)

    assert resp.status_code == 422
    assert resp.json()["detail"].startswith(detail)
    assert _structure(client, tournament).json() == before


@pytest.mark.parametrize(
    "change",
    [
        lambda b: b["age_divisions"][0]["weight_limits"].update(female=[26.05]),
        lambda b: b["age_divisions"][-1]["weight_limits"].update(male=[58, float("inf")]),
        lambda b: b["age_divisions"][0]["weight_limits"].update(male=list(range(20, 51))),  # 31 límites
        lambda b: b["grade_groups"][0].update(name="x" * 61),
        lambda b: b["age_divisions"][-1].update(name="x" * 61),
        lambda b: b["age_divisions"][-1].update(from_age=121),
    ],
)
def test_out_of_range_values_are_rejected_before_reaching_the_database(client, tournament, change):
    # SQLite doesn't enforce String(60) or int4, Postgres does: without these limits it would be a 500, not a 422.
    before = _structure(client, tournament).json()
    body = _editable(before)
    change(body)

    resp = _put(client, tournament, body)

    assert resp.status_code == 422
    assert _structure(client, tournament).json() == before


def test_the_structure_only_changes_while_the_tournament_is_a_draft(client, tournament, set_tournament_status):
    body = _editable(_structure(client, tournament).json())
    set_tournament_status(client, tournament["id"], "in_progress")

    resp = _put(client, tournament, body)

    assert resp.status_code == 409


def test_changing_the_structure_requires_login(anon_client, client, tournament):
    body = _editable(_structure(client, tournament).json())

    assert _put(anon_client, tournament, body).status_code == 401
