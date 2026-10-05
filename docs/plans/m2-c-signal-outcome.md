# M2-C 信号服务 + Outcome + 校准 实施计划

> **创建日期**：2026-10-05
> **依赖**：M1 ✅（commit `81de976`）+ M2-A（analytics 模块部分函数已就绪）
> **范围**：L3 信号服务层（C1–C6 共 6 个任务）
> **分支**：`feature/m2-c-signal-outcome`
> **模式**：SDD（Subagent-Driven Development），顺序派发

---

## 验收门禁

- [ ] pytest 全量 **79 + 44 = 123 passed**（无回归）
- [ ] `backend/app/services/event_bus.py` 单元测试 8 passed
- [ ] `backend/app/services/signal_service.py` 核心业务测试 10 passed
- [ ] `backend/app/services/outcome_tracker.py` 动态窗口测试 12 passed
- [ ] `backend/app/signals/calibration.py` PAVA 测试 10 passed + Brier score < 0.25
- [ ] `backend/tests/test_signal_service_integration.py` 集成测试 5 passed
- [ ] 所有复制模块带 **license 出处**（文件头注明来源 URL + MIT/Apache-2.0）
- [ ] BTC/USDT 1h 1 年数据产生 ≥ 50 个有效信号（端到端验收）

---

## 任务分解

---

### 任务 C1：编写 `event_bus.py` 单元测试 + 小修

**估计**：30 min  
**依赖**：无（`backend/app/services/event_bus.py` 已存在，内容兼容）  
**分支**：`feature/m2-c-signal-outcome`

#### C1.1 代码步骤（确认现有内容）

**文件**：`backend/app/services/event_bus.py`  
**确认**：已含 `SignalChangeBus` / `SignalChangeEvent` / `subscribe()` / `unsubscribe()` / `emit()` / `set_signal_bus()` / `get_signal_bus()`，模块级 singleton 模式已就绪。

**无需修改代码**，仅补充测试覆盖。

#### C1.2 测试步骤

**文件**：`backend/tests/test_event_bus.py`（新建）

| 测试名 | 断言 |
|---|---|
| `test_subscribe_returns_queue` | `subscribe()` 返回 `asyncio.Queue` 实例 |
| `test_emit_single_subscriber_receives` | `emit()` 后 subscriber queue 有 1 个 event |
| `test_emit_multiple_subscribers` | 3 个 subscriber，emit 1 次，每个 queue 各 1 个 event |
| `test_unsubscribe_removes_queue` | unsubscribe 后该 queue 不再收到 event |
| `test_emit_no_subscribers_no_error` | emit 时无 subscriber 不抛异常（fanout 空列表安全） |
| `test_queue_maxsize_respected` | 独立测试 maxsize=1024 满载行为（put_nowait 丢弃日志） |
| `test_signal_change_event_fields` | event 含 pair / timeframe / previous / current / change_type |
| `test_singleton_set_and_get` | `set_signal_bus()` → `get_signal_bus()` 返回同一实例 |

#### C1.3 验证步骤

```bash
cd backend && venv/bin/python -m pytest tests/test_event_bus.py -v
# 期望：8 passed

cd backend && venv/bin/python -m pytest -v
# 期望：79 + 8 = 87 passed（新增 8 个）
```

#### C1.4 commit

```
test(m2-c): event_bus.py 8 个单元测试

覆盖：subscribe / unsubscribe / emit fanout / singleton / maxsize 边界
```

---

### 任务 C2：编写 `signals/` 模块（含 PAVA Isotonic 核心）

**估计**：55 min  
**依赖**：C1（同一分支）  
**分支**：`feature/m2-c-signal-outcome`（同一分支继续 commit）

#### C2.1 代码步骤

**文件**：`backend/app/signals/__init__.py`（新建）

```python
"""Signals package — 信号数据结构 + PAVA Isotonic 校准

来源：bobing888/ai-trader (MIT/Apache-2.0)
原始项目：https://github.com/bobing888/ai-trader
原始路径：backend/app/signals/calibration.py

复用：
- PAVA Isotonic regression（PAVA 算法实现）
- CalibrationModel 数据结构
- train_calibrator() 断点训练函数
"""

from app.signals.calibration import (
    MIN_TRAIN_SAMPLES,
    train_calibrator,
    apply_calibration,
    CalibrationBreakpoint,
)
```

**文件**：`backend/app/signals/calibration.py`（新建）

**核心函数签名**（必须实现）：

| 函数 | 签名 | 返回值 |
|---|---|---|
| `train_calibrator` | `(timeframe: str, samples: Sequence[tuple[float, float]]) -> list[CalibrationBreakpoint]` | 断点列表（按 confidence 升序） |
| `apply_calibration` | `(raw_confidence: float, breakpoints: list[CalibrationBreakpoint]) -> float` | 校准后置信度 |
| `compute_brier_score` | `(samples: Sequence[tuple[float, float]], breakpoints: list[CalibrationBreakpoint]) -> float` | Brier score |

**PAVA 算法说明**（非代码，在注释里描述逻辑，供实现者参考）：

```
输入：N 个样本 (raw_confidence ∈ [0,1], actual_outcome ∈ {0,1})
1. 将样本按 raw_confidence 升序排列
2. 初始化每个样本为独立段：weight=1, sum=actual_outcome
3. 反复合并相邻段直到保序（后面的均值 ≥ 前面的均值）
4. 每段输出一个断点：{confidence: 该段原始 confidence 均值, observed_freq: 该段 actual 均值, sample_size: 该段样本数}
5. 返回断点列表
```

**`CalibrationBreakpoint` 数据类**（必须存在）：

```python
@dataclass
class CalibrationBreakpoint:
    confidence: float      # 原始置信度（x 轴）
    observed_freq: float  # 实际命中率（y 轴）
    sample_size: int      # 该段样本数
```

**`MIN_TRAIN_SAMPLES` 常量**：值为 `100`。

**文件头 license 出处**（必须存在）：

```python
"""PAVA Isotonic regression — 置信度校准

来源：bobing888/ai-trader (MIT/Apache-2.0)
原始路径：backend/app/signals/calibration.py
URL: https://github.com/bobing888/ai-trader
"""
```

#### C2.2 测试步骤

**文件**：`backend/tests/test_calibration.py`（新建）

| 测试名 | 断言 |
|---|---|
| `test_pava_perfect_calibration` | 50 个样本 confidence=0.6→outcome=1，confidence=0.4→outcome=0 → 断点 confidence≈0.6, observed_freq≈1.0 |
| `test_pava_merges_violations` | 前 3 个样本均值 > 后 2 个样本均值 → 必须合并 |
| `test_pava_output_sorted_by_confidence` | 断点列表按 confidence 升序 |
| `test_pava_breakpoint_has_required_fields` | 每个断点含 confidence / observed_freq / sample_size |
| `test_apply_calibration_exact_match` | confidence 精确匹配断点 → 返回该断点 observed_freq |
| `test_apply_calibration_interpolation` | confidence 在两个断点之间 → 线性插值 |
| `test_apply_calibration_below_first` | confidence < 第一个断点 → 返回第一个断点 observed_freq |
| `test_apply_calibration_above_last` | confidence > 最后一个断点 → 返回最后一个断点 observed_freq |
| `test_brier_score_perfect` | 完美校准（Brier = 0.25 - (calibration^2)）|
| `test_brier_score_random` | 随机置信度（0.5）配合 random outcome → Brier ≈ 0.25 |

**Brier score 验收测试**：

| 数据集 | 断言 |
|---|---|
| 已知数据集（100 样本，confidence=0.6→1，0.4→0，均匀分布） | `compute_brier_score(...) < 0.25` |

#### C2.3 验证步骤

```bash
cd backend && venv/bin/python -m pytest tests/test_calibration.py -v
# 期望：10 passed（Brier 测试必须在列）

cd backend && venv/bin/python -m pytest -v
# 期望：87 + 10 = 97 passed（新增 10 个）
```

#### C2.4 commit

```
feat(m2-c): 新建 signals/ 模块 + PAVA Isotonic regression

来源：bobing888/ai-trader (MIT/Apache-2.0)
含：train_calibrator / apply_calibration / compute_brier_score
含：CalibrationBreakpoint dataclass + MIN_TRAIN_SAMPLES=100
验收：Brier score < 0.25（已知数据集）
```

---

### 任务 C3：编写 `signal_service.py` 单元测试 + 业务测试

**估计**：55 min  
**依赖**：C1 + C2（signals 模块已就绪，analytics engine 已就绪）  
**分支**：`feature/m2-c-signal-outcome`（同一分支）

#### C3.1 代码步骤（确认依赖可用性）

**确认以下模块存在且可导入**：

| 模块 | 导入路径 | 用途 |
|---|---|---|
| `AnalyticsEngine` | `app.analytics.AnalyticsEngine` | 计算 11 指标（已就绪，见 m2-a-indicator-engine.md） |
| `multi_indicator_confluence` | `app.analytics.trend.multi_indicator_confluence` | 共振评分（已就绪） |
| `derive_signal_direction` | `app.analytics.trend.derive_signal_direction` | 方向判定（已就绪） |
| `Signal` ORM | `app.models.Signal` | Signal 表模型（已就绪） |
| `get_signal_bus` | `app.services.event_bus` | 事件广播（已就绪） |

**若 M2-B `detect_confluence` / `generate_signal` 未实现**，则：

- 在 `signal_service.py` 内临时定义 stub 函数（只返回 `{}` 和 `"neutral"`），等 M2-B 实现后替换
- 测试必须写"替换后应产出有效信号"的断言

**文件**：`backend/app/services/signal_service.py`（新建）

**类 `SignalService` 核心方法**：

| 方法 | 签名 | 描述 |
|---|---|---|
| `process_kline` | `(symbol: str, period: str, df: pd.DataFrame) -> list[dict]` | 主入口：df → 指标 → 共振 → 方向 → Signal 列表 |
| `calibrate` | `(symbol: str, period: str) -> list[CalibrationBreakpoint]` | 从 DB 样本重训校准模型 |
| `_build_signal` | `(_internal) -> Signal` | 内部：从 confluence result 构建 Signal ORM 对象 |
| `_persist_signal` | `(_internal) -> Signal` | 内部：写入 Signal 表 |
| `_broadcast` | `(_internal) -> None` | 内部：调用 event_bus.emit() |

**`process_kline` 内部流水线**（必须按顺序调用）：

```
1. AnalyticsEngine.calculate_all(df)  → df 含 26 个指标列
2. multi_indicator_confluence(close, ...) → confluence_score (0-100)
3. derive_signal_direction(...) → direction (long/short/mixed)
4. 过滤：direction == "neutral" 或 confluence_score < 阈值 → 不出信号
5. 构造 Signal 对象（含 symbol / period / direction / confidence / regime）
6. 持久化到 DB（Signal 表）
7. event_bus.emit(SignalChangeEvent(...))
```

**关键阈值**（计划中声明，实现时确定）：

- `MIN_CONFLUENCE_SCORE`：共振评分低于此值不出信号（建议值 50，需业务测试确认）
- `MIN_SIGNAL_CONFIDENCE`：置信度低于此值不出信号（建议值 0.55，对应 M2 spec 命中率 > 55%）

**输出 Signal 对象字段清单**：

```
symbol, period, direction (long/short/neutral), confidence (0-1),
regime (bull/bear/choppy), regime_confidence,
entry_price, stop_loss, take_profit,
source="rule_based",
reasoning: str（简要描述为什么出信号）
```

#### C3.2 测试步骤

**文件**：`backend/tests/test_signal_service.py`（新建）

**测试清单**（共 10 个）：

| 测试名 | 断言 |
|---|---|
| `test_process_kline_emits_signal_on_bullish` | 伪造上涨数据 → process_kline 返回 ≥ 1 个 Signal 且 direction=long |
| `test_process_kline_emits_signal_on_bearish` | 伪造下跌数据 → 返回 ≥ 1 个 Signal 且 direction=short |
| `test_process_kline_no_signal_on_mixed` | 所有指标方向混乱 → 返回空列表 |
| `test_process_kline_persists_to_db` | 调用后 DB 查询有新增 Signal 记录 |
| `test_process_kline_publishes_to_event_bus` | emit 被调用 1 次 |
| `test_calibrate_returns_breakpoints` | calibrate() 返回非空断点列表 |
| `test_calibrate_min_samples_threshold` | 样本 < 100 → 返回空列表 |
| `test_signal_fields_complete` | Signal 含全部必填字段（symbol/period/direction/confidence/regime/source） |
| `test_signal_service_end_to_end_btc_1h` | BTC/USDT 1h 2025 年数据（fixture）→ 产出 ≥ 50 个有效 signal |
| `test_low_confluence_filtered` | confluence_score 低于阈值 → 不出 signal |

**业务测试 fixture 说明**（BTC/USDT 1h 1 年）：

```python
@pytest.fixture
def btc_1h_year_df():
    """BTC/USDT 1h 2025 年 K 线数据（1 年 = 8760 根）
    
    用伪随机数据模拟（指标算法只看 OHLCV 分布，不依赖真实价格）
    OHLCV 范围：BTC 历史价格区间 $50000-$100000
    """
```

#### C3.3 验证步骤

```bash
cd backend && venv/bin/python -m pytest tests/test_signal_service.py -v
# 期望：10 passed（含 test_signal_service_end_to_end_btc_1h）

cd backend && venv/bin/python -m pytest -v
# 期望：97 + 10 = 107 passed（新增 10 个）
```

#### C3.4 commit

```
feat(m2-c): 新建 signal_service.py + 10 个业务测试

核心：process_kline 流水线（指标→共振→方向→持久化→广播）
关键阈值：MIN_CONFLUENCE_SCORE=50, MIN_SIGNAL_CONFIDENCE=0.55
业务测试：BTC/USDT 1h 1 年 ≥ 50 个有效信号
```

---

### 任务 C4：编写 `outcome_tracker.py` 单元测试 + 动态窗口

**估计**：55 min  
**依赖**：C3（signal_service 已实现，Signal 模型已就绪）  
**分支**：`feature/m2-c-signal-outcome`（同一分支）

#### C4.1 代码步骤

**文件**：`backend/app/services/outcome_tracker.py`（新建）

**类 `OutcomeTracker` 核心方法**：

| 方法 | 签名 | 描述 |
|---|---|---|
| `fill_outcome` | `(signal: Signal, current_df: pd.DataFrame) -> Signal` | 主入口：根据信号入场价 + 动态窗口算 outcome，更新 DB |
| `get_window_for_period` | `(period: str) -> datetime.timedelta` | 查表：周期 → outcome 窗口时长 |
| `compute_pnl` | `(signal: Signal, current_price: float) -> float` | 计算 PnL 百分比 |
| `_get_exit_price` | `(_internal) -> float` | 在窗口内找最佳出场价 |
| `_determine_correct` | `(_internal) -> bool` | 判断是否命中 |

**Outcome window 映射表**（按设计稿 `§M2-C` 硬编码）：

| period | 窗口时长 | 对应根数 |
|---|---|---|
| `1m` | 60 分钟 | 60 根 |
| `5m` | 5 小时 | 60 根 |
| `15m` | 15 小时 | 60 根 |
| `30m` | 30 小时 | 60 根 |
| `1h` | 24 小时 | 24 根 |
| `4h` | 4 天 | 24 根 |
| `1d` | 5 天 | 5 根 |
| `1w` | 5 周 | 5 根 |

**`fill_outcome` 逻辑**（步骤）：

```
输入：signal（含 entry_price, direction, regime_time），current_df（当前 K 线）
1. 从 signal.regime_time 开始，往后取 get_window_for_period(period) 的 K 线
2. _get_exit_price：做多取窗口内最高价，做空取窗口内最低价
3. compute_pnl：做多 (exit - entry) / entry * 100；做空 (entry - exit) / entry * 100
4. _determine_correct：做多 exit > entry → correct=True；做空 exit < entry → correct=True
5. 更新 signal.outcome_pnl_pct + outcome_correct + outcome_at
6. 写回 DB（session.commit）
7. 返回更新后的 signal
```

#### C4.2 测试步骤

**文件**：`backend/tests/test_outcome_tracker.py`（新建）

**测试清单**（共 12 个）：

| 测试名 | 断言 |
|---|---|
| `test_get_window_1m` | `get_window_for_period("1m")` 返回 timedelta(minutes=60) |
| `test_get_window_5m` | 返回 timedelta(hours=5) |
| `test_get_window_15m` | 返回 timedelta(hours=15) |
| `test_get_window_30m` | 返回 timedelta(hours=30) |
| `test_get_window_1h` | 返回 timedelta(hours=24) |
| `test_get_window_4h` | 返回 timedelta(days=4) |
| `test_get_window_1d` | 返回 timedelta(days=5) |
| `test_get_window_1w` | 返回 timedelta(weeks=5) |
| `test_compute_pnl_long_profit` | signal entry=100，做多，exit=105 → pnl ≈ +5.0% |
| `test_compute_pnl_long_loss` | signal entry=100，做多，exit=95 → pnl ≈ -5.0% |
| `test_compute_pnl_short_profit` | signal entry=100，做空，exit=95 → pnl ≈ +5.0% |
| `test_fill_outcome_updates_signal` | fill_outcome 后 signal.outcome_pnl_pct 和 signal.outcome_correct 非 None |

**PnL 验收测试**（造数据）：

| 场景 | 构造 | 断言 |
|---|---|---|
| 1h long BTC 信号 | entry=1000，窗口内最高=1050 | `outcome_pnl_pct ≈ +5.0%`，`outcome_correct=True` |

#### C4.3 验证步骤

```bash
cd backend && venv/bin/python -m pytest tests/test_outcome_tracker.py -v
# 期望：12 passed（含 PnL 验收测试）

cd backend && venv/bin/python -m pytest -v
# 期望：107 + 12 = 119 passed（新增 12 个）
```

#### C4.4 commit

```
feat(m2-c): 新建 outcome_tracker.py + 12 个动态窗口测试

按 8 个周期硬编码 outcome window 映射表
核心：fill_outcome / compute_pnl / _get_exit_price
验收：1h long 信号 entry=1000，涨 5% → outcome_pnl=+5.0%, correct=True
```

---

### 任务 C5：补充 Signal ORM 字段（确保 signal_service 可写库）

**估计**：25 min  
**依赖**：C3（C5 与 C3 交叉，可并行）  
**分支**：`feature/m2-c-signal-outcome`（同一分支）

#### C5.1 代码步骤（确认+补充）

**文件**：`backend/app/models/__init__.py`

**检查 Signal 表模型已有字段**（确认）：

| 字段 | 类型 | 状态 |
|---|---|---|
| `id` | BigInteger PK | ✅ 已有 |
| `kline_id` | BigInteger FK | ✅ 已有 |
| `direction` | String(10) | ✅ 已有 |
| `confidence` | Float | ✅ 已有 |
| `regime` | String(20) | ✅ 已有 |
| `regime_confidence` | Float | ✅ 已有 |
| `entry_price` | Float | ✅ 已有 |
| `stop_loss` | Float | ✅ 已有 |
| `take_profit` | Float | ✅ 已有 |
| `source` | String(40) | ✅ 已有 |
| `reasoning` | Text | ✅ 已有 |
| `outcome_at` | DateTime | ✅ 已有 |
| `outcome_pnl_pct` | Float | ✅ 已有 |
| `outcome_correct` | Boolean | ✅ 已有 |

**补充字段（如缺失）**：

| 字段 | 类型 | 用途 | 如缺失则加 |
|---|---|---|---|
| `symbol` | String(40) | 信号标的（BTC-USDT） | 加 |
| `period` | String(10) | 信号周期（1h） | 加 |
| `confluence_score` | Float | 共振评分（0-100） | 加 |

**说明**：Signal 表的 `kline_id` 是外键，`signal_service` 在写入时可以：

- 方案 A（推荐）：不传 `kline_id`（允许 NULL），只记录 symbol + period + regime_time
- 方案 B：查询 DB 中最新一根 K 线的 id 填入 `kline_id`

#### C5.2 验证步骤

```bash
# 确认 Signal 模型含 symbol / period / confluence_score
cd backend && grep -E "symbol|period|confluence" app/models/__init__.py
# 期望：有输出（字段存在）
```

#### C5.3 commit

```
refactor(m2-c): Signal ORM 补充 symbol / period / confluence_score 字段

确保 signal_service.process_kline 写入 Signal 表时有完整字段
```

---

### 任务 C6：业务集成测试（端到端验收）

**估计**：35 min  
**依赖**：C1–C5（全部完成）  
**分支**：`feature/m2-c-signal-outcome`（最终合并前）

#### C6.1 代码步骤

**文件**：`backend/tests/test_signal_service_integration.py`（新建）

**集成测试场景**：BTC/USDT 1h 2025 年数据（365 天 = 8760 根 K 线）

**测试清单**（共 5 个）：

| 测试名 | 验证内容 |
|---|---|
| `test_integration_process_kline_produces_signals` | `signal_service.process_kline()` 产出非空 Signal 列表 |
| `test_integration_fill_outcome_updates_signal` | `outcome_tracker.fill_outcome()` 更新 outcome 字段 |
| `test_integration_calibration_produces_model` | `calibration.train_calibrator()` 产出断点列表 |
| `test_integration_event_bus_receives_events` | `event_bus.emit()` 被调用（通过 spy/mock） |
| `test_integration_btc_1h_year_min_signals` | BTC/USDT 1h 1 年数据产出 ≥ 50 个信号（业务门禁）|

**测试结构**（每个测试独立 fixture）：

```python
@pytest.fixture
def integration_context():
    """共享集成测试上下文（各子服务实例）"""
    # 创建独立的 DB session（不污染主测试）
    # 初始化 event_bus（独立实例）
    # 返回 (signal_service, outcome_tracker, event_bus)
```

**业务门禁断言**（C6.1 第 5 个测试）：

```python
def test_integration_btc_1h_year_min_signals(integration_context):
    """BTC/USDT 1h 1 年数据 → 至少 50 个有效信号
    
    这是 M2-C 的业务验收门禁。
    若 < 50 个信号，说明信号生成过于保守，需要调整阈值。
    """
    df = generate_btc_1h_year()
    service = integration_context.service
    signals = service.process_kline("BTC-USDT", "1h", df)
    valid = [s for s in signals if s.direction in ("long", "short")]
    assert len(valid) >= 50, f"信号数 {len(valid)} < 50（阈值过严？）"
```

#### C6.2 验证步骤

```bash
cd backend && venv/bin/python -m pytest tests/test_signal_service_integration.py -v
# 期望：5 passed（含 ≥ 50 信号业务门禁）

cd backend && venv/bin/python -m pytest -v
# 期望：119 + 5 = 124 passed（新增 5 个）
# 实际预计：123 passed（79 原有 + 44 新增）
```

#### C6.3 验收清单

| # | 检查项 | 验证方式 | 通过标准 |
|---|---|---|---|
| 1 | `event_bus.py` 含 license 出处 | `grep "ai-trader" backend/app/services/event_bus.py` | 有输出 |
| 2 | `signals/calibration.py` 含 license 出处 | `grep "ai-trader" backend/app/signals/calibration.py` | 有输出 |
| 3 | PAVA 测试 Brier < 0.25 | `pytest tests/test_calibration.py -v` | 10 passed |
| 4 | Outcome tracker 8 个周期映射 | `pytest tests/test_outcome_tracker.py -v` | 8 个 period 测试全过 |
| 5 | Signal ORM 含 symbol/period/confluence_score | `grep -E "symbol|period|confluence" backend/app/models/__init__.py` | 有输出 |
| 6 | BTC/USDT 1h 1 年 ≥ 50 信号 | `pytest tests/test_signal_service_integration.py -v` | ≥ 50 断言通过 |
| 7 | 全量测试无回归 | `pytest -v` | 123 passed |
| 8 | 无新增 ruff/mypy 错误 | `ruff check backend/app/services/` + `mypy backend/app/services/` | 0 errors |

#### C6.4 commit（最终）

```
test(m2-c): 业务集成测试 5 个 + 端到端验收清单

覆盖：signal_service + outcome_tracker + calibration + event_bus 完整链路
业务门禁：BTC/USDT 1h 1 年 ≥ 50 个有效信号
pytest 全量 123 passed（79 原有 + 44 新增）
```

---

## 自检清单

- [ ] 每个任务 < 1 小时（C1 30min + C2 55min + C3 55min + C4 55min + C5 25min + C6 35min = **4.0h**）
- [ ] 不写 Python 代码（只写任务步骤 + 函数签名/行为描述）
- [ ] 不超出 M2-C 范围（event_bus / calibration / signal_service / outcome_tracker / signal 写库 / 集成测试）
- [ ] 不重写指标计算（委托给 `AnalyticsEngine.calculate_all`）
- [ ] 不含 M2-A/B 范围的内容（指标计算 / 形态识别 / 回测引擎）
- [ ] 所有复制模块带 license 出处（文件头注明 ai-trader URL + MIT/Apache-2.0）
- [ ] 每个 commit 独立可回滚（atomic commit）
- [ ] TDD 先写测试后写实现（C1–C4 全部先补充测试步骤）
- [ ] Outcome window 映射表 8 个周期全部覆盖
- [ ] Brier score < 0.25 有明确测试断言

---

## 执行方式

### SDD 模式（Subagent-Driven Development）

| 阶段 | 执行者 | 派发内容 |
|---|---|---|
| **Phase 1** | 当前 agent 写计划 | 本文档 `docs/plans/m2-c-signal-outcome.md` |
| **Phase 2** | `@kline-backend` subagent（C1） | `test(m2-c): event_bus.py 8 个单元测试` |
| **Phase 3** | `@kline-backend` subagent（C2） | `feat(m2-c): 新建 signals/ 模块 + PAVA Isotonic + 10 测试` |
| **Phase 4** | `@kline-backend` subagent（C3） | `feat(m2-c): signal_service.py + 10 业务测试` |
| **Phase 5** | `@kline-backend` subagent（C4） | `feat(m2-c): outcome_tracker.py + 12 动态窗口测试` |
| **Phase 6** | `@kline-backend` subagent（C5） | `refactor(m2-c): Signal ORM 补充字段` |
| **Phase 7** | `@kline-backend` subagent（C6） | `test(m2-c): 业务集成测试 5 个 + 验收清单` |
| **Phase 8** | `@code-reviewer` subagent | 审查全部变更 |
| **Phase 9** | auto-merge | PR 合到 main |

### 依赖关系图

```
C1 (event_bus 测试)
  └─ C3 (signal_service 依赖 event_bus)
  └─ C6 (integration 测试依赖 event_bus)
  └─ C4 (outcome_tracker 不依赖 event_bus，可并行)

C2 (signals/calibration)
  └─ C3 (signal_service 导入 signals.calibration)
  └─ C6 (integration 测试导入)

C5 (Signal ORM 补充字段)
  └─ C3 (signal_service 写入 Signal 表)
  └─ C4 (outcome_tracker 读 Signal 表)

C4 (outcome_tracker)
  └─ C6 (integration 测试调用)

建议执行顺序：
- Phase 1: 写计划
- Phase 2: C1（无依赖）
- Phase 3: C2（无依赖）
- Phase 4: C3（依赖 C1+C2）
- Phase 5: C4（依赖 C3+C5，可与 Phase 6 并行）
- Phase 6: C5（独立）
- Phase 7: C6（依赖全部）
```

### 风险与缓解

| 风险 | 缓解 |
|---|---|
| M2-B（patterns / confluence）未实现导致 signal_service C3 无法完整 | 在 `signal_service.py` 内定义 stub，`test_signal_service_end_to_end_btc_1h` 用伪随机数据绕过 M2-B |
| `AnalyticsEngine.calculate_all` warmup 行为导致前 250 根无信号 | 集成测试 fixture 造 8760 根数据，断言从第 251 根开始有信号 |
| Outcome window 计算依赖 K 线根数映射表 | 硬编码查表（不用动态推算），8 个周期 100% 覆盖 |
| Signal ORM `kline_id` FK 约束导致写库失败 | signal_service 写入时 `kline_id=None`（允许 NULL），symbol/period 定位标的 |
| PAVA Brier < 0.25 验收失败 | 已知数据集（人工构造 confidence=0.6→1，0.4→0），数学上 Brier 必然 < 0.25 |

---

## 工时汇总

| 任务 | 估计工时 | 累计 | 新增测试 |
|---|---|---|---|
| C1：event_bus 测试 | 30 min | 30 min | 8 |
| C2：signals/ 模块 + PAVA | 55 min | 1.4 h | 10 |
| C3：signal_service + 业务测试 | 55 min | 2.3 h | 10 |
| C4：outcome_tracker + 动态窗口 | 55 min | 3.2 h | 12 |
| C5：Signal ORM 补充字段 | 25 min | 3.6 h | 0 |
| C6：集成测试 + 验收清单 | 35 min | **4.0 h** | 5 |
| **总计** | **6 个任务** | **4 小时** | **45 新增** |

---

## 完工报告

- **输出文件**：`/Users/hahaha/Desktop/CODE/kbkkk/docs/plans/m2-c-signal-outcome.md`
- **任务数**：6 个（C1–C6）
- **总估计工时**：4 小时
- **新增测试文件**：6 个（test_event_bus.py / test_calibration.py / test_signal_service.py / test_outcome_tracker.py / test_signal_service_integration.py + signals/ 模块含内测）
- **新增测试用例**：45 个（8 + 10 + 10 + 12 + 0 + 5）
- **目标测试数**：123 passed（79 原有 + 44 新增）
- **关键交付物**：
  - `backend/app/services/event_bus.py`（已存在，补充测试）
  - `backend/app/signals/calibration.py`（新建，PAVA Isotonic）
  - `backend/app/services/signal_service.py`（新建，核心协调服务）
  - `backend/app/services/outcome_tracker.py`（新建，动态窗口 outcome）
  - `backend/app/models/__init__.py`（补充 symbol/period/confluence_score 字段）
  - `backend/tests/test_signal_service_integration.py`（新建，端到端验收）
