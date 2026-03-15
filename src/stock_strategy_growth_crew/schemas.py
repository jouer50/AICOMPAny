from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TrialActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    lead_id: str
    activated: bool
    days_since_signup: int
    used_features: list[str]
    risk_signals: list[str]
    recommended_followup_day: str
    recommended_goal: str
    updated_at: datetime


class LeadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    source: str
    stage: str
    intent_score: int
    pain_points: list[str]
    last_action: str
    next_best_action: str
    created_at: datetime
    updated_at: datetime
    trial_activity: TrialActivityRead | None = None


class LeadCreate(BaseModel):
    id: str
    name: str
    source: str
    stage: str
    intent_score: int = 0
    pain_points: list[str] = []
    last_action: str = ""
    next_best_action: str = ""


class LeadUpdate(BaseModel):
    stage: str
    intent_score: int
    next_best_action: str = ""


class TrialActivityCreate(BaseModel):
    lead_id: str
    activated: bool = False
    days_since_signup: int = 0
    used_features: list[str] = []
    risk_signals: list[str] = []
    recommended_followup_day: str = ""
    recommended_goal: str = ""


class ContentTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    channel: str
    title: str
    status: str
    cta: str
    owner: str
    scheduled_day: str
    created_at: datetime
    updated_at: datetime


class ContentTaskUpdate(BaseModel):
    status: str


class AutomationJobRead(BaseModel):
    task_id: str
    status: str
    result: dict | str | None = None


class DashboardSummary(BaseModel):
    lead_count: int
    trial_count: int
    hot_count: int
    activated_trial_count: int
    content_task_count: int


class DashboardPayload(BaseModel):
    summary: DashboardSummary
    leads: list[LeadRead]
    trials: list[TrialActivityRead]
    content_tasks: list[ContentTaskRead]
