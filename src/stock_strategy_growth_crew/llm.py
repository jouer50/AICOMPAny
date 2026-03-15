from __future__ import annotations

import json
from urllib import error, request

from stock_strategy_growth_crew.settings import settings


DEFAULT_OWNER_BY_CHANNEL = {
    "X": "x_editor",
    "小红书": "xiaohongshu_editor",
    "微信公众号": "wechat_editor",
    "雪球": "xueqiu_editor",
}
VALID_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def llm_is_configured() -> bool:
    return bool(settings.llm_api_key.strip())


def get_llm_status() -> dict:
    return {
        "configured": llm_is_configured(),
        "provider": settings.llm_provider,
        "model": settings.llm_model,
        "base_url": settings.llm_base_url,
    }


def _extract_message_content(payload: dict) -> str:
    choices = payload.get("choices") or []
    if not choices:
        raise ValueError("LLM response does not contain choices")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(item.get("text", "") for item in content if isinstance(item, dict))
    raise ValueError("LLM response content is empty")


def _extract_json_block(text: str) -> str:
    text = text.strip()
    fenced_start = text.find("```json")
    if fenced_start != -1:
        fenced_end = text.find("```", fenced_start + 7)
        if fenced_end != -1:
            return text[fenced_start + 7 : fenced_end].strip()

    for opening, closing in (("[", "]"), ("{", "}")):
        start = text.find(opening)
        end = text.rfind(closing)
        if start != -1 and end != -1 and end > start:
            return text[start : end + 1]
    raise ValueError("No JSON payload found in LLM response")


def _normalize_tasks(raw_tasks: list[dict], cta: str) -> list[dict]:
    normalized = []
    for index, raw in enumerate(raw_tasks[:7]):
        channel = str(raw.get("channel", "")).strip() or "X"
        scheduled_day = str(raw.get("scheduled_day", "")).strip() or VALID_DAYS[index % len(VALID_DAYS)]
        if scheduled_day not in VALID_DAYS:
            scheduled_day = VALID_DAYS[index % len(VALID_DAYS)]
        normalized.append(
            {
                "scheduled_day": scheduled_day,
                "channel": channel,
                "title": str(raw.get("title", "")).strip() or f"{channel} 内容计划 {index + 1}",
                "owner": str(raw.get("owner", "")).strip() or DEFAULT_OWNER_BY_CHANNEL.get(channel, "ops_analyst"),
                "cta": str(raw.get("cta", "")).strip() or cta,
                "status": "planned",
            }
        )
    if not normalized:
        raise ValueError("LLM returned no usable content tasks")
    return normalized


def generate_weekly_content_plan_with_llm(brief: dict) -> list[dict]:
    if not llm_is_configured():
        raise RuntimeError("LLM is not configured")

    cta = brief.get("primary_cta", "申请试用")
    payload = {
        "model": settings.llm_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是一个中文增长运营总监。请为 A 股散户交易教练产品输出一周内容计划。"
                    "严格返回 JSON，不要解释。输出必须是对象，包含 tasks 数组。"
                    "tasks 中每项必须包含 scheduled_day, channel, title, owner, cta。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "brief": brief,
                        "channels": ["X", "小红书", "微信公众号", "雪球"],
                        "days": VALID_DAYS,
                        "requirements": [
                            "只输出 7 条任务",
                            "避免荐股、收益承诺、老师带单",
                            "突出纪律、执行边界、持仓诊断、行为纠偏",
                            "CTA 聚焦关注公众号/X、申请试用、转付费",
                        ],
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        "temperature": 0.6,
        "response_format": {"type": "json_object"},
    }
    req = request.Request(
        url=f"{settings.llm_base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.llm_api_key}",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=settings.llm_timeout_seconds) as response:
            raw_response = response.read().decode("utf-8")
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"LLM HTTP {exc.code}: {body[:300]}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"LLM connection failed: {exc.reason}") from exc

    payload_json = json.loads(raw_response)
    message_content = _extract_message_content(payload_json)
    parsed = json.loads(_extract_json_block(message_content))
    tasks = parsed.get("tasks") if isinstance(parsed, dict) else parsed
    if not isinstance(tasks, list):
        raise ValueError("LLM response tasks is not a list")
    return _normalize_tasks(tasks, cta)
