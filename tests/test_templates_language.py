from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "app" / "templates"


def test_no_raw_enum_value_in_templates():
    """Cualquier plantilla que imprima `.value` directo de un enum se muestra en inglés.

    Este test no sabe qué enum es ni en qué plantilla está -- agarra el patrón exacto que
    causa la fuga a inglés, incluidas plantillas futuras (ej. la pantalla admin de la fase 6).
    Traducir siempre con el filtro `|es_label` (ver app/web/labels.py).
    """
    offenders = [
        html_file.name
        for html_file in TEMPLATES_DIR.glob("*.html")
        if ".value" in html_file.read_text()
    ]
    assert not offenders, f"Plantillas usando .value directo: {offenders}"


def test_home_shows_spanish_status_label(client, tournament):
    resp = client.get("/")
    assert "Borrador" in resp.text


def test_tournament_detail_shows_spanish_category_labels(client, tournament, category):
    resp = client.get(f"/torneos/{tournament['id']}")
    assert "Masculino" in resp.text
    assert "Cinturón de color" in resp.text


def test_category_detail_shows_spanish_labels_pending_and_finished(
    client, club, category, register_n_athletes
):
    register_n_athletes(client, club, category, 2)
    match = client.post(f"/api/v1/categories/{category['id']}/bracket").json()["matches"][0]

    resp = client.get(f"/categorias/{category['id']}")
    assert "Masculino" in resp.text
    assert "Cinturón de color" in resp.text
    assert "Pendiente" in resp.text

    client.post(
        f"/api/v1/matches/{match['id']}/rounds",
        json={"round_number": 1, "red_points": 12, "blue_points": 5},
    )
    client.post(
        f"/api/v1/matches/{match['id']}/rounds",
        json={"round_number": 2, "red_points": 9, "blue_points": 3},
    )

    resp = client.get(f"/categorias/{category['id']}")
    assert "Finalizado" in resp.text


def test_category_detail_shows_spanish_bye_label(client, club, category, register_n_athletes):
    register_n_athletes(client, club, category, 5)
    client.post(f"/api/v1/categories/{category['id']}/bracket")

    resp = client.get(f"/categorias/{category['id']}")
    assert "Pase directo" in resp.text
