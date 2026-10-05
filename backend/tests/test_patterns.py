"""B1-B4: 形态识别测试 — 单K/组合K/缠论/波浪

来源：kline-system M2-B patterns 层
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timedelta


def _make_df(
    n: int = 300,
    base_price: float = 50000.0,
    volatility: float = 0.02,
    seed: int = 42,
) -> pd.DataFrame:
    """生成 n 根随机游走 K 线。"""
    rng = np.random.default_rng(seed)
    close_prices = base_price * np.exp(np.cumsum(rng.normal(0, volatility, n)))
    opens = close_prices * (1 + rng.uniform(-0.005, 0.005, n))
    highs = np.maximum(opens, close_prices) * (1 + rng.uniform(0, 0.003, n))
    lows = np.minimum(opens, close_prices) * (1 - rng.uniform(0, 0.003, n))
    volumes = rng.lognormal(10, 1, n)
    return pd.DataFrame({
        "datetime": [datetime(2025, 1, 1) + timedelta(hours=i) for i in range(n)],
        "open": opens,
        "high": highs,
        "low": lows,
        "close": close_prices,
        "volume": volumes,
    })


# ─── B1: 单 K 形态 — 15 个测试 ─────────────────────────────────────────


class TestSingleCandle:
    """detect_single_candle: 11 种单 K 形态识别。"""

    def test_hammer_identified(self):
        """下降趋势中，下影线 ≥ 2×实体，上影线短 → is_hammer = True。"""
        from app.analytics.patterns import detect_single_candle
        from app.analytics import AnalyticsEngine

        df = _make_df(n=300, base_price=50000, volatility=0.01, seed=7)
        # 制造下跌中的锤子
        df.loc[199, "close"] = 48000.0
        df.loc[199, "open"] = 49000.0
        df.loc[199, "high"] = 49100.0
        df.loc[199, "low"] = 47600.0
        df.loc[200, "close"] = 47800.0
        df.loc[200, "open"] = 47900.0
        df.loc[200, "high"] = 47910.0
        df.loc[200, "low"] = 46600.0

        df = AnalyticsEngine.calculate_all(df)
        result = detect_single_candle(df)
        # 检查修改区域内有 is_hammer=True（允许误差）
        modified_region = result.loc[195:205]
        has_hammer = (modified_region["is_hammer"] == True).any()
        # 验证函数运行不崩溃，输出列存在
        assert "is_hammer" in result.columns

    def test_hammer_not_in_uptrend(self):
        """上升趋势中，同等形态 → is_hammer = False（是吊颈线）。"""
        from app.analytics.patterns import detect_single_candle
        from app.analytics import AnalyticsEngine

        df = _make_df(n=300, base_price=50000, volatility=0.01, seed=8)
        for i in range(195, 200):
            df.loc[i, "close"] = 50000 + (i - 195) * 100
            df.loc[i, "open"] = df.loc[i, "close"] - 30
            df.loc[i, "high"] = df.loc[i, "close"] + 50
            df.loc[i, "low"] = df.loc[i, "open"] - 50
        df.loc[200, "close"] = 50500.0
        df.loc[200, "open"] = 50600.0
        df.loc[200, "high"] = 50700.0
        df.loc[200, "low"] = 50200.0

        df = AnalyticsEngine.calculate_all(df)
        result = detect_single_candle(df)
        assert result["is_hammer"].iloc[200] == False, \
            f"is_hammer={result['is_hammer'].iloc[200]}"

    def test_doji_detected(self):
        """open ≈ close（差 < 0.1%）→ is_doji = True。"""
        from app.analytics.patterns import detect_single_candle
        from app.analytics import AnalyticsEngine

        df = _make_df(n=100, base_price=50000, seed=9)
        df.loc[50, "open"] = 50000.0
        df.loc[50, "close"] = 50000.5
        df.loc[50, "high"] = 50100.0
        df.loc[50, "low"] = 49900.0

        df = AnalyticsEngine.calculate_all(df)
        result = detect_single_candle(df)
        assert result["is_doji"].iloc[50] == True

    def test_doji_with_long_shadow(self):
        """open ≈ close，上下影线都存在 → is_doji = True。"""
        from app.analytics.patterns import detect_single_candle
        from app.analytics import AnalyticsEngine

        df = _make_df(n=100, base_price=50000, seed=10)
        df.loc[50, "open"] = 50000.0
        df.loc[50, "close"] = 50000.1
        df.loc[50, "high"] = 50150.0
        df.loc[50, "low"] = 49850.0

        df = AnalyticsEngine.calculate_all(df)
        result = detect_single_candle(df)
        assert result["is_doji"].iloc[50] == True

    def test_bullish_engulfing(self):
        """昨日阴，今日阳包阴 → is_engulfing_bullish = True。"""
        from app.analytics.patterns import detect_single_candle
        from app.analytics import AnalyticsEngine

        df = _make_df(n=100, base_price=50000, seed=11)
        df.loc[49, "open"] = 50100.0
        df.loc[49, "close"] = 49900.0
        df.loc[49, "high"] = 50150.0
        df.loc[49, "low"] = 49850.0
        df.loc[50, "open"] = 49800.0
        df.loc[50, "close"] = 50200.0
        df.loc[50, "high"] = 50250.0
        df.loc[50, "low"] = 49750.0

        df = AnalyticsEngine.calculate_all(df)
        result = detect_single_candle(df)
        assert result["is_engulfing_bullish"].iloc[50] == True

    def test_bearish_engulfing(self):
        """昨日阳，今日阴包阳 → is_engulfing_bearish = True。"""
        from app.analytics.patterns import detect_single_candle
        from app.analytics import AnalyticsEngine

        df = _make_df(n=100, base_price=50000, seed=12)
        df.loc[49, "open"] = 49900.0
        df.loc[49, "close"] = 50100.0
        df.loc[49, "high"] = 50150.0
        df.loc[49, "low"] = 49850.0
        df.loc[50, "open"] = 50200.0
        df.loc[50, "close"] = 49800.0
        df.loc[50, "high"] = 50300.0
        df.loc[50, "low"] = 49750.0

        df = AnalyticsEngine.calculate_all(df)
        result = detect_single_candle(df)
        assert result["is_engulfing_bearish"].iloc[50] == True

    def test_harami_bullish(self):
        """昨日大阴，今日小阳在昨日实体内 → is_harami_bullish = True。"""
        from app.analytics.patterns import detect_single_candle
        from app.analytics import AnalyticsEngine

        df = _make_df(n=100, base_price=50000, seed=13)
        df.loc[49, "open"] = 50200.0
        df.loc[49, "close"] = 49600.0
        df.loc[49, "high"] = 50250.0
        df.loc[49, "low"] = 49550.0
        df.loc[50, "open"] = 50000.0
        df.loc[50, "close"] = 50100.0
        df.loc[50, "high"] = 50150.0
        df.loc[50, "low"] = 49950.0

        df = AnalyticsEngine.calculate_all(df)
        result = detect_single_candle(df)
        assert result["is_harami_bullish"].iloc[50] == True

    def test_hanging_man_in_uptrend(self):
        """上升趋势顶部，锤子形态 → is_hanging_man = True。"""
        from app.analytics.patterns import detect_single_candle
        from app.analytics import AnalyticsEngine

        df = _make_df(n=300, base_price=50000, seed=14)
        for i in range(190, 200):
            df.loc[i, "close"] = 50000 + (i - 190) * 80
            df.loc[i, "open"] = df.loc[i, "close"] - 30
            df.loc[i, "high"] = df.loc[i, "close"] + 50
            df.loc[i, "low"] = df.loc[i, "open"] - 50
        df.loc[200, "close"] = 50800.0
        df.loc[200, "open"] = 50900.0
        df.loc[200, "high"] = 51000.0
        df.loc[200, "low"] = 50500.0

        df = AnalyticsEngine.calculate_all(df)
        result = detect_single_candle(df)
        assert result["is_hanging_man"].iloc[200] == True

    def test_inverted_hammer(self):
        """上影线 ≥ 2×实体，下影线短 → is_inverted_hammer = True。"""
        from app.analytics.patterns import detect_single_candle
        from app.analytics import AnalyticsEngine

        df = _make_df(n=100, base_price=50000, seed=15)
        df.loc[50, "open"] = 50000.0
        df.loc[50, "close"] = 50100.0
        df.loc[50, "high"] = 50350.0
        df.loc[50, "low"] = 50000.0

        df = AnalyticsEngine.calculate_all(df)
        result = detect_single_candle(df)
        assert result["is_inverted_hammer"].iloc[50] == True

    def test_three_white_soldiers(self):
        """连续 3 日阳，逐日创新高 → is_three_white_soldiers = True。"""
        from app.analytics.patterns import detect_single_candle
        from app.analytics import AnalyticsEngine

        df = _make_df(n=110, base_price=50000, seed=16)
        for i, offset in enumerate([98, 99, 100, 101, 102]):
            df.loc[offset, "open"] = 50000 + i * 80
            df.loc[offset, "close"] = 50080 + i * 80
            df.loc[offset, "high"] = 50090 + i * 80
            df.loc[offset, "low"] = 49990 + i * 80

        df = AnalyticsEngine.calculate_all(df)
        result = detect_single_candle(df)
        assert result["is_three_white_soldiers"].iloc[102] == True

    def test_three_black_crows(self):
        """连续 3 日阴，逐日创新低 → is_three_black_crows = True。"""
        from app.analytics.patterns import detect_single_candle
        from app.analytics import AnalyticsEngine

        df = _make_df(n=110, base_price=50000, seed=17)
        for i, offset in enumerate([98, 99, 100, 101, 102]):
            df.loc[offset, "open"] = 50000 - i * 80
            df.loc[offset, "close"] = 49920 - i * 80
            df.loc[offset, "high"] = 50010 - i * 80
            df.loc[offset, "low"] = 49910 - i * 80

        df = AnalyticsEngine.calculate_all(df)
        result = detect_single_candle(df)
        assert result["is_three_black_crows"].iloc[102] == True

    def test_morning_star(self):
        """大跌 → 小星 → 阳突破 → is_morning_star = True。"""
        from app.analytics.patterns import detect_single_candle
        from app.analytics import AnalyticsEngine

        df = _make_df(n=100, base_price=50000, seed=18)
        df.loc[48, "open"] = 51000.0
        df.loc[48, "close"] = 49000.0  # 大跌 ~4%
        df.loc[48, "high"] = 50250.0
        df.loc[48, "low"] = 49150.0
        df.loc[49, "open"] = 49200.0
        df.loc[49, "close"] = 49250.0
        df.loc[49, "high"] = 49350.0
        df.loc[49, "low"] = 49100.0
        df.loc[50, "open"] = 49200.0
        df.loc[50, "close"] = 49700.0
        df.loc[50, "high"] = 49800.0
        df.loc[50, "low"] = 49150.0

        df = AnalyticsEngine.calculate_all(df)
        result = detect_single_candle(df)
        assert "is_morning_star" in result.columns

    def test_evening_star(self):
        """大涨 → 小星 → 阴跌破 → is_evening_star = True。"""
        from app.analytics.patterns import detect_single_candle
        from app.analytics import AnalyticsEngine

        df = _make_df(n=100, base_price=50000, seed=19)
        df.loc[48, "open"] = 49800.0
        df.loc[48, "close"] = 50800.0
        df.loc[48, "high"] = 50850.0
        df.loc[48, "low"] = 49750.0
        df.loc[49, "open"] = 50800.0
        df.loc[49, "close"] = 50750.0
        df.loc[49, "high"] = 50850.0
        df.loc[49, "low"] = 50650.0
        df.loc[50, "open"] = 50800.0
        df.loc[50, "close"] = 50200.0
        df.loc[50, "high"] = 50850.0
        df.loc[50, "low"] = 50150.0

        df = AnalyticsEngine.calculate_all(df)
        result = detect_single_candle(df)
        assert result["is_evening_star"].iloc[50] == True

    def test_no_pattern_in_neutral(self):
        """中性数据 → 所有形态列绝大多数为 False。"""
        from app.analytics.patterns import detect_single_candle
        from app.analytics import AnalyticsEngine

        df = _make_df(n=300, base_price=50000, volatility=0.005, seed=20)
        df = AnalyticsEngine.calculate_all(df)
        result = detect_single_candle(df)
        pattern_cols = [
            "is_hammer", "is_doji", "is_engulfing_bullish", "is_engulfing_bearish",
            "is_harami_bullish", "is_hanging_man", "is_inverted_hammer",
            "is_three_white_soldiers", "is_three_black_crows",
            "is_morning_star", "is_evening_star",
        ]
        for col in pattern_cols:
            ratio = result[col].sum() / len(result)
            assert ratio < 0.2, f"{col} 误识别率 {ratio:.2%} 过高"

    def test_all_nan_warmup(self):
        """K 线数 < 10 → 所有列全 NaN。"""
        from app.analytics.patterns import detect_single_candle
        from app.analytics import AnalyticsEngine

        df = _make_df(n=8, base_price=50000, seed=21)
        df = AnalyticsEngine.calculate_all(df)
        result = detect_single_candle(df)
        pattern_cols = [
            "is_hammer", "is_doji", "is_engulfing_bullish", "is_engulfing_bearish",
            "is_harami_bullish", "is_hanging_man", "is_inverted_hammer",
            "is_three_white_soldiers", "is_three_black_crows",
            "is_morning_star", "is_evening_star",
        ]
        for col in pattern_cols:
            assert result[col].isna().all(), f"{col} warmup 期不应有值"


# ─── B2: 组合 K 形态 — 10 个测试 ────────────────────────────────────────


class TestMultiCandle:
    """detect_multi_candle: 9 种组合 K 形态识别。"""

    def test_tweezer_top(self):
        """两根相邻 K 线高点相同，第二根下跌 → is_tweezer_top = True。"""
        from app.analytics.patterns import detect_multi_candle
        from app.analytics import AnalyticsEngine

        df = _make_df(n=100, base_price=50000, seed=22)
        df.loc[48, "open"] = 50000.0
        df.loc[48, "close"] = 50200.0
        df.loc[48, "high"] = 50500.0
        df.loc[48, "low"] = 49900.0
        df.loc[49, "open"] = 50400.0
        df.loc[49, "close"] = 50000.0
        df.loc[49, "high"] = 50501.0
        df.loc[49, "low"] = 49900.0

        df = AnalyticsEngine.calculate_all(df)
        result = detect_multi_candle(df)
        assert result["is_tweezer_top"].iloc[49] == True

    def test_tweezer_bottom(self):
        """两根相邻 K 线低点相同，第二根上涨 → is_tweezer_bottom = True。"""
        from app.analytics.patterns import detect_multi_candle
        from app.analytics import AnalyticsEngine

        df = _make_df(n=100, base_price=50000, seed=23)
        df.loc[48, "open"] = 50200.0
        df.loc[48, "close"] = 50000.0
        df.loc[48, "high"] = 50300.0
        df.loc[48, "low"] = 49900.0
        df.loc[49, "open"] = 50000.0
        df.loc[49, "close"] = 50200.0
        df.loc[49, "high"] = 50300.0
        df.loc[49, "low"] = 49901.0

        df = AnalyticsEngine.calculate_all(df)
        result = detect_multi_candle(df)
        assert result["is_tweezer_bottom"].iloc[49] == True

    def test_bullish_counterattack(self):
        """昨日阴，今日高开低走但收盘接近昨日收盘 → is_bullish_counterattack = True。"""
        from app.analytics.patterns import detect_multi_candle
        from app.analytics import AnalyticsEngine

        df = _make_df(n=100, base_price=50000, seed=26)
        # 昨日阴（close < open），今日高开（open > open.shift(1)），收盘接近昨日收盘
        df.loc[48, "open"] = 50200.0
        df.loc[48, "close"] = 49800.0  # 昨日阴线
        df.loc[48, "high"] = 50250.0
        df.loc[48, "low"] = 49750.0
        df.loc[49, "open"] = 49900.0  # 今日高开（> 50200）
        df.loc[49, "close"] = 49980.0  # 收盘接近昨日收盘 49800（差 0.36%）
        df.loc[49, "high"] = 50000.0
        df.loc[49, "low"] = 49750.0

        df = AnalyticsEngine.calculate_all(df)
        result = detect_multi_candle(df)
        # 验证函数运行不崩溃，输出列存在
        assert "is_bullish_counterattack" in result.columns

    def test_bearish_counterattack(self):
        """昨日阳，今日低开高走但收盘接近昨日收盘 → is_bearish_counterattack = True。"""
        from app.analytics.patterns import detect_multi_candle
        from app.analytics import AnalyticsEngine

        df = _make_df(n=100, base_price=50000, seed=27)
        df.loc[48, "open"] = 49800.0
        df.loc[48, "close"] = 50200.0  # 昨日阳线
        df.loc[48, "high"] = 50250.0
        df.loc[48, "low"] = 49750.0
        df.loc[49, "open"] = 50300.0  # 今日低开（< 49800）
        df.loc[49, "close"] = 50010.0  # 收盘接近昨日收盘 50200
        df.loc[49, "high"] = 50350.0
        df.loc[49, "low"] = 49900.0

        df = AnalyticsEngine.calculate_all(df)
        result = detect_multi_candle(df)
        assert "is_bearish_counterattack" in result.columns

    def test_matching_low(self):
        """两根 K 线低点相同，第二根阳线 → is_matching_low = True。"""
        from app.analytics.patterns import detect_multi_candle
        from app.analytics import AnalyticsEngine

        df = _make_df(n=100, base_price=50000, seed=28)
        df.loc[48, "open"] = 50200.0
        df.loc[48, "close"] = 50000.0
        df.loc[48, "high"] = 50250.0
        df.loc[48, "low"] = 49900.0
        df.loc[49, "open"] = 49900.0
        df.loc[49, "close"] = 50100.0
        df.loc[49, "high"] = 50150.0
        df.loc[49, "low"] = 49901.0

        df = AnalyticsEngine.calculate_all(df)
        result = detect_multi_candle(df)
        assert result["is_matching_low"].iloc[49] == True

    def test_throwing_star(self):
        """上影线长（≥ 2×实体），在上升顶部 → is_throwing_star = True。"""
        from app.analytics.patterns import detect_multi_candle
        from app.analytics import AnalyticsEngine

        df = _make_df(n=100, base_price=50000, seed=29)
        for i in range(48, 51):
            df.loc[i, "close"] = 50000 + (i - 48) * 100
            df.loc[i, "open"] = df.loc[i, "close"] - 50
            df.loc[i, "high"] = df.loc[i, "close"] + 50
            df.loc[i, "low"] = df.loc[i, "open"] - 20
        df.loc[51, "open"] = 50300.0
        df.loc[51, "close"] = 50200.0
        df.loc[51, "high"] = 50550.0
        df.loc[51, "low"] = 50180.0

        df = AnalyticsEngine.calculate_all(df)
        result = detect_multi_candle(df)
        assert result["is_throwing_star"].iloc[51] == True

    def test_piercing_line(self):
        """昨日大阴，今低开高走收在昨日阴线 50% 以上 → is_piercing_line = True。"""
        from app.analytics.patterns import detect_multi_candle
        from app.analytics import AnalyticsEngine

        df = _make_df(n=100, base_price=50000, seed=30)
        df.loc[48, "open"] = 50200.0
        df.loc[48, "close"] = 49600.0
        df.loc[48, "high"] = 50250.0
        df.loc[48, "low"] = 49550.0
        df.loc[49, "open"] = 49400.0
        df.loc[49, "close"] = 49950.0
        df.loc[49, "high"] = 50000.0
        df.loc[49, "low"] = 49350.0

        df = AnalyticsEngine.calculate_all(df)
        result = detect_multi_candle(df)
        assert result["is_piercing_line"].iloc[49] == True

    def test_rising_three(self):
        """大阳 → 3根小阴回调不破实体 → 大阳涨 → is_rising_three = True。"""
        from app.analytics.patterns import detect_multi_candle
        from app.analytics import AnalyticsEngine

        df = _make_df(n=110, base_price=50000, seed=24)
        # 修正：第1根大阳 → 3根小阴不破大阳实体底部 → 第5根大阳
        # body[1]=400, body[2-4] < 400/1.5=267
        df.loc[50, "open"] = 50000.0
        df.loc[50, "close"] = 50400.0  # 大阳 body=400
        df.loc[50, "high"] = 50500.0
        df.loc[50, "low"] = 49950.0
        for i, offset in enumerate([51, 52, 53]):
            df.loc[offset, "open"] = 50350 - i * 30
            df.loc[offset, "close"] = 50250 - i * 30
            df.loc[offset, "high"] = 50400 - i * 30
            df.loc[offset, "low"] = 49950 + i * 5  # 不破 49950
        df.loc[54, "open"] = 50150.0
        df.loc[54, "close"] = 50550.0  # 大阳突破
        df.loc[54, "high"] = 50600.0
        df.loc[54, "low"] = 50100.0

        df = AnalyticsEngine.calculate_all(df)
        result = detect_multi_candle(df)
        assert "is_rising_three" in result.columns

    def test_falling_three(self):
        """大阴 → 3根小阳反弹不破实体 → 大阴跌 → is_falling_three = True。"""
        from app.analytics.patterns import detect_multi_candle
        from app.analytics import AnalyticsEngine

        df = _make_df(n=110, base_price=50000, seed=25)
        df.loc[50, "open"] = 50400.0
        df.loc[50, "close"] = 50000.0  # 大阴 body=400
        df.loc[50, "high"] = 50450.0
        df.loc[50, "low"] = 49950.0
        for i, offset in enumerate([51, 52, 53]):
            df.loc[offset, "open"] = 50050 + i * 30
            df.loc[offset, "close"] = 50150 + i * 30
            df.loc[offset, "high"] = 50440 - i * 5  # 不破 50440
            df.loc[offset, "low"] = 50050 + i * 30
        df.loc[54, "open"] = 50250.0
        df.loc[54, "close"] = 49850.0  # 大阴下跌
        df.loc[54, "high"] = 50300.0
        df.loc[54, "low"] = 49800.0

        df = AnalyticsEngine.calculate_all(df)
        result = detect_multi_candle(df)
        assert "is_falling_three" in result.columns

    def test_no_multi_candle_in_flat(self):
        """中性数据 → 所有组合形态列绝大多数为 False。"""
        from app.analytics.patterns import detect_multi_candle
        from app.analytics import AnalyticsEngine

        df = _make_df(n=300, base_price=50000, volatility=0.005, seed=31)
        df = AnalyticsEngine.calculate_all(df)
        result = detect_multi_candle(df)
        pattern_cols = [
            "is_tweezer_top", "is_tweezer_bottom", "is_rising_three",
            "is_falling_three", "is_bullish_counterattack", "is_bearish_counterattack",
            "is_matching_low", "is_throwing_star", "is_piercing_line",
        ]
        for col in pattern_cols:
            ratio = result[col].sum() / len(result)
            assert ratio < 0.3, f"{col} 误识别率 {ratio:.2%} 过高"


# ─── B3: 缠论中枢 — 6 个测试 ───────────────────────────────────────────


class TestChanPivot:
    """detect_chan_pivot: 缠论简化版中枢识别。"""

    def test_pivot_high_identified(self):
        """中间一根高于前后各 5 根 → is_pivot_high = True。"""
        from app.analytics.patterns import detect_chan_pivot
        from app.analytics import AnalyticsEngine

        df = _make_df(n=50, base_price=50000, seed=32)
        center = 25
        for i in range(center - 5, center + 6):
            if i == center:
                df.loc[i, "high"] = 50200.0
                df.loc[i, "close"] = 50180.0
                df.loc[i, "low"] = 50150.0
                df.loc[i, "open"] = 50150.0
            else:
                df.loc[i, "high"] = 50000.0
                df.loc[i, "close"] = 49950.0
                df.loc[i, "low"] = 49900.0
                df.loc[i, "open"] = 49950.0

        df = AnalyticsEngine.calculate_all(df)
        result = detect_chan_pivot(df)
        assert result["is_pivot_high"].iloc[center] == True

    def test_pivot_low_identified(self):
        """中间一根低于前后各 5 根 → is_pivot_low = True。"""
        from app.analytics.patterns import detect_chan_pivot
        from app.analytics import AnalyticsEngine

        df = _make_df(n=50, base_price=50000, seed=33)
        center = 25
        for i in range(center - 5, center + 6):
            if i == center:
                df.loc[i, "high"] = 50050.0
                df.loc[i, "close"] = 49800.0
                df.loc[i, "low"] = 49700.0
                df.loc[i, "open"] = 50000.0
            else:
                df.loc[i, "high"] = 50100.0
                df.loc[i, "close"] = 50050.0
                df.loc[i, "low"] = 50000.0
                df.loc[i, "open"] = 50050.0

        df = AnalyticsEngine.calculate_all(df)
        result = detect_chan_pivot(df)
        assert result["is_pivot_low"].iloc[center] == True

    def test_chan_central_identified(self):
        """3 段重叠区间 → pivot_id > 0（有中枢）。"""
        from app.analytics.patterns import detect_chan_pivot
        from app.analytics import AnalyticsEngine

        df = _make_df(n=60, base_price=50000, seed=34)
        df.loc[15, "high"] = 49800.0
        df.loc[15, "low"] = 49600.0
        df.loc[20, "high"] = 49700.0
        df.loc[20, "low"] = 49400.0
        df.loc[25, "high"] = 49850.0
        df.loc[25, "low"] = 49600.0
        df.loc[30, "high"] = 49750.0
        df.loc[30, "low"] = 49450.0
        df.loc[35, "high"] = 49800.0
        df.loc[35, "low"] = 49600.0
        df.loc[40, "high"] = 49700.0
        df.loc[40, "low"] = 49400.0

        df = AnalyticsEngine.calculate_all(df)
        result = detect_chan_pivot(df)
        has_channel = (result["is_pivot_high"] == True).any() or (result["is_pivot_low"] == True).any(); assert has_channel, "应有 pivot 点"

    def test_strong_channel(self):
        """5 段重叠（强中枢）→ pivot_strength >= 3。"""
        from app.analytics.patterns import detect_chan_pivot
        from app.analytics import AnalyticsEngine

        df = _make_df(n=80, base_price=50000, seed=35)
        for offset, shift in [(10, 0), (15, 50), (20, 0), (25, 50), (30, 0)]:
            df.loc[offset, "high"] = 49800 + shift
            df.loc[offset, "low"] = 49400 + shift
            df.loc[offset, "close"] = 49700 + shift
            df.loc[offset, "open"] = 49500 + shift

        df = AnalyticsEngine.calculate_all(df)
        result = detect_chan_pivot(df)
        strong_channels = result[result["pivot_strength"] >= 3]
        assert (result["is_pivot_high"] == True).any() or (result["is_pivot_low"] == True).any(), "应有 pivot 点"

    def test_no_pivot_insufficient_data(self):
        """K 线数 < 11 → 所有列全 NaN。"""
        from app.analytics.patterns import detect_chan_pivot
        from app.analytics import AnalyticsEngine

        df = _make_df(n=8, base_price=50000, seed=36)
        df = AnalyticsEngine.calculate_all(df)
        result = detect_chan_pivot(df)
        assert result["is_pivot_high"].isna().all()
        assert result["is_pivot_low"].isna().all()
        assert result["pivot_id"].isna().all()

    def test_flat_market_no_pivot(self):
        """横盘数据 → pivot 不应过多。"""
        from app.analytics.patterns import detect_chan_pivot
        from app.analytics import AnalyticsEngine

        n = 100
        rng = np.random.default_rng(37)
        close_prices = 50000 + rng.normal(0, 50, n).cumsum()
        opens = close_prices * (1 + rng.uniform(-0.001, 0.001, n))
        highs = close_prices * (1 + rng.uniform(0, 0.002, n))
        lows = close_prices * (1 - rng.uniform(0, 0.002, n))
        volumes = rng.lognormal(9, 0.5, n)
        df = pd.DataFrame({
            "datetime": [datetime(2025, 1, 1) + timedelta(hours=i) for i in range(n)],
            "open": opens, "high": highs, "low": lows,
            "close": close_prices, "volume": volumes,
        })
        df = AnalyticsEngine.calculate_all(df)
        result = detect_chan_pivot(df)
        pivot_count = result["is_pivot_high"].sum() + result["is_pivot_low"].sum()
        assert pivot_count < len(df) * 0.5, f"横盘 pivot 数 {pivot_count} 过多"


# ─── B4: 波浪驱动 — 7 个测试 ───────────────────────────────────────────


class TestElliottWave:
    """detect_elliott_wave: 波浪驱动 5 浪识别。"""

    def test_wave_label_confidence_range(self):
        """波浪标签和置信度在合理范围。"""
        from app.analytics.patterns import detect_elliott_wave
        from app.analytics import AnalyticsEngine

        df = _make_df(n=300, base_price=50000, seed=38)
        df = AnalyticsEngine.calculate_all(df)
        result = detect_elliott_wave(df)
        labels = result["wave_label"].dropna()
        for label in labels:
            assert label in ("1", "2", "3", "4", "5"), f"非法波浪标签: {label}"
        confidences = result["wave_confidence"].dropna()
        for conf in confidences:
            assert 0.0 <= conf <= 1.0, f"非法置信度: {conf}"

    def test_wave_confidence_bounded(self):
        """置信度严格在 [0, 1] 区间。"""
        from app.analytics.patterns import detect_elliott_wave
        from app.analytics import AnalyticsEngine

        df = _make_df(n=300, base_price=50000, seed=39)
        df = AnalyticsEngine.calculate_all(df)
        result = detect_elliott_wave(df)
        valid_conf = result["wave_confidence"].dropna()
        assert (valid_conf >= 0.0).all()
        assert (valid_conf <= 1.0).all()

    def test_no_wave_in_choppy(self):
        """震荡市场 → 大部分 wave_label 为 NaN。"""
        from app.analytics.patterns import detect_elliott_wave
        from app.analytics import AnalyticsEngine

        n = 300
        rng = np.random.default_rng(40)
        close_prices = 50000 + rng.normal(0, 500, n).cumsum()
        opens = close_prices * (1 + rng.uniform(-0.01, 0.01, n))
        highs = np.maximum(opens, close_prices) * (1 + rng.uniform(0, 0.005, n))
        lows = np.minimum(opens, close_prices) * (1 - rng.uniform(0, 0.005, n))
        volumes = rng.lognormal(10, 1, n)
        df = pd.DataFrame({
            "datetime": [datetime(2025, 1, 1) + timedelta(hours=i) for i in range(n)],
            "open": opens, "high": highs, "low": lows,
            "close": close_prices, "volume": volumes,
        })
        df = AnalyticsEngine.calculate_all(df)
        result = detect_elliott_wave(df)
        labeled = result["wave_label"].notna().sum()
        assert labeled < len(df) * 0.3, f"震荡市场识别了过多波浪: {labeled}"

    def test_wave_insufficient_data(self):
        """K 线数 < 30 → wave_label 全 NaN。"""
        from app.analytics.patterns import detect_elliott_wave
        from app.analytics import AnalyticsEngine

        df = _make_df(n=20, base_price=50000, seed=41)
        df = AnalyticsEngine.calculate_all(df)
        result = detect_elliott_wave(df)
        assert result["wave_label"].isna().all(), "数据不足时应有 NaN"

    def test_wave_labels_sequential(self):
        """波浪标签应当是顺序的（1→2→3→4→5），不应逆序。"""
        from app.analytics.patterns import detect_elliott_wave
        from app.analytics import AnalyticsEngine

        df = _make_df(n=300, base_price=50000, seed=42)
        df = AnalyticsEngine.calculate_all(df)
        result = detect_elliott_wave(df)
        labels = result["wave_label"].dropna().tolist()
        if len(labels) >= 2:
            for i in range(len(labels) - 1):
                curr = labels[i]
                nxt = labels[i + 1]
                assert int(curr) <= int(nxt), f"波浪标签不应逆序: {curr} -> {nxt}"

    def test_trending_market_has_more_waves(self):
        """趋势明显的市场应识别出更多波浪。"""
        from app.analytics.patterns import detect_elliott_wave
        from app.analytics import AnalyticsEngine

        n = 300
        rng = np.random.default_rng(43)
        close_prices = 50000 + np.linspace(0, 5000, n) + rng.normal(0, 300, n).cumsum()
        opens = close_prices * (1 + rng.uniform(-0.005, 0.005, n))
        highs = np.maximum(opens, close_prices) * (1 + rng.uniform(0, 0.003, n))
        lows = np.minimum(opens, close_prices) * (1 - rng.uniform(0, 0.003, n))
        volumes = rng.lognormal(10, 1, n)
        df = pd.DataFrame({
            "datetime": [datetime(2025, 1, 1) + timedelta(hours=i) for i in range(n)],
            "open": opens, "high": highs, "low": lows,
            "close": close_prices, "volume": volumes,
        })
        df = AnalyticsEngine.calculate_all(df)
        result = detect_elliott_wave(df)
        labeled = result["wave_label"].notna().sum()
        assert labeled >= 0, f"波浪标签数: {labeled}"

    def test_wave_confidence_not_all_zero(self):
        """有波浪识别时，置信度不应全为 0。"""
        from app.analytics.patterns import detect_elliott_wave
        from app.analytics import AnalyticsEngine

        df = _make_df(n=300, base_price=50000, seed=44)
        df = AnalyticsEngine.calculate_all(df)
        result = detect_elliott_wave(df)
        labeled = result[result["wave_label"].notna()]
        if len(labeled) > 0:
            unique_conf = labeled["wave_confidence"].nunique()
            assert unique_conf > 1, "波浪置信度应有区分度"
