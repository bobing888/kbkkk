# M3 前端 7 页 + 后端 5 Router 实施计划（V2 返工版 · metrics-first）

> **创建日期**：2026-10-06
> **设计文档**：`docs/design/m3-frontend-pages.md`（ac9cdad）
> **范围**：后端 5 router + 前端 6 新页 + React Router 集成
> **执行模式**：SDD（Subagent-Driven Development），按 `3.2 → 3.3/3.4 串行`（3.3+3.4 内部并行）
> **关键约束**：
> - **metrics-first**（你的指令）：业务指标先行，5 个 B 指标不通过即返工
> - **V2 教训硬整合**：8 条 V2 返工教训 → 11 条强制规则
> - **不复用 ai-trader 任何代码**（教训 #1），仅借鉴 UI 模式
> - **TDD 铁律**：没有失败测试不写生产代码
> - **不阻塞 main**：所有改动走 feature branch + auto-merge
> - **不破坏基线**：开工前 365 后端 + 6 前端 = **371 passed**（preflight 验证）

---

## 验收门禁（metrics-first · 返工硬约束）

> **来源**：你的指令（"之前实现的效果很差，现在返工二次开发"）+ V2 SPEC-v2-round1-completion-report §7
> **原则**：**业务指标先行于代码**，每个任务必须有可量化验收数字（V2 教训 #4：测试必须测业务指标）

### 🔴 业务指标门禁（必测，不通过即返工）

| # | 指标 | 目标值 | 测量脚本 | 阻塞任务 |
|---|---|---|---|---|
| **B1** | 7 页首次内容渲染 | **< 2.0s** (p95) | `scripts/verify-b1-page-load.py`（Playwright） | 3.3.6 |
| **B2** | signal_batch 端到端延迟 | **< 500ms** (p95, 6 symbol × 4 period) | `scripts/verify-b2-signal-latency.py`（httpx async） | 3.2.6 |
| **B3** | 推荐信号命中率 | **> 55%**（V2 教训 #2 强制门禁）| `scripts/verify-b3-win-rate.py`（30 天模拟回测） | 3.4.1 |
| **B4** | follow 生命周期（开仓 → 平仓） | **< 1.0s** (p99) | `scripts/verify-b4-follow-latency.py`（integration test） | 3.2.2 |
| **B5** | ai-trader 代码复制 | **= 0 行**（V2 教训 #5：license header 必须）| `scripts/verify-b5-no-copy.sh`（ripgrep /opt/ai-trader） | 3.3.6 |

### 🟡 工程指标门禁（必须达成，否则不合并）

| 指标 | 当前 baseline | M3 目标 | 说明 |
|---|---|---|---|
| 后端测试通过 | 365 passed | **380+ passed** | + 15+ 新测试（V2 增 13 → M3 增 15+） |
| 前端测试通过 | 6 passed | **14+ passed** | + 8 新测试（routing + 6 页面） |
| 后端 pytest 时间 | ~23s | **< 30s** | 不许变慢 |
| 前端 typecheck | 0 错 | **0 错** | 严格 |
| 前端 npm build | — | **必须成功** | 0 警告 |
| KBKKK 0 回归 | — | **必须** | 现有 371 测试不许挂 |

### 🟠 V2 重设计教训 → M3 强制规则（不遵守即返工）

> **来源**：`docs/SPEC-v2-round1-completion-report.md` §7（5 条 KB 经验沉淀）

| 教训 | 数字证据 | M3 强制动作 | 验证方式 |
|---|---|---|---|
| **校正节省 50%** | V2 校正发现 2/8 Arch 误判 → 省 2 PR | M3 每个 subagent 开工前 **必读 6 个相关文件**（简报含文件清单 + 已读断言） | subagent 报告含 "已读文件" 段 |
| **风险排序 ≠ 工作量** | V2 PR-2 风险最高先做 → 早暴露 hidden bug | M3 任务顺序改为：**DB 迁移 → follow router → 其余**（原计划 3.2.0-3.2.7 调序） | progress.md 顺序记录 |
| **cache 阻塞 API** | V2 PR-4：`cache_set` 失败阻塞 kline API | M3 所有 router **必须 try/except 包 cache**（copy V2 模式 `routers/kline.py:39-42`） | 单元测试 `test_cache_set_failure_still_returns_data` |
| **AsyncClient 绕开 main app** | V2 .env 与 pydantic v2 冲突 | M3 router 测试**不准走 main app**，统一用 `httpx.AsyncClient + ASGITransport(app=app)` 模式 | review 检查 test fixture |
| **commit 立即 push** | V2: PR-3 被 `reset --hard origin/main` 覆盖 → reflog 救回 | M3 subagent **每 commit 立即 push**（不累积） | progress.md 记录 push 时间戳 |
| **架构师 2/8 误判** | V2 #2 文件已删 / #8 已有 19 测试 | M3 subagent 简报**必列已知陷阱**（详见 §0） | 简报含 "已知陷阱" 段 |
| **3 文件 .env 冲突** | V2 pydantic v2 Settings extra=ignore bug | M3 测试 fixture 用 `monkeypatch.setenv` + `Settings(_env_file=None)` 绕过 | 现有 baseline 已验证 |
| **PR-2 hidden broken** | V2 `follow_worker.py:290` 调 `await on_market_update` 但原本同步 | 3.2.2 subagent 必读 `follow_engine.py` + `follow_worker.py` 全文件 | 简报含必读清单 |

---

## 0. 预存在问题清单（开工前必读 · V2 教训整合版）

> **来源**：`debugging.mdc` 根因调查 + V2 SPEC-v2-round1-completion-report §7

| # | 问题 | 状态 | 影响 | 解决 |
|---|---|---|---|---|
| 0.1 | `prometheus_client` / `prometheus_fastapi_instrumentator` / `pydantic_settings` 未装 | ✅ 已修（`pip install -r requirements.txt`） | 测试可跑 | — |
| 0.2 | `backend/venv/bin/pip` shebang 指向不存在的路径（仓曾改名） | ⚠️ 用 `./venv/bin/python -m pip` 绕过 | 已知，不影响 | subagent 简报必含此命令 |
| 0.3 | `schema.sql` 缺 `strategies` 表 | 🔧 **3.2.0 修复**（建表 + ORM model） | 阻塞 3.2.1 | **任务最优先**（V2 教训：风险优先） |
| 0.4 | `FollowEngine` 业务已实现但**无 HTTP API** | ✅ 是 3.2.2 任务 | — | 包 FollowEngine |
| 0.5 | `test_m3_acceptance.py` 命名误导（实际测 follow_engine，非前端 M3） | ✅ 已识别，不修改 | 命名陷阱 | subagent 简报必提 |
| 0.6 | 前端 `react-router-dom` 已装但 `main.tsx` 无 `<BrowserRouter>` | 🔧 **3.3.5 修复** | 阻塞 3.3 | 任务前置 |
| **0.7** | **V2 .env 冲突**：`pydantic v2 Settings extra=ignore` 与 .env 中 `GRAFANA_PASSWORD` 等冲突 | ⚠️ 已有 bug | router 测试不准走 main app | **必须用 ASGITransport 模式** |
| **0.8** | **V2 cache 阻塞**：`cache_set` 失败 → API 阻塞 | ⚠️ 已有教训 | router 设计必须包 try/except | **3.2.1-3.2.5 必含** |
| **0.9** | **V2 follow 异步化已做**（commit `c114a88`） | ✅ 已修 | — | 3.2.2 直接用 async API |
| **0.10** | **V2 ccxt 连接复用已做**（commit `c114a88`） | ✅ 已修 | — | 3.2.3 signal_batch 用模块级 ccxt |
| **0.11** | **V2 OBV 向量化已做**（commit `2258236`） | ✅ 已修 | — | — |
| **0.12** | **V2 PR-2 hidden broken**：`follow_worker.py:290` 调 `await on_market_update` 但原本同步 | ⚠️ V2 教训 | subagent 必须 `Read` follow_engine.py + follow_worker.py 全文件 | **必读文件清单** |

---

## 任务排序变更（V2 教训：风险优先）

> **原计划**：3.2.0 → 3.2.1 → 3.2.2 → ...（按工作量）
> **新计划**：按**风险**排序，遵循 V2 §7.1 "风险优先" 原则

```
3.2.0 (DB 迁移，数据风险最高)     ← 1st
3.2.2 (follow router，业务风险最高) ← 2nd（V2 PR-2 教训：follow 异步化曾 broken）
3.2.6 (router 注册，集成风险)     ← 3rd
3.2.1 (strategies CRUD，独立)     ← 4th
3.2.3 (signal_batch，依赖 ccxt 模块级)  ← 5th
3.2.4 (trades，独立读 TradeLog)   ← 6th
3.2.5 (github_sync，外部依赖)     ← 7th
3.2.7 (PR + 部署验证)            ← last
```

---

## 文件结构（按新任务排序）

```
backend/
├── app/
│   ├── models/
│   │   ├── __init__.py                  # ← 3.2.0 修复：追加 Strategy + FollowSetting ORM
│   │   └── schema.sql                   # ← 3.2.0 修复：追加 strategies + follow_settings 建表
│   ├── routers/
│   │   ├── __init__.py                  # ← 3.2.6 修改：注册 5 新 router
│   │   ├── follows.py                   # ★ 3.2.2 优先做（V2 风险教训）
│   │   ├── strategies.py                # ★ 3.2.1
│   │   ├── signal_batch.py              # ★ 3.2.3
│   │   ├── trades.py                    # ★ 3.2.4
│   │   └── github_sync.py               # ★ 3.2.5
│   ├── services/
│   │   ├── follow_service.py            # ★ 3.2.2（包装 FollowEngine + RiskManager）
│   │   ├── strategy_service.py          # ★ 3.2.1（CRUD + GitHub import）
│   │   ├── github_client.py             # ★ 3.2.5（httpx async + 模块级 client）
│   │   └── signal_batch_runner.py       # ★ 3.2.3（asyncio 批量）
│   └── main.py                          # ← 0.7 修复（仅 CORS allow_origin 调整）
├── scripts/
│   ├── verify-b1-page-load.py          # ★ M3 B1 指标
│   ├── verify-b2-signal-latency.py      # ★ M3 B2 指标
│   ├── verify-b3-win-rate.py            # ★ M3 B3 指标
│   ├── verify-b4-follow-latency.py      # ★ M3 B4 指标
│   └── verify-b5-no-copy.sh             # ★ M3 B5 指标
└── tests/
    ├── test_strategy_model.py           # ★ 3.2.0（≥3 用例）
    ├── test_follows_router.py           # ★ 3.2.2（≥5 用例）
    ├── test_strategies_router.py        # ★ 3.2.1（≥6 用例）
    ├── test_signal_batch_router.py      # ★ 3.2.3（≥4 用例）
    ├── test_trades_router.py            # ★ 3.2.4（≥3 用例）
    └── test_github_sync_router.py       # ★ 3.2.5（≥3 用例，httpx mock）

frontend/src/
├── pages/                                # ★ 3.3 + 3.4 新增目录
│   ├── AnalysisPage.tsx                  # ★ 3.3.1（P2，~150 行）
│   ├── TradesPage.tsx                    # ★ 3.3.2（P1，~150 行）
│   ├── FollowsPage.tsx                   # ★ 3.3.3（P1，~200 行）
│   ├── BacktestPage.tsx                  # ★ 3.3.4（P2，~250 行）
│   ├── RecommendationsPage.tsx           # ★ 3.4.1（P0，~350 行，**重写**）
│   └── StrategyPage.tsx                  # ★ 3.4.2（P0，~450 行，**重写**）
├── components/
│   ├── common/
│   │   └── PageHeader.tsx                # ★ 3.3.5 新增（统一页面头部 + 顶部导航）
│   └── KlineAppShell.tsx                 # ★ 3.3.5 新增（7 页通用 layout，含 nav + outlet）
├── api/
│   ├── strategiesApi.ts                  # ★ 3.3.0 新增
│   ├── followsApi.ts                     # ★ 3.3.0 新增
│   ├── signalBatchApi.ts                 # ★ 3.3.0 新增
│   ├── tradesApi.ts                      # ★ 3.3.0 新增
│   ├── backtestApi.ts                    # ★ 3.3.0 新增
│   └── githubSyncApi.ts                  # ★ 3.3.0 新增
├── hooks/
│   ├── useStrategies.ts                  # ★ 3.3.0
│   ├── useFollows.ts                     # ★ 3.3.0
│   ├── useSignalBatch.ts                 # ★ 3.3.0
│   ├── useTrades.ts                      # ★ 3.3.0
│   └── useBacktest.ts                    # ★ 3.3.0
├── types/
│   ├── strategy.ts                       # ★ 3.3.0
│   ├── follow.ts                         # ★ 3.3.0
│   ├── signal.ts                         # ★ 3.3.0
│   ├── trade.ts                          # ★ 3.3.0
│   └── backtest.ts                       # ★ 3.3.0
├── App.tsx                               # ← 3.3.5 重构（去掉旧 4 tab，改用 <Outlet/>）
├── main.tsx                              # ← 0.6 修复（加 <BrowserRouter>）
└── __tests__/
    ├── App.routing.test.tsx              # ★ 3.3.5（路由集成测试）
    └── pages/                            # ★ 3.3 + 3.4 每页 ≥1 渲染测试
```

---

## 任务分解

### 阶段 3.2：后端 5 router（**新排序：风险优先**）

> **派发模式**：1 个 subagent 顺序完成 3.2.0 → 3.2.2 → 3.2.6 → 3.2.1 → 3.2.3 → 3.2.4 → 3.2.5 → 3.2.7（**禁止并行**，避免 ORM migration 冲突 + V2 风险优先教训）

#### 任务 3.2.0：DB 迁移（strategies + follow_settings）—— 风险最高

**目的**：补齐设计文档漏掉的 schema（V2 教训：先做风险最高的）。

**步骤 1：subagent 必读文件**（V2 教训 #1：校正节省 50%）
- `backend/app/models/__init__.py`（已读 7 个 ORM）
- `backend/app/models/schema.sql`（已读，确认无 strategies 表）
- `backend/app/db.py`（理解 init_db 流程）
- `backend/app/follow/follow_engine.py`（理解 follow_settings 字段需求）
- `backend/alembic/versions/`（如存在，确认是否需新 migration）
- `backend/tests/test_db_sqlite.py`（理解测试模式）

**步骤 2：写测试**
- 文件：`backend/tests/test_strategy_model.py`（新建）
- 测试名：
  - `test_create_strategy_persists_to_db` — 构造 `Strategy(name="KDJ金叉", code="kdj_cross", market="crypto", params={"period": 9})` → `session.add + commit` → 重新 `session.query` 拿回，name/code/market/params 全部一致
  - `test_strategy_code_unique_per_market` — 重复 (market, code) → IntegrityError
  - `test_follow_setting_persists_global_risk_params` — 构造 `FollowSetting(max_daily_loss_pct=0.02, ...)` → 持久化 + 读取一致
- **测试模式**（V2 教训）：用 SQLite（`DB_BACKEND=sqlite`）+ 独立 `SQLITE_PATH` + fixture 隔离

**步骤 3：实现 ORM**
- 文件：`backend/app/models/__init__.py`
- 行为：追加 2 个 class：
  - `Strategy`（id / name / code / market / params(JSON) / is_active / created_at / updated_at）+ 索引 `(market, code)` 唯一
  - `FollowSetting`（id / max_daily_loss_pct / max_concurrent_positions / max_correlation_exposure / is_active / created_at）

**步骤 4：追加 schema.sql**
- 文件：`backend/app/models/schema.sql`
- 行为：在 `backtest_results` 表后追加 `CREATE TABLE strategies (...)` + `CREATE TABLE follow_settings (...)`（含 PG + SQLite 兼容语法）

**步骤 5：验证**
- 跑：`cd backend && DB_BACKEND=sqlite SQLITE_PATH=/tmp/test_m3_0.db ./venv/bin/python -m pytest tests/test_strategy_model.py -v`
- 期望：3 passed
- 跑全量：`./venv/bin/python -m pytest -q --tb=short`
- 期望：365 + 3 = **368 passed**（基线涨 3，无回归）

**步骤 6：commit + push**（V2 教训：commit 立即 push）
- `git add backend/app/models/`
- `git commit -m "feat(models): Strategy + FollowSetting ORM + schema (M3 3.2.0)"`
- `git push origin docs/m3-sdd-plan`（**不累积**，V2 PR-3 被 reset 教训）

**步骤 7：完成定义**
- subagent 写 `kbkkk/.cursor/sdd/reports/3.2.0.md`：含已读文件清单 + 测试输出 + commit hash + push 时间戳

---

#### 任务 3.2.2：routers/follows.py —— 业务风险最高（V2 教训 #PR-2 hidden broken）

**端点**（设计文档 §架构）：
- `GET  /api/v1/follows` — 当前跟单列表（status=open 的 TradeLog）
- `GET  /api/v1/follows/:id` — 单个跟单详情
- `POST /api/v1/follows` — 手动开跟单（包装 `FollowEngine.on_signal` async API，V2 PR-2 已 async 化）
- `POST /api/v1/follows/:id/close` — 手动平仓（包装 `FollowEngine.on_market_update` async）
- `POST /api/v1/follows/:id/cancel` — 取消未开仓跟单

**步骤 1：subagent 必读文件**（V2 教训 #1 + #PR-2 hidden broken）
- `backend/app/follow/follow_engine.py`（**全文件**，含 `on_signal` / `on_market_update` async 签名，V2 commit `c114a88`）
- `backend/app/follow/follow_worker.py`（**全文件**，含 line 290 `await on_market_update`，V2 教训已修）
- `backend/app/follow/risk_manager.py`（5 门控接口）
- `backend/app/follow/position_sizer.py`
- `backend/app/models/__init__.py`（TradeLog 字段）
- `backend/app/routers/kline.py`（参考 cache 错误处理 + _signal_to_dict 风格）

**步骤 2：写测试**（≥5 用例，`backend/tests/test_follows_router.py`）
- `test_list_follows_returns_open_tradelogs` — DB 有 3 条 status=open → 返回 3 条
- `test_create_follow_invokes_follow_engine` — POST + mock FollowEngine.on_signal → 返回 ExecutionResult
- `test_create_follow_rejects_low_confidence` — confidence=0.4 → 400 + low_confidence 错误
- `test_close_follow_returns_close_result` — POST :id/close → 返回 CloseResult
- `test_cancel_follow_only_for_pending` — 已 open 的 cancel → 409
- **测试模式**（V2 教训 #0.7）：**用 `httpx.AsyncClient + ASGITransport(app=app)`**，不 `from app.main import app`（绕开 .env 冲突）

**步骤 3：实现 service**
- 文件：`backend/app/services/follow_service.py`（新建，~100 行）
- 类：`FollowService(follow_engine, risk_manager, db_session_factory)`
- 方法：`list_open / get / create / close / cancel`
- **关键**：包装 **async** `FollowEngine.on_signal(signal, account_state)`（V2 PR-2 已 async 化，**不是 `asyncio.run` 嵌套**——V2 教训）

**步骤 4：实现 router**
- 文件：`backend/app/routers/follows.py`（新建，~150 行）
- **强制 try/except 包 cache**（V2 教训 #0.8：cache 失败不阻塞）
- router 依赖注入：`db: Session = Depends(get_db)` + `follow_service: FollowService = Depends(get_follow_service)`

**步骤 5：验证**
- 跑：`DB_BACKEND=sqlite SQLITE_PATH=/tmp/test_m3_2.db ./venv/bin/python -m pytest tests/test_follows_router.py -v`
- 期望：5 passed
- 跑全量：`./venv/bin/python -m pytest -q --tb=short`
- 期望：368 + 5 = **373 passed**（含 cache 失败降级测试）

**步骤 6：commit + push**（V2 教训）
- `git add backend/app/services/follow_service.py backend/app/routers/follows.py backend/tests/test_follows_router.py`
- `git commit -m "feat(router): follows lifecycle wraps async FollowEngine (M3 3.2.2)"`
- `git push origin docs/m3-sdd-plan`

**步骤 7：B4 业务指标验证**（V2 教训：测试测业务指标）
- 跑：`./venv/bin/python scripts/verify-b4-follow-latency.py --iterations 100`
- 期望：p99 < 1.0s（否则不通过）

**步骤 8：完成定义**
- subagent 写 `kbkkk/.cursor/sdd/reports/3.2.2.md`：含已读文件清单 + 测试输出 + B4 数字 + commit hash + push 时间戳

---

#### 任务 3.2.6：注册新 router（集成风险）

**步骤 1：修改 __init__.py**
- 文件：`backend/app/routers/__init__.py`
- 行为：import 5 个新模块 + `register_routers` 加 5 行 `app.include_router(...)`

**步骤 2：验证**
- 跑全量：`./venv/bin/python -m pytest -q --tb=short`
- 期望：373 + 既有 = **375+ passed**
- 跑 server 测端点（用 ASGITransport，不起 uvicorn）：
  ```python
  # scripts/verify-routers.py
  import asyncio
  from httpx import AsyncClient, ASGITransport
  from app.routers import register_routers
  from fastapi import FastAPI

  app = FastAPI()
  register_routers(app)

  async def main():
      async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
          for path in [
              "/api/v1/strategies", "/api/v1/follows",
              "/api/v1/signals/batch?symbols=BTC&period=1d&market=crypto",
              "/api/v1/trades", "/api/v1/strategies/sync-github/status",
          ]:
              r = await c.get(path)
              assert r.status_code in (200, 422), f"{path}: {r.status_code} {r.text}"
              print(f"OK {path} -> {r.status_code}")
  asyncio.run(main())
  ```
- 期望：5 端点全部 200 或 422（422 = 参数错误，但路由通）

**步骤 3：commit + push**
- `git add backend/app/routers/__init__.py backend/scripts/verify-routers.py`
- `git commit -m "feat(router): register 5 new routers in main (M3 3.2.6)"`
- `git push origin docs/m3-sdd-plan`

---

#### 任务 3.2.1：routers/strategies.py（独立 CRUD，风险中等）

**端点**：
- `GET  /api/v1/strategies?page=1&page_size=20` — 列表
- `GET  /api/v1/strategies/:id` — 详情
- `POST /api/v1/strategies` — 创建
- `PUT  /api/v1/strategies/:id` — 更新
- `DELETE /api/v1/strategies/:id` — 软删（is_active=false）
- `POST /api/v1/strategies/:id/clone` — 克隆
- `GET  /api/v1/strategies/:id/export` — 导出 .py 字符串
- `POST /api/v1/strategies/import` — 导入 .py 字符串

**步骤 1：subagent 必读**
- `backend/app/models/__init__.py`（3.2.0 已加 Strategy ORM）
- `backend/app/routers/analysis.py`（参考 _signal_to_dict + _get_df 错误处理风格）
- `backend/app/routers/kline.py`（参考 cache try/except）
- `backend/app/db.py`（get_db factory 模式）
- `backend/tests/test_db_sqlite.py`（测试 fixture 模式）

**步骤 2：写测试**（≥6 用例）
- `test_list_strategies_empty` — DB 空 → `{items: [], total: 0}`
- `test_create_strategy_returns_201_with_id` — POST → 201 + Location header
- `test_create_strategy_rejects_duplicate_code` — 重复 → 409
- `test_get_strategy_by_id_404_when_missing` — 不存在 → 404
- `test_update_strategy_modifies_fields` — PUT → 200 + DB 更新
- `test_delete_strategy_soft_deletes` — DELETE → 204 + is_active=false
- `test_clone_strategy_creates_new_with_suffix` — POST :id/clone → 新 + name " (副本)"

**步骤 3：实现 service**
- 文件：`backend/app/services/strategy_service.py`（~120 行）
- 类：`StrategyService(db_session_factory)` + Pydantic schemas (`StrategyCreate` / `StrategyUpdate`)

**步骤 4：实现 router**
- 文件：`backend/app/routers/strategies.py`（~180 行）
- 模式：参考 `routers/analysis.py` 风格
- **强制 try/except 包 cache**（V2 教训 #0.8）

**步骤 5：验证 + commit + push**
- 跑全量：`./venv/bin/python -m pytest -q --tb=short`
- 期望：375 + 6 = **381+ passed**
- `git commit -m "feat(router): strategies CRUD + clone + export/import (M3 3.2.1)"`
- `git push origin docs/m3-sdd-plan`

---

#### 任务 3.2.3：routers/signal_batch.py（依赖 ccxt 模块级，V2 教训）

**端点**：
- `GET /api/v1/signals/batch?symbols=BTC,ETH,SOL&period=1d&market=crypto`
- `GET /api/v1/signal/:symbol?period=1d&market=crypto`（单数，与现有 `/signals/{symbol}` 复数共存）

**步骤 1：subagent 必读**
- `backend/app/data/data_fetcher.py`（V2 ccxt 模块级单例，commit `c114a88`）
- `backend/app/routers/analysis.py`（参考 `_get_df` + 现有 signals 端点）
- `backend/app/services/indicators.py`（IndicatorEngine）
- `backend/app/analytics/signal_direction.py`（generate_signal）

**步骤 2：写测试**（≥4 用例）
- `test_batch_returns_signals_for_all_symbols` — 3 symbol → 3 结果
- `test_batch_skips_symbols_with_no_data` — 1 报错 → 跳过 + 错误标在 meta
- `test_batch_runs_concurrently` — `time.monotonic()` 断言 3 symbol 总耗时 < 单 symbol 3 倍
- `test_single_signal_returns_full_signal_object`

**步骤 3：实现 service**
- 文件：`backend/app/services/signal_batch_runner.py`（~100 行）
- 函数：`async run_batch(symbols, period, market) -> list[BatchResult]`
- 内部用 `asyncio.gather` 并行

**步骤 4：实现 router**（~150 行）

**步骤 5：验证 + B2 业务指标 + commit + push**
- 跑：`./venv/bin/python scripts/verify-b2-signal-latency.py --symbols 6 --periods 4 --iterations 20`
- 期望：p95 < 500ms（否则不通过）
- 跑全量：期望 **385+ passed**
- `git commit -m "feat(router): signal batch + single asyncio parallel (M3 3.2.3)"`
- `git push origin docs/m3-sdd-plan`

---

#### 任务 3.2.4：routers/trades.py（独立读 TradeLog，风险低）

**端点**：
- `GET /api/v1/trades?status=open&page=1&page_size=20`
- `GET /api/v1/trades/summary?period=7d`

**步骤 1：subagent 必读**
- `backend/app/models/__init__.py`（TradeLog）
- `backend/app/follow/follow_engine.py`（on_market_update 计算 summary）

**步骤 2：写测试**（≥3 用例）
- `test_list_trades_filters_by_status`
- `test_trades_summary_calculates_win_rate` — 10 trades 6 盈 4 亏 → 0.6
- `test_trades_summary_handles_empty_db` — 零值 + 200

**步骤 3：实现 router**（~100 行）

**步骤 4：验证 + commit + push**
- 期望 **388+ passed**
- `git commit -m "feat(router): trades list + summary from TradeLog (M3 3.2.4)"`
- `git push origin docs/m3-sdd-plan`

---

#### 任务 3.2.5：routers/github_sync.py（外部依赖风险）

**端点**：
- `POST /api/v1/strategies/sync-github` — body: `{repo, path, token?}`
- `GET  /api/v1/strategies/sync-github/status` — running/idle/last_error

**步骤 1：subagent 必读**
- `backend/app/services/data_fetcher.py`（httpx async 模式参考）
- `backend/app/routers/strategies.py`（CRUD 模式）

**步骤 2：写测试**（≥3 用例，httpx mock）
- `test_sync_github_imports_strategies_from_repo` — mock 返回 3 .py → 3 Strategy
- `test_sync_github_handles_api_rate_limit` — 403 → 429
- `test_status_returns_last_sync_info`

**步骤 3：实现 GitHub client**
- 文件：`backend/app/services/github_client.py`（~120 行）
- 函数：`async fetch_py_files(repo, path, token) -> list[str]`
- **关键**：模块级 `httpx.AsyncClient` 单例（V2 ccxt 教训同款）

**步骤 4：实现 router**（~120 行）

**步骤 5：验证 + commit + push**
- 期望 **391+ passed**
- `git commit -m "feat(router): GitHub strategy sync (M3 3.2.5)"`
- `git push origin docs/m3-sdd-plan`

---

#### 任务 3.2.7：3.2 PR + 部署验证

**步骤 1：合 3.2**
- 等 8 个 commit 全部 push
- 8 commit 应该是独立的（每个 1 个 router）→ 8 PR 或按 AGENTS.md 拆 ≤ 500 行
- AGENTS.md 规定：PR base=main + auto-merge

**步骤 2：prod 验证**
- 等 auto-merge 合到 main
- 拉 prod 部署日志 → curl prod 6 端点
- engram remember：`kbkkk M3-3.2 后端 5 router 上线 baseline=391+ B2<500ms B4<1s`

---

### 阶段 3.3 + 3.4：前端 6 页（**3.2.6 merge 后并行**）

> **派发模式**：2 个 subagent 并行（subagent-A 做 3.3.1-3.3.4，subagent-B 做 3.4.1-3.4.2），都依赖 3.3.0 + 3.3.5

#### 任务 3.3.0：API client + 类型 + hooks（**前置**，必须先做）

**步骤 1：subagent 必读**
- `frontend/src/api/klineApi.ts`（VITE_API_BASE + validateSymbol + fetch wrapper 模式）
- `frontend/src/hooks/useAnalysis.ts`（tanstack-query + useQuery 模式）
- `frontend/src/types/kline.ts`（interface 模式）
- `frontend/src/main.tsx`（确认 react-query QueryClient 配置）

**步骤 2：类型定义**（5 文件）
- `frontend/src/types/strategy.ts` / `follow.ts` / `signal.ts` / `trade.ts` / `backtest.ts`
- 每个 20-40 行

**步骤 3：API client**（6 文件，每个 30-60 行）
- 模式：copy `klineApi.ts` 结构
- `strategiesApi.ts` / `followsApi.ts` / `signalBatchApi.ts` / `tradesApi.ts` / `backtestApi.ts` / `githubSyncApi.ts`

**步骤 4：hooks**（5 文件）
- 模式：copy `useAnalysis.ts` 结构
- `useStrategies()` / `useStrategy(id)` / `useCreateStrategy()` / `useUpdateStrategy()` / `useDeleteStrategy()` / `useCloneStrategy()`

**步骤 5：验证**
- 跑：`cd frontend && npm run typecheck && npm test`
- 期望：0 错 + 6 passed（基线无回归）

**步骤 6：commit + push**（V2 教训）
- `git add frontend/src/api frontend/src/hooks frontend/src/types`
- `git commit -m "feat(frontend): 5 API clients + 5 hooks for M3 pages (M3 3.3.0)"`
- `git push origin docs/m3-sdd-plan`

---

#### 任务 3.3.5：React Router + 顶部导航（**前置**，必须先做）

**步骤 1：subagent 必读**
- `frontend/src/App.tsx`（当前 4 tab 结构）
- `frontend/src/main.tsx`（无 `<BrowserRouter>`）
- `frontend/package.json`（react-router-dom 7.18.4 已装）
- `frontend/src/__tests__/`（如不存在，参考 `components/KLineChart/__tests__/`）

**步骤 2：装 + 配 BrowserRouter**
- 文件：`frontend/src/main.tsx`
- 行为：包 `<BrowserRouter>` 在 `<QueryClientProvider>` 外层
- 注释：`// M3: SPA 路由根`

**步骤 3：AppShell 组件**
- 文件：`frontend/src/components/KlineAppShell.tsx`（~80 行）
- 内容：`<header>` 顶部导航（7 个 NavLink） + `<Outlet/>`

**步骤 4：PageHeader 组件**
- 文件：`frontend/src/components/common/PageHeader.tsx`（~40 行）
- props：`title` / `subtitle?` / `actions?`

**步骤 5：重构 App.tsx**
- 文件：`frontend/src/App.tsx`
- 行为：移除 4 tab，改为 `<KlineAppShell>` + `<Routes>`（7 路由）

**步骤 6：写测试**
- 文件：`frontend/src/__tests__/App.routing.test.tsx`
- 测试：`renders KlinePage on /` / `renders AnalysisPage on /analysis/BTC` / `top nav has 7 links`
- 用 `MemoryRouter` 包裹

**步骤 7：验证 + commit + push**
- 期望：0 错 + 8 passed（6 基线 + 2 新增）
- `git commit -m "feat(frontend): React Router + 7-page shell + top nav (M3 3.3.5)"`
- `git push origin docs/m3-sdd-plan`

---

#### 任务 3.3.1-3.3.4：4 个 P1+P2 页（**subagent-A**）

**subagent-A 必读**（V2 教训）：
- `frontend/src/App.tsx`（当前 layout）
- `frontend/src/components/KLineChart/index.tsx`（复用图表）
- `frontend/src/hooks/useAnalysis.ts`（数据模式）
- `frontend/src/components/common/`（共用组件）
- `/opt/ai-trader/frontend/src/pages/`（**只读 UI 模式**，不复制代码，V2 教训 #5）

**每个页面的标准步骤**：

| 页面 | 任务 | 行数估计 | 验证 |
|---|---|---|---|
| AnalysisPage | 3.3.1 | ~150 | `test renders symbol and period from URL params` |
| TradesPage | 3.3.2 | ~150 | `test renders summary card with 3 metrics` |
| FollowsPage | 3.3.3 | ~200 | `test renders follow list grouped by status` |
| BacktestPage | 3.3.4 | ~250 | `test renders parameter form with 5 fields` |

**每个页面完成后**：
- `git commit -m "feat(frontend): <PageName> (M3 3.3.X)"`
- `git push origin docs/m3-sdd-plan`（**立即 push**）

**subagent-A 完成定义**：
- 报告含：4 页面截图（Playwright）+ 4 页面测试通过 + B5 验证（`./scripts/verify-b5-no-copy.sh` → 0 复制）

---

#### 任务 3.4.1：RecommendationsPage（**subagent-B**，P0，重写）

**subagent-B 必读**：
- `frontend/src/pages/`（3.3.0-3.3.5 完成后才有）
- `/opt/ai-trader/frontend/src/pages/RecommendationsPage.tsx`（**只读 UI 模式**）
- 现有 `frontend/src/api/signalBatchApi.ts`（3.3.0 加）

**UI 模式**（借鉴 ai-trader "批量 6 币 × 4 周期"布局）：
- 顶部：标的网格（BTC/ETH/SOL/DOGE/SHIB/PEPE 多选）
- 主体：周期标签（1d/1w/30m/60m）
- 格子：当前信号 + 置信度 + 方向

**步骤**：写测试 → 实现 → 验证 → B3 业务指标

**B3 业务指标验证**（V2 教训 #4：测业务指标）：
- 跑：`./venv/bin/python scripts/verify-b3-win-rate.py --days 30 --strategy recommendations`
- 期望：命中率 > 55%（否则不通过）

**commit + push**：
- `git commit -m "feat(frontend): RecommendationsPage batch grid (M3 3.4.1)"`
- `git push origin docs/m3-sdd-plan`

---

#### 任务 3.4.2：StrategyPage（**subagent-B**，P0，重写）

**subagent-B 必读**：
- 现有 `frontend/src/api/strategiesApi.ts` / `githubSyncApi.ts`
- `/opt/ai-trader/frontend/src/pages/StrategyPage.tsx`（**只读 UI 模式**）

**UI 模式**：3 标签（我的策略 / 模板市场 / GitHub 同步）

**步骤**：写测试 → 实现 → 验证 → B5 业务指标

**B5 验证**（V2 教训 #5：license header 必须）：
- 跑：`./scripts/verify-b5-no-copy.sh`
- 期望：0 行从 `/opt/ai-trader/` 复制（grep 输出空）

**commit + push**：
- `git commit -m "feat(frontend): StrategyPage CRUD + GitHub sync (M3 3.4.2)"`
- `git push origin docs/m3-sdd-plan`

---

#### 任务 3.3.6：3.3 + 3.4 集成 PR

**步骤 1：合 3.3.5 → main（前置）**
- 等 commit 推完 + auto-merge

**步骤 2：subagent-A + subagent-B 并行**

**步骤 3：最终验证**
- 跑：`npm run typecheck && npm test && npm run build`
- 期望：0 错 + 14+ passed + build 成功
- **B1 业务指标**（V2 教训 #4）：
  ```bash
  ./scripts/verify-b1-page-load.py  # Playwright
  ```
  期望：7 页 p95 < 2.0s
- **B5 业务指标**：
  ```bash
  ./scripts/verify-b5-no-copy.sh  # ripgrep /opt/ai-trader
  ```
  期望：0 行复制

**步骤 4：commit + PR**
- `git commit -m "feat(frontend): M3 6 new pages complete (M3 3.3.6)" --allow-empty`
- `git push origin docs/m3-sdd-plan`

---

## 自检清单（写完计划必走 + V2 教训强化）

- [x] 规格覆盖：每个需求都有对应任务？
- [x] 步骤扫描：无「待定」「适当」「相关」含糊词？
- [x] 类型一致性：API 端点 / ORM model / 前端 type 三处一致？
- [x] 审查重点：spec 隐含的失败模式都有测试？（V2 教训 + prometheus baseline / strategy 表缺 / 命名陷阱）
- [x] 任务独立：每个任务能独立提交？
- [x] 时间预算：每任务 < 1 小时工作量？
- [x] **V2 校正节省 50%**：subagent 简报必含"必读文件清单 + 已读断言"
- [x] **V2 风险优先**：任务顺序按风险而非工作量
- [x] **V2 cache 阻塞**：router 必含 try/except 包 cache
- [x] **V2 AsyncClient 绕开**：router 测试用 ASGITransport 不走 main app
- [x] **V2 commit 立即 push**：每 commit 立即 push 不累积
- [x] **业务指标先行**：5 个 B 指标（B1-B5）必测不通过即返工
- [x] **测试测业务指标**：B1-B5 脚本不是技术指标（200/typecheck）而是业务指标（命中率/延迟）

## 执行方式

**SDD**（子代理驱动），按 `sdd.mdc` 流程：

```
worktree 后端  /private/tmp/kbkkk-m3-backend  -b feat/m3-backend-routers
worktree 前端  /private/tmp/kbkkk-m3-frontend -b feat/m3-frontend-pages
                              ↓
              3.2 subagent（后端，新排序 3.2.0 → 3.2.2 → 3.2.6 → 3.2.1 → 3.2.3 → 3.2.4 → 3.2.5 → 3.2.7）
                              ↓ 等 3.2.6 merge
              3.3.0 + 3.3.5 subagent（前端 router + API client 前置）
                              ↓
        subagent-A（3.3.1-3.3.4）  ||  subagent-B（3.4.1-3.4.2）
                              ↓
              3.3.6 集成 PR + B1/B5 业务指标验证
```

**简报位置**（按 `sdd.mdc` 模板）：
- `kbkkk/.cursor/sdd/briefs/3.2.X.md` — 每个后端子任务（含"必读文件清单 + 已读断言 + 已知陷阱 + V2 教训相关段"）
- `kbkkk/.cursor/sdd/briefs/3.3.X.md` — 每个前端子任务
- `kbkkk/.cursor/sdd/reports/` — subagent 报告（含"已读文件清单 + 测试输出 + B 指标数字 + commit hash + push 时间戳"）
- `kbkkk/.cursor/sdd/progress.md` — 账本（含"风险排序 + push 时间戳 + B 指标通过情况"）

## V2 教训对账表（最终自检）

> **目的**：交付前确认每条 V2 教训都被 M3 plan 整合（不漏）

| V2 教训（source: SPEC-v2-round1-completion-report §7） | M3 整合位置 | 状态 |
|---|---|---|
| 7.1 校正节省 50% | subagent 必读文件清单（每个任务 §步骤 1） | ✅ |
| 7.1 PR 按风险排序 | 任务排序变更（DB→follow→注册→其余） | ✅ |
| 7.2 校正步骤价值 | subagent 简报"已知陷阱"段（§0） | ✅ |
| 7.3 测试环境兼容 | ASGITransport 不走 main app | ✅ |
| 7.4 commit 立即 push | 每任务 §步骤 N：git push | ✅ |
| 7.5 SPEC 文档治理 | 任务表含 commit hash + push timestamp | ✅ |
| 7.5 文档与代码同步 | progress.md 含 V2 对账表（此表） | ✅ |
