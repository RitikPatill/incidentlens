from fastapi.testclient import TestClient
from app.main import app


def test_app_title():
    assert app.title == "IncidentLens"


def test_healthz():
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
