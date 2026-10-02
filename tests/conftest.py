import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def client():
    database_url = os.environ.get("DATABASE_URL", "sqlite:///:memory:")
    is_sqlite = database_url.startswith("sqlite")

    if is_sqlite:
        engine = create_engine(
            database_url, connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
    else:
        engine = create_engine(database_url)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    if not is_sqlite:
        # Postgres es un servidor persistente, no una base nueva por test como :memory: --
        # hay que limpiarla a mano para mantener el mismo aislamiento entre tests.
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def club(client):
    resp = client.post("/api/v1/clubs", json={"name": "Dojang Central"})
    return resp.json()


@pytest.fixture()
def tournament(client):
    resp = client.post(
        "/api/v1/tournaments",
        json={"name": "Copa Nacional", "date": "2026-11-15", "location": "San Salvador"},
    )
    return resp.json()


@pytest.fixture()
def category(client, tournament):
    resp = client.post(
        "/api/v1/categories",
        json={
            "tournament_id": tournament["id"],
            "gender": "male",
            "age_label": "Cadete",
            "min_age": 12,
            "max_age": 14,
            "belt_group": "color",
            "weight_label": "Hasta 45kg",
            "min_weight": None,
            "max_weight": 45,
        },
    )
    return resp.json()


@pytest.fixture()
def athlete(client, club):
    resp = client.post(
        "/api/v1/athletes",
        json={
            "name": "Juan Perez",
            "birth_date": "2012-05-01",
            "gender": "male",
            "belt_rank": "verde",
            "weight_kg": 40.5,
            "club_id": club["id"],
        },
    )
    return resp.json()


@pytest.fixture()
def register_n_athletes():
    def _register(client, club, category, n, weight_kg=40):
        registrations = []
        for i in range(n):
            athlete = client.post(
                "/api/v1/athletes",
                json={
                    "name": f"Atleta {i}",
                    "birth_date": "2012-01-01",
                    "gender": "male",
                    "belt_rank": "verde",
                    "weight_kg": weight_kg,
                    "club_id": club["id"],
                },
            ).json()
            resp = client.post(
                "/api/v1/registrations",
                json={"athlete_id": athlete["id"], "category_id": category["id"]},
            )
            registrations.append(resp.json())
        return registrations

    return _register
