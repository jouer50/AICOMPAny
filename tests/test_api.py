from __future__ import annotations

from fastapi.testclient import TestClient

from stock_strategy_growth_crew.web import app


def login(client: TestClient) -> None:
    response = client.post(
        "/api/login",
        json={"username": "admin", "password": "change-me"},
    )
    assert response.status_code == 200


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


def test_login_page_loads() -> None:
    with TestClient(app) as client:
        response = client.get("/login")
    assert response.status_code == 200
    assert "Admin Login" in response.text


def test_dashboard_requires_auth() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/dashboard")
    assert response.status_code == 401


def test_dashboard_payload() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get("/api/v1/dashboard")
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["lead_count"] >= 1
    assert len(payload["leads"]) >= 1


def test_app_page() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.get("/app")
    assert response.status_code == 200
    assert "Robot Company App" in response.text


def test_create_lead() -> None:
    with TestClient(app) as client:
        login(client)
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


def test_update_lead() -> None:
    with TestClient(app) as client:
        login(client)
        create_response = client.post(
            "/api/v1/leads",
            json={
                "id": "lead_update_api",
                "name": "待更新线索",
                "source": "API",
                "stage": "warm",
                "intent_score": 55,
                "pain_points": [],
                "last_action": "",
                "next_best_action": "等待更新",
            },
        )
        assert create_response.status_code in (201, 409)

        response = client.patch(
            "/api/v1/leads/lead_update_api",
            json={
                "stage": "hot",
                "intent_score": 92,
                "next_best_action": "立即推进正式版成交",
            },
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "lead_update_api"
    assert payload["stage"] == "hot"
    assert payload["intent_score"] == 92


def test_upsert_trial() -> None:
    with TestClient(app) as client:
        login(client)
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
        login(client)
        tasks = client.get("/api/v1/content-tasks").json()
        assert tasks
        task_id = tasks[0]["id"]
        response = client.patch(f"/api/v1/content-tasks/{task_id}", json={"status": "published"})
    assert response.status_code == 200
    assert response.json()["status"] == "published"


def test_trigger_content_plan_job() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.post("/api/v1/automation/content-plan")
        assert response.status_code == 200
        payload = response.json()
        assert payload["task_id"]
        assert payload["status"] in ("SUCCESS", "PENDING")

        job_response = client.get(f"/api/v1/jobs/{payload['task_id']}")
    assert job_response.status_code == 200
    job_payload = job_response.json()
    assert job_payload["task_id"] == payload["task_id"]
    assert job_payload["status"] in ("SUCCESS", "PENDING")


def test_trigger_lead_triage_job() -> None:
    with TestClient(app) as client:
        login(client)
        response = client.post("/api/v1/automation/lead-triage")
        assert response.status_code == 200
        payload = response.json()
        assert payload["task_id"]
        assert payload["status"] in ("SUCCESS", "PENDING")

        job_response = client.get(f"/api/v1/jobs/{payload['task_id']}")
    assert job_response.status_code == 200
    job_payload = job_response.json()
    assert job_payload["task_id"] == payload["task_id"]
    assert job_payload["status"] in ("SUCCESS", "PENDING")
