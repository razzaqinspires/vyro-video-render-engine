import base64

from fastapi.testclient import TestClient

from vyro_video_render_engine import api


def test_health_endpoint():
    client = TestClient(api.app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["version"] == "1.3.0"


def test_upload_requires_service_key(monkeypatch, tmp_path):
    monkeypatch.setenv("VYRO_SERVICE_API_KEY", "test-secret-key")
    monkeypatch.setattr(api, "ASSETS_DIR", tmp_path / "assets")
    client = TestClient(api.app)
    body = {"filename": "one.png", "data_base64": base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"x" * 30).decode()}
    response = client.post("/v1/assets", json=body, headers={"X-Vyro-Demo-ID": "VYRO-DEMO-a1b2c3d4"})
    assert response.status_code == 401


def test_upload_rejects_signature_mismatch(monkeypatch, tmp_path):
    monkeypatch.setenv("VYRO_SERVICE_API_KEY", "test-secret-key")
    monkeypatch.setattr(api, "ASSETS_DIR", tmp_path / "assets")
    client = TestClient(api.app)
    body = {"filename": "one.png", "data_base64": base64.b64encode(b"not-a-png" + b"x" * 30).decode()}
    response = client.post("/v1/assets", json=body, headers={
        "Authorization": "Bearer test-secret-key", "X-Vyro-Demo-ID": "VYRO-DEMO-a1b2c3d4"
    })
    assert response.status_code == 415


def test_render_requires_human_approval(monkeypatch, tmp_path):
    monkeypatch.setenv("VYRO_SERVICE_API_KEY", "test-secret-key")
    monkeypatch.setattr(api, "ASSETS_DIR", tmp_path / "assets")
    monkeypatch.setattr(api, "RENDERS_DIR", tmp_path / "renders")
    client = TestClient(api.app)
    response = client.post("/v1/render", json={"timeline": {}, "review_approved": False}, headers={
        "Authorization": "Bearer test-secret-key", "X-Vyro-Demo-ID": "VYRO-DEMO-a1b2c3d4"
    })
    assert response.status_code == 409
