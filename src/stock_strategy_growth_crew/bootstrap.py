from __future__ import annotations

import json
import os
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from stock_strategy_growth_crew.db import Base, engine
from stock_strategy_growth_crew.models import ContentTask, Lead, TrialActivity


def resolve_project_root() -> Path:
    candidates = []
    env_root = os.getenv("STOCK_STRATEGY_GROWTH_CREW_HOME")
    if env_root:
        candidates.append(Path(env_root).expanduser())
    candidates.append(Path.cwd())
    candidates.append(Path(__file__).resolve().parents[2])

    for candidate in candidates:
        if (candidate / "examples").exists():
            return candidate
    return Path.cwd()


PROJECT_ROOT = resolve_project_root()
EXAMPLES_DIR = PROJECT_ROOT / "examples"


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)


def seed_demo_data(db: Session) -> None:
    existing = db.scalar(select(Lead.id).limit(1))
    if existing:
        return

    leads = read_json(EXAMPLES_DIR / "lead_pipeline.json").get("leads", [])
    trials = read_json(EXAMPLES_DIR / "trial_activity.json").get("trials", [])

    for lead in leads:
        db.add(
            Lead(
                id=lead["id"],
                name=lead["name"],
                source=lead["source"],
                stage=lead["stage"],
                intent_score=lead.get("intent_score", 0),
                pain_points=json.dumps(lead.get("pain_points", []), ensure_ascii=True),
                last_action=lead.get("last_action", ""),
                next_best_action=lead.get("next_best_action", ""),
            )
        )

    content_seed = [
        {
            "channel": "X",
            "title": "少做错误交易",
            "status": "planned",
            "cta": "关注 X / 申请试用",
            "owner": "x_editor",
            "scheduled_day": "Mon",
        },
        {
            "channel": "微信公众号",
            "title": "教练指令的价值",
            "status": "draft",
            "cta": "申请试用",
            "owner": "wechat_editor",
            "scheduled_day": "Wed",
        },
        {
            "channel": "雪球",
            "title": "持仓诊断与仓位纪律",
            "status": "planned",
            "cta": "申请试用",
            "owner": "xueqiu_editor",
            "scheduled_day": "Thu",
        },
    ]
    for item in content_seed:
        db.add(ContentTask(**item))

    for trial in trials:
        db.add(
            TrialActivity(
                lead_id=trial["lead_id"],
                activated=trial.get("activated", False),
                days_since_signup=trial.get("days_since_signup", 0),
                used_features=json.dumps(trial.get("used_features", []), ensure_ascii=True),
                risk_signals=json.dumps(trial.get("risk_signals", []), ensure_ascii=True),
                recommended_followup_day=trial.get("recommended_followup_day", ""),
                recommended_goal=trial.get("recommended_goal", ""),
            )
        )

    db.commit()

