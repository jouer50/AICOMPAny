from __future__ import annotations

import json
from pathlib import Path

from celery import Celery
from sqlalchemy import delete

from stock_strategy_growth_crew.bootstrap import initialize_database, seed_demo_data
from stock_strategy_growth_crew.db import SessionLocal
from stock_strategy_growth_crew.main import demo_run
from stock_strategy_growth_crew.models import ContentTask
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


def run_worker() -> None:
    celery_app.worker_main(
        [
            "worker",
            "--loglevel=INFO",
        ]
    )


if __name__ == "__main__":
    run_worker()
