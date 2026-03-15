# Stock Strategy Growth Crew

这是一个基于 `CrewAI` 的增长团队骨架，目标不是“自动荐股”，而是为你的
“股票交易策略教练系统”生成合规的多平台推广内容。

当前内置角色：

- 增长策略负责人
- 金融合规审校官
- X 编辑
- 小红书编辑
- 微信公众号编辑
- 雪球编辑
- 运营分析师

当前内置流程：

1. 生成一周增长策略
2. 做金融内容合规审校
3. 分别改写成 X / 小红书 / 公众号 / 雪球内容
4. 汇总成发布执行表

当前知识库：

- [user_preference.txt](/Users/jou/stock_strategy_growth_crew/knowledge/user_preference.txt)
- [compliance_rules.md](/Users/jou/stock_strategy_growth_crew/knowledge/compliance_rules.md)
- [channel_playbooks.md](/Users/jou/stock_strategy_growth_crew/knowledge/channel_playbooks.md)
- [full_company_blueprint.md](/Users/jou/stock_strategy_growth_crew/knowledge/full_company_blueprint.md)
- [sales_conversion_playbook.md](/Users/jou/stock_strategy_growth_crew/knowledge/sales_conversion_playbook.md)
- [7_day_followup_messages.md](/Users/jou/stock_strategy_growth_crew/knowledge/7_day_followup_messages.md)
- [ceo_dashboard.md](/Users/jou/stock_strategy_growth_crew/knowledge/ceo_dashboard.md)
- [handoff_rules.md](/Users/jou/stock_strategy_growth_crew/knowledge/handoff_rules.md)
- [weekly_operating_system.md](/Users/jou/stock_strategy_growth_crew/knowledge/weekly_operating_system.md)

当前样例输入与样例内容：

- [campaign_brief.json](/Users/jou/stock_strategy_growth_crew/examples/campaign_brief.json)
- [launch_content_examples.md](/Users/jou/stock_strategy_growth_crew/examples/launch_content_examples.md)
- [market_signals.json](/Users/jou/stock_strategy_growth_crew/examples/market_signals.json)
- [competitor_snapshots.json](/Users/jou/stock_strategy_growth_crew/examples/competitor_snapshots.json)
- [first_week_content_pack.md](/Users/jou/stock_strategy_growth_crew/examples/first_week_content_pack.md)
- [lead_pipeline.json](/Users/jou/stock_strategy_growth_crew/examples/lead_pipeline.json)
- [trial_activity.json](/Users/jou/stock_strategy_growth_crew/examples/trial_activity.json)
- [crm_dashboard_template.md](/Users/jou/stock_strategy_growth_crew/examples/crm_dashboard_template.md)

## 重要原则

这个项目默认按“教育、复盘、方法、纪律训练”方向输出内容。
不要把它用于：

- 直接荐股
- 承诺收益
- 胜率包装
- 老师带单
- 无资质投顾式营销

建议流程始终保持：

`AI 生成 -> 合规审校 -> 人工终审 -> 发布`

建议先读一遍规则库，再开始跑内容。

## 环境准备

你已经有一个可用的 CrewAI 环境：

```bash
source /Users/jou/.venvs/crewai312/bin/activate
```

进入项目目录：

```bash
cd /Users/jou/stock_strategy_growth_crew
```

安装项目依赖：

```bash
crewai install
```

## 模型配置

先准备一个你要给 CrewAI 使用的模型 key。最简单的是 OpenAI：

```bash
export OPENAI_API_KEY=your_key_here
```

如果你想长期使用，放到项目根目录 `.env` 里也可以。

## 运行

直接运行：

```bash
crewai run
```

默认输出会落到项目根目录：

- `growth_execution_plan.md`

默认会优先读取：

- [campaign_brief.json](/Users/jou/stock_strategy_growth_crew/examples/campaign_brief.json)

所以你平时改 brief，不需要改 Python 代码。
如果你希望策略更贴近市场，再补充：

- `examples/market_signals.json`
- `examples/competitor_snapshots.json`

## 本地 Dashboard 服务

这个项目现在已经补了一个最小 Web 服务，可以直接把本地 demo 暴露成云上页面。

本地启动：

```bash
source /Users/jou/.venvs/crewai312/bin/activate
cd /Users/jou/stock_strategy_growth_crew
python -m uvicorn stock_strategy_growth_crew.web:app --host 0.0.0.0 --port 8000 --app-dir src
```

可用地址：

- `GET /dashboard`：查看后台页面
- `GET /api/dashboard`：查看汇总 JSON
- `POST /api/refresh`：重新生成 demo 输出并刷新 dashboard
- `GET /healthz`：健康检查

## Docker 部署

如果你要部署到腾讯云，当前最小可用方式是 Docker：

```bash
cd /Users/jou/stock_strategy_growth_crew
cp .env.example .env
docker compose up -d --build
```

默认端口：

- `http://服务器IP:8000/dashboard`

当前 `docker-compose.yml` 已升级成生产骨架，多了：

- `api`
- `worker`
- `postgres`
- `redis`

你现在可以把它理解成：

- `api`：FastAPI 应用入口
- `worker`：后台任务执行器
- `postgres`：业务数据存储
- `redis`：队列和缓存

如果你有小龙虾/Nginx 反向代理，把域名转发到容器 `8000` 即可。

### 服务器更新

代码更新后重建：

```bash
docker compose up -d --build
```

查看日志：

```bash
docker compose logs -f
```

## 生产骨架状态

当前已落地的生产文件：

- 配置：
  [`settings.py`](/Users/jou/stock_strategy_growth_crew/src/stock_strategy_growth_crew/settings.py)
- 数据库：
  [`db.py`](/Users/jou/stock_strategy_growth_crew/src/stock_strategy_growth_crew/db.py)
- 模型：
  [`models.py`](/Users/jou/stock_strategy_growth_crew/src/stock_strategy_growth_crew/models.py)
- Schema：
  [`schemas.py`](/Users/jou/stock_strategy_growth_crew/src/stock_strategy_growth_crew/schemas.py)
- 初始化：
  [`bootstrap.py`](/Users/jou/stock_strategy_growth_crew/src/stock_strategy_growth_crew/bootstrap.py)
- API：
  [`web.py`](/Users/jou/stock_strategy_growth_crew/src/stock_strategy_growth_crew/web.py)
- Worker：
  [`worker.py`](/Users/jou/stock_strategy_growth_crew/src/stock_strategy_growth_crew/worker.py)

当前已经有的生产接口：

- `GET /healthz`
- `GET /login`
- `POST /api/login`
- `POST /api/logout`
- `GET /app`
- `GET /dashboard` -> redirect `/app`
- `GET /dashboard-static`
- `GET /api/v1/dashboard`
- `GET /api/v1/leads`
- `POST /api/v1/leads`
- `GET /api/v1/trials`
- `POST /api/v1/trials`
- `GET /api/v1/content-tasks`
- `POST /api/v1/bootstrap`

注意：

- `/dashboard` 现在已经切到生产页面 `/app`
- 旧静态页面保留在：`/dashboard-static`
- 新的 API 驱动页面入口是：`/app`
- `/app` 和业务 API 现在需要管理员登录
- 默认管理员凭据由环境变量控制：
  - `ADMIN_USERNAME`
  - `ADMIN_PASSWORD`
  - `SESSION_SECRET`
- 真实模型入口也已经接上：
  - `LLM_PROVIDER`
  - `LLM_BASE_URL`
  - `LLM_API_KEY`
  - `LLM_MODEL`
- 当前优先被真实模型接管的是：
  - `Generate Weekly Content Plan`
  - 有 key 时走 OpenAI 兼容接口
  - 没 key 或调用失败时自动回退规则生成
- 新的生产化方向已经转向：`数据库 + API + worker`

## 改哪些文件

- Agent 定义：
  [`agents.yaml`](/Users/jou/stock_strategy_growth_crew/src/stock_strategy_growth_crew/config/agents.yaml)
- Task 定义：
  [`tasks.yaml`](/Users/jou/stock_strategy_growth_crew/src/stock_strategy_growth_crew/config/tasks.yaml)
- Crew 编排：
  [`crew.py`](/Users/jou/stock_strategy_growth_crew/src/stock_strategy_growth_crew/crew.py)
- 默认输入：
  [`main.py`](/Users/jou/stock_strategy_growth_crew/src/stock_strategy_growth_crew/main.py)

## 建议下一步

你现在最值得补的不是更多 agent，而是两个能力：

1. 平台内容模板库
2. 合规规则库

再往后可以加：

- 热点抓取工具
- 竞品内容分析工具
- 表单/私域线索承接
- 发布后数据复盘
