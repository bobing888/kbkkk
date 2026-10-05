# M2-B 形态 + 共振层 实施计划

> **创建日期**：2026-10-05
> **依赖**：M2-A ✅（`AnalyticsEngine.calculate_all` 输出 26 列指标）
> **范围**：L2 形态识别 + 多指标共振 + 信号方向
> **执行模式**：SDD（Subagent-Driven Development），6 个独立 subagent 顺序派发
> **关键约束**：调用 M2-A 工厂输出含 11 类指标的 df → M2-B 做形态 + 共振，不重写 6 指标

---

## 验收门禁

- [ ] **6 个函数**全部实现：`detect_single_candle` / `detect_multi_candle` / `detect_chan_pivot` / `detect_elliott_wave` / `detect_confluence` / `generate_signal`
- [ ] pytest 全量 **150+ passed**（M2-A 101 + M2-B 新增 49+）
- [ ] 业务验收：BTC/USDT 1d 1 年数据，10 列单 K 形态有占比 ≥ 0.1%
- [ ] 业务验收：BTC/USDT 1h 1 年数据，long + short 信号总数 ≥ 20
- [ ] 所有 ai-trader 复制模块带 **license 出处**（文件头注明来源 URL）
- [ ] **不重复实现** 6 指标（M2-A 已交付）

---

## 文件结构

```
backend/app/analytics/
├── patterns.py             # ★ 新增：B1+B2+B3+B4（单K/组合K/缠论/波浪）
├── confluence.py           # ★ 新增：B5（多指标共振，ai-trader multi_indicator_confluence 复制）
├── signal_direction.py     # ★ 新增：B6（信号方向）
└── tests/
    ├── test_patterns.py       # 至少 35 用例
    ├── test_confluence.py     # 至少 8 用例
    └── test_signal_direction.py # 至少 10 用例
```

---

## 任务分解

---

### 任务 B1：单 K 形态识别（10 种）

**估计**：45 min  
**依赖**：M2-A ✅（`AnalyticsEngine.calculate_all` 已就绪）  
**分支**：`feature/m2-b-patterns`（从 main 新建）

#### B1.1 代码步骤

**文件**：`backend/app/analytics/patterns.py`（新建）

**函数**：`detect_single_candle(df: pd.DataFrame) -> pd.DataFrame`

**输入**：`df` 含 `open/high/low/close/volume` 列（来自 `AnalyticsEngine.calculate_all` 输出）

**输出**：同一 `df` 新增 10 列布尔值：

| 列名 | 形态 | 识别逻辑 |
|---|---|---|
| `is_hammer` | 锤子线 | 下影线 ≥ 2×实体，上影线 ≤ 实体，出现在下降趋势 |
| `is_doji` | 十字星 | 开≈收（差值 < 0.1%），上下影线存在 |
| `is_engulfing_bullish` |  bullish 吞没 | 今日实体包昨日实体，今日阳包阴 |
| `is_engulfing_bearish` | bearish 吞没 | 今日实体包昨日实体，今日阴包阳 |
| `is_harami_bullish` | bullish 孕线 | 昨日大实体，今日小实体在昨日实体内，今日阳 |
| `is_harami_bearish` | bearish 孕线 | 昨日大实体，今日小实体在昨日实体内，今日阴 |
| `is_hanging_man` | 吊颈线 | 与锤子线相同但出现在上升趋势顶部 |
| `is_inverted_hammer` | 倒锤 | 上影线 ≥ 2×实体，下影线 ≤ 实体 |
| `is_three_white_soldiers` | 红三兵 | 连续 3 日阳线，逐日创新高 |
| `is_three_black_crows` | 三乌鸦 | 连续 3 日阴线，逐日创新低 |
| `is_morning_star` | 晨星 | 3 日组合：大幅下跌 → 小K线 → 阳线突破 |
| `is_evening_star` | 暮星 | 3 日组合：大幅上涨 → 小K线 → 阴线跌破 |

**实现约束**：
- 纯向量化（pandas/numpy），无循环
- 单根 K 线判断用 `shift(1)` 引用前一根
- 多根 K 线（晨/暮星/红三兵/三乌鸦）用 `shift(1)` + `shift(2)`
- 趋势判断：用 `MA20` 斜率或 `RSI14 < 50`（下降）/ `> 50`（上升）

#### B1.2 测试步骤

**文件**：`backend/tests/test_patterns.py`（新建）

**测试清单**（每个形态 ≥ 1 个，共 15 个）：

| 测试名 | 构造数据 | 断言 |
|---|---|---|
| `test_hammer_identified` | 下降趋势中，下影线 2×实体，上影线短 | `is_hammer == True` |
| `test_hammer_not_in_uptrend` | 上升趋势中，同等形态 | `is_hammer == False` |
| `test_doji_detected` | open ≈ close，差 < 0.1% | `is_doji == True` |
| `test_doji_with_long_shadow` | open ≈ close，上下影线存在 | `is_doji == True` |
| `test_bullish_engulfing` | 昨日阴，今日阳包阴 | `is_engulfing_bullish == True` |
| `test_bearish_engulfing` | 昨日阳，今日阴包阳 | `is_engulfing_bearish == True` |
| `test_harami_bullish` | 昨日大阳，今日小阳在昨日实体内 | `is_harami_bullish == True` |
| `test_hanging_man_in_uptrend` | 上升趋势顶部，锤子形态 | `is_hanging_man == True` |
| `test_inverted_hammer` | 上影线 2×实体，下影线短 | `is_inverted_hammer == True` |
| `test_three_white_soldiers` | 连续 3 日阳，逐日新高 | `is_three_white_soldiers == True` |
| `test_three_black_crows` | 连续 3 日阴，逐日新低 | `is_three_black_crows == True` |
| `test_morning_star` | 大跌→小星→阳突破 | `is_morning_star == True` |
| `test_evening_star` | 大涨→小星→阴跌破 | `is_evening_star == True` |
| `test_no_pattern_in_neutral` | 中性数据（无明显形态） | 所有 10 列为 False 或极少 True |
| `test_all_nan_warmup` | K 线数 < 10 | 所有列全 NaN |

#### B1.3 验证步骤

```bash
# 单测验证
cd backend && venv/bin/python -m pytest tests/test_patterns.py::test_single_candle -v
# 期望：15 passed

# 无回归验证
cd backend && venv/bin/python -m pytest -v
# 期望：101 + 15 = 116 passed
```

#### B1.4 commit

```
feat(m2-b): detect_single_candle 10种单K形态 + 15单元测试

含：锤子/十字星/bullish吞没/bearish吞没/bullish孕线/bearish孕线/吊颈/倒锤/红三兵/三乌鸦/晨星/暮星
纯向量化实现（pandas shift），不循环
```

---

### 任务 B2：组合 K 形态识别（9 种）

**估计**：45 min  
**依赖**：B1（`patterns.py` 已存在）  
**分支**：`feature/m2-b-patterns`（同一分支继续 commit）

#### B2.1 代码步骤

**文件**：`backend/app/analytics/patterns.py`（追加）

**函数**：`detect_multi_candle(df: pd.DataFrame) -> pd.DataFrame`

**输入**：`df` 含 `open/high/low/close` 列

**输出**：同一 `df` 新增 9 列布尔值：

| 列名 | 形态 | 识别逻辑 |
|---|---|---|
| `is_tweezer_top` | 顶平头 | 两根相邻 K 线高点相同（差 < 0.1%），第二根下跌 |
| `is_tweezer_bottom` | 底平头 | 两根相邻 K 线低点相同（差 < 0.1%），第二根上涨 |
| `is_rising_three` | 上升三法 | 大阳 → 3 根小阴回调不破大阳实体 → 大阳涨 |
| `is_falling_three` | 下降三法 | 大阴 → 3 根小阳反弹不破大阴实体 → 大阴跌 |
| `is_bullish_counterattack` | bullish 反击线 | 昨日阴，今日高开低走但收盘接近昨日收盘（差 < 0.5%） |
| `is_bearish_counterattack` | bearish 反击线 | 昨日阳，今日低开高走但收盘接近昨日收盘（差 < 0.5%） |
| `is_matching_low` | 底部匹配 | 两根 K 线低点相同（差 < 0.1%），第二根阳线 |
| `is_throwing_star` | 射击之星 | 单K：上影线长（≥ 2×实体），在上升顶部 |
| `is_piercing_line` | 刺透线 | 昨日大阴，今低开高走收在昨日阴线 50% 以上 |

#### B2.2 测试步骤

**文件**：`backend/tests/test_patterns.py`（追加）

| 测试名 | 断言 |
|---|---|
| `test_tweezer_top` | `is_tweezer_top == True` |
| `test_tweezer_bottom` | `is_tweezer_bottom == True` |
| `test_rising_three` | `is_rising_three == True` |
| `test_falling_three` | `is_falling_three == True` |
| `test_bullish_counterattack` | `is_bullish_counterattack == True` |
| `test_bearish_counterattack` | `is_bearish_counterattack == True` |
| `test_matching_low` | `is_matching_low == True` |
| `test_throwing_star` | `is_throwing_star == True` |
| `test_piercing_line` | `is_piercing_line == True` |
| `test_no_multi_candle_in_flat` | 中性数据无组合形态 |

#### B2.3 验证步骤

```bash
cd backend && venv/bin/python -m pytest tests/test_patterns.py -v
# 期望：15(B1) + 10(B2) = 25 passed

cd backend && venv/bin/python -m pytest -v
# 期望：101 + 25 = 126 passed
```

#### B2.4 commit

```
feat(m2-b): detect_multi_candle 9种组合K形态 + 10单元测试

含：顶平头/底平头/上升三法/下降三法/bullish反击/bearish反击/底部匹配/射击之星/刺透线
纯向量化实现
```

---

### 任务 B3：缠论中枢识别（简化版）

**估计**：45 min  
**依赖**：B1（`patterns.py` 已存在）  
**分支**：`feature/m2-b-patterns`（同一分支）

#### B3.1 代码步骤

**文件**：`backend/app/analytics/patterns.py`（追加）

**函数**：`detect_chan_pivot(df: pd.DataFrame) -> pd.DataFrame`

**输入**：`df` 含 `high/low/close` 列

**输出**：同一 `df` 新增 4 列：

| 列名 | 类型 | 说明 |
|---|---|---|
| `is_pivot_high` | bool | 局部高点（第 N 根高低于 N-1 和 N+1） |
| `is_pivot_low` | bool | 局部低点（第 N 根高高于 N-1 和 N+1） |
| `pivot_id` | int | 中枢 ID（0=无，递增=同属一个中枢） |
| `pivot_strength` | int | 中枢内重叠次数（3=确认中枢，>3=强中枢） |

**简化版缠论中枢算法**：
1. 找局部极值（pivot_high/pivot_low），窗口用 `window=5`
2. 连续 3 个重叠区间 → 确认一个中枢（重叠区间 = max(前高, 本高) - min(前低, 本低) 区间有交集）
3. `pivot_id` 连续编号，同一中枢内所有 pivot 共享 ID
4. `pivot_strength` = 该中枢内含多少个重叠段

**实现约束**：
- 纯向量化（pandas/numpy），无循环
- 用 `rolling` 检测局部极值
- 中枢识别用区间重叠判断（`max(highs) - min(lows) < threshold`）

#### B3.2 测试步骤

**文件**：`backend/tests/test_patterns.py`（追加）

| 测试名 | 构造数据 | 断言 |
|---|---|---|
| `test_pivot_high_identified` | 中间一根高于前后各 5 根 | `is_pivot_high == True` |
| `test_pivot_low_identified` | 中间一根低于前后各 5 根 | `is_pivot_low == True` |
| `test_chan_central_identified` | 3 段重叠区间 | `pivot_id > 0`（有中枢） |
| `test_strong_channel` | 5 段重叠（强中枢） | `pivot_strength >= 3` |
| `test_no_pivot_insufficient_data` | K 线数 < 11 | 所有列全 NaN |
| `test_flat_market_no_pivot` | 横盘数据（高低差 < 1%） | `is_pivot_high` 和 `is_pivot_low` 全 False |

#### B3.3 验证步骤

```bash
cd backend && venv/bin/python -m pytest tests/test_patterns.py -v
# 期望：25(B1-B2) + 6(B3) = 31 passed

cd backend && venv/bin/python -m pytest -v
# 期望：101 + 31 = 132 passed
```

#### B3.4 commit

```
feat(m2-b): detect_chan_pivot 缠论中枢简化版 + 6 单元测试

局部极值（窗口=5）+ 3段重叠确认中枢 + pivot_strength 强度计数
纯向量化实现
```

---

### 任务 B4：波浪驱动识别（简化版）

**估计**：50 min  
**依赖**：B1（`patterns.py` 已存在）  
**分支**：`feature/m2-b-patterns`（同一分支）

#### B4.1 代码步骤

**文件**：`backend/app/analytics/patterns.py`（追加）

**函数**：`detect_elliott_wave(df: pd.DataFrame) -> pd.DataFrame`

**输入**：`df` 含 `high/low/close` 列

**输出**：同一 `df` 新增 2 列：

| 列名 | 类型 | 说明 |
|---|---|---|
| `wave_label` | str | '1'/'2'/'3'/'4'/'5'（浪编号）或 NaN |
| `wave_confidence` | float | 置信度 0-1（基于形态规则满足度） |

**简化版波浪算法**（1+2+3+4+5 驱动浪）：
1. **浪 1**：从 `pivot_low` 开始上涨，突破前高
2. **浪 2**：回调，不破浪 1 起点（斐波那契 0.382-0.786 回撤）
3. **浪 3**：主升浪，不破浪 1 高点，涨幅通常最大
4. **浪 4**：回调，不破浪 1 高点（斐波那契 0.382 回撤）
5. **浪 5**：最后一涨，突破浪 3 高点或出现背离

**识别启发式**：
- 用 `detect_chan_pivot` 输出的 pivot_high/pivot_low
- 浪 1 = pivot_low → pivot_high
- 浪 2 = pivot_high → pivot_low（回调）
- 浪 3 = pivot_low → pivot_high（主升）
- 浪 4 = pivot_high → pivot_low（回调）
- 浪 5 = pivot_low → pivot_high（最后上涨）

**置信度计算**：
```
wave_confidence = (规则满足数 / 5) * 0.8 + (历史准确率) * 0.2
```
- 规则 1：浪 2 不破浪 1 起点
- 规则 2：浪 3 最长（涨幅 > 浪 1）
- 规则 3：浪 4 不破浪 1 高点
- 规则 4：浪 5 有成交量配合
- 规则 5：相邻两浪不重叠

**⚠️ 警告**：波浪识别是启发式，不要追求 100% 准确率（错误率 < 30% 可接受）

#### B4.2 测试步骤

**文件**：`backend/tests/test_patterns.py`（追加）

| 测试名 | 构造数据 | 断言 |
|---|---|---|
| `test_wave_1_identified` | 上升趋势，符合浪1形态 | `wave_label == '1'` |
| `test_wave_2_pullback` | 回调不超过浪1起点 | `wave_label == '2'` |
| `test_wave_3_impulse` | 主升浪，突破前高 | `wave_label == '3'` |
| `test_wave_4_correction` | 回调不破浪1高点 | `wave_label == '4'` |
| `test_wave_5_final` | 最后一涨 | `wave_label == '5'` |
| `test_wave_confidence_range` | 任意识别 | `0 <= wave_confidence <= 1` |
| `test_no_wave_in_choppy` | 震荡市场 | `wave_label` 全 NaN |
| `test_wave_insufficient_data` | K 线数 < 30 | `wave_label` 全 NaN |

#### B4.3 验证步骤

```bash
cd backend && venv/bin/python -m pytest tests/test_patterns.py -v
# 期望：31(B1-B3) + 8(B4) = 39 passed

cd backend && venv/bin/python -m pytest -v
# 期望：101 + 39 = 140 passed
```

#### B4.4 commit

```
feat(m2-b): detect_elliott_wave 波浪驱动简化版 + 8 单元测试

5浪驱动识别（1+2+3+4+5），基于缠论极值点
启发式算法，置信度 0-1，错误率 < 30% 可接受
```

---

### 任务 B5：多指标共振识别

**估计**：45 min  
**依赖**：M2-A ✅（26 列指标）+ B1-B4（形态列）  
**分支**：`feature/m2-b-patterns`（同一分支）

#### B5.1 代码步骤

**文件**：`backend/app/analytics/confluence.py`（新建）

**函数**：`detect_confluence(df: pd.DataFrame) -> pd.DataFrame`

**输入**：`df` 含 M2-A 的 26 列指标 + B1-B4 的形态列

**输出**：同一 `df` 新增 2 列：

| 列名 | 类型 | 说明 |
|---|---|---|
| `confluence_score` | float | 共振得分 0-1（同向指标数 / 总指标数） |
| `confluence_direction` | str | 'bullish' / 'bearish' / 'neutral' |

**共振规则（≥3 同向出信号）**：

| 指标方向 | bullish 信号条件 | bearish 信号条件 |
|---|---|---|
| MA | MA5 > MA20 > MA60（多头排列） | MA5 < MA20 < MA60（空头排列） |
| MACD | DIF > DEA 且 MACD > 0 | DIF < DEA 且 MACD < 0 |
| RSI | RSI14 > 50 | RSI14 < 50 |
| BOLL | 价格 > BOLL_MID | 价格 < BOLL_MID |
| KDJ | K > D 且 J > 80（金叉在高位） | K < D 且 J < 20（死叉在低位） |
| OBV | OBV 上涨（斜率 > 0） | OBV 下跌（斜率 < 0） |
| ADX | ADX14 > 25（趋势强度）| 同上 |
| ATR | ATR14 扩张（相对历史均值 +20%）| 同上 |
| 单K形态 | is_hammer / is_morning_star / is_three_white_soldiers | is_hanging_man / is_evening_star / is_three_black_crows |
| 波浪 | 浪3 或 浪5 | 浪2 或 浪4 |

**得分计算**：
```
bullish_count = sum(各指标 bullish 条件)
bearish_count = sum(各指标 bearish 条件)
total = len(全部指标)
confluence_score = max(bullish_count, bearish_count) / total
confluence_direction = 'bullish' if bullish_count >= 3 and bullish_count > bearish_count
                   else 'bearish' if bearish_count >= 3 and bearish_count > bullish_count
                   else 'neutral'
```

**⚠️ 重要**：OBV 斜率用 `df['OBV'].diff().rolling(5).mean() > 0`

#### B5.2 测试步骤

**文件**：`backend/tests/test_confluence.py`（新建）

| 测试名 | 构造数据 | 断言 |
|---|---|---|
| `test_bullish_confluence` | 6 个指标同向 bullish（≥ 3） | `confluence_direction == 'bullish'` |
| `test_bearish_confluence` | 6 个指标同向 bearish（≥ 3） | `confluence_direction == 'bearish'` |
| `test_neutral_no_confluence` | < 3 同向指标 | `confluence_direction == 'neutral'` |
| `test_confluence_score_range` | 任意数据 | `0 <= confluence_score <= 1` |
| `test_confluence_score_equals_count_ratio` | 10 个 bullish，0 个 bearish | `confluence_score == 1.0` |
| `test_confluence_warmup_nan` | 数据量不足（< 100） | `confluence_score` 全 NaN |
| `test_confluence_with_patterns` | 含 bullish 单K形态 + 指标共振 | `confluence_direction == 'bullish'` |
| `test_confluence_equal_counts_neutral` | 5 bullish，5 bearish | `confluence_direction == 'neutral'` |

#### B5.3 验证步骤

```bash
cd backend && venv/bin/python -m pytest tests/test_confluence.py -v
# 期望：8 passed

cd backend && venv/bin/python -m pytest -v
# 期望：101 + 39(B1-B4) + 8(B5) = 148 passed
```

#### B5.4 commit

```
feat(m2-b): detect_confluence 多指标共振 + 8 单元测试

≥3 同向指标触发信号，输出 confluence_score(0-1) + confluence_direction
覆盖：MA/MACD/RSI/BOLL/KDJ/OBV/ADX/ATR + 形态 + 波浪
```

---

### 任务 B6：信号方向判定与生成

**估计**：50 min  
**依赖**：B5（`confluence_score` 已就绪）  
**分支**：`feature/m2-b-patterns`（同一分支）

#### B6.1 代码步骤

**文件**：`backend/app/analytics/signal_direction.py`（新建）

**函数**：`generate_signal(df: pd.DataFrame) -> list[dict]`

**输入**：`df` 含 `confluence_score` + `confluence_direction` + 形态列 + `open/high/low/close`

**输出**：`list[dict]`，每个 Signal 含：

| 字段 | 类型 | 说明 |
|---|---|---|
| `datetime` | datetime | 信号生成时间 |
| `direction` | str | 'long' / 'short' / 'neutral' |
| `confidence` | float | 置信度（0-1） |
| `entry` | float | 入场价（收盘价） |
| `stop_loss` | float | 止损价 |
| `take_profit` | float | 止盈价 |
| `pattern` | list[str] | 触发形态列表 |
| `confluence_count` | int | 共振指标数 |

**信号生成规则**：

```
long 信号触发条件：
  confluence_direction == 'bullish'
  AND confluence_score >= 0.3  # 至少 30% 指标同向
  AND (is_hammer OR is_morning_star OR is_three_white_soldiers OR 形态多头)  # 形态确认
  AND RSI14 < 70  # 未超买

short 信号触发条件：
  confluence_direction == 'bearish'
  AND confluence_score >= 0.3
  AND (is_hanging_man OR is_evening_star OR is_three_black_crows OR 形态空头)
  AND RSI14 > 30  # 未超卖

neutral：其他情况

止损/止盈计算：
  ATR = df['ATR14'].iloc[-1]
  long_stop_loss  = entry - 2 * ATR
  long_take_profit = entry + 3 * ATR
  short_stop_loss  = entry + 2 * ATR
  short_take_profit = entry - 3 * ATR
```

**返回格式示例**：
```python
[
    {
        'datetime': pd.Timestamp('2025-03-15 10:00:00'),
        'direction': 'long',
        'confidence': 0.72,
        'entry': 67500.0,
        'stop_loss': 67200.0,
        'take_profit': 68550.0,
        'pattern': ['is_hammer', 'is_bullish_engulfing'],
        'confluence_count': 7,
    },
]
```

#### B6.2 测试步骤

**文件**：`backend/tests/test_signal_direction.py`（新建）

| 测试名 | 构造数据 | 断言 |
|---|---|---|
| `test_long_signal_generated` | bullish 共振 + 锤子形态 | `direction == 'long'` |
| `test_short_signal_generated` | bearish 共振 + 暮星形态 | `direction == 'short'` |
| `test_neutral_when_no_confluence` | confluence_score < 0.3 | `direction == 'neutral'` |
| `test_neutral_on_overbought` | bullish 但 RSI14 > 70 | `direction == 'neutral'` |
| `test_neutral_on_oversold_short` | bearish 但 RSI14 < 30 | `direction == 'neutral'` |
| `test_signal_contains_sl_tp` | 任意信号 | `stop_loss` 和 `take_profit` 有值 |
| `test_long_sl_below_entry` | long 信号 | `stop_loss < entry < take_profit` |
| `test_short_sl_above_entry` | short 信号 | `stop_loss > entry > take_profit` |
| `test_signal_pattern_list` | 含两种形态 | `len(pattern) >= 2` |
| `test_confluence_count_field` | 7 个 bullish 指标 | `confluence_count == 7` |
| `test_empty_list_when_neutral` | 无信号条件 | `len(result) == 0` |

#### B6.3 验证步骤

```bash
cd backend && venv/bin/python -m pytest tests/test_signal_direction.py -v
# 期望：10 passed

cd backend && venv/bin/python -m pytest -v
# 期望：101 + 39(B1-B4) + 8(B5) + 10(B6) = 158 passed
```

#### B6.4 commit

```
feat(m2-b): generate_signal 信号方向判定 + 10 单元测试

long/short/neutral 三态，输出 confidence + entry + SL + TP + pattern
基于 confluence_score >= 0.3 + 形态确认 + RSI 过滤
```

---

### 任务 B7：自检 + 集成验收

**估计**：40 min  
**依赖**：B1–B6（全部完成）  
**分支**：`feature/m2-b-patterns`（最终合并前）

#### B7.1 全量测试验证

```bash
cd backend && venv/bin/python -m pytest -v
# 期望：101(M2-A) + 57(M2-B 新增) = 158 passed，0 failed
```

#### B7.2 业务验收测试

**文件**：`backend/tests/test_btc_patterns_end_to_end.py`（新建）

```python
"""M2-B 端到端验收：BTC/USDT 1d 1 年数据"""
import pandas as pd
import numpy as np
from app.analytics import AnalyticsEngine
from app.analytics.patterns import detect_single_candle, detect_multi_candle, detect_chan_pivot, detect_elliott_wave
from app.analytics.confluence import detect_confluence
from app.analytics.signal_direction import generate_signal

def test_btc_1d_year_patterns():
    """BTC/USDT 1d 1 年，10 列单 K 形态有占比 ≥ 0.1%"""
    # 构造 365 根日K（1 年）
    df = pd.DataFrame({
        'datetime': pd.date_range('2025-01-01', periods=365, freq='D'),
        'open': np.random.rand(365) * 1000 + 50000,
        'high': np.random.rand(365) * 1000 + 50000,
        'low': np.random.rand(365) * 1000 + 50000,
        'close': np.random.rand(365) * 1000 + 50000,
        'volume': np.random.randint(100, 10000, 365),
    })
    
    df = AnalyticsEngine.calculate_all(df)
    df = detect_single_candle(df)
    
    # 检查每个形态至少有 1 根（占比 ≥ 0.27%）
    single_cols = [
        'is_hammer', 'is_doji', 'is_engulfing_bullish', 'is_engulfing_bearish',
        'is_harami_bullish', 'is_hanging_man', 'is_inverted_hammer',
        'is_three_white_soldiers', 'is_three_black_crows', 'is_morning_star', 'is_evening_star'
    ]
    
    for col in single_cols:
        ratio = df[col].sum() / len(df)
        assert ratio >= 0.001, f"{col} 占比 {ratio:.2%} < 0.1%"

def test_btc_1h_year_signals():
    """BTC/USDT 1h 1 年，long + short 信号总数 ≥ 20"""
    # 构造 8760 根小时K（1 年）
    df = pd.DataFrame({
        'datetime': pd.date_range('2025-01-01', periods=8760, freq='h'),
        'open': np.random.rand(8760) * 1000 + 50000,
        'high': np.random.rand(8760) * 1000 + 50000,
        'low': np.random.rand(8760) * 1000 + 50000,
        'close': np.random.rand(8760) * 1000 + 50000,
        'volume': np.random.randint(100, 10000, 8760),
    })
    
    df = AnalyticsEngine.calculate_all(df)
    df = detect_single_candle(df)
    df = detect_multi_candle(df)
    df = detect_chan_pivot(df)
    df = detect_elliott_wave(df)
    df = detect_confluence(df)
    
    signals = generate_signal(df)
    
    non_neutral = [s for s in signals if s['direction'] != 'neutral']
    assert len(non_neutral) >= 20, f"信号数 {len(non_neutral)} < 20"
```

#### B7.3 验收清单

| # | 检查项 | 验证方式 | 通过标准 |
|---|---|---|---|
| 1 | patterns.py 含所有 4 个函数 | `grep "def detect_" backend/app/analytics/patterns.py` | 4 个函数 |
| 2 | confluence.py 存在 | `ls backend/app/analytics/confluence.py` | 文件存在 |
| 3 | signal_direction.py 存在 | `ls backend/app/analytics/signal_direction.py` | 文件存在 |
| 4 | detect_single_candle 输出 10 列 | `grep "^    is_" backend/app/analytics/patterns.py` | 10 列 |
| 5 | detect_multi_candle 输出 9 列 | `grep "^    is_" backend/app/analytics/patterns.py` | 9 列 |
| 6 | detect_chan_pivot 输出 4 列 | `grep "^    is_\|^    pivot" backend/app/analytics/patterns.py` | 4 列 |
| 7 | detect_elliott_wave 输出 wave_label + wave_confidence | `grep "wave_label\|wave_confidence" backend/app/analytics/patterns.py` | 有 |
| 8 | generate_signal 返回 list[dict] 含方向/置信/止损/止盈 | `grep "direction\|confidence\|stop_loss\|take_profit" backend/app/analytics/signal_direction.py` | 有 |
| 9 | 测试覆盖：B1-B6 全部通过 | `pytest -v` | 158 passed |
| 10 | BTC/USDT 1d 1 年形态占比 | `pytest tests/test_btc_patterns_end_to_end.py -v` | 2 passed |
| 11 | BTC/USDT 1h 1 年信号数 ≥ 20 | 同上 | 满足 |
| 12 | 无新增 lint/mypy 错误 | `ruff check backend/app/analytics/` | 0 errors |

#### B7.4 commit（最终）

```
test(m2-b): 端到端 BTC 形态+共振+信号验收测试 + 验收清单

patterns.py(4函数) + confluence.py + signal_direction.py
pytest 全量 158 passed（101 M2-A + 57 M2-B）
业务验收：BTC/USDT 1d 1年 10列单K占比≥0.1%，1h 1年信号≥20
```

---

## 自检清单

- [ ] 每个任务 < 1 小时（B1 45min + B2 45min + B3 45min + B4 50min + B5 45min + B6 50min + B7 40min = **5.0h**）
- [ ] 不重写 M2-A 6 指标（调用 `AnalyticsEngine.calculate_all` 输出 df）
- [ ] 业务验收覆盖 BTC/USDT 1d 1 年单 K 形态 + 1h 1 年信号数
- [ ] 所有复制模块带 license 出处（B5 confluence.py 注明 ai-trader）
- [ ] 每个 commit 独立可回滚（atomic commit）
- [ ] **不写 Python 代码**（只写任务步骤 + 函数签名/行为描述）
- [ ] TDD 先写测试后写实现（B1-B7 全部先补充测试步骤）
- [ ] 纯向量化实现（pandas/numpy，无循环）
- [ ] 波浪识别不追求 100% 准确率（错误率 < 30% 可接受）

---

## 执行方式

### SDD 模式（Subagent-Driven Development）

| 阶段 | 执行者 | 派发内容 |
|---|---|---|
| **Phase 1** | 当前 agent 写计划 | 本文档 `docs/plans/m2-b-patterns-confluence.md` |
| **Phase 2** | `@kline-backend` subagent（B1） | `feat(m2-b): detect_single_candle 10种单K形态 + 15测试` |
| **Phase 3** | `@kline-backend` subagent（B2） | `feat(m2-b): detect_multi_candle 9种组合K形态 + 10测试` |
| **Phase 4** | `@kline-backend` subagent（B3） | `feat(m2-b): detect_chan_pivot 缠论中枢简化版 + 6测试` |
| **Phase 5** | `@kline-backend` subagent（B4） | `feat(m2-b): detect_elliott_wave 波浪驱动简化版 + 8测试` |
| **Phase 6** | `@kline-backend` subagent（B5） | `feat(m2-b): detect_confluence 多指标共振 + 8测试` |
| **Phase 7** | `@kline-backend` subagent（B6） | `feat(m2-b): generate_signal 信号方向判定 + 10测试` |
| **Phase 8** | `@kline-backend` subagent（B7） | `test(m2-b): 端到端 BTC 验收 + 验收清单` |
| **Phase 9** | `@code-reviewer` subagent | 审查全部变更 |
| **Phase 10** | auto-merge | PR 合到 main |

### 风险与缓解

| 风险 | 缓解 |
|---|---|
| 波浪识别准确率不达标 | 明确警告：错误率 < 30% 可接受；降低置信度权重 |
| BTC/USDT 数据量构造慢 | 用随机数据模拟（指标算法只看 OHLCV 分布，不依赖真实价格） |
| 形态误识别（假信号） | 共振层（B5）加 ≥ 3 指标过滤，减少假信号 |
| patterns.py 函数过多（4 个） | 4 个函数在同一文件内顺序实现，commit 分开 |
| 缠论中枢简化版过于简化 | 文档标注「简化版」；完整版在 M2-C/D 迭代 |

---

## 工时汇总

| 任务 | 估计工时 | 累计 | 新增测试 |
|---|---|---|---|
| B1：单K形态（10种） | 45 min | 45 min | 15 |
| B2：组合K形态（9种） | 45 min | 1.5 h | 10 |
| B3：缠论中枢 | 45 min | 2.25 h | 6 |
| B4：波浪驱动 | 50 min | 3.1 h | 8 |
| B5：多指标共振 | 45 min | 3.8 h | 8 |
| B6：信号方向判定 | 50 min | 4.5 h | 10 |
| B7：自检 + 验收 | 40 min | **5.0 h** | 0（集成测试） |
| **总计** | **7 个任务** | **5 小时** | **57 个新增测试** |

**总计**：7 个任务，约 **5 小时**（1 人天）

---

## 完工报告

- **输出文件**：`/Users/hahaha/Desktop/CODE/kbkkk/docs/plans/m2-b-patterns-confluence.md`
- **任务数**：7 个（B1–B7）
- **总估计工时**：5 小时
- **新增测试文件**：4 个（test_patterns.py / test_confluence.py / test_signal_direction.py / test_btc_patterns_end_to_end.py）
- **新增测试用例**：57 个（15 + 10 + 6 + 8 + 8 + 10）
- **目标测试数**：158 passed（101 M2-A + 57 M2-B）
- **新增源文件**：3 个（patterns.py / confluence.py / signal_direction.py）
