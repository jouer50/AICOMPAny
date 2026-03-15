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
- `pyproject.toml` 已补生产依赖：
  - `sqlalchemy`
  - `psycopg`
  - `pydantic-settings`
  - `celery`
  - `redis`

## Latest Backup

- Git commit:
  - `fca792d`
- 已推送到 GitHub `main`

## Current Project State

### Still Demo-Oriented

以下模块仍然是 demo 逻辑，未完成生产迁移：

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

## What To Do Next

明天继续时按这个顺序：

1. 新增生产 API 目录与 schema
   - leads
   - trials
   - dashboard summary
2. 新增 DB 初始化和 demo seed
3. 把 `web.py` 改成真正的 FastAPI app factory
4. 接入 Postgres / Redis / Celery
5. 改造 `docker-compose.yml` 为多服务：
   - api
   - postgres
   - redis
   - worker
6. 更新 README 为生产化部署说明

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

目前不影响本地 dashboard，但后续生产化时要统一依赖版本，避免继续堆在同一个 venv 里。

## Recommended Start Command Tomorrow

从这里开始查看：

```bash
cd /Users/jou/stock_strategy_growth_crew
git log --oneline -n 5
git status
```

然后继续做生产 API 和数据库接入。
