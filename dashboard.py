#!/usr/bin/env python3
from __future__ import annotations

import html
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent

SECTIONS = [
    ("CEO看板", "crm_dashboard.md"),
    ("增长计划", "growth_execution_plan.md"),
    ("线索分层", "lead_triage.md"),
    ("试用跟进", "trial_followup_plan.md"),
    ("成交推进", "sales_conversion_plan.md"),
]


def read_text(path: Path) -> str:
    if not path.exists():
        return f"Missing file: {path.name}"
    return path.read_text(encoding="utf-8")


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def stage_label(stage: str) -> str:
    labels = {
        "cold": "冷线索",
        "warm": "温线索",
        "trial": "试用中",
        "hot": "高意向",
        "paid": "已付费",
    }
    return labels.get(stage, stage or "未知")


def build_html() -> str:
    panels = []
    nav = []
    leads = read_json(PROJECT_ROOT / "examples" / "lead_pipeline.json").get("leads", [])
    trials = read_json(PROJECT_ROOT / "examples" / "trial_activity.json").get("trials", [])
    hot_leads = [x for x in leads if x.get("stage") == "hot"]
    warm_leads = [x for x in leads if x.get("stage") == "warm"]
    trial_leads = [x for x in leads if x.get("stage") == "trial"]
    activated_trials = [x for x in trials if x.get("activated")]
    summary_cards = [
        ("活跃线索", str(len(leads)), "来自内容与渠道承接"),
        ("试用用户", str(len(trial_leads)), "进入试用流程"),
        ("高意向", str(len(hot_leads)), "优先推进成交"),
        ("已激活试用", str(len(activated_trials)), "已体验核心功能"),
    ]
    priorities = [
        "优先跟进 `hot` 线索，推进正式版成交",
        "督促 `trial` 用户先体验教练指令和持仓诊断",
        "把高表现内容 CTA 统一到公众号关注和试用申请",
    ]
    risk_items = [
        "不要只有内容曝光，没有试用承接",
        "不要让试用用户停留在未激活状态",
        "不要让高意向用户无人跟进超过 24 小时",
    ]
    funnel_max = max(len(leads), 1)
    funnel_rows = [
        ("关注/线索", len(leads)),
        ("试用", len(trial_leads)),
        ("激活", len(activated_trials)),
        ("高意向", len(hot_leads)),
    ]
    source_rows = []
    source_counts = {}
    for lead in leads:
        source = lead.get("source", "未知来源")
        source_counts[source] = source_counts.get(source, 0) + 1
    source_max = max(source_counts.values(), default=1)
    for source, count in sorted(source_counts.items(), key=lambda item: (-item[1], item[0])):
        source_rows.append(
            f'<div class="source-row"><div class="source-line"><span>{html.escape(source)}</span><strong>{count}</strong></div><div class="mini-bar"><span style="width:{max(int((count / source_max) * 100), 12)}%"></span></div></div>'
        )
    stage_order = ["all", "hot", "trial", "warm", "cold", "paid"]
    stage_counts = {"all": len(leads)}
    for lead in leads:
        stage = lead.get("stage", "cold")
        stage_counts[stage] = stage_counts.get(stage, 0) + 1
    stage_filters = []
    for stage in stage_order:
        label = "全部" if stage == "all" else stage_label(stage)
        count = stage_counts.get(stage, 0)
        active = "active" if stage == "all" else ""
        stage_filters.append(
            f'<button class="filter-chip {active}" data-stage="{html.escape(stage)}">{html.escape(label)} <span>{count}</span></button>'
        )
    trend_rows = [
        ("公域触达", len(leads), "内容曝光后进入线索池"),
        ("提交试用", len(trial_leads), "对产品有明确兴趣"),
        ("试用激活", len(activated_trials), "已经开始体验关键功能"),
        ("询价/成交推进", len(hot_leads), "适合销售优先跟进"),
    ]

    lead_rows = []
    for lead in leads:
        stage = lead.get("stage", "")
        lead_rows.append(
            f"""
            <tr data-stage="{html.escape(stage)}">
              <td><strong>{html.escape(lead.get("name", "-"))}</strong><br><small>{html.escape(lead.get("id", "-"))}</small></td>
              <td>{html.escape(lead.get("source", "-"))}</td>
              <td><span class="badge stage-{html.escape(stage)}">{html.escape(stage_label(stage))}</span></td>
              <td>{html.escape(str(lead.get("intent_score", "-")))}</td>
              <td>{html.escape(lead.get("next_best_action", "-"))}</td>
            </tr>
            """
        )

    lead_lookup = {lead.get("id"): lead for lead in leads}
    trial_cards = []
    for trial in trials:
        lead = lead_lookup.get(trial.get("lead_id"), {})
        features = ", ".join(trial.get("used_features", [])) or "暂无"
        risks = "；".join(trial.get("risk_signals", [])) or "暂无明显风险"
        trial_cards.append(
            f"""
            <article class="trial-card">
              <div class="trial-head">
                <div>
                  <strong>{html.escape(lead.get("name", trial.get("lead_id", "-")))}</strong>
                  <small>{html.escape(lead.get("source", "未知来源"))}</small>
                </div>
                <span class="badge {'is-on' if trial.get('activated') else 'is-off'}">{'已激活' if trial.get('activated') else '未激活'}</span>
              </div>
              <div class="trial-meta">注册 {html.escape(str(trial.get("days_since_signup", "-")))} 天 | 跟进节点 {html.escape(trial.get("recommended_followup_day", "-"))}</div>
              <div class="trial-block"><b>已使用功能</b><span>{html.escape(features)}</span></div>
              <div class="trial-block"><b>当前风险</b><span>{html.escape(risks)}</span></div>
              <div class="trial-block"><b>建议动作</b><span>{html.escape(trial.get("recommended_goal", "-"))}</span></div>
            </article>
            """
        )

    for idx, (label, filename) in enumerate(SECTIONS):
        active = "active" if idx == 0 else ""
        safe = html.escape(read_text(PROJECT_ROOT / filename))
        nav.append(
            f"""
            <button class="tab {active}" data-panel="panel-{idx}">
              <span class="tab-kicker">模块 {idx + 1}</span>
              <strong>{html.escape(label)}</strong>
              <small>{html.escape(filename)}</small>
            </button>
            """
        )
        panels.append(
            f"""
            <section id="panel-{idx}" class="panel {active}">
              <div class="panel-header">
                <h2>{html.escape(label)}</h2>
                <span>{html.escape(filename)}</span>
              </div>
              <pre>{safe}</pre>
            </section>
            """
        )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>机器人公司 Dashboard</title>
  <style>
    :root {{
      --bg: #f4f1ea;
      --panel: #fffdf8;
      --panel-2: #f8f5ee;
      --text: #161616;
      --muted: #6a655f;
      --line: #ddd5ca;
      --accent: #184e3b;
      --accent-2: #d8eadf;
      --accent-3: #eef6f2;
      --shadow: 0 18px 50px rgba(26, 28, 24, .08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "PingFang SC", "Noto Sans CJK SC", sans-serif;
      background:
        radial-gradient(circle at top left, #efe6da 0, transparent 28%),
        radial-gradient(circle at top right, #ddeee6 0, transparent 26%),
        var(--bg);
      color: var(--text);
    }}
    .shell {{
      min-height: 100vh;
      display: grid;
      grid-template-columns: 300px minmax(0, 1fr);
    }}
    .sidebar {{
      padding: 22px 18px;
      border-right: 1px solid var(--line);
      background: linear-gradient(180deg, rgba(255,253,248,.98), rgba(248,245,238,.96));
      position: sticky;
      top: 0;
      height: 100vh;
      overflow: auto;
    }}
    .brand {{
      background: linear-gradient(135deg, #153e30, #26624b);
      color: white;
      border-radius: 22px;
      padding: 20px;
      margin-bottom: 16px;
      box-shadow: var(--shadow);
    }}
    .brand h1 {{
      margin: 0 0 8px;
      font-size: 28px;
      line-height: 1.02;
      letter-spacing: -.04em;
    }}
    .brand p {{
      margin: 0;
      color: rgba(255,255,255,.82);
      line-height: 1.6;
      font-size: 13px;
    }}
    .sidebar-meta {{
      display: grid;
      gap: 10px;
      margin-bottom: 18px;
    }}
    .meta-card {{
      background: rgba(255,255,255,.72);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 12px 14px;
    }}
    .meta-card b {{
      display: block;
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 4px;
    }}
    .meta-card span {{
      font-size: 14px;
      font-weight: 700;
    }}
    .main {{
      padding: 26px 22px 34px;
    }}
    .topbar {{
      display: flex;
      align-items: end;
      justify-content: space-between;
      gap: 18px;
      margin-bottom: 18px;
    }}
    .topbar h2 {{
      margin: 0 0 8px;
      font-size: 34px;
      letter-spacing: -.04em;
    }}
    .topbar p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.65;
      font-size: 14px;
    }}
    .card {{
      background: rgba(255,253,248,.88);
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 20px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(6px);
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0,1fr));
      gap: 12px;
      margin-bottom: 18px;
    }}
    .overview {{
      display: grid;
      grid-template-columns: 1.15fr .85fr;
      gap: 14px;
      margin-bottom: 18px;
    }}
    .grid-2 {{
      display: grid;
      grid-template-columns: 1.1fr .9fr;
      gap: 14px;
      margin-bottom: 18px;
    }}
    .stack {{
      display: grid;
      gap: 14px;
    }}
    .stat {{
      background: linear-gradient(180deg, rgba(255,255,255,.96), rgba(248,245,238,.9));
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 14px;
    }}
    .stat b {{
      display: block;
      font-size: 13px;
      color: var(--muted);
      margin-bottom: 6px;
    }}
    .stat span {{
      font-size: 24px;
      font-weight: 700;
      display: block;
      margin-bottom: 4px;
    }}
    .stat small {{
      color: var(--muted);
      font-size: 12px;
    }}
    .tabs {{
      display: grid;
      gap: 10px;
    }}
    .tab {{
      border: 1px solid var(--line);
      background: rgba(255,255,255,.7);
      color: var(--text);
      padding: 12px 14px;
      border-radius: 18px;
      cursor: pointer;
      text-align: left;
      display: grid;
      gap: 4px;
    }}
    .tab.active {{
      background: var(--accent-3);
      color: var(--text);
      border-color: #b8d7c9;
      box-shadow: inset 0 0 0 1px rgba(24,78,59,.12);
    }}
    .tab-kicker {{
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: .08em;
    }}
    .tab strong {{
      font-size: 15px;
    }}
    .tab small {{
      color: var(--muted);
      font-size: 12px;
    }}
    .panel {{
      display: none;
      background: rgba(255,253,248,.92);
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 18px;
      min-height: 65vh;
    }}
    .panel.active {{ display: block; }}
    .panel-grid {{
      display: grid;
      grid-template-columns: 1.05fr .95fr;
      gap: 14px;
      margin-bottom: 18px;
    }}
    .panel-header {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: baseline;
      margin-bottom: 12px;
    }}
    .panel-header h2 {{
      margin: 0;
      font-size: 22px;
    }}
    .panel-header span {{
      color: var(--muted);
      font-size: 12px;
    }}
    pre {{
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      line-height: 1.6;
      font-size: 13px;
      background: white;
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 16px;
      max-height: 70vh;
      overflow: auto;
    }}
    .mini-title {{
      margin: 0 0 10px;
      font-size: 18px;
    }}
    .bullets {{
      display: grid;
      gap: 10px;
    }}
    .bullet {{
      background: white;
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px 13px;
      font-size: 14px;
      line-height: 1.55;
    }}
    .funnel {{
      display: grid;
      gap: 10px;
    }}
    .funnel-row {{
      background: white;
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 12px;
    }}
    .funnel-label {{
      display: flex;
      justify-content: space-between;
      font-size: 13px;
      color: var(--muted);
      margin-bottom: 8px;
    }}
    .bar {{
      height: 12px;
      border-radius: 999px;
      background: #efe8dc;
      overflow: hidden;
    }}
    .bar > span {{
      display: block;
      height: 100%;
      border-radius: 999px;
      background: linear-gradient(90deg, #184e3b, #4b8b6f);
    }}
    .mini-bar {{
      height: 8px;
      border-radius: 999px;
      background: #efe8dc;
      overflow: hidden;
    }}
    .mini-bar > span {{
      display: block;
      height: 100%;
      border-radius: 999px;
      background: linear-gradient(90deg, #3e6b58, #79a58e);
    }}
    .source-grid {{
      display: grid;
      gap: 10px;
    }}
    .source-row {{
      background: white;
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px;
    }}
    .source-line {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 8px;
      font-size: 14px;
    }}
    .filters {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-bottom: 12px;
    }}
    .filter-chip {{
      border: 1px solid var(--line);
      background: white;
      color: var(--text);
      border-radius: 999px;
      padding: 8px 12px;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
    }}
    .filter-chip span {{
      color: var(--muted);
      margin-left: 4px;
      font-weight: 600;
    }}
    .filter-chip.active {{
      background: var(--accent-3);
      border-color: #b8d7c9;
      color: var(--accent);
    }}
    .table-wrap {{
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 16px;
      background: white;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 620px;
    }}
    th, td {{
      text-align: left;
      padding: 12px 14px;
      border-bottom: 1px solid #ebe3d8;
      vertical-align: top;
      font-size: 14px;
      line-height: 1.5;
    }}
    th {{
      font-size: 12px;
      letter-spacing: .04em;
      text-transform: uppercase;
      color: var(--muted);
      background: #fcfaf5;
      position: sticky;
      top: 0;
    }}
    td small {{
      color: var(--muted);
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 4px 10px;
      font-size: 12px;
      font-weight: 700;
      border: 1px solid transparent;
      white-space: nowrap;
    }}
    .stage-hot {{
      background: #fff1ea;
      color: #9c3c14;
      border-color: #f3cfbf;
    }}
    .stage-warm {{
      background: #fff8e7;
      color: #8a6400;
      border-color: #ead9a3;
    }}
    .stage-trial {{
      background: #eef6ff;
      color: #16508f;
      border-color: #c8daf4;
    }}
    .stage-cold {{
      background: #f2f3f5;
      color: #5f6470;
      border-color: #d9dce2;
    }}
    .stage-paid {{
      background: #edf8f2;
      color: #176042;
      border-color: #c3e2d2;
    }}
    .is-on {{
      background: #edf8f2;
      color: #176042;
      border-color: #c3e2d2;
    }}
    .is-off {{
      background: #f2f3f5;
      color: #5f6470;
      border-color: #d9dce2;
    }}
    .risk-card {{
      background: linear-gradient(180deg, #fff8f4, #fffdf9);
      border: 1px solid #ecd4c4;
    }}
    .trial-list {{
      display: grid;
      gap: 12px;
    }}
    .trial-card {{
      background: white;
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 14px;
    }}
    .trial-head {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: start;
      margin-bottom: 8px;
    }}
    .trial-head strong {{
      display: block;
      font-size: 15px;
      margin-bottom: 2px;
    }}
    .trial-head small,
    .trial-meta {{
      color: var(--muted);
      font-size: 12px;
    }}
    .trial-meta {{
      margin-bottom: 12px;
    }}
    .trial-block {{
      display: grid;
      gap: 4px;
      margin-top: 10px;
    }}
    .trial-block b {{
      font-size: 12px;
      color: var(--muted);
    }}
    .trial-block span {{
      font-size: 14px;
      line-height: 1.55;
    }}
    .trend-grid {{
      display: grid;
      gap: 10px;
    }}
    .trend-row {{
      display: grid;
      grid-template-columns: 128px 1fr;
      gap: 12px;
      align-items: center;
    }}
    .trend-label {{
      font-size: 13px;
      color: var(--muted);
      line-height: 1.4;
    }}
    .trend-card {{
      background: white;
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px 14px;
    }}
    .trend-card strong {{
      display: block;
      font-size: 20px;
      margin-bottom: 4px;
    }}
    .trend-card small {{
      color: var(--muted);
      font-size: 12px;
      line-height: 1.5;
    }}
    .note {{
      margin-top: 16px;
      padding: 14px 16px;
      border-radius: 16px;
      background: var(--accent-2);
      color: #16382b;
      font-size: 14px;
      line-height: 1.6;
      border: 1px solid #bdd8c8;
    }}
    @media (max-width: 900px) {{
      .shell {{ grid-template-columns: 1fr; }}
      .sidebar {{ position: static; height: auto; border-right: 0; border-bottom: 1px solid var(--line); }}
      .stats {{ grid-template-columns: 1fr 1fr; }}
      .overview {{ grid-template-columns: 1fr; }}
      .grid-2 {{ grid-template-columns: 1fr; }}
      .panel-grid {{ grid-template-columns: 1fr; }}
      .topbar {{ flex-direction: column; align-items: stretch; }}
      .topbar h2 {{ font-size: 28px; }}
    }}
    @media (max-width: 640px) {{
      .main {{ padding: 18px 14px 28px; }}
      .stats {{ grid-template-columns: 1fr; }}
      .brand h1 {{ font-size: 24px; }}
      .tab {{ border-radius: 14px; }}
      .card, .panel {{ padding: 16px; }}
      .tabs {{
        grid-auto-flow: column;
        grid-auto-columns: 220px;
        overflow: auto;
      }}
      .trend-row {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <aside class="sidebar">
      <section class="brand">
        <h1>Robot Company</h1>
        <p>面向 A 股散户的内容增长、试用转化与付费推进后台。</p>
      </section>
      <section class="sidebar-meta">
        <div class="meta-card"><b>公司类型</b><span>内容 + 销售机器人公司</span></div>
        <div class="meta-card"><b>目标用户</b><span>A股散户</span></div>
        <div class="meta-card"><b>主转化路径</b><span>关注 -> 试用 -> 付费</span></div>
        <div class="meta-card"><b>当前模式</b><span>本地 Demo</span></div>
      </section>
      <nav class="tabs">
        {''.join(nav)}
      </nav>
    </aside>

    <main class="main">
      <section class="topbar">
        <div>
          <h2>运营驾驶台</h2>
          <p>你现在看到的是这家机器人公司一次 demo run 的后台结果。左侧切换模块，右侧查看本周运营、线索、试用与成交推进。</p>
        </div>
        <div class="card">
          <strong>刷新方式</strong><br>
          <span style="color:var(--muted);font-size:13px;line-height:1.6;">重新运行 demo，然后刷新这个页面即可。</span>
        </div>
      </section>

      <section class="stats">
        {''.join(f'<div class="stat"><b>{html.escape(title)}</b><span>{html.escape(value)}</span><small>{html.escape(desc)}</small></div>' for title, value, desc in summary_cards)}
      </section>

      <section class="overview">
        <div class="card">
          <h3 class="mini-title">本周优先任务</h3>
          <div class="bullets">
            {''.join(f'<div class="bullet">{html.escape(item)}</div>' for item in priorities)}
          </div>
        </div>
        <div class="stack">
          <div class="card">
            <h3 class="mini-title">用户漏斗</h3>
            <div class="funnel">
              {''.join(f'<div class="funnel-row"><div class="funnel-label"><span>{html.escape(label)}</span><strong>{value}</strong></div><div class="bar"><span style="width:{max(int((value / funnel_max) * 100), 8)}%"></span></div></div>' for label, value in funnel_rows)}
            </div>
          </div>
          <div class="card risk-card">
            <h3 class="mini-title">风险提醒</h3>
            <div class="bullets">
              {''.join(f'<div class="bullet">{html.escape(item)}</div>' for item in risk_items)}
            </div>
          </div>
        </div>
      </section>

      <section class="grid-2">
        <div class="card">
          <h3 class="mini-title">线索来源分布</h3>
          <div class="source-grid">
            {''.join(source_rows)}
          </div>
        </div>
        <div class="card">
          <h3 class="mini-title">转化趋势概览</h3>
          <div class="trend-grid">
            {''.join(f'<div class="trend-row"><div class="trend-label">{html.escape(label)}</div><div class="trend-card"><strong>{value}</strong><small>{html.escape(desc)}</small></div></div>' for label, value, desc in trend_rows)}
          </div>
        </div>
      </section>

      <section class="panel-grid">
        <div class="card">
          <div class="panel-header">
            <h2>CRM 线索池</h2>
            <span>按意向与下一步动作查看</span>
          </div>
          <div class="filters">
            {''.join(stage_filters)}
          </div>
          <div class="table-wrap">
            <table id="lead-table">
              <thead>
                <tr>
                  <th>线索</th>
                  <th>来源</th>
                  <th>阶段</th>
                  <th>意向分</th>
                  <th>下一步动作</th>
                </tr>
              </thead>
              <tbody>
                {''.join(lead_rows)}
              </tbody>
            </table>
          </div>
        </div>
        <div class="card">
          <h3 class="mini-title">试用状态概览</h3>
          <div class="trial-list">
            {''.join(trial_cards) if trial_cards else '<div class="bullet">当前没有试用记录。</div>'}
          </div>
        </div>
      </section>

      <section class="panel-grid">
        <div class="card">
          <h3 class="mini-title">操作提示</h3>
          <div class="bullets">
            <div class="bullet">点击左侧模块，可以看这家公司每个部门当前产出的详细 markdown 内容。</div>
            <div class="bullet">阶段筛选按钮适合老板或销售负责人快速锁定今天该跟进的那一批人。</div>
            <div class="bullet">如果你后面接真实表单或 CRM，只要替换 `examples/*.json`，这个界面就能继续复用。</div>
          </div>
        </div>
        <div class="card">
          <h3 class="mini-title">下一步可接入</h3>
          <div class="bullets">
            <div class="bullet">真实表单申请数据：把试用申请直接写入线索池。</div>
            <div class="bullet">真实用户行为：把登录、功能使用、复购意向同步到试用状态。</div>
            <div class="bullet">自动刷新：让老板打开页面就能看到最新状态，而不是手动重跑。</div>
          </div>
        </div>
      </section>

      {''.join(panels)}

      <div class="note">
        下一步如果要更像真正 SaaS，可以继续接：真实表单线索、真实试用行为、自动刷新和用户状态筛选。
      </div>
    </main>
  </div>

  <script>
    const tabs = [...document.querySelectorAll('.tab')];
    const panels = [...document.querySelectorAll('.panel')];
    tabs.forEach(tab => {{
      tab.addEventListener('click', () => {{
        tabs.forEach(x => x.classList.remove('active'));
        panels.forEach(x => x.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById(tab.dataset.panel).classList.add('active');
      }});
    }});

    const chips = [...document.querySelectorAll('.filter-chip')];
    const leadRows = [...document.querySelectorAll('#lead-table tbody tr')];
    chips.forEach(chip => {{
      chip.addEventListener('click', () => {{
        chips.forEach(x => x.classList.remove('active'));
        chip.classList.add('active');
        const stage = chip.dataset.stage;
        leadRows.forEach(row => {{
          row.style.display = stage === 'all' || row.dataset.stage === stage ? '' : 'none';
        }});
      }});
    }});
  </script>
</body>
</html>"""


def main() -> None:
    output = PROJECT_ROOT / "dashboard.html"
    output.write_text(build_html(), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
