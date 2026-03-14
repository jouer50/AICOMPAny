from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


PROJECT_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES_DIR = PROJECT_ROOT / "examples"


def _load_json(filename: str) -> Any:
    path = EXAMPLES_DIR / filename
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


class TrendSignalToolInput(BaseModel):
    """Input schema for TrendSignalTool."""

    channel: str = Field(default="all", description="渠道名，例如 X、小红书、微信公众号、雪球，或 all。")
    theme: str = Field(default="", description="主题关键词，例如 交易纪律、复盘、风控。")


class TrendSignalTool(BaseTool):
    name: str = "trend_signal_tool"
    description: str = (
        "读取本地 market_signals.json，返回当前值得关注的热点信号，"
        "适合用来生成选题、栏目和发布时间建议。"
    )
    args_schema: Type[BaseModel] = TrendSignalToolInput

    def _run(self, channel: str = "all", theme: str = "") -> str:
        data = _load_json("market_signals.json")
        entries = data.get("signals", [])
        filtered = []
        channel_lower = channel.lower()
        theme_lower = theme.lower()

        for entry in entries:
            channels = [item.lower() for item in entry.get("channels", [])]
            themes = [item.lower() for item in entry.get("themes", [])]
            if channel_lower != "all" and channel_lower not in channels:
                continue
            if theme_lower and theme_lower not in themes and theme_lower not in entry.get(
                "summary", ""
            ).lower():
                continue
            filtered.append(entry)

        if not filtered:
            return "未找到匹配的热点信号，请先更新 examples/market_signals.json。"

        lines = ["可用热点信号："]
        for item in filtered:
            lines.append(
                f"- [{item.get('priority', 'P2')}] {item.get('title')} | "
                f"渠道: {', '.join(item.get('channels', []))} | "
                f"主题: {', '.join(item.get('themes', []))} | "
                f"建议角度: {item.get('summary')}"
            )
        return "\n".join(lines)


class CompetitorSnapshotToolInput(BaseModel):
    """Input schema for CompetitorSnapshotTool."""

    competitor: str = Field(default="all", description="竞品名称，或 all 查看全部。")


class CompetitorSnapshotTool(BaseTool):
    name: str = "competitor_snapshot_tool"
    description: str = (
        "读取本地 competitor_snapshots.json，返回竞品定位、内容打法和可借鉴点，"
        "适合用来做差异化定位与选题对比。"
    )
    args_schema: Type[BaseModel] = CompetitorSnapshotToolInput

    def _run(self, competitor: str = "all") -> str:
        data = _load_json("competitor_snapshots.json")
        entries = data.get("competitors", [])
        competitor_lower = competitor.lower()

        if competitor_lower != "all":
            entries = [item for item in entries if item.get("name", "").lower() == competitor_lower]

        if not entries:
            return "未找到匹配的竞品信息，请先更新 examples/competitor_snapshots.json。"

        lines = ["可用竞品快照："]
        for item in entries:
            lines.append(
                f"- {item.get('name')}: 定位={item.get('positioning')} | "
                f"强项={'; '.join(item.get('strengths', []))} | "
                f"常见内容={'; '.join(item.get('content_patterns', []))} | "
                f"可借鉴={'; '.join(item.get('takeaways', []))}"
            )
        return "\n".join(lines)


class LeadPipelineToolInput(BaseModel):
    """Input schema for LeadPipelineTool."""

    stage: str = Field(default="all", description="线索阶段，如 warm、trial、hot 或 all。")


class LeadPipelineTool(BaseTool):
    name: str = "lead_pipeline_tool"
    description: str = (
        "读取本地 lead_pipeline.json，返回线索池和下一步动作，"
        "适合安排试用承接和销售推进。"
    )
    args_schema: Type[BaseModel] = LeadPipelineToolInput

    def _run(self, stage: str = "all") -> str:
        data = _load_json("lead_pipeline.json")
        leads = data.get("leads", [])
        stage_lower = stage.lower()
        if stage_lower != "all":
            leads = [item for item in leads if str(item.get("stage", "")).lower() == stage_lower]
        if not leads:
            return "未找到匹配的线索，请先更新 examples/lead_pipeline.json。"

        lines = ["当前线索池："]
        for item in leads:
            lines.append(
                f"- {item.get('id')} | 来源={item.get('source')} | 阶段={item.get('stage')} | "
                f"意向分={item.get('intent_score')} | 痛点={', '.join(item.get('pain_points', []))} | "
                f"下一步={item.get('next_best_action')}"
            )
        return "\n".join(lines)


class TrialActivityToolInput(BaseModel):
    """Input schema for TrialActivityTool."""

    lead_id: str = Field(default="all", description="线索 ID，或 all 查看全部试用活动。")


class TrialActivityTool(BaseTool):
    name: str = "trial_activity_tool"
    description: str = (
        "读取本地 trial_activity.json，返回试用用户激活情况和建议跟进动作，"
        "适合试用成功经理和成交经理使用。"
    )
    args_schema: Type[BaseModel] = TrialActivityToolInput

    def _run(self, lead_id: str = "all") -> str:
        data = _load_json("trial_activity.json")
        trials = data.get("trials", [])
        lead_id_lower = lead_id.lower()
        if lead_id_lower != "all":
            trials = [item for item in trials if str(item.get("lead_id", "")).lower() == lead_id_lower]
        if not trials:
            return "未找到匹配的试用活动，请先更新 examples/trial_activity.json。"

        lines = ["当前试用活动："]
        for item in trials:
            lines.append(
                f"- {item.get('lead_id')} | 激活={item.get('activated')} | "
                f"注册天数={item.get('days_since_signup')} | "
                f"已用功能={', '.join(item.get('used_features', []))} | "
                f"建议跟进={item.get('recommended_followup_day')} / {item.get('recommended_goal')}"
            )
        return "\n".join(lines)
