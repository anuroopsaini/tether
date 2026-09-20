from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def complete_demo() -> dict:
    created = client.post("/api/demo")
    assert created.status_code == 202
    assert set(created.json()) == {"id", "status"}
    assert created.json()["status"] == "queued"

    analysis = client.get(f"/api/analyses/{created.json()['id']}")
    assert analysis.status_code == 200
    assert analysis.json()["status"] == "complete"
    return analysis.json()


def test_health_contract():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "provider": "ollama",
        "nemotron": "mock",
        "model": "nemotron-3-ultra:cloud",
    }


def test_create_analysis_and_get_analysis_contract():
    created = client.post(
        "/api/analyses",
        data={"doc_type": "essay", "draft_text": "I led 3 students in a robotics project."},
        files={"files": ("advisor.txt", b"Advisor confirms three students.", "text/plain")},
    )

    assert created.status_code == 202
    assert set(created.json()) == {"id", "status"}
    analysis = client.get(f"/api/analyses/{created.json()['id']}")
    assert analysis.status_code == 200
    body = analysis.json()
    assert {
        "id",
        "status",
        "doc_type",
        "draft_text",
        "evidence",
        "progress",
        "result",
        "error",
    } <= set(body)
    assert {"extracting", "matching", "judging", "privacy", "scoring", "done"} <= {
        item["step"] for item in body["progress"]
    }
    assert body["result"] is not None


def test_demo_contract_includes_all_trust_map_colors():
    analysis = complete_demo()
    result = analysis["result"]

    assert result["summary"]["claims_reviewed"] >= 4
    assert {claim["color"] for claim in result["claims"]} >= {
        "green",
        "yellow",
        "red",
        "purple",
    }
    claim = result["claims"][0]
    assert {
        "id",
        "text",
        "category",
        "verdict",
        "color",
        "action",
        "confidence",
        "evidence_snippets",
        "evidence_match",
        "safe_rewrite",
    } <= set(claim)


def test_events_use_named_progress_and_complete_events():
    analysis = complete_demo()

    response = client.get(f"/api/analyses/{analysis['id']}/events")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: progress\ndata: {\"step\":\"extracting\"" in response.text
    assert "event: complete\ndata: {\"status\": \"complete\"}" in response.text


def test_accept_rewrite_returns_updated_claim_contract():
    analysis = complete_demo()
    claim = next(item for item in analysis["result"]["claims"] if item["color"] == "yellow")

    response = client.post(f"/api/analyses/{analysis['id']}/claims/{claim['id']}/accept-rewrite")

    assert response.status_code == 200
    returned = response.json()
    assert returned["id"] == claim["id"]
    assert returned["accepted_rewrite"] == returned["safe_rewrite"]


def test_evidence_pack_preview_and_pdf_contract():
    analysis = complete_demo()

    preview = client.get(f"/api/analyses/{analysis['id']}/evidence-pack/preview")
    assert preview.status_code == 200
    assert preview.headers["content-type"].startswith("text/html")
    assert "Tether Evidence Pack" in preview.text

    pdf = client.get(f"/api/analyses/{analysis['id']}/evidence-pack")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.headers["content-disposition"].startswith("attachment;")
    assert pdf.content.startswith(b"%PDF-1.4")


def test_api_errors_use_a_consistent_envelope():
    missing = client.get("/api/analyses/not-an-analysis")
    invalid = client.post("/api/analyses", data={"doc_type": "essay", "draft_text": ""})

    assert missing.status_code == 404
    assert missing.json() == {
        "error": {"code": "NOT_FOUND", "message": "Analysis not found"}
    }
    assert invalid.status_code == 422
    assert set(invalid.json()) == {"error"}
    assert invalid.json()["error"]["code"] in {"MISSING_DRAFT", "VALIDATION_ERROR"}
    assert isinstance(invalid.json()["error"]["message"], str)


def test_vite_default_origin_is_allowed_by_cors():
    response = client.options(
        "/api/analyses",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
