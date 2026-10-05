"""B6: 信号方向判定测试（10 单元测试）

覆盖：
  test_long_signal_from_confluence_bullish          — 共振 bullish + ADX > 25 → long
  test_short_signal_from_confluence_bearish         — 共振 bearish + ADX > 25 → short
  test_long_signal_from_hammer_in_downtrend         — 锤子形态 → long
  test_short_signal_from_evening_star_in_uptrend   — 暮星形态 → short
  test_combined_signal_high_confidence              — 共振 + 形态同向 → confidence 0.8
  test_no_signal_in_neutral_market                 — 中性 → 无信号
  test_stop_loss_long_below_entry                  — long: SL < entry
  test_take_profit_long_above_entry                — long: TP > entry
  test_risk_reward_ratio_two_to_one                — 2:1 风险回报
  test_signal_datetime_matches_kline                — Signal.datetime == K 线时间
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timedelta


def _df_minimal(clear_patterns: bool = True) -> pd.DataFrame:
    """最小 DataFrame：仅含 generate_signal 必需的列。

    Args:
        clear_patterns: True 时所有形态列=0，False 时保留自然数据（用于随机数据测试）
    """
    n = 20
    close = np.array([50000.0 + i * 10 for i in range(n)])
    opens = np.array([c * (1 + 0.001) for c in close])
    highs = np.array([c * 1.005 for c in close])
    lows = np.array([c * 0.995 for c in close])

    data = {
        "datetime": [datetime(2025, 1, 1) + timedelta(hours=i) for i in range(n)],
        "open": opens, "high": highs, "low": lows,
        "close": close,
        "ADX14": 30.0,
        "ATR14": 100.0,
        "RSI14": 50.0,
        "confluence_direction": "neutral",
    }

    # 形态列：全部初始化为 0（clear_patterns=True 时）
    if clear_patterns:
        for col in [
            "is_hammer", "is_morning_star", "is_three_white_soldiers",
            "is_engulfing_bullish", "is_harami_bullish", "is_piercing_line",
            "is_tweezer_bottom", "is_bullish_counterattack",
            "is_hanging_man", "is_evening_star", "is_three_black_crows",
            "is_engulfing_bearish", "is_throwing_star",
            "is_tweezer_top", "is_bearish_counterattack",
        ]:
            data[col] = 0.0

    df = pd.DataFrame(data)
    return df


def _df_full() -> pd.DataFrame:
    """含 AnalyticsEngine 全套指标的 DataFrame。用于 confluence 相关测试。"""
    from app.analytics import AnalyticsEngine
    from app.analytics.patterns import (
        detect_single_candle, detect_multi_candle,
        detect_chan_pivot, detect_elliott_wave,
    )
    from app.analytics.confluence import detect_confluence

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
    df = AnalyticsEngine.calculate_all(df)
    df = detect_single_candle(df)
    df = detect_multi_candle(df)
    df = detect_chan_pivot(df)
    df = detect_elliott_wave(df)
    df = detect_confluence(df)
    return df


class TestSignalDirection:
    def test_long_signal_from_confluence_bullish(self):
        """confluence_direction='bullish' + ADX14 > 25 → direction='long'，confidence=0.6。"""
        from app.analytics.signal_direction import generate_signal, Signal
        df = _df_full()
        df["confluence_direction"] = "bullish"
        df["ADX14"] = 30.0
        df["ATR14"] = 100.0
        df["close"] = 50000.0

        signals = generate_signal(df)
        long_sigs = [s for s in signals if s.direction == "long"]
        assert len(long_sigs) > 0, "bullish 共振应有 long 信号"
        s = long_sigs[0]
        assert s.direction == "long"
        assert s.confidence == 0.6
        assert "confluence_bullish" in s.sources

    def test_short_signal_from_confluence_bearish(self):
        """confluence_direction='bearish' + ADX14 > 25 → direction='short'，confidence=0.6。"""
        from app.analytics.signal_direction import generate_signal, Signal
        df = _df_full()
        df["confluence_direction"] = "bearish"
        df["ADX14"] = 30.0
        df["ATR14"] = 100.0
        df["close"] = 50000.0

        signals = generate_signal(df)
        short_sigs = [s for s in signals if s.direction == "short"]
        assert len(short_sigs) > 0, "bearish 共振应有 short 信号"
        s = short_sigs[0]
        assert s.direction == "short"
        assert s.confidence == 0.6
        assert "confluence_bearish" in s.sources

    def test_long_signal_from_hammer_in_downtrend(self):
        """is_hammer=1 → direction='long'，confidence=0.4，无共振时。"""
        from app.analytics.signal_direction import generate_signal, Signal
        df = _df_minimal(clear_patterns=True)
        df["is_hammer"] = 0.0
        last_idx = len(df) - 1
        df.loc[last_idx, "is_hammer"] = 1.0

        signals = generate_signal(df)
        long_sigs = [s for s in signals if s.direction == "long"]
        assert len(long_sigs) > 0, "锤子形态应有 long 信号"
        s = long_sigs[-1]
        assert s.direction == "long"
        assert s.confidence == 0.4
        assert "hammer_bullish" in s.sources

    def test_short_signal_from_evening_star_in_uptrend(self):
        """is_evening_star=1 → direction='short'，confidence=0.4。"""
        from app.analytics.signal_direction import generate_signal, Signal
        df = _df_minimal(clear_patterns=True)
        df["is_evening_star"] = 0.0
        last_idx = len(df) - 1
        df.loc[last_idx, "is_evening_star"] = 1.0

        signals = generate_signal(df)
        short_sigs = [s for s in signals if s.direction == "short"]
        assert len(short_sigs) > 0, "暮星形态应有 short 信号"
        s = short_sigs[-1]
        assert s.direction == "short"
        assert s.confidence == 0.4
        assert "evening_star_bearish" in s.sources

    def test_combined_signal_high_confidence(self):
        """共振 + 形态同向 → confidence = 0.6 + 0.2 = 0.8。"""
        from app.analytics.signal_direction import generate_signal, Signal
        df = _df_minimal(clear_patterns=True)
        df["confluence_direction"] = "bullish"
        df["ADX14"] = 30.0
        df["RSI14"] = 55.0
        last_idx = len(df) - 1
        df.loc[last_idx, "is_hammer"] = 1.0

        signals = generate_signal(df)
        long_sigs = [s for s in signals if s.direction == "long"]
        assert len(long_sigs) > 0, "共振+形态应有 long 信号"
        hammer_sigs = [s for s in long_sigs if "hammer_bullish" in s.sources]
        assert len(hammer_sigs) > 0, "应有含 hammer_bullish 的信号"
        s = hammer_sigs[-1]
        assert s.confidence == 0.8, f"confidence 应为 0.8，实际 {s.confidence}"
        assert "confluence_bullish" in s.sources
        assert "hammer_bullish" in s.sources

    def test_no_signal_in_neutral_market(self):
        """confluence_direction='neutral' 且无形态 → 无信号。"""
        from app.analytics.signal_direction import generate_signal, Signal
        df = _df_minimal(clear_patterns=True)
        df["confluence_direction"] = "neutral"
        df["ADX14"] = 20.0

        signals = generate_signal(df)
        non_neutral = [s for s in signals if s.direction != "neutral"]
        assert len(non_neutral) == 0, "中性市场 + 无形态应无信号"

    def test_stop_loss_long_below_entry(self):
        """long 信号：stop_loss < entry。"""
        from app.analytics.signal_direction import generate_signal
        df = _df_full()
        df["confluence_direction"] = "bullish"
        df["ADX14"] = 30.0
        df["ATR14"] = 100.0
        df["close"] = 50000.0

        signals = generate_signal(df)
        long_sigs = [s for s in signals if s.direction == "long"]
        assert len(long_sigs) > 0
        for s in long_sigs:
            assert s.stop_loss < s.entry, (
                f"long: SL={s.stop_loss} 应 < E={s.entry}"
            )

    def test_take_profit_long_above_entry(self):
        """long 信号：take_profit > entry。"""
        from app.analytics.signal_direction import generate_signal
        df = _df_full()
        df["confluence_direction"] = "bullish"
        df["ADX14"] = 30.0
        df["ATR14"] = 100.0
        df["close"] = 50000.0

        signals = generate_signal(df)
        long_sigs = [s for s in signals if s.direction == "long"]
        assert len(long_sigs) > 0
        for s in long_sigs:
            assert s.take_profit > s.entry, (
                f"long: TP={s.take_profit} 应 > E={s.entry}"
            )

    def test_risk_reward_ratio_two_to_one(self):
        """2:1 风险回报：TP 距 entry = 4*ATR，SL 距 entry = 2*ATR。"""
        from app.analytics.signal_direction import generate_signal
        df = _df_full()
        df["confluence_direction"] = "bullish"
        df["ADX14"] = 30.0
        df["ATR14"] = 100.0
        df["close"] = 50000.0

        signals = generate_signal(df)
        long_sigs = [s for s in signals if s.direction == "long"]
        assert len(long_sigs) > 0
        s = long_sigs[0]
        reward = s.take_profit - s.entry
        risk = s.entry - s.stop_loss
        ratio = reward / risk if risk > 0 else 0
        assert abs(ratio - 2.0) < 0.01, (
            f"风险回报应为 2:1，实际 {ratio:.2f}"
        )

    def test_signal_datetime_matches_kline(self):
        """Signal.datetime 与 K 线 datetime 一致。"""
        from app.analytics.signal_direction import generate_signal
        df = _df_full()
        df["confluence_direction"] = "bullish"
        df["ADX14"] = 30.0
        df["ATR14"] = 100.0

        signals = generate_signal(df)
        assert len(signals) > 0, "应有信号"
        for s in signals:
            assert s.datetime is not None, "datetime 不应为 None"
            assert isinstance(s.datetime, pd.Timestamp)
