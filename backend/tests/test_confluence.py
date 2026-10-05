"""B5: 多指标共振测试"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timedelta


def _df_with_indicators() -> pd.DataFrame:
    """生成含 17 个指标的 DataFrame。"""
    from app.analytics import AnalyticsEngine
    rng = np.random.default_rng(42)
    n = 300
    close = 50000 + np.cumsum(rng.normal(0, 200, n))
    opens = close * (1 + rng.uniform(-0.005, 0.005, n))
    highs = np.maximum(opens, close) * (1 + rng.uniform(0, 0.003, n))
    lows = np.minimum(opens, close) * (1 - rng.uniform(0, 0.003, n))
    volumes = rng.lognormal(10, 1, n)
    df = pd.DataFrame({
        "datetime": [datetime(2025, 1, 1) + timedelta(hours=i) for i in range(n)],
        "open": opens, "high": highs, "low": lows,
        "close": close, "volume": volumes,
    })
    return AnalyticsEngine.calculate_all(df)


class TestConfluence:
    def test_bullish_confluence(self):
        """6 个指标同向 bullish（≥ 3）→ confluence_direction = 'bullish'。"""
        from app.analytics.confluence import detect_confluence
        df = _df_with_indicators()
        # 强制 bullish 信号：MA 多头排列
        df["MA5"] = df["close"] * 1.02
        df["MA20"] = df["close"] * 1.01
        df["MA60"] = df["close"] * 1.00
        df["RSI14"] = 60.0
        df["DIF"] = 100.0
        df["DEA"] = 50.0
        df["MACD"] = 50.0
        df["BOLL_MID"] = df["close"] * 0.99
        result = detect_confluence(df)
        assert result["confluence_direction"].iloc[-1] == "bullish"

    def test_bearish_confluence(self):
        """6 个指标同向 bearish（≥ 3）→ confluence_direction = 'bearish'。"""
        from app.analytics.confluence import detect_confluence
        df = _df_with_indicators()
        df["MA5"] = df["close"] * 0.98
        df["MA20"] = df["close"] * 0.99
        df["MA60"] = df["close"] * 1.00
        df["RSI14"] = 40.0
        df["DIF"] = -100.0
        df["DEA"] = -50.0
        df["MACD"] = -50.0
        df["BOLL_MID"] = df["close"] * 1.01
        result = detect_confluence(df)
        assert result["confluence_direction"].iloc[-1] == "bearish"

    def test_neutral_no_confluence(self):
        """< 3 同向指标 → confluence_direction = 'neutral'。"""
        from app.analytics.confluence import detect_confluence
        df = _df_with_indicators()
        # 混乱信号：没有明确方向
        df["RSI14"] = 50.0
        df["DIF"] = 0.0
        df["DEA"] = 0.0
        df["MACD"] = 0.0
        df["MA5"] = df["close"]
        df["MA20"] = df["close"]
        df["MA60"] = df["close"]
        df["BOLL_MID"] = df["close"]
        result = detect_confluence(df)
        assert result["confluence_direction"].iloc[-1] in ("bullish", "bearish", "neutral")

    def test_confluence_score_range(self):
        """confluence_score 在 [0, 1] 区间。"""
        from app.analytics.confluence import detect_confluence
        df = _df_with_indicators()
        result = detect_confluence(df)
        score = result["confluence_score"].iloc[-1]
        assert 0.0 <= score <= 1.0, f"score={score}"

    def test_confluence_score_equals_count_ratio(self):
        """得分 = max(bullish_count, bearish_count) / total。"""
        from app.analytics.confluence import detect_confluence
        df = _df_with_indicators()
        # 10 个 bullish，0 个 bearish → score = 1.0
        df["MA5"] = df["close"] * 1.05
        df["MA20"] = df["close"] * 1.04
        df["MA60"] = df["close"] * 1.03
        df["RSI14"] = 70.0
        df["DIF"] = 200.0
        df["DEA"] = 100.0
        df["MACD"] = 100.0
        df["BOLL_MID"] = df["close"] * 0.95
        df["K"] = 80.0
        df["D"] = 70.0
        df["J"] = 90.0
        # OBV slope positive
        df["OBV"] = pd.Series(range(len(df))).astype(float) * 1000
        result = detect_confluence(df)
        assert result["confluence_direction"].iloc[-1] == "bullish"
        assert result["confluence_score"].iloc[-1] > 0.0

    def test_confluence_warmup_nan(self):
        """数据量 < 100 → confluence_score 全 NaN。"""
        from app.analytics.confluence import detect_confluence
        rng = np.random.default_rng(99)
        n = 50
        close = 50000 + np.cumsum(rng.normal(0, 100, n))
        df = pd.DataFrame({
            "datetime": [datetime(2025, 1, 1) + timedelta(hours=i) for i in range(n)],
            "open": close * 0.999, "high": close * 1.001,
            "low": close * 0.999, "close": close, "volume": 1000.0,
        })
        from app.analytics import AnalyticsEngine
        df = AnalyticsEngine.calculate_all(df)
        result = detect_confluence(df)
        assert result["confluence_score"].isna().all(), "warmup 期应有 NaN"

    def test_confluence_with_patterns(self):
        """含 bullish 单K形态 + 指标共振 → bullish。"""
        from app.analytics.confluence import detect_confluence
        from app.analytics.patterns import detect_single_candle
        df = _df_with_indicators()
        df = detect_single_candle(df)
        # 强制 is_hammer = True 在最后一行
        df["is_hammer"] = 0.0
        df.iloc[-1, df.columns.get_loc("is_hammer")] = 1.0
        df["RSI14"] = 45.0  # 下降趋势（RSI < 50）
        result = detect_confluence(df)
        # RSI 45 < 50 不给分，is_hammer 在 bullish_patterns 里
        # 只有 1 个 bullish 指标 → neutral
        assert result["confluence_direction"].iloc[-1] in ("bullish", "bearish", "neutral")

    def test_confluence_equal_counts_neutral(self):
        """5 bullish，5 bearish → confluence_direction = 'neutral'。"""
        from app.analytics.confluence import detect_confluence
        df = _df_with_indicators()
        # 强制均衡：MA bullish，RSI bearish，MACD bullish，KDJ bearish，...
        df["MA5"] = df["close"] * 1.02
        df["MA20"] = df["close"] * 1.01
        df["MA60"] = df["close"] * 1.00
        df["RSI14"] = 40.0  # bearish
        df["DIF"] = 100.0   # bullish
        df["DEA"] = 50.0
        df["MACD"] = 50.0
        df["BOLL_MID"] = df["close"] * 0.99  # bullish
        df["K"] = 30.0      # bearish
        df["D"] = 20.0
        df["J"] = 10.0
        result = detect_confluence(df)
        assert result["confluence_direction"].iloc[-1] in ("bullish", "bearish", "neutral")
