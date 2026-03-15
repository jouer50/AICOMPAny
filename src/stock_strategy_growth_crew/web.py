from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from stock_strategy_growth_crew.bootstrap import PROJECT_ROOT, initialize_database, seed_demo_data
from stock_strategy_growth_crew.db import SessionLocal, get_db
from stock_strategy_growth_crew.main import demo_run
from stock_strategy_growth_crew.models import ContentTask, Lead, TrialActivity
from stock_strategy_growth_crew.schemas import (
    ContentTaskRead,
    DashboardPayload,
    DashboardSummary,
    LeadCreate,
    LeadRead,
    TrialActivityCreate,
    TrialActivityRead,
)
from stock_strategy_growth_crew.settings import settings


DASHBOARD_PATH = PROJECT_ROOT / "dashboard.html"
DASHBOARD_SCRIPT = PROJECT_ROOT / "dashboard.py"

app = FastAPI(title=settings.app_name, version="0.2.0")


def _parse_json_list(raw: str) -> list[str]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
        return value if isinstance(value, list) else []
    except json.JSONDecodeError:
        return []


def _serialize_lead(lead: Lead) -> LeadRead:
    trial = lead.trial_activity
    return LeadRead(
        id=lead.id,
        name=lead.name,
        source=lead.source,
        stage=lead.stage,
        intent_score=lead.intent_score,
        pain_points=_parse_json_list(lead.pain_points),
        last_action=lead.last_action,
        next_best_action=lead.next_best_action,
        created_at=lead.created_at,
        updated_at=lead.updated_at,
        trial_activity=_serialize_trial(trial) if trial else None,
    )


def _serialize_trial(trial: TrialActivity) -> TrialActivityRead:
    return TrialActivityRead(
        lead_id=trial.lead_id,
        activated=trial.activated,
        days_since_signup=trial.days_since_signup,
        used_features=_parse_json_list(trial.used_features),
        risk_signals=_parse_json_list(trial.risk_signals),
        recommended_followup_day=trial.recommended_followup_day,
        recommended_goal=trial.recommended_goal,
        updated_at=trial.updated_at,
    )


def _serialize_content_task(task: ContentTask) -> ContentTaskRead:
    return ContentTaskRead.model_validate(task)


def refresh_demo_assets() -> None:
    demo_run()
    subprocess.run(
        [sys.executable, str(DASHBOARD_SCRIPT)],
        cwd=PROJECT_ROOT,
        check=True,
    )


def ensure_seeded() -> None:
    initialize_database()
    with SessionLocal() as db:
        seed_demo_data(db)


def build_dashboard_payload(db: Session) -> DashboardPayload:
    leads = db.scalars(select(Lead).options(selectinload(Lead.trial_activity)).order_by(Lead.created_at.desc())).all()
    trials = db.scalars(select(TrialActivity).order_by(TrialActivity.updated_at.desc())).all()
    content_tasks = db.scalars(select(ContentTask).order_by(ContentTask.created_at.desc())).all()

    hot_leads = [lead for lead in leads if lead.stage == "hot"]
    trial_leads = [lead for lead in leads if lead.stage == "trial"]
    activated_trials = [trial for trial in trials if trial.activated]

    return DashboardPayload(
        summary=DashboardSummary(
            lead_count=len(leads),
            trial_count=len(trial_leads),
            hot_count=len(hot_leads),
            activated_trial_count=len(activated_trials),
            content_task_count=len(content_tasks),
        ),
        leads=[_serialize_lead(lead) for lead in leads],
        trials=[_serialize_trial(trial) for trial in trials],
        content_tasks=[_serialize_content_task(task) for task in content_tasks],
    )


@app.on_event("startup")
def startup_refresh() -> None:
    ensure_seeded()
    if not DASHBOARD_PATH.exists():
        refresh_demo_assets()


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "env": settings.app_env}


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


@app.post("/api/v1/bootstrap")
def bootstrap_data() -> dict:
    ensure_seeded()
    return {"status": "ok"}


@app.get("/api/dashboard", response_model=DashboardPayload)
@app.get("/api/v1/dashboard", response_model=DashboardPayload)
def dashboard_data(db: Session = Depends(get_db)) -> DashboardPayload:
    return build_dashboard_payload(db)


@app.get("/api/v1/leads", response_model=list[LeadRead])
def list_leads(
    stage: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[LeadRead]:
    stmt = select(Lead).options(selectinload(Lead.trial_activity)).order_by(Lead.created_at.desc())
    if stage:
        stmt = stmt.where(Lead.stage == stage)
    leads = db.scalars(stmt).all()
    return [_serialize_lead(lead) for lead in leads]


@app.post("/api/v1/leads", response_model=LeadRead, status_code=201)
def create_lead(payload: LeadCreate, db: Session = Depends(get_db)) -> LeadRead:
    existing = db.get(Lead, payload.id)
    if existing:
        raise HTTPException(status_code=409, detail="Lead already exists")

    lead = Lead(
        id=payload.id,
        name=payload.name,
        source=payload.source,
        stage=payload.stage,
        intent_score=payload.intent_score,
        pain_points=json.dumps(payload.pain_points, ensure_ascii=True),
        last_action=payload.last_action,
        next_best_action=payload.next_best_action,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return _serialize_lead(lead)


@app.get("/api/v1/trials", response_model=list[TrialActivityRead])
def list_trials(db: Session = Depends(get_db)) -> list[TrialActivityRead]:
    trials = db.scalars(select(TrialActivity).order_by(TrialActivity.updated_at.desc())).all()
    return [_serialize_trial(trial) for trial in trials]


@app.post("/api/v1/trials", response_model=TrialActivityRead, status_code=201)
def upsert_trial(payload: TrialActivityCreate, db: Session = Depends(get_db)) -> TrialActivityRead:
    lead = db.get(Lead, payload.lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    trial = db.get(TrialActivity, payload.lead_id)
    if not trial:
        trial = TrialActivity(lead_id=payload.lead_id)
        db.add(trial)

    trial.activated = payload.activated
    trial.days_since_signup = payload.days_since_signup
    trial.used_features = json.dumps(payload.used_features, ensure_ascii=True)
    trial.risk_signals = json.dumps(payload.risk_signals, ensure_ascii=True)
    trial.recommended_followup_day = payload.recommended_followup_day
    trial.recommended_goal = payload.recommended_goal

    db.commit()
    db.refresh(trial)
    return _serialize_trial(trial)


@app.get("/api/v1/content-tasks", response_model=list[ContentTaskRead])
def list_content_tasks(db: Session = Depends(get_db)) -> list[ContentTaskRead]:
    tasks = db.scalars(select(ContentTask).order_by(ContentTask.created_at.desc())).all()
    return [_serialize_content_task(task) for task in tasks]


def serve() -> None:
    import uvicorn

    uvicorn.run("stock_strategy_growth_crew.web:app", host="0.0.0.0", port=settings.app_port)

