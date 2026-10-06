# K 线趋势分析系统 — SPEC v2.0（PM + 架构师双重视审视后）

> **日期**: 2026-10-06
> **版本**: v2.0（在 v1.0 基础上，依据 PM + 架构师专家 agent 审视修订）
> **来源**: v1.0 + 4 个 KB 蒸馏笔记 + [kbkkk-pm-review.md](file:///Users/hahaha/Desktop/CODE/meiduo-workspace/kb/notes/kbkkk-pm-review.md) + [kbkkk-architect-review.md](file:///Users/hahaha/Desktop/CODE/meiduo-workspace/kb/notes/kbkkk-architect-review.md)
> **核心变更**: 聚焦 BTC/ETH、删除多市场承诺、里程碑重排、模块边界重划、API 契约定 hybrid

**v1 → v2 主要差异**：

| 维度 | v1.0 | v2.0 | 变更理由 |
|---|---|---|---|
| 目标市场 | A 股 / 美股 / 加密 / 期货 | **仅 BTC/ETH**（crypto）| PM §1 — 与 README/代码严重错位 |
| Milestone 顺序 | M1→M2→M3→M4→M5 | **M1→M1.5→M3→M2→M4→M5** | PM §3 — 前后端并行、接口契约先行 |
| Follow 模块归属 | M3（前端混在一起）| **拆到 M4 execution 层** | Arch §1.2 — follow 是执行层不是前端 |
| API 契约 | 模糊 | **K线 REST + 信号 WebSocket** | 用户决策 |
| 回测策略 | Backtrader 集成 | **自研 JSONL + 命中率统计** | PM §4 + 用户决策 |
| 多指标引擎 | 两套并存 | **IndicatorEngine 委托 analytics/** | Arch §4 决策 B |

---

## 🎯 系统目标（v2 重写）

**专注加密货币短线交易者（BTC / ETH）的专业 K 线趋势分析平台**：

1. BTC / ETH 全周期 K 线数据（1m / 5m / 15m / 1h / 4h / 1d）+ ccxt 多源 fallback
2. 9 个技术指标（MA / MACD / RSI / 布林带 / KDJ / OBV / ADX / ATR / Hurst）
3. 多指标共振信号 + 置信度校准（Brier score < 0.25）
4. 轻量回测评估（JSONL + 命中率统计，不是 Backtrader）
5. macOS Sonoma 风格前端（毛玻璃 + K 线主图 + 信号标注）

**显式不做**（v1 → v2 砍掉）：
- A 股数据接入（akshare 链路）
- 美股数据接入（yfinance 链路）
- 缠论中枢 / 波浪 5 浪形态识别（M2 之后再考虑）
- 多 Provider 抽象层（等第二个数据源再加）
- Backtrader 完整集成（用轻量 JSONL 评估）

**未来扩展路径**（M5+ 之后）：M5 验收通过后再开 v3 spec 评估是否扩展到 A 股（仅在有真实用户需求时）。

---

## 📐 架构原则（10 条不可妥协，v1 保留 + v2 微调）

| # | 原则 | 来源 | 违反后果 |
|---|------|------|---------|
| 1 | **数据层 100% 就绪后，才能开 AI 层** | ai-trader 教训：实时数据进了死胡同 | 半成品功能 |
| 2 | **后端计算的数据，前端必须可视化** | ai-trader 教训：指标计算了不显示 | 数据无价值 |
| 3 | **每个 milestone 都有量化验收标准** | ai-trader 教训：49.8% 当 baseline | 形同虚设 |
| 4 | **TDD 先行：测试必须测业务指标** | ai-trader 教训：技术指标全过但业务失败 | 自欺欺人 |
| 5 | **design tokens 强制执行** | ai-trader 教训：颜色散乱 | 风格不一 |
| 6 | **同一概念不允许两套实现** | ai-trader 教训：Affinity Matrix 有名无实 | 维护灾难 |
| 7 | **FALLBACK 路径必须有降级逻辑** | ai-trader 教训：无 API key 就空白 | UX 断裂（**v2 强化：Redis 可选降级**）|
| 8 | **代码前先看 GitHub 调研** | ai-trader 自身规则 #8 | 闭门造车 |
| 9 | **骨架屏是感知性能核心** | ai-trader 教训：无骨架屏 | 用户感知慢 |
| 10 | **API 契约先于组件实现** | kline-system 新增（**v2 从"多市场交互矩阵"改写**）| 重构灾难 |

---

## 🗺️ 里程碑 + 量化验收标准（v2 重排）

> **重排理由**（PM §3）：M1.5 插在 M1/M2 之间提供最小可用 API，让前后端并行；M3 调到 M2 前以并行加速；M4 推后到 M2 后因为风控依赖真实信号。

### 进度状态（2026-10-06 实测）

| Milestone | v1 状态 | v2 实际 | 备注 |
|---|---|---|---|
| M1 数据基础设施 | 🟡 进行中 | 🟡 进行中 | 需砍 akshare/yfinance 验收项 |
| M1.5 K 线 API | 未规划 | ⚪ 未开始 | **新增** |
| M2 分析引擎 | ⏸️ 未开始 | ⏸️ 未开始 | analytics/ 目录有但无测试 |
| M3 前端可视化 | ⏸️ 未开始 | ⏸️ 未开始 | README 标错（实际 M3 follow 在 M4）|
| M4 API + 风控 | ⏸️ 未开始 | 🟡 部分完成 | follow_engine.py 已实现（347 行）|
| M5 集成 + 交付 | ⏸️ 未开始 | ⚪ 未开始 | |

---

### M1: 数据基础设施（2 周）— 聚焦 BTC/ETH + ccxt

**目标**: 任何 dev 拉起服务，30 秒内拉到 BTC 或 ETH 1 年 K 线数据。

| 子模块 | 量化验收（v2 改） | 必测场景 |
|--------|---------|---------|
| 1.1 数据获取层 | ccxt（Binance primary）+ 1 个 fallback（Hyperliquid / OKX 任选），<br>延迟 < 3s/请求 | BTC-USDT/1d、ETH-USDT/1h |
| 1.2 数据存储层 | PostgreSQL schema + 索引，<br>1000 根 K 线查询 < 50ms | kline / indicator / signal / trade_log 4 张表 |
| 1.3 Redis 缓存 | **Redis 可选降级**（AI-Trader 模式）：<br>`redis_client is None → return None`，<br>命中率 ≥ 80%（有 Redis 时）| 重复请求同一 K 线返回缓存 |
| 1.4 数据质量 | 缺失 / 异常值标记 100% 覆盖 | 缺交易日、长假期、API 限流 |
| 1.5 测试 | **业务指标测试**：<br>数据完整率 ≥ 99% | mock + 真实 BTC/ETH 数据双测 |

**门禁**: M1 未达 80% 验收标准，**禁止开始 M1.5**。

---

### M1.5: 最小 K 线 API（1 周）— 新增

**目标**: 前端团队可在 M2 信号未就绪时，开始联调 K 线图。

| 子模块 | 量化验收 |
|--------|---------|
| 1.5.1 `GET /api/v1/kline/{symbol}` | 返回 BTC/ETH K 线，<br>**REST 接口**（hybrid 决策：K 线 REST、信号 WebSocket）|
| 1.5.2 错误码语义化 | 400/404/429/500 区分 |
| 1.5.3 p95 < 200ms | 1 万根 K 线查询（**含分页/游标**，非一次性返回） |

**门禁**: M1.5 上线后，**M2 与 M3 可并行启动**。

---

### M2: 分析引擎（3 周）— 砍掉形态 + 聚焦信号

**目标**: 信号命中率达到显著超过 50% 基准（仅 BTC/ETH）。

| 子模块 | 量化验收（v2 改） |
|--------|---------|
| 2.1 指标计算 | **`IndicatorEngine` 委托 `analytics/`**（Arch §4 决策 B），<br>9 个指标（MA/MACD/RSI/布林带/KDJ/OBV/ADX/ATR/Hurst），<br>**禁止两套同名实现** |
| 2.2 ~~形态识别~~ | **砍掉**（PM §4：缠论中枢 + 波浪 5 浪移到 v3+）|
| 2.3 信号生成 | **命中率 > 55%**（BTC + ETH × 5 个周期平均），<br>**置信度校准**：Brier score < 0.25，<br>**Evaluation Cliff**：< 0.6 置信度信号不展示 |
| 2.4 ~~Backtrader 集成~~ | **改为 JSONL 评估器**（自研）：<br>写 `data/backtests/{date}.jsonl`，每行一条信号+ N 根后盈亏，<br>统计命中率 / 置信度校准曲线 |
| 2.5 outcome tracking | 信号发出后 N 根 K 线自动跟踪盈亏，写回 `signal_outcomes` 表 |
| 2.6 测试 | 业务指标测试：**命中率 / Brier score / 多指标一致性** |

**门禁**: M2 命中率 < 55% 时，**禁止上线**，必须继续优化或降级方案（用 evaluation cliff 阈值过滤）。

---

### M3: 前端可视化（4 周）— 与 M2 并行

**目标**: Lighthouse 性能 ≥ 90，无障碍 ≥ 95，**毛玻璃 + K 线主图 + 信号标注**先就位。

| 子模块 | 量化验收 |
|--------|---------|
| 3.0 设计系统 | macOS Sonoma tokens.ts 落地（强制执行）|
| 3.1 路由 + 骨架 | 路由级懒加载 + Suspense fallback = GlassSkeleton |
| 3.2 K 线主图 | lightweight-charts WebGL，1 万根 K 线滚动 ≥ 50fps |
| 3.3 指标叠加 | 所有后端指标必须显示（ai-trader 教训）|
| 3.4 信号标注 | markers 接口接通（ai-trader "已预留但未接入"反面教材），<br>**WebSocket 推送**（hybrid 决策）|
| 3.5 共享元素 | layoutId 周期切换 + 入场 stagger |
| 3.6 智能预取 | usePrefetchSymbol（hover 150ms 预取）+ ⌘K 命令面板 |
| 3.7 响应式 | 3 个断点全测 |
| 3.8 Lighthouse | 性能 ≥ 90 / 无障碍 ≥ 95 / LCP < 2.5s / FPS ≥ 50 |

---

### M4: 执行层 + 风控（2 周）— 从 M3 拆出

> **变更**：原 M4 = "API + 风控"，但 `follow/` 已在 M3 阶段实现。v2 拆为 M4.1（执行层）和 M4.2（监控）。

| 子模块 | 量化验收 |
|--------|---------|
| 4.1 执行引擎 | `backend/app/execution/` 目录（从 `follow/` 迁出），<br>5 门控检查 + SL/TP（ATR/支撑位/固定比例） / 盈亏比 ≥ 2:1 |
| 4.2 信号 WebSocket | `/ws/signals` 推送新信号，<br>**JSON schema 锁定**（M3.4 markers 依赖此 schema）|
| 4.3 监控告警 | Prometheus + Grafana，**p95 < 200ms**，<br>已有（commit 8fb2272 SRE 监控）|

---

### M5: 集成 + 交付（1 周）

| 子模块 | 量化验收 |
|--------|---------|
| 5.1 端到端 | happy path：拉数据 → 算指标 → 出信号 → JSONL 评估 → 展示 |
| 5.2 Docker | docker-compose 一键启动（**Redis 可选**） |
| 5.3 文档 | 用户手册 + 开发者文档 + 运维文档 |

---

## 🏛️ 模块边界（v2 新增 — Arch §3）

> **变更要点**（Arch §3）：
> 1. 新增 `infrastructure/` 层：统一生命周期 + DI
> 2. `follow/` → `execution/`（语义清晰）
> 3. `signal_service` 改为 DI 注入 `AnalyticsEngine`（消除内联实例化）

```
┌──────────────────────────────────────────────────────────────────┐
│                        FastAPI (main.py)                        │
│  lifespan: init_redis → init_db → set_signal_bus               │
│            close_redis ← close_db ← (倒序)                      │
└────────────────────────┬───────────────────────────────────────┘
                         │ inject via __init__
┌────────────────────────▼───────────────────────────────────────┐
│  Layer 1: 基础设施 (infrastructure/)                           │
│  ┌─────────┐ ┌─────────┐ ┌──────────────────┐ ┌─────────────┐ │
│  │cache.py│ │db.py    │ │resource_manager.py│ │config.py    │ │
│  │(Redis 可│ │(Postgres│ │(统一生命周期+DI)  │ │(.env加载)   │ │
│  │ 选降级)│ │ +SQLite) │ │                   │ │             │ │
│  └─────────┘ └─────────┘ └──────────────────┘ └─────────────┘ │
└────────────────────────┬───────────────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────────────┐
│  Layer 2: 数据层 (data/)                                       │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────────────────┐  │
│  │data_fetcher.py│ │normalize.py  │ │market_adapter.py      │  │
│  │(ccxt+fallback)│ │(统一列名)   │ │(24/7 流动性检测)      │  │
│  └──────────────┘ └──────────────┘ └────────────────────────┘  │
└────────────────────────┬───────────────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────────────┐
│  Layer 3: 分析层 (analytics/) — 纯 numpy，M2 核心              │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────────────────┐  │
│  │trend.py      │ │statistical.py│ │volatility.py           │  │
│  │(ADX/MACD/SMA)│ │(Hurst/熵)   │ │(ATR/波动率)           │  │
│  └──────────────┘ └──────────────┘ └────────────────────────┘  │
│  ┌──────────────┐ ┌──────────────┐                            │
│  │signal_direc. │ │confluence.py │                            │
│  │(generate_sig)│ │(多指标共振)  │                            │
│  └──────────────┘ └──────────────┘                            │
└────────────────────────┬───────────────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────────────┐
│  Layer 4: 服务层 (services/)                                    │
│  ┌────────────────────┐ ┌──────────────┐ ┌──────────────────┐   │
│  │indicator_engine.py │ │signal_service│ │event_bus.py      │   │
│  │(pandas兼容层,DI)   │ │(协调器,DI)   │ │(模块级单例,DI)   │   │
│  └────────────────────┘ └──────────────┘ └──────────────────┘   │
│  ┌────────────────────┐ ┌──────────────┐ ┌──────────────────┐   │
│  │calibration.py      │ │outcome_track.│ │backtest_logger   │   │
│  │(PAVA Isotonic,M2.5)│ │(M2.5)       │ │(JSONL 评估器)    │   │
│  └────────────────────┘ └──────────────┘ └──────────────────┘   │
└────────────────────────┬───────────────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────────────┐
│  Layer 5: 执行层 (execution/) — 从 follow/ 迁出                 │
│  ┌────────────────────┐ ┌──────────────┐ ┌──────────────────┐   │
│  │execution_engine.py │ │risk_manager. │ │position_sizer.py  │   │
│  │(市场执行gate,DI)   │ │(5门控,DI)    │ │(仓位计算,DI)     │   │
│  └────────────────────┘ └──────────────┘ └──────────────────┘   │
│  ┌────────────────────┐                                        │
│  │trade_recorder.py   │                                        │
│  │(TradeLog持久化,DI) │                                        │
│  └────────────────────┘                                        │
└────────────────────────┬───────────────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────────────┐
│  Layer 6: 路由层 (routers/)                                    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │kline.py — 注入 data_fetcher + indicator_engine + cache  │    │
│  └──────────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────┘
```

**依赖方向规则**：
- **外向内**：路由 → 服务 → 分析/数据 → 基础设施
- **禁止反向依赖**：分析层（analytics/）**不能** import 服务层（services/）
- **注入点**：所有 `__init__` 接受依赖项；模块内禁止 `import singleton`

---

## 📦 复用清单（v2 修订）

### 直接复用（零修改或最小修改）

| 模块 | 来源 | 复用方式 | 风险评估 |
|------|------|---------|---------|
| `analytics/trend.py` (ADX/MACD/SMA) | ai-trader | 复制到 `backend/app/analytics/trend.py` | 低（纯 numpy） |
| `analytics/statistical.py` (Hurst/fractal/Shannon) | ai-trader | 复制 | 低 |
| `analytics/volatility.py` (ATR) | ai-trader | 复制 | 低 |
| `services/signal_change_bus.py` | ai-trader | 复制 → `event_bus.py` | 低 |
| `services/calibration_trainer.py` (PAVA Isotonic) | ai-trader | 复制 → `calibration.py` | 低 |
| `data/basemodel_to_df()` | OpenBB | 引用统一 DataFrame 转换 | 低（关键统一层）|
| `validate_window()` rolling 校验 | OpenBB | `indicators.py` 每个 `_calc_*` 前置 | 低 |
| Vibe-Trading frozen dataclass | Vibe-Trading | `models/position.py` 不可变头寸 | 低 |
| AI-Trader Redis 降级模式 | AI-Trader | `cache.py` 实现可选降级 | 低（**v2 强制**）|

### 参考但不复用

| 模块 | 原因 |
|------|------|
| `agent/agent.py` (TrendAgent) | kline-system 走 kline-analyst agent 路径，不复用此分层 |
| `app/agent/prompts.py` | 中文 prompt 可参考，但 RAG 集成方式要重做 |
| `app/data/okx_ws.py` | kline-system 用 ccxt 全市场，复用面窄 |
| `services/github_sync.py` | kline-system 不需要 GitHub 同步 |
| 前端 `LightweightKlineChart.tsx` | v4 → v5 API 变了 + macOS 风格要重写 |

### 绝对不碰的坑

| 坑 | 位置 | kline-system 怎么做 |
|----|------|-------------------|
| 命中率 49.8% 接受为 baseline | `reports/bt-baseline-*.md` | M2.3 验收：必须 > 55%，否则不上线 |
| affinity matrix 有名无实 | `services/signal_change_bus.py` 等 | M2.1 用 ai-trader `multi_indicator_confluence`，但**必须接测试** |
| markers 接口"已预留但未接入" | `LightweightKlineChart.tsx` line 240 | M3.4 验收：markers 必须接通，测试覆盖 |
| 指标计算了不显示 | analytics → 前端未打通 | M3.3 验收：所有后端指标必须前端可见 |
| Redis 配了不用 | `config.py` 有 redis_url | **v2 改**：M1.3 验收 = Redis 可选降级 + 命中率 ≥ 80% |
| AGENTS.md 规则比实现多 | `AGENTS.md` 9 条 | 规范精简到 **本 SPEC 的 10 条原则 + 各 milestone 验收表** |
| `_global_state` 模式 | ClawWork | **不引入**（反模式，与 DI 冲突）|
| Backtrader 全套量化 | **v2 移除** | 用 JSONL + 自研轻量评估器 |

---

## 🔄 与现有代码的集成策略（v2 修订）

### 现有 assets

```
backend/
├── app/
│   ├── cache.py               # 已有 Redis 缓存（基本骨架）— v2 加降级
│   ├── config.py              # 已有配置
│   ├── db.py                  # 已有 DB 连接（仅 PostgreSQL）— v2 加 SQLite 适配
│   ├── main.py                # FastAPI 入口
│   ├── models/__init__.py     # 数据模型
│   ├── routers/kline.py       # K 线 API
│   ├── services/
│   │   ├── data_fetcher.py    # 已有（akshare/yfinance/ccxt）— v2 砍 akshare/yfinance
│   │   ├── indicators.py      # 已有（pandas 引擎）— v2 重构为 DI 薄封装
│   │   ├── signal_service.py  # 内联 AnalyticsEngine 实例化 — v2 改为 DI
│   │   ├── event_bus.py       # 新增
│   │   └── calibration.py     # 新增（PAVA Isotonic）
│   ├── analytics/             # 纯 numpy（trend/statistical/volatility/signal_direction/confluence）
│   ├── execution/             # ★ v2 从 follow/ 迁出（execution_engine / risk_manager / position_sizer）
│   └── utils/
└── requirements.txt
```

### 集成方案（v2 重写）

1. **`services/indicators.py` 重构为 `IndicatorEngine`**，内部委托给 `analytics/` + 维护 pandas 兼容层（**Arch §4 决策 B**）
2. **`services/signal_service.py` DI 改造**：构造函数接受 `analytics_engine: AnalyticsEngine`，消除内联实例化（`signal_service.py:69`）
3. **`cache.py` 加 Redis 可选降级**：`redis_client is None → return None`，所有 `cache_get/cache_set` 调用自动支持
4. **`db.py` 加 SQLite 适配**：`DB_BACKEND=sqlite|postgres` 环境变量，运行时路由（开发体验）
5. **`follow/` 目录迁出到 `execution/`**：5 门控 + SL/TP + 仓位计算逻辑保留，目录名重命名
6. **新增 `services/event_bus.py`**：模块级单例 + DI 注入，发布信号变化事件
7. **新增 `services/calibration.py`**：PAVA Isotonic 置信度校准（M2.3 验收）
8. **新增 `services/backtest_logger.py`**：JSONL append-only 评估器（M2.4 替代 Backtrader）
9. **`follow_engine.py:179` 异步化**：`on_market_update` 改 `async def`，删 `asyncio.run()`

---

## 📊 业务指标验收表（kline-system 特有）

| 指标 | 目标值 | 测试场景 | 验证方式 |
|------|--------|---------|---------|
| 信号命中率 | > 55%（BTC + ETH × 5 周期平均）| 2025 年 BTC/ETH 历史 | JSONL 评估器 |
| 置信度校准（Brier）| < 0.25 | 同上 | PAVA Isotonic |
| K 线查询延迟 | p95 < 200ms | 1 万根 BTC/1d | locust |
| Redis 命中率 | ≥ 80%（有 Redis 时）| 重复请求同一 K 线 | Prometheus |
| 数据完整率 | ≥ 99% | mock + 真实数据 | 业务指标测试 |
| 前端 Lighthouse | ≥ 90 | K 线主图 + 信号叠加 | Chrome DevTools |

---

## 📁 目录约定（kline-system 标准）— v2 更新

```
kbkkk/
├── SPEC.md                    # 本文件（团队宪法 v2.0）
├── README.md                  # 项目说明
├── project-tasks/             # 任务清单 + 进度
│   └── 00-tasklist.md
├── docs/
│   ├── architecture/          # 架构图 + spec
│   ├── runbooks/              # 运维手册
│   └── lessons-from-ai-trader.md  # ai-trader 教训汇总
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── infrastructure/    # ★ v2 新增（统一生命周期+DI）
│   │   ├── data/              # 数据层（Layer 2）
│   │   ├── analytics/         # 纯 numpy 高级指标（Layer 3）
│   │   ├── services/          # 协调器（Layer 4）
│   │   ├── execution/         # ★ v2 从 follow/ 迁出（Layer 5）
│   │   └── routers/           # API 端点（Layer 6）
│   ├── tests/
│   └── requirements.txt
├── data/
│   └── backtests/             # ★ v2 新增（JSONL 评估输出）
│       └── 2026-XX-XX.jsonl
├── frontend/
│   ├── design-system/         # macOS Sonoma tokens
│   ├── components/
│   └── pages/
└── deploy/
    └── docker-compose.yml     # ★ v2：Redis 可选
```

---

## 🛠️ v2 立即可执行的技术债清单（Arch §5）

> **下个 sprint 第一个 PR**（Arch §6 反思）：把 `indicators.py` 重构为 `IndicatorEngine` DI 封装 + 补 `test_business_metrics.py`。

| # | 位置 | 问题 | KB 参考 | 立即可改 | 工作量 |
|---|------|------|---------|---------|--------|
| 1 | `services/indicators.py` `_calc_obv` | Python for 循环（慢）| OpenBB 纯 numpy rolling | 向量化 | 0.5h |
| 2 | `signal_service.py:69` | 内联 `AnalyticsEngine()` 实例化 | Vibe-Trading DI 模式 | `__init__` 注入 | 1h |
| 3 | `follow_engine.py:179` | `asyncio.run()` 在同步方法内 | Vibe-Trading async hook | `on_market_update` 改 `async def` | 2h |
| 4 | `cache.py` | Redis 失败直接抛异常 | AI-Trader `redis_client is None → None` | 加降级 | 0.5h |
| 5 | `db.py` | 仅 PostgreSQL | AI-Trader SQLite/Postgres 双后端 | 加 `DB_BACKEND` 环境变量 | 1d |
| 6 | `data_fetcher.py:290` | 每次新 `ccxt.binance()` | Vibe-Trading 连接复用 | 类级 `exchange_cache` | 0.5h |
| 7 | `routers/kline.py:39-42` | `cache_set` 失败阻塞 API | ClawWork JSONL 幂等 | 失败只 log 不抛 | 0.5h |
| 8 | `analytics/` 全目录 | 无单元测试 | OpenBB APIEx 测试 | `test_signal_direction.py` | 2d |

**下 4 个 PR 顺序建议**：
1. PR-1：#1 + #2 + #4（信号 pipeline 端到端可测，1 天）
2. PR-2：#3 + #6（follow 异步化 + 连接复用，1 天）
3. PR-3：#5（SQLite 适配，降低开发门槛，1 天）
4. PR-4：#7 + #8（cache 降级 + analytics 测试，3 天）

---

## 🚦 质量门禁（每个 PR 必过）

1. **代码覆盖率** ≥ 80%（业务模块）
2. **类型检查** mypy strict + tsc --noEmit
3. **业务指标测试**（不是技术测试）必须新增 / 更新
4. **场景覆盖矩阵** ≥ 3 个用户场景（多周期/多标的/桌面/移动）
5. **ai-trader 教训自检**：勾选 10 条原则，有违反必须 PR 描述解释
6. **架构边界自检**（v2 新增）：模块导入方向符合「路由 → 服务 → 数据/分析 → 基础设施」

---

## 🔗 引用

- [ai-trader 架构复盘 Canvas](.cursor/canvases/ai-trader-architecture-review.canvas.tsx)
- [kline-frontend 规范](../.cursor/agents/kline-frontend.md)（macOS Sonoma 设计系统）
- [kline-analyst 规范](../.cursor/agents/kline-analyst.md)
- [kline-backend 规范](../.cursor/agents/kline-backend.md)
- [kline-orchestrator 规范](../.cursor/agents/kline-orchestrator.md)
- [kline-pm 任务清单](../kbkkk/project-tasks/00-tasklist.md)
- **v2 审视依据**：
  - [kbkkk-pm-review.md](file:///Users/hahaha/Desktop/CODE/meiduo-workspace/kb/notes/kbkkk-pm-review.md)（PM agent）
  - [kbkkk-architect-review.md](file:///Users/hahaha/Desktop/CODE/meiduo-workspace/kb/notes/kbkkk-architect-review.md)（架构师 agent）
- **KB 蒸馏笔记（实施可用版）**：
  - [openbb-implementation-ready.md](file:///Users/hahaha/Desktop/CODE/meiduo-workspace/kb/notes/openbb-implementation-ready.md)
  - [vibetrading-implementation-ready.md](file:///Users/hahaha/Desktop/CODE/meiduo-workspace/kb/notes/vibetrading-implementation-ready.md)
  - [aitrader-implementation-ready.md](file:///Users/hahaha/Desktop/CODE/meiduo-workspace/kb/notes/aitrader-implementation-ready.md)
  - [clawwork-implementation-ready.md](file:///Users/hahaha/Desktop/CODE/meiduo-workspace/kb/notes/clawwork-implementation-ready.md)