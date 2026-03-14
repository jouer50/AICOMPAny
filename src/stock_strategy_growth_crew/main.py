#!/usr/bin/env python
import json
import os
import sys
import warnings

from datetime import datetime
from pathlib import Path

from stock_strategy_growth_crew.crew import StockStrategyGrowthCrew

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

DEFAULT_INPUTS = {
    "product_name": "股票交易策略教练系统",
    "product_summary": "帮助用户复盘交易、训练纪律、理解策略逻辑，并生成教育型内容与陪练建议。",
    "target_audience": "有股票交易经验、希望提升策略纪律和复盘能力的中文投资者",
    "channels": "X、小红书、微信公众号、雪球",
    "brand_tone": "专业、克制、可信，不夸收益，不带单",
    "primary_cta": "引导用户预约演示、领取试用或进入私域了解产品",
    "campaign_theme": f"{datetime.now().year} 年交易纪律与策略复盘内容周计划",
    "current_year": str(datetime.now().year)
}


def _resolve_project_root() -> Path:
    candidates = []
    env_root = os.getenv("STOCK_STRATEGY_GROWTH_CREW_HOME")
    if env_root:
        candidates.append(Path(env_root).expanduser())
    candidates.append(Path.cwd())
    candidates.append(Path(__file__).resolve().parents[2])

    for candidate in candidates:
        if (candidate / "examples").exists():
            return candidate
    return Path(__file__).resolve().parents[2]


PROJECT_ROOT = _resolve_project_root()
EXAMPLES_DIR = PROJECT_ROOT / "examples"
BRIEF_PATH = EXAMPLES_DIR / "campaign_brief.json"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def load_inputs():
    inputs = dict(DEFAULT_INPUTS)
    if BRIEF_PATH.exists():
        with BRIEF_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        inputs.update(data)
    inputs["current_year"] = str(datetime.now().year)
    return inputs


def demo_run():
    """
    Generate a local demo without requiring any model API key.
    """
    inputs = load_inputs()
    leads = json.loads(_read_text(EXAMPLES_DIR / "lead_pipeline.json")).get("leads", [])
    trials = json.loads(_read_text(EXAMPLES_DIR / "trial_activity.json")).get("trials", [])
    market_signals = json.loads(_read_text(EXAMPLES_DIR / "market_signals.json")).get("signals", [])
    competitors = json.loads(_read_text(EXAMPLES_DIR / "competitor_snapshots.json")).get(
        "competitors", []
    )

    growth_execution_plan = f"""# Growth Execution Plan

## Product

- 产品：{inputs['product_name']}
- 目标用户：{inputs['target_audience']}
- 主题：{inputs['campaign_theme']}
- 核心 CTA：{inputs['primary_cta']}

## Content Pillars

{chr(10).join(f"- {item}" for item in inputs.get('content_pillars', []))}

## Market Signals

{chr(10).join(f"- [{item.get('priority', 'P2')}] {item.get('title')}: {item.get('summary')}" for item in market_signals)}

## Competitor Snapshots

{chr(10).join(f"- {item.get('name')}: {item.get('positioning')}" for item in competitors)}

## Weekly Calendar

| Day | Channel | Topic | CTA |
|---|---|---|---|
| Mon | X | 少做错误交易 | 关注 X / 申请试用 |
| Tue | 小红书 | 为什么散户总在不该动的时候动 | 关注公众号 |
| Wed | 公众号 | 教练指令的价值 | 申请试用 |
| Thu | 雪球 | 持仓诊断与仓位纪律 | 申请试用 |
| Fri | X + 公众号 | 本周复盘与行为纠偏 | 试用转付费 |
"""

    lead_triage = """# Lead Triage

| Lead ID | Source | Stage | Intent | Pain Points | Next Action |
|---|---|---|---:|---|---|
"""
    for lead in leads:
        lead_triage += (
            f"| {lead['id']} | {lead['source']} | {lead['stage']} | {lead['intent_score']} | "
            f"{', '.join(lead.get('pain_points', []))} | {lead['next_best_action']} |\n"
        )

    trial_followup = """# Trial Follow-up Plan

| Lead ID | Activated | Days Since Signup | Used Features | Next Follow-up | Goal |
|---|---|---:|---|---|---|
"""
    for trial in trials:
        trial_followup += (
            f"| {trial['lead_id']} | {trial['activated']} | {trial['days_since_signup']} | "
            f"{', '.join(trial.get('used_features', []))} | {trial['recommended_followup_day']} | "
            f"{trial['recommended_goal']} |\n"
        )

    sales_conversion = """# Sales Conversion Plan

## High Intent Leads

"""
    hot_leads = [lead for lead in leads if lead.get("stage") == "hot" or lead.get("intent_score", 0) >= 85]
    if hot_leads:
        for lead in hot_leads:
            sales_conversion += (
                f"- {lead['id']} / {lead['name']} / 来源={lead['source']} / "
                f"成交理由=高意向或已询问正式版 / 推荐动作={lead['next_best_action']}\n"
            )
    else:
        sales_conversion += "- 当前没有高意向线索，需要优先提升试用激活。\n"

    crm_dashboard = f"""# CRM Dashboard

## This Week Overview

- 新增线索：{len(leads)}
- 试用用户：{len([lead for lead in leads if lead.get('stage') == 'trial'])}
- 高意向用户：{len(hot_leads)}
- 已激活试用：{len([trial for trial in trials if trial.get('activated')])}

## Lead Stages

| Stage | Count |
|---|---:|
| warm | {len([lead for lead in leads if lead.get('stage') == 'warm'])} |
| trial | {len([lead for lead in leads if lead.get('stage') == 'trial'])} |
| hot | {len([lead for lead in leads if lead.get('stage') == 'hot'])} |

## This Week Todos

- 周一确认主题：{inputs['campaign_theme']}
- 周三发布公众号主文
- 周四重点跟进 trial 用户
- 周五推进 hot 用户转付费

## Risk Alerts

- 必须保留人工终审
- CTA 要统一为：关注公众号 / 关注 X / 申请试用 / 付费升级
- 优先推进高意向试用，不要只堆内容
"""

    _write_text(PROJECT_ROOT / "growth_execution_plan.md", growth_execution_plan)
    _write_text(PROJECT_ROOT / "lead_triage.md", lead_triage)
    _write_text(PROJECT_ROOT / "trial_followup_plan.md", trial_followup)
    _write_text(PROJECT_ROOT / "sales_conversion_plan.md", sales_conversion)
    _write_text(PROJECT_ROOT / "crm_dashboard.md", crm_dashboard)

    print("Demo outputs generated:")
    print("- growth_execution_plan.md")
    print("- lead_triage.md")
    print("- trial_followup_plan.md")
    print("- sales_conversion_plan.md")
    print("- crm_dashboard.md")

def run():
    """
    Run the crew.
    """
    inputs = load_inputs()

    try:
        StockStrategyGrowthCrew().crew().kickoff(inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")


def train():
    """
    Train the crew for a given number of iterations.
    """
    inputs = load_inputs()
    try:
        StockStrategyGrowthCrew().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")

def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        StockStrategyGrowthCrew().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")

def test():
    """
    Test the crew execution and returns the results.
    """
    inputs = load_inputs()

    try:
        StockStrategyGrowthCrew().crew().test(n_iterations=int(sys.argv[1]), eval_llm=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")

def run_with_trigger():
    """
    Run the crew with trigger payload.
    """
    if len(sys.argv) < 2:
        raise Exception("No trigger payload provided. Please provide JSON payload as argument.")

    try:
        trigger_payload = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        raise Exception("Invalid JSON payload provided as argument")

    inputs = load_inputs()
    inputs["crewai_trigger_payload"] = trigger_payload
    inputs.update({
        "product_name": trigger_payload.get("product_name", inputs["product_name"]),
        "product_summary": trigger_payload.get("product_summary", inputs["product_summary"]),
        "target_audience": trigger_payload.get("target_audience", inputs["target_audience"]),
        "channels": trigger_payload.get("channels", inputs["channels"]),
        "brand_tone": trigger_payload.get("brand_tone", inputs["brand_tone"]),
        "primary_cta": trigger_payload.get("primary_cta", inputs["primary_cta"]),
        "campaign_theme": trigger_payload.get("campaign_theme", inputs["campaign_theme"]),
    })

    try:
        result = StockStrategyGrowthCrew().crew().kickoff(inputs=inputs)
        return result
    except Exception as e:
        raise Exception(f"An error occurred while running the crew with trigger: {e}")
