"""Hosted demo access-control regression tests."""
import os
import subprocess
import sys

from fastapi.testclient import TestClient


def test_hosted_demo_rejects_mutations(monkeypatch):
    monkeypatch.setenv("HOSTED_DEMO_MODE", "true")
    monkeypatch.setenv("EAM_API_KEY", "test-only-private-key")
    import importlib
    import api.mock_eam as mock_eam
    importlib.reload(mock_eam)
    client = TestClient(mock_eam.app)
    headers = {"X-API-Key": "test-only-private-key"}
    assert client.get("/health").status_code == 200
    assert client.get("/assets", headers=headers).status_code == 200
    response = client.patch(
        "/assets/A133/condition",
        headers=headers,
        json={"condition_score": 5, "inspection_date": "2026-10-28"},
    )
    assert response.status_code == 403
    assert client.post("/admin/reset", headers=headers).status_code == 403
    monkeypatch.delenv("HOSTED_DEMO_MODE", raising=False)
    monkeypatch.delenv("EAM_API_KEY", raising=False)
    importlib.reload(mock_eam)


def test_hosted_demo_rejects_default_key():
    env = dict(os.environ, HOSTED_DEMO_MODE="true", EAM_API_KEY="demo-secret-key")
    run = subprocess.run(
        [sys.executable, "-c", "import api.mock_eam"],
        capture_output=True, text=True, env=env
    )
    assert run.returncode != 0
    assert "non-default EAM_API_KEY" in run.stderr
