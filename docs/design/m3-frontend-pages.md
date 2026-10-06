# M3 前端补齐：7 个页面 + 后端 5 个新 Router

> **日期**: 2026-10-06
> **版本**: v0.1（草案）
> **范围**: kbkkk.com 前端从 1 页（K线 + 4 tab）扩展到 7 页
> **前置**: M5 阶段 2 已上线（[PR #26](https://github.com/bobing888/kbkkk/pull/26) + [PR #27](https://github.com/bobing888/kbkkk/pull/27)，commit `d2f33b5`）
> **状态**: 等用户批准

---

## 🎯 目标

参考 [bobing888/ai-trader](https://github.com/bobing888/ai-trader) 的**交互模式**（不复用代码，教训 #1），把 kbkkk.com 前端从单页扩展为 7 页：

| # | 页面 | 路径 | 优先级 | 后端位置 |
|---|---|---|---|---|
| 1 | **KlinePage**（已有） | `/` | ✅ 已上线 | `routers/kline.py` |
| 2 | **AnalysisPage** | `/analysis/:symbol` | P2 | `routers/analysis.py` 扩展 |
| 3 | **RecommendationsPage** | `/recommendations` | **P0** | 新增 `routers/signal_batch.py` + `routers/follows.py` |
| 4 | **StrategyPage** | `/strategies` | **P0** | 新增 `routers/strategies.py` + `routers/github_sync.py` |
| 5 | **TradesPage** | `/trades` | P1 | 新增 `routers/trades.py` |
| 6 | **BacktestPage** | `/backtest` | P2 | 新增 `routers/backtest.py` |
| 7 | **FollowsPage** | `/follows` | P1 | `routers/follows.py`（同 P0）|
| 8 | **SettingsPage** | `/settings` | P2 | 本地状态，无后端 |

**P0 = 核心需求，P1 = 重要，P2 = 加分**。阶段 3 必做 P0+P1，P2 后续。

---

## 📦 复用清单（ai-trader 借鉴）

| ai-trader 模块 | kbkkk 处理 | 教训 |
|---|---|---|
| `pages/RecommendationsPage.tsx` (936 行) | **重写**，借鉴"批量 6 币 × 4 周期"布局 | 教训 #1（命中率 > 55%）|
| `pages/StrategyPage.tsx` (789 行) | **重写**，借鉴 CRUD + GitHub 同步 UI | 教训 #5（license header）|
| `lib/api.ts` 46 个函数 | **逐个新写**到 `frontend/src/api/*.ts` | 不抄代码 |
| `pages/BacktestPage.tsx` | 借鉴"双栏（参数 + 收益曲线）"布局 | — |

---

## 🏗️ 架构

### 路由层

```
React Router 7 (已装)
├── /                  → KlinePage (已有)
├── /analysis/:symbol  → AnalysisPage
├── /recommendations   → RecommendationsPage
├── /strategies        → StrategyPage
├── /trades            → TradesPage
├── /follows           → FollowsPage
├── /backtest          → BacktestPage
└── /settings          → SettingsPage
```

### 后端增量

| Router | 端点（最小集）| 估算行数 |
|---|---|---|
| `routers/strategies.py` | `GET/POST/PUT/DELETE /api/v1/strategies` + `GET /api/v1/strategies/:id` + `POST :id/clone` + `GET :id/export` + `POST /import` | 200 |
| `routers/follows.py` | `GET/POST /api/v1/follows` + `GET /api/v1/follows/:id` + `POST :id/close` + `POST :id/cancel` | 150 |
| `routers/signal_batch.py` | `GET /api/v1/signals/batch?symbols=...&period=...` + `GET /api/v1/signal/:symbol?period=...` | 150 |
| `routers/trades.py` | `GET /api/v1/trades` + `GET /api/v1/trades/summary` | 100 |
| `routers/github_sync.py` | `POST /api/v1/strategies/sync-github` + `GET /api/v1/strategies/sync-github/status` | 120 |
| `routers/backtest.py`（可选 P2） | `POST /api/v1/backtest/run` + `GET /api/v1/backtest/:id` | 200 |

总计 ~1120 行后端 + ~2500 行前端 + 测试。

### 关键技术决策

1. **不复用 ai-trader 任何代码**（教训 #1），只借鉴交互模式
2. **GitHub 同步**：用 GitHub REST API `repos/{owner}/{repo}/contents` 拉策略 .py 文件，token 走环境变量
3. **批量信号**：复用现有 `IndicatorEngine + generate_signal` 在 asyncio 任务里并行循环多 symbol
4. **数据持久化**：复用现有 PG schema（已含 `orders`/`signals`/`follows`/`strategies` 表）
5. **前端路由**：react-router-dom 7（已装）
6. **实时性**：跟单状态用轮询（5s），避免 WebSocket 复杂度
8. **前端代码组织**：新增 `pages/` 目录（模仿 ai-trader）+ 复用现有 `components/common/` + `components/KLineChart/` + `hooks/`

---

## 📅 阶段拆分

### 3.1 设计文档（本文档）

- ✅ 完成

### 3.2 后端 5 router

| 子阶段 | 工作 | 验证 |
|---|---|---|
| 3.2.1 | `routers/strategies.py` + 6 测试 | pytest 跑过 + curl POST/GET |
| 3.2.2 | `routers/follows.py` + 5 测试 | 同上 |
| 3.2.3 | `routers/signal_batch.py` + 4 测试 | 同上（需 OKX 真实数据）|
| 3.2.4 | `routers/trades.py` + 3 测试 | 同上 |
| 3.2.5 | `routers/github_sync.py` + 3 测试 | 同上 |
| 3.2.6 | `routers/__init__.py` 注册新 router | 全量 pytest 362+ 通过 |
| 3.2.7 | PR + 部署 + prod curl 端到端 | prod 6 端点 200 |

### 3.3 前端 4 个 P1 页面（Analysis + Trades + Backtest + Follows）

| 子阶段 | 工作 | 验证 |
|---|---|---|
| 3.3.1 | `pages/AnalysisPage.tsx` | npm build 0 错 + 浏览器截图 |
| 3.3.2 | `pages/TradesPage.tsx` | 同上 |
| 3.3.3 | `pages/FollowsPage.tsx` | 同上 |
| 3.3.4 | `pages/BacktestPage.tsx` | 同上 |
| 3.3.5 | `App.tsx` 加 react-router 配置 + 顶部导航 | 同上 |

### 3.4 前端 2 个 P0 页面（Recommendations + Strategy）

| 子阶段 | 工作 | 验证 |
|---|---|---|
| 3.4.1 | `pages/RecommendationsPage.tsx`（重写，300-400 行）| npm build + 浏览器截图 |
| 3.4.2 | `pages/StrategyPage.tsx`（重写，400-500 行）| 同上 |

### 3.5 Caddy + 端到端

- `caddy reload`（Caddyfile 不变，SPA fallback 已就位）
- 浏览器验证 7 页 + 截图

---

## ⚠️ 风险

| 风险 | 应对 |
|---|---|
| ai-trader 前端 2200 行全重写，单 PR 难合 | 按 3.2/3.3/3.4 分 3 PR |
| 后端 strategy 表 PG 没建 | 检查 schema.sql，缺则先建表 |
| GitHub API 速率（未授权 60/h）| 测试用 mock repo |
| 跟单状态实时性差 | 5s 轮询（够用） |
| 后端 router 间循环依赖 | 严格分层：router → service → model |

---

## 🎯 阶段 3 完成定义

- ✅ 后端 5 router 上线 + 全量 380+ pytest 通过
- ✅ 前端 7 页全部可访问 + React Router 配置
- ✅ kbkkk.com 浏览器实测 7 页全部 200 + 截图
- ✅ 0 个 ai-trader 代码片段被复制（仅借鉴 UI 模式）
- ✅ 端到端：BTC/ETH/SOL 推荐单 + 策略 CRUD + 跟单生命周期全流程通

---

## 📚 参考

- 教训清单：`/Users/hahaha/.cursor/rules/personal-coding-style.mdc` + `/Users/hahaha/Desktop/CODE/kbkkk/SPEC.md`
- ai-trader 源（本地优化）:/opt/ai-trader/frontend/src/pages/ + `lib/api.ts`
- kbkkk 后端现有：backend/app/routers/kline.py + analysis.py
- 已合 PR：[#26](https://github.com/bobing888/kbkkk/pull/26) 后端 + [#27](https://github.com/bobing888/kbkkk/pull/27) 前端

---

## 🔄 后续会话推进指南

**新会话第一步**：

```bash
# 1. recall 阶段 3 设计
npx @jnmetacode/engram recall "kbkkk 阶段 3 设计 7 页 5 router"

# 2. 读设计文档
cat /Users/hahaha/Desktop/CODE/kbkkk/docs/design/m3-frontend-pages.md

# 3. 拉最新 main
cd /Users/hahaha/Desktop/CODE/kbkkk && git checkout main && git pull

# 4. 建 worktree（后端 / 前端 两个）
git worktree add /tmp/kbkkk-m3-backend -b feat/m3-backend-routers origin/main
git worktree add /tmp/kbkkk-m3-frontend -b feat/m3-frontend-pages origin/main

# 5. 派 subagent 并行推进 3.2 + 3.3/3.4
# (按 SDD 规则，每个 task 一个 fresh subagent)
```

**每个子任务流程**：TDD 红 → 绿 → 重构 → PR → 等 CI → auto-merge → 部署验证。