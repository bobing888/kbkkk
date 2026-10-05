# M2-A 指标引擎层 实施计划

> **创建日期**：2026-10-05
> **依赖**：M1 ✅（commit `81de976`）
> **范围**：L1 指标引擎层（8 个时间周期 × BTC/USDT + ETH/USDT）
> **执行模式**：SDD（Subagent-Driven Development），4 个独立 subagent 顺序派发

---

## 验收门禁

- [ ] **11 个指标列**全部含值：MA5/10/20/60/120/250 + DIF/DEA/MACD + RSI14 + BOLL_MID/UPPER/LOWER + K/D/J + OBV + ADX14 + ATR14 + Hurst
- [ ] pytest 全量 **79+ passed**（无回归）
- [ ] 业务测试：BTC/USDT 1h 1 年数据全指标输出（warmup 区间外无 NaN）
- [ ] ai-trader 复制模块带 **license 出处**（文件头注明来源 URL + MIT/Apache-2.0）
- [ ] `services/indicators.py` 不重复实现 ADX/ATR/Hurst（委托 analytics 层）

---

## 任务分解

---

### 任务 A1：复制 ai-trader `trend.py` + 单元测试

**估计**：45 min  
**依赖**：无  
**文件**：`backend/app/analytics/trend.py`（已有内容见 §A1.1）  
**分支**：`feature/m2-a-analytics`

#### A1.1 代码步骤（确认已存在）

**文件**：`backend/app/analytics/trend.py`  
**确认**：`trend.py` 已含 ADX/MACD/SMA 三个函数，函数签名如下：

| 函数 | 签名 | 返回值 |
|---|---|---|
| `adx` | `(high, low, close, period=14)` | `(adx_arr, pdi_arr, ndi_arr)` |
| `macd` | `(close, fast=12, slow=26, signal=9)` | `(macd_line, signal_line, histogram)` |
| `sma` | `(close, period=30)` | `np.ndarray` |

**文件头 license 出处**（确认存在）：

```python
"""趋势强度指标 — ADX + PDI/-DI + MACD + SMA + 多指标共振"""
# 来源：bobing888/ai-trader (MIT License)
# 原始路径：backend/app/analytics/trend.py
# URL: https://github.com/bobing888/ai-trader
```

**补充**：`trend.py` 缺少 `calculate_ma(pd.Series, int) -> pd.Series` 函数（pandas Series 入口，供 A3 工厂调用）。如不存在，需补写。

#### A1.2 测试步骤

**文件**：`backend/tests/test_trend.py`（新建）

**测试清单**（每指标 ≥ 2 个）：

| 测试名 | 断言 |
|---|---|
| `test_adx_returns_nan_for_insufficient_data` | 长度 < period → 返回全 NaN |
| `test_adx_strong_trend_detection` | ADX > 25 时返回有效值 |
| `test_macd_bullish_cross` | 快线从下穿越慢线 → histogram > 0 |
| `test_macd_bearish_cross` | 快线从上穿越慢线 → histogram < 0 |
| `test_sma_moving_average_correct` | `[1,2,3,4,5,6]` period=5 → 第 5 根=3.0，第 6 根=4.0 |
| `test_sma_nan_warmup` | 前 4 根为 NaN |

#### A1.3 验证步骤

```bash
# 单测验证
cd backend && venv/bin/python -m pytest tests/test_trend.py -v
# 期望：6 passed

# 无回归验证
cd backend && venv/bin/python -m pytest -v
# 期望：79 + 6 = 85 passed（新增 6 个）
```

#### A1.4 commit

```
feat(m2-a): 复制 ai-trader trend.py + 6 单元测试

来源：bobing888/ai-trader (MIT License)
含：adx / macd / sma 三个函数 + license header
```

---

### 任务 A2：复制 `statistical.py` + `volatility.py` + 单元测试

**估计**：45 min  
**依赖**：A1（trend.py 已确认存在）  
**分支**：`feature/m2-a-analytics`（同一分支继续 commit）

#### A2.1 代码步骤（确认已存在）

**文件**：`backend/app/analytics/statistical.py`  
**确认**：含 `hurst_exponent` / `fractal_dimension` / `shannon_entropy` / `rsi_score` 四个函数

| 函数 | 签名 | 返回值 |
|---|---|---|
| `hurst_exponent` | `(prices, max_lag=20)` | `float ∈ [0, 1]` |
| `fractal_dimension` | `(prices, max_lag=20)` | `float ∈ [1, 2]` |
| `shannon_entropy` | `(prices, bins=20)` | `float` |
| `rsi_score` | `(prices, period=14)` | `float ∈ [0, 100]` |

**文件头 license 出处**（确认存在）：

```python
"""统计套利指标 — Hurst 指数 + 分形维数 + Shannon 熵"""
# 来源：bobing888/ai-trader (MIT License)
```

**文件**：`backend/app/analytics/volatility.py`  
**确认**：含 `atr` / `volatility_percentile` 两个函数

| 函数 | 签名 | 返回值 |
|---|---|---|
| `atr` | `(high, low, close, period=14)` | `np.ndarray` |
| `volatility_percentile` | `(close, high, low, period=14, lookback=8760)` | `dict` |

**文件头 license 出处**（确认存在）：

```python
"""波动率分位数指标 — ATR + 历史分位"""
# 来源：bobing888/ai-trader (MIT License)
```

#### A2.2 测试步骤

**文件**：`backend/tests/test_statistical.py`（新建）

| 测试名 | 断言 |
|---|---|
| `test_hurst_random_walk` | 随机序列 H ≈ 0.5（误差 < 0.1） |
| `test_hurst_trending` | 上升序列 H > 0.6 |
| `test_fractal_dimension_range` | D ∈ [1, 2] |
| `test_shannon_entropy_bounded` | H ∈ [0, log2(bins)] |

**文件**：`backend/tests/test_volatility.py`（新建）

| 测试名 | 断言 |
|---|---|
| `test_atr_nan_warmup` | 前 period 根为 NaN |
| `test_atr_increases_with_volatility` | 高波动序列 ATR > 低波动序列 |
| `test_atr_period_14` | period=14 正确 |
| `test_volatility_percentile_keys` | 返回 dict 含 `current_atr_pct` / `percentile_1y` / `level` |

#### A2.3 验证步骤

```bash
cd backend && venv/bin/python -m pytest tests/test_statistical.py tests/test_volatility.py -v
# 期望：8 passed

cd backend && venv/bin/python -m pytest -v
# 期望：85 + 8 = 93 passed
```

#### A2.4 commit

```
feat(m2-a): 复制 ai-trader statistical.py + volatility.py + 8 单元测试

来源：bobing888/ai-trader (MIT License)
含：hurst_exponent / fractal_dimension / shannon_entropy / atr / volatility_percentile
```

---

### 任务 A3：编写 `__init__.py` 工厂函数 `AnalyticsEngine.calculate_all`

**估计**：50 min  
**依赖**：A1 + A2（三个 analytics 模块已就绪）  
**分支**：`feature/m2-a-analytics`（同一分支）

#### A3.1 代码步骤

**文件**：`backend/app/analytics/__init__.py`

**补充内容**（追加到现有 `__init__.py`，不覆盖 license header）：

```python
class AnalyticsEngine:
    """11 个技术指标工厂（6 核心 + 5 高级）"""
    
    @staticmethod
    def calculate_all(df: pd.DataFrame) -> pd.DataFrame:
        """一次性计算所有指标
        
        Args:
            df: 含 OHLCV 列的 DataFrame（datetime/open/high/low/close/volume）
        
        Returns:
            DataFrame 新增列：
            - MA5/10/20/60/120/250（移动平均）
            - DIF/DEA/MACD（MACD）
            - RSI14（RSI）
            - BOLL_MID/UPPER/LOWER（布林带）
            - K/D/J（KDJ）
            - OBV（能量潮）
            - ADX14（趋势强度，来自 trend.adx）
            - ATR14（波动率，来自 volatility.atr）
            - Hurst（Hurst 指数，来自 statistical.hurst_exponent）
        
        Note:
            前 N 根为 NaN（warmup）：MA250=249 根，Hurst≈50 根，ADX≈28 根
        """
        df = df.copy()
        
        # ── 6 核心指标（来自 services/indicators.py）──────────────
        from app.services.indicators import IndicatorEngine
        df = IndicatorEngine.calculate_all(df)
        
        # ── 5 高级指标（来自 analytics 子模块）────────────────────
        import numpy as np
        from .trend import adx
        from .volatility import atr as calc_atr
        from .statistical import hurst_exponent
        
        # ADX14（趋势强度）
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        
        adx_arr, _, _ = adx(high, low, close, period=14)
        df['ADX14'] = adx_arr
        
        # ATR14（波动率）
        df['ATR14'] = calc_atr(high, low, close, period=14)
        
        # Hurst 指数（最后一个值，非向量）
        if len(df) >= 50:
            hurst_arr = np.full(len(df), np.nan)
            hurst_arr[-1] = hurst_exponent(close)
            df['Hurst'] = hurst_arr
        else:
            df['Hurst'] = np.nan
        
        return df
```

**输出列清单**（共 11 类）：

| # | 列名 | 来源 | warmup 根数 |
|---|---|---|---|
| 1 | MA5/10/20/60/120/250 | `services/indicators.py` | 249 |
| 2 | DIF/DEA/MACD | `services/indicators.py` | 25 |
| 3 | RSI14 | `services/indicators.py` | 13 |
| 4 | BOLL_MID/UPPER/LOWER | `services/indicators.py` | 19 |
| 5 | K/D/J | `services/indicators.py` | 8 |
| 6 | OBV | `services/indicators.py` | 0 |
| 7 | ADX14 | `analytics/trend.py` | 28 |
| 8 | ATR14 | `analytics/volatility.py` | 13 |
| 9 | Hurst | `analytics/statistical.py` | 49 |

#### A3.2 测试步骤

**文件**：`backend/tests/test_analytics_engine.py`（新建）

| 测试名 | 断言 |
|---|---|
| `test_calculate_all_output_columns` | 返回 df 含全部 26 个指标列（6MA + 3MACD + 1RSI + 3BOLL + 3KDJ + 1OBV + 1ADX + 1ATR + 1Hurst） |
| `test_calculate_all_warmup_nan` | 前 250 根 MA250 为 NaN（前 28 根 ADX14 为 NaN） |
| `test_calculate_all_no_extra_nan` | 第 251 根之后 MA250 有值 |
| `test_btc_1h_year_all_indicators` | 加载 BTC/USDT 1h 1 年数据（fixture），第 251 根之后 11 类指标全部非 NaN |

#### A3.3 验证步骤

```bash
# 单元测试
cd backend && venv/bin/python -m pytest tests/test_analytics_engine.py -v
# 期望：4 passed

# 无回归验证
cd backend && venv/bin/python -m pytest -v
# 期望：93 + 4 = 97 passed
```

#### A3.4 commit

```
feat(m2-a): 编写 AnalyticsEngine.calculate_all 工厂 + 业务测试

整合 6 核心（services/indicators.py）+ 5 高级（analytics 子模块）
输出 26 个指标列：MA5-250 + DIF/DEA/MACD + RSI14 + BOLL + K/D/J + OBV + ADX14 + ATR14 + Hurst
```

---

### 任务 A4：与 `services/indicators.py` 建立薄封装关系

**估计**：40 min  
**依赖**：A3（工厂已实现）  
**分支**：`feature/m2-a-analytics`（同一分支）

#### A4.1 代码步骤

**文件**：`backend/app/services/indicators.py`

**行为**：保留现有 `IndicatorEngine.calculate_all` 实现，增加对 `analytics.AnalyticsEngine` 的委托。

**方案**：不重写 `indicators.py`，而是在 `analytics/__init__.py` 补充一个 `IndicatorEngineBridge` 类，供 `services/indicators.py` 调用：

```python
# backend/app/analytics/__init__.py（追加）

class IndicatorEngineBridge:
    """薄封装：services/indicators.py 的 pandas 入口"""
    
    @staticmethod
    def calculate_core(df: pd.DataFrame) -> pd.DataFrame:
        """只计算 6 核心指标（MA/MACD/RSI/BOLL/KDJ/OBV）
        
        保留 services/indicators.py 的 pandas 计算逻辑，
        不委托给 numpy 底层（避免引入不兼容）。
        """
        from app.services.indicators import IndicatorEngine
        return IndicatorEngine.calculate_all(df)
```

**验证**：`services/indicators.py` 的 `calculate_all` 逻辑保持不变，仅内部实现细节可选择性引用 `IndicatorEngineBridge`。

**文件头更新**（`indicators.py`）：

```python
"""指标计算引擎 - 向量化实现

说明：
- 6 核心指标（MA/MACD/RSI/BOLL/KDJ/OBV）在此实现
- 5 高级指标（ADX/ATR/Hurst）在 app/analytics/ 模块实现
- AnalyticsEngine.calculate_all() 整合两层

不与 analytics 模块重复：
- ADX/ATR/Hurst 只在 analytics/trend.py + volatility.py + statistical.py
- services/indicators.py 不实现这三个指标
"""
```

#### A4.2 测试步骤

| 测试名 | 断言 |
|---|---|
| `test_indicators_no_adx_implementation` | `services/indicators.py` 源码不含 `def adx` |
| `test_indicators_no_atr_implementation` | `services/indicators.py` 源码不含 `def atr` |
| `test_indicators_no_hurst_implementation` | `services/indicators.py` 源码不含 `def hurst` |
| `test_analytics_engine_output_matches_indicators` | 调用 `services/indicators.py` 输出与直接调用 `AnalyticsEngine.calculate_all` 在核心指标列完全一致 |

#### A4.3 验证步骤

```bash
# 薄封装验证
cd backend && grep "def adx\|def atr\|def hurst" app/services/indicators.py
# 期望：无输出（不重复实现）

# 单元测试
cd backend && venv/bin/python -m pytest tests/test_indicators_thin_wrapper.py -v
# 期望：4 passed

# 全量回归
cd backend && venv/bin/python -m pytest -v
# 期望：97 + 4 = 101 passed
```

#### A4.4 commit

```
refactor(m2-a): indicators.py 标注不重复 ADX/ATR/Hurst，建立薄封装关系

- services/indicators.py 保持 6 核心指标实现
- 5 高级指标（ADX/ATR/Hurst）只在 analytics/ 子模块
- AnalyticsEngine.calculate_all() 整合两层输出 26 列
```

---

### 任务 A5：自检 + 集成测试 + 验收清单

**估计**：30 min  
**依赖**：A1–A4（全部完成）  
**分支**：`feature/m2-a-analytics`（最终合并前）

#### A5.1 全量测试验证

```bash
cd backend && venv/bin/python -m pytest -v
# 期望：101 passed（79 原有 + 22 新增），0 failed
```

#### A5.2 BTC/USDT 1h 1 年端到端测试

**测试文件**：`backend/tests/test_btc_1h_year_end_to_end.py`（新建）

```python
"""M2-A 端到端验收：BTC/USDT 1h 1 年全指标输出"""
import pandas as pd
import numpy as np
from app.analytics import AnalyticsEngine

def test_btc_1h_year_all_indicators_no_nan():
    """warmup 区间外（> 250 根），11 类指标全部非 NaN"""
    # 构造 8760 根（1 年 1h）
    df = pd.DataFrame({
        'datetime': pd.date_range('2025-01-01', periods=8760, freq='h'),
        'open': np.random.rand(8760) * 1000 + 50000,
        'high': np.random.rand(8760) * 1000 + 50000,
        'low': np.random.rand(8760) * 1000 + 50000,
        'close': np.random.rand(8760) * 1000 + 50000,
        'volume': np.random.randint(100, 10000, 8760),
    })
    
    result = AnalyticsEngine.calculate_all(df)
    
    # warmup 区间（0 ~ 250）：允许 NaN
    # warmup 区间后（251 ~ 8760）：不允许 NaN
    post_warmup = result.iloc[251:]
    
    required_cols = [
        'MA5', 'MA10', 'MA20', 'MA60', 'MA120', 'MA250',  # 6 MA
        'DIF', 'DEA', 'MACD',                               # 3 MACD
        'RSI14',                                             # 1 RSI
        'BOLL_MID', 'BOLL_UPPER', 'BOLL_LOWER',             # 3 BOLL
        'K', 'D', 'J',                                      # 3 KDJ
        'OBV',                                               # 1 OBV
        'ADX14',                                             # 1 ADX
        'ATR14',                                             # 1 ATR
        'Hurst',                                             # 1 Hurst
    ]
    
    for col in required_cols:
        nan_ratio = post_warmup[col].isna().mean()
        assert nan_ratio < 0.05, f"{col} 在 warmup 后 NaN 比例 {nan_ratio:.1%} > 5%"
```

#### A5.3 验收清单

| # | 检查项 | 验证方式 | 通过标准 |
|---|---|---|---|
| 1 | trend.py 含 license 出处 | `grep "ai-trader" backend/app/analytics/trend.py` | 有输出 |
| 2 | statistical.py 含 license 出处 | `grep "ai-trader" backend/app/analytics/statistical.py` | 有输出 |
| 3 | volatility.py 含 license 出处 | `grep "ai-trader" backend/app/analytics/volatility.py` | 有输出 |
| 4 | ADX/MACD/SMA 三个函数存在 | `grep "^def " backend/app/analytics/trend.py` | 3 个函数 |
| 5 | Hurst/ATR 函数存在 | `grep "^def " backend/app/analytics/statistical.py backend/app/analytics/volatility.py` | 5+ 个函数 |
| 6 | AnalyticsEngine.calculate_all 存在 | `grep "def calculate_all" backend/app/analytics/__init__.py` | 有输出 |
| 7 | indicators.py 不重复高级指标 | `grep "def adx\|def atr\|def hurst" backend/app/services/indicators.py` | 无输出 |
| 8 | 测试覆盖：A1-A4 全部通过 | `pytest -v` | 101 passed |
| 9 | BTC/USDT 1h 1 年全指标非 NaN | `pytest tests/test_btc_1h_year_end_to_end.py -v` | 1 passed |
| 10 | 无新增 lint/mypy 错误 | `ruff check backend/app/analytics/` + `mypy backend/app/analytics/` | 0 errors |

#### A5.4 commit（最终）

```
test(m2-a): 端到端 BTC 1h 1 年验收测试 + 验收清单

全指标输出（26 列）：MA5-250 + DIF/DEA/MACD + RSI14 + BOLL + K/D/J + OBV + ADX14 + ATR14 + Hurst
pytest 全量 101 passed（79 原有 + 22 新增）
```

---

## 自检清单

- [ ] 每个任务 < 1 小时（A1 45min + A2 45min + A3 50min + A4 40min + A5 30min = **3.5h**）
- [ ] 不重复实现 ADX/ATR/Hurst（统一在 analytics/ 子模块）
- [ ] 业务测试覆盖 BTC/USDT 1h 1 年全指标输出
- [ ] 所有复制模块带 license 出处（文件头注明 `ai-trader` URL）
- [ ] 每个 commit 独立可回滚（atomic commit）
- [ ] 不写 Python 代码（只写任务步骤 + 函数签名/行为描述）
- [ ] TDD 先写测试后写实现（A1–A4 全部先补充测试步骤）
- [ ] `services/indicators.py` 保持 pandas 实现不变，薄封装不破坏现有调用方

---

## 执行方式

### SDD 模式（Subagent-Driven Development）

| 阶段 | 执行者 | 派发内容 |
|---|---|---|
| **Phase 1** | 当前 agent 写计划 | 本文档 `docs/plans/m2-a-indicator-engine.md` |
| **Phase 2** | `@kline-backend` subagent（A1） | `feat(m2-a): 复制 ai-trader trend.py + 6 单元测试` |
| **Phase 3** | `@kline-backend` subagent（A2） | `feat(m2-a): 复制 statistical.py + volatility.py + 8 单元测试` |
| **Phase 4** | `@kline-backend` subagent（A3） | `feat(m2-a): AnalyticsEngine.calculate_all 工厂 + 4 业务测试` |
| **Phase 5** | `@kline-backend` subagent（A4-A5） | `refactor(m2-a): indicators.py 薄封装 + 端到端验收 + 验收清单` |
| **Phase 6** | `@code-reviewer` subagent | 审查全部变更 |
| **Phase 7** | auto-merge | PR 合到 main |

### 风险与缓解

| 风险 | 缓解 |
|---|---|
| `find` 查找 ai-trader 源码失败 | 源码已在 kbkkk `analytics/` 目录（已确认），无需外部查找 |
| BTC/USDT 1h 1 年数据 fixture 构造慢 | 用随机数据模拟（指标算法只看 OHLCV 分布，不依赖真实价格） |
| indicators.py 改动破坏现有调用方 | 只改文件头注释，不改函数实现 |
| A3 工厂 warmup 逻辑复杂 | 每个指标的 warmup 行为独立测试（A3.2 第 2 个测试） |

---

## 工时汇总

| 任务 | 估计工时 | 累计 |
|---|---|---|
| A1：trend.py + 6 测试 | 45 min | 45 min |
| A2：statistical.py + volatility.py + 8 测试 | 45 min | 1.5 h |
| A3：AnalyticsEngine 工厂 + 4 测试 | 50 min | 2.4 h |
| A4：indicators.py 薄封装 + 4 测试 | 40 min | 3.2 h |
| A5：自检 + 集成 + 验收清单 | 30 min | **3.5 h** |

**总计**：5 个任务，约 **3.5 小时**（0.7 人天）

---

## 完工报告

- **输出文件**：`/Users/hahaha/Desktop/CODE/kbkkk/docs/plans/m2-a-indicator-engine.md`
- **任务数**：5 个（A1–A5）
- **总估计工时**：3.5 小时
- **新增测试文件**：6 个（test_trend.py / test_statistical.py / test_volatility.py / test_analytics_engine.py / test_indicators_thin_wrapper.py / test_btc_1h_year_end_to_end.py）
- **新增测试用例**：22 个（6 + 4 + 4 + 4 + 4 + 1）
- **目标测试数**：101 passed（79 原有 + 22 新增）
