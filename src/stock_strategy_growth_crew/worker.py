from __future__ import annotations

import json
from pathlib import Path

from celery import Celery
from sqlalchemy import delete

from stock_strategy_growth_crew.bootstrap import initialize_database, seed_demo_data
from stock_strategy_growth_crew.db import SessionLocal
from stock_strategy_growth_crew.main import demo_run
from stock_strategy_growth_crew.models import ContentTask, Lead, TrialActivity
from stock_strategy_growth_crew.settings import settings


celery_broker = "memory://" if settings.app_env == "test" else settings.redis_url
celery_backend = "cache+memory://" if settings.app_env == "test" else settings.redis_url
celery_app = Celery("robot_company", broker=celery_broker, backend=celery_backend)
celery_app.conf.update(
    task_always_eager=settings.app_env == "test",
    task_store_eager_result=True,
)


def _load_campaign_brief() -> dict:
    brief_path = Path(settings.stock_strategy_growth_crew_home or Path.cwd()) / "examples" / "campaign_brief.json"
    if not brief_path.exists():
        return {}
    return json.loads(brief_path.read_text(encoding="utf-8"))


def _build_weekly_content_plan(brief: dict) -> list[dict]:
    product_name = brief.get("product_name", "交易策略教练系统")
    cta = brief.get("primary_cta", "申请试用")
    theme = brief.get("campaign_theme", "首周内容测试")
    pillars = brief.get(
        "content_pillars",
        ["少做错误交易", "教练指令", "执行计划与仓位纪律", "持仓诊断", "行为账单与复盘"],
    )
    proof_points = brief.get("proof_points", [])

    plan_seed = [
        ("Mon", "X", f"{pillars[0]}: 为什么大多数 A 股散户输在频繁乱动", "x_editor"),
        ("Tue", "小红书", f"{theme}: 用 {product_name} 修正追高冲动的第一步", "xiaohongshu_editor"),
        ("Wed", "微信公众号", f"{pillars[1]}: 今天到底该不该动", "wechat_editor"),
        ("Thu", "雪球", f"{pillars[2]}: 从候选区到防守线，先有边界再下单", "xueqiu_editor"),
        ("Fri", "X", f"{pillars[3]}: 持仓诊断比找下一只票更重要", "x_editor"),
        ("Sat", "微信公众号", f"{pillars[4]}: 行为账单怎么帮你减少冲动交易", "wechat_editor"),
        ("Sun", "雪球", proof_points[0] if proof_points else f"{product_name} 首周复盘与下周选题", "xueqiu_editor"),
    ]
    return [
        {
            "scheduled_day": day,
            "channel": channel,
            "title": title,
            "owner": owner,
            "cta": cta,
            "status": "planned",
        }
        for day, channel, title, owner in plan_seed
    ]


def _classify_lead(lead: Lead, trial: TrialActivity | None) -> tuple[str, int, str]:
    score = int(lead.intent_score or 0)
    pain_points = json.loads(lead.pain_points or "[]") if lead.pain_points else []
    if trial:
        score += min(trial.days_since_signup * 2, 10)
        if trial.activated:
            score += 12
        if trial.used_features:
            used = json.loads(trial.used_features or "[]") if trial.used_features else []
            score += min(len(used) * 4, 12)
    score += min(len(pain_points) * 3, 9)
    score = max(0, min(score, 100))

    if score >= 85:
        return "hot", score, "立即推进付费沟通，强调纪律改进和正式版边界"
    if score >= 70:
        return "trial", score, "推进试用关键动作，要求完成教练指令和持仓诊断"
    if score >= 50:
        return "warm", score, "继续教育和案例触达，引导进入试用"
    return "cold", score, "降低触达频率，保留在内容培育池"


def _build_trial_followup(trial: TrialActivity) -> tuple[str, str]:
    used = json.loads(trial.used_features or "[]") if trial.used_features else []
    risks = json.loads(trial.risk_signals or "[]") if trial.risk_signals else []

    if not trial.activated:
        return "Day 1", "先完成首次登录，并至少体验一次教练指令"
    if "持仓诊断" not in used:
        return "Day 3", "引导体验持仓诊断，并让用户说出当前最大持仓风险"
    if len(used) < 3:
        return "Day 5", "推动补全关键功能体验，形成从指令到执行计划的闭环"
    if risks:
        return "Day 6", "围绕风险信号做针对性跟进，推动用正式版持续纠偏"
    return "Day 7", "推进正式版成交，强调长期纪律和复盘价值"


def _build_sales_conversion_action(lead: Lead, trial: TrialActivity | None) -> tuple[str, int]:
    score = int(lead.intent_score or 0)
    if trial:
        if trial.activated:
            score += 8
        if trial.used_features:
            used = json.loads(trial.used_features or "[]") if trial.used_features else []
            score += min(len(used) * 3, 9)
    score = max(0, min(score, 100))

    if score >= 90:
        return "直接推进成交，给出正式版价值边界、价格和下一步开通动作", score
    if score >= 80:
        return "安排成交沟通，强调正式版能持续纠偏和复盘，不再只停留在试用体验", score
    if score >= 70:
        return "先推动完成关键功能体验，再收集异议准备成交", score
    return "继续内容培育，不进入强销售推进", score


@celery_app.task(name="robot_company.seed_demo_data")
def seed_demo_data_task() -> str:
    initialize_database()
    with SessionLocal() as db:
        seed_demo_data(db)
    return "seeded"


@celery_app.task(name="robot_company.generate_demo_outputs")
def generate_demo_outputs_task() -> str:
    demo_run()
    return "generated"


@celery_app.task(name="robot_company.generate_weekly_content_plan")
def generate_weekly_content_plan_task() -> dict:
    return _run_weekly_content_plan()


def _run_weekly_content_plan() -> dict:
    initialize_database()
    brief = _load_campaign_brief()
    plan = _build_weekly_content_plan(brief)
    with SessionLocal() as db:
        db.execute(delete(ContentTask))
        for item in plan:
            db.add(ContentTask(**item))
        db.commit()
    return {
        "status": "generated",
        "content_task_count": len(plan),
        "channels": sorted({item["channel"] for item in plan}),
    }


@celery_app.task(name="robot_company.triage_leads")
def triage_leads_task() -> dict:
    return _run_lead_triage()


def _run_lead_triage() -> dict:
    initialize_database()
    updated = 0
    with SessionLocal() as db:
        leads = db.query(Lead).all()
        for lead in leads:
            trial = db.get(TrialActivity, lead.id)
            stage, score, next_action = _classify_lead(lead, trial)
            lead.stage = stage
            lead.intent_score = score
            lead.next_best_action = next_action
            updated += 1
        db.commit()
    return {"status": "triaged", "lead_count": updated}


@celery_app.task(name="robot_company.generate_trial_followup")
def generate_trial_followup_task() -> dict:
    return _run_trial_followup()


def _run_trial_followup() -> dict:
    initialize_database()
    updated = 0
    with SessionLocal() as db:
        trials = db.query(TrialActivity).all()
        for trial in trials:
            followup_day, goal = _build_trial_followup(trial)
            trial.recommended_followup_day = followup_day
            trial.recommended_goal = goal
            updated += 1
        db.commit()
    return {"status": "followup_generated", "trial_count": updated}


@celery_app.task(name="robot_company.generate_sales_conversion")
def generate_sales_conversion_task() -> dict:
    return _run_sales_conversion()


def _run_sales_conversion() -> dict:
    initialize_database()
    updated = 0
    with SessionLocal() as db:
        leads = db.query(Lead).all()
        for lead in leads:
            trial = db.get(TrialActivity, lead.id)
            next_action, score = _build_sales_conversion_action(lead, trial)
            lead.intent_score = score
            if score >= 85:
                lead.stage = "hot"
            lead.next_best_action = next_action
            updated += 1
        db.commit()
    return {"status": "sales_conversion_generated", "lead_count": updated}


@celery_app.task(name="robot_company.run_full_daily_ops")
def run_full_daily_ops_task() -> dict:
    content_result = _run_weekly_content_plan()
    triage_result = _run_lead_triage()
    followup_result = _run_trial_followup()
    sales_result = _run_sales_conversion()
    return {
        "status": "daily_ops_completed",
        "content_task_count": content_result.get("content_task_count", 0),
        "triaged_leads": triage_result.get("lead_count", 0),
        "followup_trials": followup_result.get("trial_count", 0),
        "sales_leads": sales_result.get("lead_count", 0),
    }


def run_worker() -> None:
    celery_app.worker_main(
        [
            "worker",
            "--loglevel=INFO",
        ]
    )


if __name__ == "__main__":
    run_worker()
