from __future__ import annotations

from fastapi.testclient import TestClient

from stock_strategy_growth_crew.web import app


def test_healthz() -> None:
    with TestClient(app) as client:
        response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_dashboard_payload() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/dashboard")
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["lead_count"] >= 1
    assert len(payload["leads"]) >= 1


def test_app_page() -> None:
    with TestClient(app) as client:
        response = client.get("/app")
    assert response.status_code == 200
    assert "Robot Company App" in response.text


def test_create_lead() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/leads",
            json={
                "id": "lead_test_api",
                "name": "测试线索",
                "source": "API",
                "stage": "warm",
                "intent_score": 66,
                "pain_points": [],
                "last_action": "",
                "next_best_action": "继续跟进",
            },
        )
        if response.status_code == 409:
            assert response.json()["detail"] == "Lead already exists"
        else:
            assert response.status_code == 201
            assert response.json()["id"] == "lead_test_api"
