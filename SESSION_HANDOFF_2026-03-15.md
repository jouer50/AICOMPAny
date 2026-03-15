# Session Handoff 2026-03-15

## Current Goal

将 `stock_strategy_growth_crew` 从本地 demo 改造成可长期维护的生产系统骨架。

## What Was Completed Today

- 本地项目已初始化为 git 仓库并推送到 GitHub：
  - `https://github.com/jouer50/AICOMPAny`
- 腾讯云服务器已完成：
  - 拉取仓库
  - 安装 Docker
  - 启动容器
- 本地 dashboard 已成功在 Mac 上启动过：
  - `http://127.0.0.1:8000/dashboard`
- 生产化改造已开始，已新增：
  - `src/stock_strategy_growth_crew/settings.py`
  - `src/stock_strategy_growth_crew/db.py`
  - `src/stock_strategy_growth_crew/models.py`
  - `src/stock_strategy_growth_crew/schemas.py`
  - `src/stock_strategy_growth_crew/bootstrap.py`
  - `src/stock_strategy_growth_crew/worker.py`
- `src/stock_strategy_growth_crew/web.py` 已不再只是 demo：
  - 已有生产 API
  - 已有 API 驱动页面 `/app`
- `pyproject.toml` 已补生产依赖：
  - `sqlalchemy`
  - `psycopg`
  - `pydantic-settings`
  - `celery`
  - `redis`

## Latest Backup

- Git commit:
  - `edb6e3a`
- 已推送到 GitHub `main`

## Current Project State

### Still Demo-Oriented

以下模块仍然保留 demo 成分，但不再是纯静态骨架：

- `src/stock_strategy_growth_crew/main.py`
- `src/stock_strategy_growth_crew/web.py`
- `dashboard.py`

它们仍主要依赖：

- `examples/*.json`
- 本地 markdown 输出
- 静态 HTML dashboard

### Production Skeleton Started

已新增的生产骨架：

- `settings.py`
  - 统一环境变量入口
- `db.py`
  - SQLAlchemy engine / session / Base
- `models.py`
  - `Lead`
  - `TrialActivity`
  - `ContentTask`
- `schemas.py`
  - API 输入输出结构
- `bootstrap.py`
  - 建表
  - demo seed
- `worker.py`
  - Celery worker 入口
- `web.py`
  - `GET /healthz`
  - `GET /api/v1/dashboard`
  - `GET/POST /api/v1/leads`
  - `GET/POST /api/v1/trials`
  - `GET /api/v1/content-tasks`
  - `GET /app`

### Verified Locally

已验证：

- 本地 seed 成功
- `/api/v1/dashboard` 返回正常
- `/app` 页面返回正常
- `pytest tests/test_api.py` 通过

## What To Do Next

明天继续时按这个顺序：

1. 把 `/app` 页面继续扩成真正操作后台
   - lead 创建/编辑
   - trial 更新
   - content task 状态切换
2. 把旧 `/dashboard` 静态页逐步废弃
3. 本地和云上联调 `api + postgres + redis + worker`
4. 把 `web.py` 的 `on_event` 改成 lifespan
5. 增加认证和管理入口
6. 把更多业务动作接到 worker 任务

## Tencent Cloud Notes

服务器上当前做过这些：

- 仓库目录：
  - `/root/apps/AICOMPAny`
- Docker 已安装
- 容器曾成功跑起
- 端口曾映射到：
  - `8000`
  - 后又测试改成 `80`

但云上外部访问链路没有完全收口，后续建议在生产化完成后重新部署一次，不要继续基于当前 demo 容器反复修补。

## Local Notes

本机 venv：

- `/Users/jou/.venvs/crewai312`

本地为了跑 dashboard 已安装：

- `fastapi==0.116.1`
- `uvicorn[standard]==0.35.0`

有一个依赖告警：

- `sse-starlette 3.3.2` 需要更高版本 `starlette`

目前不影响本地开发，但后续生产化时要统一依赖版本，避免继续堆在同一个 venv 里。

## Recommended Start Command Tomorrow

从这里开始查看：

```bash
cd /Users/jou/stock_strategy_growth_crew
git log --oneline -n 5
git status
```

然后继续做 `/app` 的真实操作能力和多服务联调。
