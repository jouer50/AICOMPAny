from __future__ import annotations

import json
import secrets
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from stock_strategy_growth_crew.bootstrap import PROJECT_ROOT, initialize_database, seed_demo_data
from stock_strategy_growth_crew.db import SessionLocal, get_db
from stock_strategy_growth_crew.main import demo_run
from stock_strategy_growth_crew.models import ContentTask, Lead, TrialActivity
from stock_strategy_growth_crew.schemas import (
    AutomationJobRead,
    ContentTaskRead,
    ContentTaskUpdate,
    DashboardPayload,
    DashboardSummary,
    LeadCreate,
    LeadRead,
    LeadUpdate,
    TrialActivityCreate,
    TrialActivityRead,
)
from stock_strategy_growth_crew.settings import settings
from stock_strategy_growth_crew.worker import (
    celery_app,
    generate_trial_followup_task,
    generate_weekly_content_plan_task,
    triage_leads_task,
)


DASHBOARD_PATH = PROJECT_ROOT / "dashboard.html"
DASHBOARD_SCRIPT = PROJECT_ROOT / "dashboard.py"

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


def build_live_app_html() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Robot Company App</title>
  <style>
    :root {
      --bg: #f4f1ea;
      --panel: #fffdf8;
      --text: #161616;
      --muted: #6a655f;
      --line: #ddd5ca;
      --accent: #184e3b;
      --accent-2: #eef6f2;
      --shadow: 0 18px 50px rgba(26, 28, 24, .08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "PingFang SC", "Noto Sans CJK SC", sans-serif;
      background:
        radial-gradient(circle at top left, #efe6da 0, transparent 28%),
        radial-gradient(circle at top right, #ddeee6 0, transparent 26%),
        var(--bg);
      color: var(--text);
    }
    .shell {
      max-width: 1320px;
      margin: 0 auto;
      padding: 28px 18px 40px;
    }
    .hero {
      display: flex;
      align-items: end;
      justify-content: space-between;
      gap: 20px;
      margin-bottom: 18px;
    }
    .hero h1 {
      margin: 0 0 8px;
      font-size: 38px;
      letter-spacing: -.04em;
    }
    .hero p {
      margin: 0;
      color: var(--muted);
      line-height: 1.7;
      font-size: 14px;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border-radius: 999px;
      padding: 10px 14px;
      background: #163c2f;
      color: white;
      box-shadow: var(--shadow);
      font-size: 13px;
      font-weight: 700;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }
    .card {
      background: rgba(255,253,248,.92);
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 18px;
      box-shadow: var(--shadow);
    }
    .metric b {
      display: block;
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 8px;
    }
    .metric span {
      display: block;
      font-size: 28px;
      font-weight: 800;
      margin-bottom: 6px;
    }
    .metric small {
      color: var(--muted);
      font-size: 12px;
    }
    .layout {
      display: grid;
      grid-template-columns: 1.2fr .8fr;
      gap: 14px;
      margin-bottom: 18px;
    }
    .section-title {
      margin: 0 0 12px;
      font-size: 19px;
    }
    .table-wrap {
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 16px;
      background: white;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      min-width: 640px;
    }
    th, td {
      text-align: left;
      padding: 12px 14px;
      border-bottom: 1px solid #ebe3d8;
      vertical-align: top;
      font-size: 14px;
      line-height: 1.5;
    }
    th {
      font-size: 12px;
      letter-spacing: .04em;
      text-transform: uppercase;
      color: var(--muted);
      background: #fcfaf5;
    }
    .pill {
      display: inline-flex;
      border-radius: 999px;
      padding: 4px 10px;
      font-size: 12px;
      font-weight: 700;
      border: 1px solid transparent;
      white-space: nowrap;
    }
    .stage-hot { background: #fff1ea; color: #9c3c14; border-color: #f3cfbf; }
    .stage-trial { background: #eef6ff; color: #16508f; border-color: #c8daf4; }
    .stage-warm { background: #fff8e7; color: #8a6400; border-color: #ead9a3; }
    .stage-cold { background: #f2f3f5; color: #5f6470; border-color: #d9dce2; }
    .stage-paid { background: #edf8f2; color: #176042; border-color: #c3e2d2; }
    .trial-list, .task-list {
      display: grid;
      gap: 12px;
    }
    .item {
      background: white;
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 14px;
    }
    .item strong {
      display: block;
      margin-bottom: 4px;
      font-size: 15px;
    }
    .item small, .muted {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.6;
    }
    .toolbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      margin-bottom: 12px;
    }
    .button {
      border: 0;
      border-radius: 999px;
      background: var(--accent);
      color: white;
      padding: 10px 14px;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
    }
    .button.secondary {
      background: #e8efe9;
      color: #173e30;
    }
    .button.small {
      padding: 8px 12px;
      font-size: 12px;
    }
    .form-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 12px;
    }
    .field {
      display: grid;
      gap: 6px;
    }
    .field label {
      font-size: 12px;
      color: var(--muted);
      font-weight: 700;
    }
    .field input, .field select {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: white;
      padding: 10px 12px;
      font-size: 14px;
      color: var(--text);
    }
    .field.wide {
      grid-column: 1 / -1;
    }
    .actions {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      align-items: center;
    }
    .empty {
      color: var(--muted);
      font-size: 14px;
    }
    .status {
      color: var(--muted);
      font-size: 13px;
    }
    .status.good {
      color: #0f5132;
    }
    .inline-row {
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
      margin-top: 10px;
    }
    .footer-note {
      margin-top: 16px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.7;
    }
    @media (max-width: 960px) {
      .grid { grid-template-columns: 1fr 1fr; }
      .layout { grid-template-columns: 1fr; }
      .hero { flex-direction: column; align-items: stretch; }
    }
    @media (max-width: 640px) {
      .grid { grid-template-columns: 1fr; }
      .shell { padding: 20px 14px 28px; }
      .hero h1 { font-size: 30px; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div>
        <h1>Robot Company App</h1>
        <p>这是生产 API 驱动页面。数据直接来自 <code>/api/v1/dashboard</code>，不再依赖预生成的 JSON 或静态 markdown。</p>
      </div>
      <div class="badge" id="env-badge">Loading...</div>
    </section>

    <section class="grid" id="metric-grid"></section>

    <section class="layout">
      <div class="card">
        <div class="toolbar">
          <h2 class="section-title">Leads</h2>
          <button class="button" id="refresh-button">Refresh</button>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Source</th>
                <th>Stage</th>
                <th>Intent</th>
                <th>Next Action</th>
              </tr>
            </thead>
            <tbody id="lead-rows"></tbody>
          </table>
        </div>
      </div>

      <div class="card">
        <h2 class="section-title">Trials</h2>
        <div class="trial-list" id="trial-list"></div>
      </div>
    </section>

    <section class="layout">
      <div class="card">
        <h2 class="section-title">Content Tasks</h2>
        <div class="task-list" id="task-list"></div>
      </div>
      <div class="card">
        <h2 class="section-title">Create Lead</h2>
        <form id="lead-form">
          <div class="form-grid">
            <div class="field">
              <label for="lead-id">Lead ID</label>
              <input id="lead-id" name="id" placeholder="lead_004" required>
            </div>
            <div class="field">
              <label for="lead-name">Name</label>
              <input id="lead-name" name="name" placeholder="A股纪律交易用户" required>
            </div>
            <div class="field">
              <label for="lead-source">Source</label>
              <input id="lead-source" name="source" placeholder="微信公众号" required>
            </div>
            <div class="field">
              <label for="lead-stage">Stage</label>
              <select id="lead-stage" name="stage">
                <option value="warm">温线索</option>
                <option value="trial">试用中</option>
                <option value="hot">高意向</option>
                <option value="cold">冷线索</option>
                <option value="paid">已付费</option>
              </select>
            </div>
            <div class="field">
              <label for="lead-intent">Intent Score</label>
              <input id="lead-intent" name="intent_score" type="number" min="0" max="100" value="70" required>
            </div>
            <div class="field wide">
              <label for="lead-next">Next Action</label>
              <input id="lead-next" name="next_best_action" placeholder="引导申请试用" required>
            </div>
          </div>
          <div class="actions">
            <button class="button" type="submit">Create Lead</button>
            <button class="button secondary" type="button" id="reload-button">Reload Dashboard</button>
            <span class="status" id="form-status">Ready</span>
          </div>
        </form>
        <div class="footer-note">
          兼容页面仍保留在 <code>/dashboard</code>。生产页面入口是 <code>/app</code>。
        </div>
      </div>
    </section>

    <section class="layout">
      <div class="card">
        <h2 class="section-title">Update Lead</h2>
        <form id="lead-update-form">
          <div class="form-grid">
            <div class="field">
              <label for="lead-update-id">Lead ID</label>
              <input id="lead-update-id" name="lead_id" placeholder="lead_001" required>
            </div>
            <div class="field">
              <label for="lead-update-stage">Stage</label>
              <select id="lead-update-stage" name="stage">
                <option value="warm">温线索</option>
                <option value="trial">试用中</option>
                <option value="hot">高意向</option>
                <option value="cold">冷线索</option>
                <option value="paid">已付费</option>
              </select>
            </div>
            <div class="field">
              <label for="lead-update-intent">Intent Score</label>
              <input id="lead-update-intent" name="intent_score" type="number" min="0" max="100" value="75" required>
            </div>
            <div class="field wide">
              <label for="lead-update-next">Next Action</label>
              <input id="lead-update-next" name="next_best_action" placeholder="推进试用转付费" required>
            </div>
          </div>
          <div class="actions">
            <button class="button" type="submit">Update Lead</button>
            <span class="status" id="lead-update-status">Ready</span>
          </div>
        </form>
      </div>
      <div class="card">
        <h2 class="section-title">Ops Notes</h2>
        <div class="item">
          <strong>Robot Actions</strong>
          <div class="muted">这里开始接入真正的机器人任务。现在有两条：生成本周内容计划，以及按试用/行为信号重排线索优先级。</div>
          <div class="actions" style="margin-top:12px;">
            <button class="button" id="plan-button" type="button">Generate Weekly Content Plan</button>
            <span class="status" id="plan-status">Ready</span>
          </div>
          <div class="actions" style="margin-top:12px;">
            <button class="button secondary" id="triage-button" type="button">Run Lead Triage</button>
            <span class="status" id="triage-status">Ready</span>
          </div>
          <div class="actions" style="margin-top:12px;">
            <button class="button secondary" id="followup-button" type="button">Generate Trial Follow-up</button>
            <span class="status" id="followup-status">Ready</span>
          </div>
        </div>
        <div class="item">
          <strong>Current Backend Scope</strong>
          <div class="muted">现在 `/app` 已经有四类真实写操作，再加上三条真正的 worker 任务：内容计划、线索分层、试用跟进。</div>
        </div>
      </div>
    </section>

    <section class="layout">
      <div class="card">
        <h2 class="section-title">Update Trial</h2>
        <form id="trial-form">
          <div class="form-grid">
            <div class="field">
              <label for="trial-lead-id">Lead ID</label>
              <input id="trial-lead-id" name="lead_id" placeholder="lead_002" required>
            </div>
            <div class="field">
              <label for="trial-day">Days Since Signup</label>
              <input id="trial-day" name="days_since_signup" type="number" min="0" value="1" required>
            </div>
            <div class="field">
              <label for="trial-followup">Follow-up Day</label>
              <input id="trial-followup" name="recommended_followup_day" placeholder="Day 3">
            </div>
            <div class="field">
              <label for="trial-activated">Activated</label>
              <select id="trial-activated" name="activated">
                <option value="true">true</option>
                <option value="false">false</option>
              </select>
            </div>
            <div class="field wide">
              <label for="trial-features">Used Features</label>
              <input id="trial-features" name="used_features" placeholder="教练指令, 执行计划">
            </div>
            <div class="field wide">
              <label for="trial-goal">Recommended Goal</label>
              <input id="trial-goal" name="recommended_goal" placeholder="引导用户体验持仓诊断">
            </div>
          </div>
          <div class="actions">
            <button class="button" type="submit">Update Trial</button>
            <span class="status" id="trial-status">Ready</span>
          </div>
        </form>
      </div>
      <div class="card">
        <h2 class="section-title">Current Mode</h2>
        <div class="item">
          <strong>Production App Direction</strong>
          <div class="muted">现在 `/app` 已经有两个真实写操作：创建 lead 和更新 trial。下一步可以继续补 content task 状态变更，再把静态 `/dashboard` 逐步淘汰。</div>
        </div>
      </div>
    </section>
  </div>

  <script>
    const stageLabel = {
      cold: '冷线索',
      warm: '温线索',
      trial: '试用中',
      hot: '高意向',
      paid: '已付费',
    };

    function pillClass(stage) {
      return `pill stage-${stage || 'cold'}`;
    }

    function metricCard(title, value, detail) {
      return `
        <article class="card metric">
          <b>${title}</b>
          <span>${value}</span>
          <small>${detail}</small>
        </article>
      `;
    }

    function renderDashboard(payload) {
      const summary = payload.summary;
      document.getElementById('env-badge').textContent = 'API Connected';

      document.getElementById('metric-grid').innerHTML = [
        metricCard('活跃线索', summary.lead_count, '当前数据库中的线索'),
        metricCard('试用用户', summary.trial_count, '当前处于 trial 阶段'),
        metricCard('高意向', summary.hot_count, '优先推进成交'),
        metricCard('内容任务', summary.content_task_count, '待执行内容排期'),
      ].join('');

      document.getElementById('lead-rows').innerHTML = payload.leads.length
        ? payload.leads.map((lead) => `
            <tr>
              <td><strong>${lead.name}</strong><br><small>${lead.id}</small></td>
              <td>${lead.source}</td>
              <td><span class="${pillClass(lead.stage)}">${stageLabel[lead.stage] || lead.stage}</span></td>
              <td>${lead.intent_score}</td>
              <td>${lead.next_best_action || ''}</td>
            </tr>
          `).join('')
        : '<tr><td colspan="5" class="empty">No leads yet.</td></tr>';

      document.getElementById('trial-list').innerHTML = payload.trials.length
        ? payload.trials.map((trial) => `
            <article class="item">
              <strong>${trial.lead_id}</strong>
              <small>Day ${trial.days_since_signup} · ${trial.recommended_followup_day || '待定'}</small>
              <div class="muted">已使用：${trial.used_features.join(' / ') || '暂无'}</div>
              <div class="muted">建议：${trial.recommended_goal || '暂无'}</div>
            </article>
          `).join('')
        : '<div class="empty">No trials yet.</div>';

      document.getElementById('task-list').innerHTML = payload.content_tasks.length
        ? payload.content_tasks.map((task) => `
            <article class="item">
              <strong>${task.title}</strong>
              <small>${task.channel} · ${task.scheduled_day || '未排期'} · ${task.status}</small>
              <div class="muted">CTA：${task.cta || '暂无'}</div>
              <div class="inline-row">
                <select data-task-status="${task.id}">
                  <option value="planned" ${task.status === 'planned' ? 'selected' : ''}>planned</option>
                  <option value="draft" ${task.status === 'draft' ? 'selected' : ''}>draft</option>
                  <option value="review" ${task.status === 'review' ? 'selected' : ''}>review</option>
                  <option value="published" ${task.status === 'published' ? 'selected' : ''}>published</option>
                </select>
                <button class="button small secondary" type="button" data-task-save="${task.id}">Update Status</button>
              </div>
            </article>
          `).join('')
        : '<div class="empty">No content tasks yet.</div>';

      document.querySelectorAll('[data-task-save]').forEach((button) => {
        button.addEventListener('click', async () => {
          const taskId = button.getAttribute('data-task-save');
          const select = document.querySelector(`[data-task-status="${taskId}"]`);
          await updateTaskStatus(taskId, select.value);
        });
      });
    }

    async function loadDashboard() {
      const response = await fetch('/api/v1/dashboard', { cache: 'no-store' });
      if (!response.ok) {
        throw new Error(`Failed to load dashboard: ${response.status}`);
      }
      const payload = await response.json();
      renderDashboard(payload);
    }

    async function refreshDemo() {
      const button = document.getElementById('refresh-button');
      button.disabled = true;
      button.textContent = 'Refreshing...';
      try {
        await fetch('/api/refresh', { method: 'POST' });
        await loadDashboard();
      } finally {
        button.disabled = false;
        button.textContent = 'Refresh';
      }
    }

    async function createLead(event) {
      event.preventDefault();
      const status = document.getElementById('form-status');
      const form = event.currentTarget;
      const payload = {
        id: form.id.value.trim(),
        name: form.name.value.trim(),
        source: form.source.value.trim(),
        stage: form.stage.value,
        intent_score: Number(form.intent_score.value || 0),
        next_best_action: form.next_best_action.value.trim(),
        pain_points: [],
        last_action: '',
      };

      status.textContent = 'Submitting...';
      const response = await fetch('/api/v1/leads', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        let detail = `Failed: ${response.status}`;
        try {
          const body = await response.json();
          detail = body.detail || detail;
        } catch (_) {
        }
        status.textContent = detail;
        return;
      }

      status.textContent = 'Lead created';
      form.reset();
      form.stage.value = 'warm';
      form.intent_score.value = '70';
      await loadDashboard();
    }

    function parseCsv(value) {
      return value
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean);
    }

    async function updateTrial(event) {
      event.preventDefault();
      const status = document.getElementById('trial-status');
      const form = event.currentTarget;
      const payload = {
        lead_id: form.lead_id.value.trim(),
        activated: form.activated.value === 'true',
        days_since_signup: Number(form.days_since_signup.value || 0),
        used_features: parseCsv(form.used_features.value),
        risk_signals: [],
        recommended_followup_day: form.recommended_followup_day.value.trim(),
        recommended_goal: form.recommended_goal.value.trim(),
      };

      status.textContent = 'Submitting...';
      const response = await fetch('/api/v1/trials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        let detail = `Failed: ${response.status}`;
        try {
          const body = await response.json();
          detail = body.detail || detail;
        } catch (_) {
        }
        status.textContent = detail;
        return;
      }

      status.textContent = 'Trial updated';
      await loadDashboard();
    }

    async function updateLead(event) {
      event.preventDefault();
      const status = document.getElementById('lead-update-status');
      const form = event.currentTarget;
      const leadId = form.lead_id.value.trim();
      const payload = {
        stage: form.stage.value,
        intent_score: Number(form.intent_score.value || 0),
        next_best_action: form.next_best_action.value.trim(),
      };

      status.textContent = 'Submitting...';
      const response = await fetch(`/api/v1/leads/${leadId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        let detail = `Failed: ${response.status}`;
        try {
          const body = await response.json();
          detail = body.detail || detail;
        } catch (_) {
        }
        status.textContent = detail;
        return;
      }

      status.textContent = 'Lead updated';
      await loadDashboard();
    }

    async function updateTaskStatus(taskId, status) {
      const response = await fetch(`/api/v1/content-tasks/${taskId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      });
      if (!response.ok) {
        return;
      }
      await loadDashboard();
    }

    async function pollJob(taskId, statusId, successText) {
      const status = document.getElementById(statusId);
      for (let i = 0; i < 12; i += 1) {
        const response = await fetch(`/api/v1/jobs/${taskId}`, { cache: 'no-store' });
        if (!response.ok) {
          status.textContent = `Job check failed: ${response.status}`;
          return;
        }
        const payload = await response.json();
        status.textContent = `Job ${payload.status}`;
        if (payload.status === 'SUCCESS') {
          status.classList.add('good');
          status.textContent = successText(payload.result || {});
          await loadDashboard();
          return;
        }
        if (payload.status === 'FAILURE') {
          status.textContent = 'Job failed';
          return;
        }
        await new Promise((resolve) => setTimeout(resolve, 1000));
      }
      status.textContent = 'Job still running';
    }

    async function generateWeeklyPlan() {
      const button = document.getElementById('plan-button');
      const status = document.getElementById('plan-status');
      button.disabled = true;
      status.classList.remove('good');
      status.textContent = 'Queueing...';

      const response = await fetch('/api/v1/automation/content-plan', {
        method: 'POST',
      });

      if (!response.ok) {
        let detail = `Failed: ${response.status}`;
        try {
          const body = await response.json();
          detail = body.detail || detail;
        } catch (_) {
        }
        status.textContent = detail;
        button.disabled = false;
        return;
      }

      const payload = await response.json();
      status.textContent = `Queued ${payload.task_id}`;
      await pollJob(
        payload.task_id,
        'plan-status',
        (result) => `Generated ${result.content_task_count} tasks`
      );
      button.disabled = false;
    }

    async function runLeadTriage() {
      const button = document.getElementById('triage-button');
      const status = document.getElementById('triage-status');
      button.disabled = true;
      status.classList.remove('good');
      status.textContent = 'Queueing...';

      const response = await fetch('/api/v1/automation/lead-triage', {
        method: 'POST',
      });

      if (!response.ok) {
        let detail = `Failed: ${response.status}`;
        try {
          const body = await response.json();
          detail = body.detail || detail;
        } catch (_) {
        }
        status.textContent = detail;
        button.disabled = false;
        return;
      }

      const payload = await response.json();
      status.textContent = `Queued ${payload.task_id}`;
      await pollJob(
        payload.task_id,
        'triage-status',
        (result) => `Triaged ${result.lead_count} leads`
      );
      button.disabled = false;
    }

    async function generateTrialFollowup() {
      const button = document.getElementById('followup-button');
      const status = document.getElementById('followup-status');
      button.disabled = true;
      status.classList.remove('good');
      status.textContent = 'Queueing...';

      const response = await fetch('/api/v1/automation/trial-followup', {
        method: 'POST',
      });

      if (!response.ok) {
        let detail = `Failed: ${response.status}`;
        try {
          const body = await response.json();
          detail = body.detail || detail;
        } catch (_) {
        }
        status.textContent = detail;
        button.disabled = false;
        return;
      }

      const payload = await response.json();
      status.textContent = `Queued ${payload.task_id}`;
      await pollJob(
        payload.task_id,
        'followup-status',
        (result) => `Updated ${result.trial_count} trials`
      );
      button.disabled = false;
    }

    document.getElementById('refresh-button').addEventListener('click', refreshDemo);
    document.getElementById('reload-button').addEventListener('click', loadDashboard);
    document.getElementById('lead-form').addEventListener('submit', createLead);
    document.getElementById('lead-update-form').addEventListener('submit', updateLead);
    document.getElementById('trial-form').addEventListener('submit', updateTrial);
    document.getElementById('plan-button').addEventListener('click', generateWeeklyPlan);
    document.getElementById('triage-button').addEventListener('click', runLeadTriage);
    document.getElementById('followup-button').addEventListener('click', generateTrialFollowup);
    loadDashboard().catch((error) => {
      document.getElementById('env-badge').textContent = 'Load Failed';
      document.getElementById('metric-grid').innerHTML = `<article class="card empty">${error.message}</article>`;
    });
  </script>
</body>
</html>"""


def ensure_seeded() -> None:
    initialize_database()
    with SessionLocal() as db:
        seed_demo_data(db)


ensure_seeded()


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

@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_seeded()
    if not DASHBOARD_PATH.exists():
        refresh_demo_assets()
    yield


app = FastAPI(title=settings.app_name, version="0.2.0", lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    same_site="lax",
    https_only=False,
)


class LoginRequest(BaseModel):
    username: str
    password: str


def is_authenticated(request: Request) -> bool:
    return bool(request.session.get("authenticated"))


def require_admin_api(request: Request) -> None:
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Authentication required")


def build_login_html() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Robot Company Login</title>
  <style>
    :root {
      --bg: #f4f1ea;
      --panel: #fffdf8;
      --text: #161616;
      --muted: #6a655f;
      --line: #ddd5ca;
      --accent: #184e3b;
      --shadow: 0 18px 50px rgba(26, 28, 24, .08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "PingFang SC", "Noto Sans CJK SC", sans-serif;
      background:
        radial-gradient(circle at top left, #efe6da 0, transparent 28%),
        radial-gradient(circle at top right, #ddeee6 0, transparent 26%),
        var(--bg);
      color: var(--text);
    }
    .panel {
      width: min(100%, 420px);
      background: rgba(255,253,248,.94);
      border: 1px solid var(--line);
      border-radius: 22px;
      padding: 24px;
      box-shadow: var(--shadow);
    }
    h1 {
      margin: 0 0 8px;
      font-size: 30px;
      letter-spacing: -.04em;
    }
    p {
      margin: 0 0 18px;
      color: var(--muted);
      line-height: 1.7;
      font-size: 14px;
    }
    .field {
      display: grid;
      gap: 6px;
      margin-bottom: 12px;
    }
    label {
      font-size: 12px;
      color: var(--muted);
      font-weight: 700;
    }
    input {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: white;
      padding: 11px 12px;
      font-size: 14px;
    }
    button {
      width: 100%;
      border: 0;
      border-radius: 999px;
      background: var(--accent);
      color: white;
      padding: 12px 14px;
      font-size: 14px;
      font-weight: 700;
      cursor: pointer;
      margin-top: 4px;
    }
    .status {
      margin-top: 12px;
      color: var(--muted);
      font-size: 13px;
      min-height: 20px;
    }
  </style>
</head>
<body>
  <div class="panel">
    <h1>Admin Login</h1>
    <p>这是生产后台的管理员入口。登录后才能访问 <code>/app</code> 和业务 API。</p>
    <form id="login-form">
      <div class="field">
        <label for="username">Username</label>
        <input id="username" name="username" value="admin" autocomplete="username" required>
      </div>
      <div class="field">
        <label for="password">Password</label>
        <input id="password" name="password" type="password" autocomplete="current-password" required>
      </div>
      <button type="submit">Login</button>
      <div class="status" id="status">Use the configured admin credentials.</div>
    </form>
  </div>
  <script>
    document.getElementById('login-form').addEventListener('submit', async (event) => {
      event.preventDefault();
      const status = document.getElementById('status');
      status.textContent = 'Signing in...';
      const payload = {
        username: document.getElementById('username').value.trim(),
        password: document.getElementById('password').value,
      };
      const response = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        status.textContent = 'Login failed';
        return;
      }
      window.location.href = '/app';
    });
  </script>
</body>
</html>"""


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "env": settings.app_env}


@app.get("/login", response_class=HTMLResponse, response_model=None)
def login_page(request: Request):
    if is_authenticated(request):
        return RedirectResponse(url="/app", status_code=302)
    return HTMLResponse(build_login_html())


@app.post("/api/login")
def login(payload: LoginRequest, request: Request) -> dict:
    username_ok = secrets.compare_digest(payload.username, settings.admin_username)
    password_ok = secrets.compare_digest(payload.password, settings.admin_password)
    if not (username_ok and password_ok):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    request.session["authenticated"] = True
    return {"status": "ok"}


@app.post("/api/logout")
def logout(request: Request) -> dict:
    request.session.clear()
    return {"status": "ok"}


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/app", status_code=302)


@app.get("/dashboard")
def dashboard() -> RedirectResponse:
    return RedirectResponse(url="/app", status_code=302)


@app.get("/dashboard-static", response_model=None)
def dashboard_static(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)
    if not DASHBOARD_PATH.exists():
        refresh_demo_assets()
    return FileResponse(DASHBOARD_PATH, media_type="text/html")


@app.get("/app", response_class=HTMLResponse, response_model=None)
def app_page(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)
    return HTMLResponse(build_live_app_html())


@app.post("/api/refresh")
def refresh(request: Request) -> JSONResponse:
    require_admin_api(request)
    try:
        refresh_demo_assets()
    except subprocess.CalledProcessError as exc:
        raise HTTPException(status_code=500, detail=f"Dashboard rebuild failed: {exc}") from exc
    return JSONResponse({"status": "ok", "dashboard": "/dashboard"})


@app.post("/api/v1/bootstrap")
def bootstrap_data(request: Request) -> dict:
    require_admin_api(request)
    ensure_seeded()
    return {"status": "ok"}


@app.get("/api/dashboard", response_model=DashboardPayload)
@app.get("/api/v1/dashboard", response_model=DashboardPayload)
def dashboard_data(request: Request, db: Session = Depends(get_db)) -> DashboardPayload:
    require_admin_api(request)
    return build_dashboard_payload(db)


@app.get("/api/v1/leads", response_model=list[LeadRead])
def list_leads(
    request: Request,
    stage: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[LeadRead]:
    require_admin_api(request)
    stmt = select(Lead).options(selectinload(Lead.trial_activity)).order_by(Lead.created_at.desc())
    if stage:
        stmt = stmt.where(Lead.stage == stage)
    leads = db.scalars(stmt).all()
    return [_serialize_lead(lead) for lead in leads]


@app.post("/api/v1/leads", response_model=LeadRead, status_code=201)
def create_lead(payload: LeadCreate, request: Request, db: Session = Depends(get_db)) -> LeadRead:
    require_admin_api(request)
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


@app.patch("/api/v1/leads/{lead_id}", response_model=LeadRead)
def update_lead(lead_id: str, payload: LeadUpdate, request: Request, db: Session = Depends(get_db)) -> LeadRead:
    require_admin_api(request)
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead.stage = payload.stage
    lead.intent_score = payload.intent_score
    lead.next_best_action = payload.next_best_action
    db.commit()
    db.refresh(lead)
    return _serialize_lead(lead)


@app.get("/api/v1/trials", response_model=list[TrialActivityRead])
def list_trials(request: Request, db: Session = Depends(get_db)) -> list[TrialActivityRead]:
    require_admin_api(request)
    trials = db.scalars(select(TrialActivity).order_by(TrialActivity.updated_at.desc())).all()
    return [_serialize_trial(trial) for trial in trials]


@app.post("/api/v1/trials", response_model=TrialActivityRead, status_code=201)
def upsert_trial(payload: TrialActivityCreate, request: Request, db: Session = Depends(get_db)) -> TrialActivityRead:
    require_admin_api(request)
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
def list_content_tasks(request: Request, db: Session = Depends(get_db)) -> list[ContentTaskRead]:
    require_admin_api(request)
    tasks = db.scalars(select(ContentTask).order_by(ContentTask.created_at.desc())).all()
    return [_serialize_content_task(task) for task in tasks]


@app.patch("/api/v1/content-tasks/{task_id}", response_model=ContentTaskRead)
def update_content_task(task_id: int, payload: ContentTaskUpdate, request: Request, db: Session = Depends(get_db)) -> ContentTaskRead:
    require_admin_api(request)
    task = db.get(ContentTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Content task not found")

    task.status = payload.status
    db.commit()
    db.refresh(task)
    return _serialize_content_task(task)


@app.post("/api/v1/automation/content-plan", response_model=AutomationJobRead)
def trigger_content_plan(request: Request) -> AutomationJobRead:
    require_admin_api(request)
    result = generate_weekly_content_plan_task.delay()
    return AutomationJobRead(task_id=result.id, status=result.status)


@app.post("/api/v1/automation/lead-triage", response_model=AutomationJobRead)
def trigger_lead_triage(request: Request) -> AutomationJobRead:
    require_admin_api(request)
    result = triage_leads_task.delay()
    return AutomationJobRead(task_id=result.id, status=result.status)


@app.post("/api/v1/automation/trial-followup", response_model=AutomationJobRead)
def trigger_trial_followup(request: Request) -> AutomationJobRead:
    require_admin_api(request)
    result = generate_trial_followup_task.delay()
    return AutomationJobRead(task_id=result.id, status=result.status)


@app.get("/api/v1/jobs/{task_id}", response_model=AutomationJobRead)
def read_job_status(task_id: str, request: Request) -> AutomationJobRead:
    require_admin_api(request)
    result = celery_app.AsyncResult(task_id)
    payload = result.result if isinstance(result.result, (dict, str)) else None
    return AutomationJobRead(task_id=task_id, status=result.status, result=payload)


def serve() -> None:
    import uvicorn

    uvicorn.run("stock_strategy_growth_crew.web:app", host="0.0.0.0", port=settings.app_port)
