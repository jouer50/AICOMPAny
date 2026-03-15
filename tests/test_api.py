from __future__ import annotations

from fastapi.testclient import TestClient

from stock_strategy_growth_crew.web import app


def test_healthz() -> None:
    with TestClient(app) as client:
        response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_root_redirects_to_app() -> None:
    with TestClient(app) as client:
        response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/app"


def test_dashboard_redirects_to_app() -> None:
    with TestClient(app) as client:
        response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/app"


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


def test_upsert_trial() -> None:
    with TestClient(app) as client:
        create_lead_response = client.post(
            "/api/v1/leads",
            json={
                "id": "lead_trial_api",
                "name": "试用用户",
                "source": "API",
                "stage": "trial",
                "intent_score": 72,
                "pain_points": [],
                "last_action": "",
                "next_best_action": "引导体验持仓诊断",
            },
        )
        assert create_lead_response.status_code in (201, 409)

        response = client.post(
            "/api/v1/trials",
            json={
                "lead_id": "lead_trial_api",
                "activated": True,
                "days_since_signup": 3,
                "used_features": ["教练指令", "执行计划"],
                "risk_signals": [],
                "recommended_followup_day": "Day 4",
                "recommended_goal": "继续推进试用转付费",
            },
        )
    assert response.status_code == 201
    payload = response.json()
    assert payload["lead_id"] == "lead_trial_api"
    assert payload["activated"] is True


def test_update_content_task() -> None:
    with TestClient(app) as client:
        tasks = client.get("/api/v1/content-tasks").json()
        assert tasks
        task_id = tasks[0]["id"]
        response = client.patch(f"/api/v1/content-tasks/{task_id}", json={"status": "published"})
    assert response.status_code == 200
    assert response.json()["status"] == "published"
