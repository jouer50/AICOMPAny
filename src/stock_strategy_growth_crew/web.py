from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

from stock_strategy_growth_crew.main import demo_run


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_PATH = PROJECT_ROOT / "dashboard.html"
DASHBOARD_SCRIPT = PROJECT_ROOT / "dashboard.py"

app = FastAPI(title="Robot Company Dashboard", version="0.1.0")


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def refresh_demo_assets() -> None:
    demo_run()
    subprocess.run(
        [sys.executable, str(DASHBOARD_SCRIPT)],
        cwd=PROJECT_ROOT,
        check=True,
    )


def build_dashboard_payload() -> dict:
    leads = _read_json(PROJECT_ROOT / "examples" / "lead_pipeline.json").get("leads", [])
    trials = _read_json(PROJECT_ROOT / "examples" / "trial_activity.json").get("trials", [])
    hot_leads = [lead for lead in leads if lead.get("stage") == "hot"]
    trial_leads = [lead for lead in leads if lead.get("stage") == "trial"]
    activated_trials = [trial for trial in trials if trial.get("activated")]

    return {
        "summary": {
            "lead_count": len(leads),
            "trial_count": len(trial_leads),
            "hot_count": len(hot_leads),
            "activated_trial_count": len(activated_trials),
        },
        "leads": leads,
        "trials": trials,
        "files": {
            "crm_dashboard": str(PROJECT_ROOT / "crm_dashboard.md"),
            "growth_execution_plan": str(PROJECT_ROOT / "growth_execution_plan.md"),
            "lead_triage": str(PROJECT_ROOT / "lead_triage.md"),
            "trial_followup_plan": str(PROJECT_ROOT / "trial_followup_plan.md"),
            "sales_conversion_plan": str(PROJECT_ROOT / "sales_conversion_plan.md"),
        },
    }


@app.on_event("startup")
def startup_refresh() -> None:
    if not DASHBOARD_PATH.exists():
        refresh_demo_assets()


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/dashboard", status_code=302)


@app.get("/dashboard")
def dashboard() -> FileResponse:
    if not DASHBOARD_PATH.exists():
        refresh_demo_assets()
    return FileResponse(DASHBOARD_PATH, media_type="text/html")


@app.post("/api/refresh")
def refresh() -> JSONResponse:
    try:
        refresh_demo_assets()
    except subprocess.CalledProcessError as exc:
        raise HTTPException(status_code=500, detail=f"Dashboard rebuild failed: {exc}") from exc
    return JSONResponse({"status": "ok", "dashboard": "/dashboard"})


@app.get("/api/dashboard")
def dashboard_data() -> JSONResponse:
    return JSONResponse(build_dashboard_payload())


def serve() -> None:
    import uvicorn

    uvicorn.run("stock_strategy_growth_crew.web:app", host="0.0.0.0", port=8000)

