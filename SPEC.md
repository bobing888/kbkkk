# K 线趋势分析系统 — 完整 SPEC（基于 ai-trader 复盘）

> **日期**: 2026-10-04
> **版本**: v1.0（首次正式 spec）
> **来源**: 完整复盘 [bobing888/ai-trader](https://github.com/bobing888/ai-trader) 后，**谨慎复用**成熟模块
> **核心原则**: **规范 = 验收标准，不是愿望清单**（ai-trader 教训 #1）

---

## 🎯 系统目标

**为 A 股 / 美股 / 加密 / 期货交易者提供**专业级 K 线分析平台：

1. 多市场 K 线数据获取 + 持久化（A 股红涨绿跌 / 美股绿涨红跌 / 加密绿涨红跌）
2. 实时技术指标计算（MA / MACD / RSI / 布林带 / KDJ / OBV / ADX / Hurst）
3. 形态识别 + 买卖信号生成（含置信度）
4. 跟单回测 + 风险控制
5. macOS Sonoma 风格前端（毛玻璃 + spring 物理 + 智能预取）

---

## 📐 架构原则（10 条不可妥协）

| # | 原则 | 来源 | 违反后果 |
|---|------|------|---------|
| 1 | **数据层 100% 就绪后，才能开 AI 层** | ai-trader 教训：实时数据进了死胡同 | 半成品功能 |
| 2 | **后端计算的数据，前端必须可视化** | ai-trader 教训：指标计算了不显示 | 数据无价值 |
| 3 | **每个 milestone 都有量化验收标准** | ai-trader 教训：49.8% 当 baseline | 形同虚设 |
| 4 | **TDD 先行：测试必须测业务指标** | ai-trader 教训：技术指标全过但业务失败 | 自欺欺人 |
| 5 | **design tokens 强制执行** | ai-trader 教训：颜色散乱 | 风格不一 |
| 6 | **同一概念不允许两套实现** | ai-trader 教训：Affinity Matrix 有名无实 | 维护灾难 |
| 7 | **FALLBACK 路径必须有降级逻辑** | ai-trader 教训：无 API key 就空白 | UX 断裂 |
| 8 | **代码前先看 GitHub 调研** | ai-trader 自身规则 #8 | 闭门造车 |
| 9 | **骨架屏是感知性能核心** | ai-trader 教训：无骨架屏 | 用户感知慢 |
| 10 | **多市场交互矩阵先于组件实现** | kline-system 新增 | 重构灾难 |

---

## 🗺️ 里程碑 + 量化验收标准

### M1: 数据基础设施（2 周）

**目标**: 任何 dev 拉起服务，30 秒内拉到任意市场的 1 年 K 线数据。

| 子模块 | 量化验收 | 必测场景 |
|--------|---------|---------|
| 1.1 数据获取层 | 3 个数据源全跑通（akshare/yfinance/ccxt），<br>延迟 < 5s/请求 | A股 600519/1d、US AAPL/1h、Crypto BTC-USDT/5m |
| 1.2 数据存储层 | PostgreSQL schema 完整 + 索引优化，<br>1000 根 K 线查询 < 50ms | K线/指标/信号/订单 4 张表 |
| 1.3 Redis 缓存 | **必须实际使用**（ai-trader 教训：配了不用），<br>命中率 ≥ 80% | 重复请求同一 K 线时返回缓存 |
| 1.4 数据质量 | 复权 / 缺失 / 涨跌停 / 停牌标记 100% 覆盖 | A 股复权日、停牌日、ST 日 |
| 1.5 测试 | **业务指标测试**，不只是 HTTP 200：<br>数据完整率 ≥ 99%，<br>涨跌停标记准确率 100% | mock + 真实数据双测 |

**🚦 门禁**: M1 未达 80% 验收标准，**禁止开始 M2**。

### M2: 分析引擎（3 周）

**目标**: 信号命中率达到显著超过 50% 的基准（ai-trader 49.8% ≈ 随机，是反面教材）。

| 子模块 | 量化验收 | 必测场景 |
|--------|---------|---------|
| 2.1 指标计算 | **复用 ai-trader analytics + kline-system 现有 pandas 引擎**，<br>6 个核心指标 + 5 个高级指标（ADX/Hurst/ATR/多指标共振/信号方向）<br>**不允许两套同名实现** | BTC-USDT 1h 历史数据回放 |
| 2.2 形态识别 | 单 K 10 种 + 组合 K 9 种 + 缠论中枢 + 波浪 5 浪驱动 | A 股 600519 历史 3 年回放 |
| 2.3 信号生成 | **命中率 > 55%**（5 个时间周期平均），<br>**置信度校准**：Brier score < 0.25 | 2025 年 BTC/ETH/AAPL 历史回测 |
| 2.4 跟单回测 | Backtrader 集成，<br>**含 A 股特殊规则**（T+1/涨跌停） | mock 数据端到端回测 |
| 2.5 outcome tracking | 实时跟踪信号 N 根 K 线后的盈亏，<br>写回 DB 用于 M2.3 校准 | 24h 自动校准任务 |
| 2.6 测试 | 业务指标测试：**命中率 / 置信度校准 / 多指标一致性** | 7 个时间周期 + 5 个标的 |

**🚦 门禁**: M2 命中率 < 55% 时，**禁止上线**，必须继续优化或降级方案。

### M3: 前端可视化（4 周）

**目标**: Lighthouse 性能 ≥ 90，无障碍 ≥ 95，**毛玻璃 + spring 物理 + 智能预取**全部就位。

| 子模块 | 量化验收 |
|--------|---------|
| 3.0 设计系统 | macOS Sonoma tokens.ts 落地，<br>**强制执行**（不允许多 color 散落） |
| 3.1 路由 + 骨架 | 路由级懒加载 + Suspense fallback = GlassSkeleton |
| 3.2 K 线主图 | lightweight-charts WebGL，1 万根 K 线滚动 ≥ 50fps |
| 3.3 指标叠加 | **所有后端指标必须显示在图表**（ai-trader 教训） |
| 3.4 信号标注 | markers 接口完整接通（ai-trader "已预留但未接入"反面教材） |
| 3.5 共享元素 | layoutId 周期切换 + 入场 stagger |
| 3.6 智能预取 | usePrefetchSymbol（hover 150ms 预取）+ ⌘K 命令面板 |
| 3.7 响应式 | 3 个断点全测，**不允许"桌面能用移动端"** |
| 3.8 Lighthouse | 性能 ≥ 90 / 无障碍 ≥ 95 / LCP < 2.5s / FPS ≥ 50 |

### M4: API + 风控（2 周）

| 子模块 | 量化验收 |
|--------|---------|
| 4.1 风控引擎 | 仓位 ≤ 30% / 总仓 ≤ 70% / 止损止盈（ATR/支撑位/固定比例） / 盈亏比 ≥ 2:1 |
| 4.2 FastAPI | REST + WebSocket + 版本控制 + 自动文档 |
| 4.3 监控告警 | Prometheus + Grafana，**p95 < 200ms** |

### M5: 集成 + 交付（1 周）

| 子模块 | 量化验收 |
|--------|---------|
| 5.1 端到端 | happy path 完整：拉数据 → 算指标 → 出信号 → 回测 → 展示 |
| 5.2 Docker | docker-compose 一键启动 |
| 5.3 文档 | 用户手册 + 开发者文档 + 运维文档 |

---

## 📦 复用清单（ai-trader 可用模块）

### ✅ **直接复用**（零修改或最小修改）

| 模块 | 来源 | 复用方式 | 风险评估 |
|------|------|---------|---------|
| `analytics/trend.py` (ADX/MACD/SMA) | ai-trader | 复制到 `backend/app/analytics/trend.py` | 低（纯 numpy，已 40+ 测试覆盖） |
| `analytics/statistical.py` (Hurst/fractal/Shannon) | ai-trader | 复制 | 低（纯 numpy） |
| `analytics/volatility.py` (ATR) | ai-trader | 复制 | 低（纯 numpy） |
| `services/signal_change_bus.py` | ai-trader | 复制 → `backend/app/services/event_bus.py` | 低（asyncio 标准模式） |
| `data/okx.py` 公开 API 模式 | ai-trader | 参考（不复制，因为用 ccxt） | 中（注意限流） |
| `services/calibration_trainer.py` (PAVA Isotonic) | ai-trader | 复制 → `backend/app/services/calibration.py` | 低（标准算法） |
| 前端 lightweight-charts v4 markers 实现 | ai-trader | 参考模式（不复制代码，因 kline-system 升级到 v5 + macOS 风格） | 中（API 升级了） |

### ⚠️ **参考但不复用**

| 模块 | 原因 |
|------|------|
| `agent/agent.py` (TrendAgent) | kline-system 走 kline-analyst agent 路径，不复用此分层 |
| `app/agent/prompts.py` | 中文 prompt 可参考，但 RAG 集成方式要重做 |
| `app/data/okx_ws.py` | kline-system 用 ccxt 全市场，复用面窄 |
| `services/github_sync.py` | kline-system 不需要 GitHub 同步 |
| `services/follow_scheduler.py` | 跟单架构有借鉴价值，但实现要重做（多市场） |
| 前端 `LightweightKlineChart.tsx` | v4 → v5 API 变了 + macOS 风格要重写 |

### ❌ **绝对不碰的坑**

| 坑 | 位置 | kline-system 怎么做 |
|----|------|-------------------|
| 命中率 49.8% 接受为 baseline | `reports/bt-baseline-*.md` | M2.3 验收：必须 > 55%，否则不上线 |
| affinity matrix 有名无实 | `services/signal_change_bus.py` 等 | M2.1 用 ai-trader `multi_indicator_confluence`，但**必须接测试** |
| markers 接口"已预留但未接入" | `LightweightKlineChart.tsx` line 240 | M3.4 验收：markers 必须接通，测试覆盖 |
| 指标计算了不显示 | analytics → 前端未打通 | M3.3 验收：所有后端指标必须前端可见 |
| Redis 配了不用 | `config.py` 有 redis_url | M1.3 验收：Redis 命中率 ≥ 80%，测试验证 |
| AGENTS.md 规则比实现多 | `AGENTS.md` 9 条 | 规范精简到 **本 SPEC 的 10 条原则 + 各 milestone 验收表** |

---

## 🔄 与现有代码的集成策略

### 现有 assets

```
backend/
├── app/
│   ├── cache.py               # 已有 Redis 缓存（基本骨架）
│   ├── config.py              # 已有配置
│   ├── db.py                  # 已有 DB 连接
│   ├── main.py                # FastAPI 入口
│   ├── models/__init__.py     # 数据模型
│   ├── routers/kline.py       # K 线 API
│   ├── services/
│   │   ├── data_fetcher.py    # 已有（akshare/yfinance/ccxt）
│   │   └── indicators.py      # 已有（pandas 引擎，6 个指标）
│   └── utils/
└── requirements.txt
```

### 集成方案

1. **保留 `services/indicators.py`（pandas 引擎）**——适合 DataFrame 批量计算、kline 页面叠加
2. **新增 `app/analytics/`（ai-trader 复制）**——纯 numpy 高级指标 + 信号方向 + 多指标共振
3. **`services/indicators.py` 改为 `IndicatorEngine` 薄封装**，内部委托给 `analytics/` + 维护 pandas 兼容层
4. **新增 `services/event_bus.py`（ai-trader signal_change_bus 复制）**——M3.6 智能预取的前置
5. **新增 `services/calibration.py`（ai-trader calibration_trainer 复制）**——M2.3 信号校准

### 不允许的反模式

- ❌ `indicators.py` + `analytics/trend.py` 出现同名函数（MACD/RSI）两套实现
- ❌ 直接覆盖 `services/indicators.py` 而不留 pandas 兼容入口
- ❌ 复制 ai-trader 代码但不写 license 出处

---

## 📊 业务指标验收表（kline-system 特有）

| 指标 | 目标 | 测试方式 | milestone |
|------|------|---------|-----------|
| 数据完整率 | ≥ 99% | 全市场全周期抽样 | M1 |
| K 线 API p95 延迟 | < 200ms | wrk 压测 | M1 |
| Redis 缓存命中率 | ≥ 80% | 7 天观察 | M1 |
| 信号命中率 | > 55% | 5 个时间周期平均 | M2 |
| Brier score（置信度校准） | < 0.25 | PAVA Isotonic | M2 |
| 多指标一致性 | > 70% | 至少 3 个指标同向 | M2 |
| Lighthouse 性能 | ≥ 90 | 4 个页面测 | M3 |
| Lighthouse 无障碍 | ≥ 95 | 4 个页面测 | M3 |
| 1 万根 K 线滚动 FPS | ≥ 50 | 性能测试 | M3 |
| 骨架屏覆盖率 | 100% | 所有数据加载场景 | M3 |
| 智能预取响应 | < 50ms | hover 到数据 ready | M3 |

---

## 📁 目录约定（kline-system 标准）

```
kbkkk/
├── SPEC.md                    # 本文件（团队宪法）
├── README.md                  # 项目说明
├── project-tasks/             # 任务清单 + 进度
│   └── 00-tasklist.md
├── docs/
│   ├── architecture/          # 架构图 + spec
│   ├── runbooks/              # 运维手册
│   └── lessons-from-ai-trader.md  # ai-trader 教训汇总
├── backend/
│   ├── app/
│   │   ├── analytics/         # ★ 新增（ai-trader 复用）
│   │   ├── agents/            # kline-analyst agent
│   │   ├── routers/
│   │   ├── services/
│   │   │   ├── data_fetcher.py
│   │   │   ├── indicators.py
│   │   │   ├── event_bus.py   # ★ 新增
│   │   │   └── calibration.py # ★ 新增
│   │   └── main.py
│   ├── tests/
│   └── requirements.txt
├── frontend/                  # kline-frontend 规范
└── knowledge/                 # K 线知识库
```

---

## 🚦 质量门禁（每个 PR 必过）

1. **代码覆盖率** ≥ 80%（业务模块）
2. **类型检查** mypy strict + tsc --noEmit
3. **业务指标测试**（不是技术测试）必须新增 / 更新
4. **场景覆盖矩阵** ≥ 3 个用户场景（多市场/多周期/移动端/桌面端）
5. **ai-trader 教训自检**：勾选 10 条原则，有违反必须 PR 描述解释

---

## 🔗 引用

- [ai-trader 架构复盘 Canvas](.cursor/canvases/ai-trader-architecture-review.canvas.tsx)
- [kline-frontend 规范](../.cursor/agents/kline-frontend.md)（macOS Sonoma 设计系统）
- [kline-analyst 规范](../.cursor/agents/kline-analyst.md)
- [kline-backend 规范](../.cursor/agents/kline-backend.md)
- [kline-orchestrator 规范](../.cursor/agents/kline-orchestrator.md)
- [kline-pm 任务清单](../kbkkk/project-tasks/00-tasklist.md)

---

**🚦 当前状态**: Phase 0 完成（spec 写完，analytics/ 复制完成）。下一动作：M1 数据层开工。

**维护者**: kline-pm + kline-orchestrator
**审查周期**: 每个 milestone 结束更新一次
