from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_demo_completes():
    created = client.post("/api/demo")
    assert created.status_code == 202
    analysis = client.get(f"/api/analyses/{created.json()['id']}")
    assert analysis.status_code == 200
    result = analysis.json()["result"]
    assert result["summary"]["claims_reviewed"] >= 4
    assert {claim["color"] for claim in result["claims"]} >= {"green", "yellow", "red", "purple"}
    preview = client.get(f"/api/analyses/{created.json()['id']}/evidence-pack/preview")
    assert preview.status_code == 200
    assert "Tether Evidence Pack" in preview.text


def test_missing_draft_is_rejected():
    response = client.post("/api/analyses", data={"doc_type": "essay", "draft_text": ""})
    assert response.status_code == 422
