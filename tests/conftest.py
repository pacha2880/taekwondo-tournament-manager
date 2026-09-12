import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
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
