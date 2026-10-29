from fastapi.testclient import TestClient
from api.mock_eam import app

client = TestClient(app)


def test_api_rejects_missing_key():
    response = client.get("/assets")
    assert response.status_code == 401


def test_api_returns_assets_with_key():
    response = client.get("/assets", headers={"X-API-Key": "demo-secret-key"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] > 30
