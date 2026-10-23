from app import create_app
from fastapi.testclient import TestClient


def test_health_route():
    app = create_app()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
