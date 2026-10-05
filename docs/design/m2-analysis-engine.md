# M2 分析引擎设计（BTC/USDT + ETH/USDT 收窄版）

> **日期**: 2026-10-05
> **版本**: v0.1（待审）
> **范围**: SPEC M2 收窄到 BTC/USDT + ETH/USDT 两个标的
> **状态**: 草案，等用户批准
> **依赖**: M1 ✅（commit `e94c1bd` + 修复 `81de976`）

---

## 🎯 目标

为 BTC/USDT + ETH/USDT 提供：

1. 8 个时间周期（1m/5m/15m/30m/1h/4h/1d/1w）的 K 线数据接入与持久化
2. 6 核心 + 5 高级技术指标（向量化）
3. 单 K/组合 K/缠论/波浪形态识别
4. 多指标共振信号生成
5. 业务指标验收：命中率 > 55% / Brier < 0.25 / 多指标一致性 > 70%

---

## 📐 范围收窄（与原始 M2 的差异）

| 维度 | 原始 M2 | 收窄版 | 理由 |
|---|---|---|---|
| 标的 | 全市场（A股+美股+加密） | **仅 BTC/USDT + ETH/USDT** | 用户明确 |
| 数据源 | akshare/yfinance/ccxt | **仅 OKX REST API** | 用户选 + 公网稳定 |
| 回测引擎 | Backtrader | **手写向量化（纯 pandas）** | 多周期命中率验证快 10-100x |
| 市场 | 3 个 | **仅 crypto** | 收窄 |
| Outcome window | 待定 | **按周期动态** | 用户选 |

> **未来扩展点保留**：架构必须支持未来加回 A股/美股（接口层抽象），但不实现。

---

## 🏗️ 架构（4 层）

```
┌──────────────────────────────────────────────────────────┐
│  L4: 回测 + 业务验收 (M2-D)                              │
│    - 向量化回测引擎（多周期 + 多标的）                    │
│    - 业务指标：命中率 / Brier / 多指标一致性              │
└──────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│  L3: 信号服务 + Outcome (M2-C)                           │
│    - signal_service: 协调 indicator → signal → outcome  │
│    - calibration: PAVA Isotonic 置信度校准                │
│    - event_bus: 信号变更广播（前端订阅）                  │
└──────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│  L2: 形态 + 共振 + 信号方向 (M2-B)                       │
│    - patterns: 单 K(10) + 组合 K(9) + 缠论 + 波浪        │
│    - confluence: 多指标共振（≥3 同向）                   │
│    - signal_direction: long/short/neutral               │
└──────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│  L1: 指标计算引擎 (M2-A)                                 │
│    - 6 核心: MA/MACD/RSI/布林/KDJ/OBV（已有 services/    │
│      indicators.py，迁移/扩展为 analytics 协议）          │
│    - 5 高级: ADX/ATR/Hurst/多指标共振/信号方向           │
│    - 纯 numpy + pandas 向量化，无循环                     │
└──────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│  L0: 数据层（M1 已完成 ✅）                              │
│    - OKX REST → crypto_fetcher → DB (Kline)            │
│    - Redis 缓存 + 涨跌停标记                             │
└──────────────────────────────────────────────────────────┘
```

---

## 📁 文件结构

### L1 指标引擎 (M2-A)

```
backend/app/analytics/
├── trend.py                # ADX/MACD/SMA（ai-trader 复制）
├── statistical.py          # Hurst/fractal/Shannon
├── volatility.py           # ATR
├── __init__.py             # AnalyticsEngine 工厂
└── tests/
    ├── test_trend.py
    ├── test_statistical.py
    └── test_volatility.py
```

**任务清单 M2-A**：

| # | 任务 | 验证 | 估计 |
|---|---|---|---|
| A1 | 复制 ai-trader `analytics/trend.py` 并加 license 出处 | pytest 跑通 | 0.5d |
| A2 | 复制 `statistical.py` + `volatility.py` | pytest | 0.5d |
| A3 | 写 `__init__.py` 工厂函数 `AnalyticsEngine.calculate_all(df)` | 业务测试：BTC 1h 1 年数据全指标输出非空 | 0.5d |
| A4 | 与 `services/indicators.py` 建立薄封装关系（不重写） | 集成测试 | 0.5d |

**验收**：BTC/USDT 1h 1 年数据，6 核心 + 5 高级 11 个指标全部输出，零 NaN（除前 N 根 warmup）。

### L2 形态 + 共振 (M2-B)

```
backend/app/analytics/
├── patterns.py             # ★ 新增
├── confluence.py           # ★ 新增（ai-trader multi_indicator_confluence 复制）
├── signal_direction.py     # ★ 新增
└── tests/
    ├── test_patterns.py    # 至少 30 用例（10+9+5+5）
    ├── test_confluence.py
    └── test_signal_direction.py
```

**任务清单 M2-B**：

| # | 任务 | 验证 | 估计 |
|---|---|---|---|
| B1 | 单 K 形态（10 种）：锤子/十字星/吞没/孕线/吊颈/倒锤/红三兵/三乌鸦/晨星/暮星 | test_patterns.py 30+ 用例 | 1.5d |
| B2 | 缠论中枢识别（简化版：3 段重叠区间） | 至少 5 个测试 | 1d |
| B3 | 波浪驱动 5 浪识别（简化版：1+2+3+4+5 浪） | 至少 5 个测试 | 1d |
| B4 | 多指标共振（≥3 同向 → 出信号） | test_confluence.py | 0.5d |
| B5 | 信号方向判定（long/short/neutral） | test_signal_direction.py | 0.5d |

**验收**：BTC/USDT 1d 3 年数据，10 单 K + 9 组合 K 形态识别准确率 ≥ 80%。

### L3 信号服务 + Outcome (M2-C)

```
backend/app/services/
├── event_bus.py            # ★ 新增（ai-trader signal_change_bus 复制）
├── calibration.py          # ★ 新增（ai-trader calibration_trainer 复制）
├── signal_service.py       # ★ 新增
└── tests/
    ├── test_event_bus.py
    ├── test_calibration.py
    └── test_signal_service.py  # 业务测试
```

**任务清单 M2-C**：

| # | 任务 | 验证 | 估计 |
|---|---|---|---|
| C1 | 复制 event_bus（asyncio 队列模式） | 单元测试 | 0.5d |
| C2 | 复制 calibration（PAVA Isotonic） | 单元测试 + 已知数据集 | 0.5d |
| C3 | signal_service：协调 indicator → pattern → confluence → direction | 业务测试 | 1.5d |
| C4 | outcome tracking：按周期动态窗口回填 | 业务测试：1h 信号 → 24h 后 outcome | 1d |
| C5 | 把 signal 写回 DB（含 confidence + outcome） | 集成测试 | 0.5d |

**Outcome window 映射**（**关键设计**）：

| 周期 | Outcome 窗口 | 备注 |
|---|---|---|
| 1m | 60m（60 根 K） | 1 分钟决策看 1 小时走势 |
| 5m | 5h（60 根 K） | |
| 15m | 15h（60 根 K） | |
| 30m | 30h（60 根 K） | |
| 1h | 24h（24 根 K） | **最常引用** |
| 4h | 4d（24 根 K） | |
| 1d | 5d（5 根 K） | |
| 1w | 5w（5 根 K） | |

### L4 回测 + 业务验收 (M2-D)

```
backend/app/analytics/
├── backtest.py             # ★ 新增：向量化回测
└── tests/
    └── test_backtest.py    # 业务指标测试
```

**任务清单 M2-D**：

| # | 任务 | 验证 | 估计 |
|---|---|---|---|
| D1 | 向量化回测引擎：拉 K 线 → 算指标 → 出信号 → 模拟下单 → 算 PnL | 单元测试 | 1d |
| D2 | 业务指标计算：命中率 / Brier / 多指标一致性 | 业务测试 | 0.5d |
| D3 | BTC/USDT 5 周期（5m/15m/1h/4h/1d）× 1 年历史回测 | 业务验收 | 1d |
| D4 | ETH/USDT 5 周期 × 1 年历史回测 | 业务验收 | 1d |
| D5 | 交叉验证：BTC vs ETH 命中率差异 < 15% | 业务验收 | 0.5d |

**业务指标验收门禁**：

| 指标 | 目标 | 测法 |
|---|---|---|
| 命中率 | **> 55%** | 5 周期平均（5m/15m/1h/4h/1d） |
| Brier score | **< 0.25** | PAVA 校准后 |
| 多指标一致性 | **> 70%** | ≥ 3 指标同向占比 |
| 业务测试覆盖 | **≥ 80%** | pytest --cov |

---

## 🔗 数据流（端到端）

```python
# 1. 拉数据（M1）
df = crypto_fetcher.get_kline("BTC-USDT", period="1h", start="20250101", end="20251231")
# 2. 算指标（L1）
df = analytics_engine.calculate_all(df)
# 3. 形态识别（L2）
df = pattern_recognizer.detect_all(df)
# 4. 共振 + 方向（L2）
signals = signal_direction.generate(df)
# 5. 写库 + 广播（L3）
for sig in signals:
    db.write(sig)
    event_bus.publish(sig)
# 6. Outcome 回填（L3，1d 后异步任务）
calibration.fill_outcome(signal_id, current_df)
# 7. 业务指标（L4）
metrics = backtest.evaluate(period="1h", market="crypto")
assert metrics.hit_rate > 0.55
assert metrics.brier_score < 0.25
```

---

## 📊 任务量与工期估计

| 阶段 | 子任务 | 估计工时 | 累计 |
|---|---|---|---|
| M2-A | 4 | 2d | 2d |
| M2-B | 5 | 4.5d | 6.5d |
| M2-C | 5 | 4d | 10.5d |
| M2-D | 5 | 4d | **14.5d** |
| 缓冲 + 集成 | - | 2.5d | **17d ≈ 3.5 周** |

SPEC 原始 M2 是 3 周，本收窄版 3.5 周（**多 0.5 周**给 OKX 数据源适配 + 向量化回测框架）。

---

## ⚠️ 风险与缓解

| # | 风险 | 缓解 |
|---|---|---|
| 1 | OKX API 限流 | 增量对账 + 缓存层 + 单连接 ≤ 10 req/s |
| 2 | BTC/ETH 历史数据获取延迟 | M2-D 验收允许 p95 < 10s/请求（M1 是 < 5s，但 1 年 1m 数据是 50 万根，差异大） |
| 3 | 形态识别准确率不达标 | 收敛到「单 K + 共振」组合，缠论/波浪后置 |
| 4 | 命中率 < 55% 验收失败 | 加更多过滤器（量价共振 + 趋势过滤）迭代 |
| 5 | M1 已有 `services/indicators.py` 与 ai-trader `analytics/trend.py` 冲突 | 严格分层：`services/indicators.py` = pandas 薄封装，`analytics/` = ai-trader 复制 |
| 6 | 4 subagent 顺序派发可能慢 | 每步独立可合 + 增量演示 |

---

## 🛑 关键决策点（待用户拍板）

| # | 决策 | 选项 | 我的推荐 |
|---|---|---|---|
| 1 | OKX REST 鉴权 | 公开端点（无需 key）vs 需 V5 API key | **公开端点**（只读 K 线不需要签名） |
| 2 | K 线数据落库策略 | 实时拉 vs 定时任务批量 | **定时任务**（每 5 分钟拉一次增量） |
| 3 | 缠论/波浪实现深度 | 完整版 vs 简化版 | **简化版**（中枢=3 段重叠；波浪=1+2+3+4+5 浪驱动） |
| 4 | 信号源默认 | rule_based（多指标共振）vs ml_based | **rule_based**（M2 阶段不上 ML） |
| 5 | 业务测试覆盖率门槛 | 80% vs 90% | **80%**（与 SPEC 一致） |
| 6 | 跨周期信号合并 | 各自独立 vs 取最长周期为主 | **各自独立**（简化实现） |

---

## 📦 复用清单（ai-trader）

| 模块 | 来源 | 复用方式 | 风险 |
|---|---|---|---|
| `analytics/trend.py` | ai-trader | 复制到 `backend/app/analytics/trend.py` | 低（40+ 测试覆盖） |
| `analytics/statistical.py` | ai-trader | 复制 | 低（纯 numpy） |
| `analytics/volatility.py` | ai-trader | 复制 | 低（纯 numpy） |
| `services/signal_change_bus.py` | ai-trader | 复制 → `event_bus.py` | 低 |
| `services/calibration_trainer.py` | ai-trader | 复制 → `calibration.py` | 低 |
| `analytics/multi_indicator_confluence.py` | ai-trader | 复制 → `confluence.py` | 中（必须接测试） |

---

## 🚦 质量门禁（继承 SPEC）

- [ ] 代码覆盖率 ≥ 80%（业务模块）
- [ ] 业务指标测试必须新增/更新（不是 HTTP 200）
- [ ] 命中率 > 55% / Brier < 0.25 / 多指标一致性 > 70%
- [ ] ai-trader 复制模块必须带 license 出处
- [ ] 不允许两套同名实现（MACD/RSI 只能一个来源）

---

## ❓ 等待批准

- [ ] 整体设计是否通过？
- [ ] 4 阶段拆解（A→B→C→D）是否合理？
- [ ] 6 个关键决策点是否有要改的？
- [ ] 工期 3.5 周是否接受？

批准后调 writing-plans skill 生成实施计划。

---

**维护者**: kline-pm + kline-orchestrator
**下次更新**: 批准后生成 writing-plans 输出
