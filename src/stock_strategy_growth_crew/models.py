from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from stock_strategy_growth_crew.db import Base


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    source: Mapped[str] = mapped_column(String(64))
    stage: Mapped[str] = mapped_column(String(32), index=True)
    intent_score: Mapped[int] = mapped_column(Integer, default=0)
    pain_points: Mapped[str] = mapped_column(Text, default="")
    last_action: Mapped[str] = mapped_column(Text, default="")
    next_best_action: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    trial_activity: Mapped["TrialActivity | None"] = relationship(back_populates="lead", uselist=False)


class TrialActivity(Base):
    __tablename__ = "trial_activities"

    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id"), primary_key=True)
    activated: Mapped[bool] = mapped_column(Boolean, default=False)
    days_since_signup: Mapped[int] = mapped_column(Integer, default=0)
    used_features: Mapped[str] = mapped_column(Text, default="")
    risk_signals: Mapped[str] = mapped_column(Text, default="")
    recommended_followup_day: Mapped[str] = mapped_column(String(32), default="")
    recommended_goal: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lead: Mapped[Lead] = relationship(back_populates="trial_activity")


class ContentTask(Base):
    __tablename__ = "content_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="planned", index=True)
    cta: Mapped[str] = mapped_column(String(255), default="")
    owner: Mapped[str] = mapped_column(String(64), default="")
    scheduled_day: Mapped[str] = mapped_column(String(32), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AutomationRun(Base):
    __tablename__ = "automation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    run_type: Mapped[str] = mapped_column(String(64), index=True)
    trigger_source: Mapped[str] = mapped_column(String(32), default="manual")
    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True)
    mode: Mapped[str] = mapped_column(String(32), default="rules")
    result_json: Mapped[str] = mapped_column(Text, default="")
    error_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
