"""M2-B 集成验收测试 — B7

端到端验证 M2-B 全链路：
  指标计算（AnalyticsEngine）→ 形态识别（B1-B4）→ 共振检测（B5）→ 信号生成（B6）

业务验收测试：
  test_btc_1h_pipeline_produces_signals     — 全链路产生信号
  test_signals_have_valid_entry_sl_tp      — 信号含有效 entry/SL/TP
  test_confluence_and_pattern_signals_aligned — 共振方向与形态方向一致
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

import pytest


def _df_btc_1h_year() -> pd.DataFrame:
    """生成模拟 BTC 1h 1 年数据（8760 根 K 线）。"""
    rng = np.random.default_rng(99)
    n = 8760
    close = 50000 + rng.normal(0, 200, n).cumsum()
    opens = close * (1 + rng.uniform(-0.005, 0.005, n))
    highs = np.maximum(opens, close) * (1 + rng.uniform(0, 0.003, n))
    lows = np.minimum(opens, close) * (1 - rng.uniform(0, 0.003, n))
    volumes = rng.lognormal(10, 1, n)
    df = pd.DataFrame({
        "datetime": [datetime(2025, 1, 1) + timedelta(hours=i) for i in range(n)],
        "open": opens, "high": highs, "low": lows,
        "close": close, "volume": volumes,
    })
    return df


class TestM2BIntegration:
    """M2-B 全链路集成验收。"""

    def test_btc_1h_pipeline_produces_signals(self):
        """全链路：AnalyticsEngine → 形态 → 共振 → 信号，8760 根 K 线产生 ≥ 1 个信号。"""
        from app.analytics import AnalyticsEngine
        from app.analytics.patterns import (
            detect_single_candle, detect_multi_candle,
            detect_chan_pivot, detect_elliott_wave,
        )
        from app.analytics.confluence import detect_confluence
        from app.analytics.signal_direction import generate_signal

        df = _df_btc_1h_year()

        # Pipeline
        df = AnalyticsEngine.calculate_all(df)
        df = detect_single_candle(df)
        df = detect_multi_candle(df)
        df = detect_chan_pivot(df)
        df = detect_elliott_wave(df)
        df = detect_confluence(df)
        signals = generate_signal(df)

        non_neutral = [s for s in signals if s.direction != "neutral"]
        long_cnt = sum(1 for s in signals if s.direction == "long")
        short_cnt = sum(1 for s in signals if s.direction == "short")

        print(f"\n  BTC 1h 1年：信号总数={len(non_neutral)}, long={long_cnt}, short={short_cnt}")
        assert len(non_neutral) >= 1, f"全链路应至少产生 1 个信号，实际 {len(non_neutral)}"
        assert long_cnt + short_cnt == len(non_neutral)

    def test_signals_have_valid_entry_sl_tp(self):
        """每个信号含有效 entry/SL/TP，且满足 2:1 风险回报。"""
        from app.analytics import AnalyticsEngine
        from app.analytics.patterns import (
            detect_single_candle, detect_multi_candle,
            detect_chan_pivot, detect_elliott_wave,
        )
        from app.analytics.confluence import detect_confluence
        from app.analytics.signal_direction import generate_signal

        df = _df_btc_1h_year()
        df = AnalyticsEngine.calculate_all(df)
        df = detect_single_candle(df)
        df = detect_multi_candle(df)
        df = detect_chan_pivot(df)
        df = detect_elliott_wave(df)
        df = detect_confluence(df)
        signals = generate_signal(df)

        non_neutral = [s for s in signals if s.direction != "neutral"]
        assert len(non_neutral) >= 1, "需要至少 1 个信号"

        for s in non_neutral:
            # entry 正数
            assert s.entry > 0, f"entry={s.entry} 应 > 0"
            # long: SL < entry < TP
            if s.direction == "long":
                assert s.stop_loss < s.entry, f"long SL={s.stop_loss} 应 < E={s.entry}"
                assert s.take_profit > s.entry, f"long TP={s.take_profit} 应 > E={s.entry}"
            # short: SL > entry > TP
            elif s.direction == "short":
                assert s.stop_loss > s.entry, f"short SL={s.stop_loss} 应 > E={s.entry}"
                assert s.take_profit < s.entry, f"short TP={s.take_profit} 应 < E={s.entry}"
            # 2:1 风险回报
            reward = abs(s.take_profit - s.entry)
            risk = abs(s.entry - s.stop_loss)
            ratio = reward / risk if risk > 0 else 0
            assert abs(ratio - 2.0) < 0.1, (
                f"signal {s.name}: 风险回报 {ratio:.2f}（期望 2:1）"
            )

    def test_confluence_and_pattern_signals_aligned(self):
        """共振方向与信号方向一致（confluence_bullish → long，confluence_bearish → short）。"""
        from app.analytics import AnalyticsEngine
        from app.analytics.patterns import (
            detect_single_candle, detect_multi_candle,
            detect_chan_pivot, detect_elliott_wave,
        )
        from app.analytics.confluence import detect_confluence
        from app.analytics.signal_direction import generate_signal

        df = _df_btc_1h_year()
        df = AnalyticsEngine.calculate_all(df)
        df = detect_single_candle(df)
        df = detect_multi_candle(df)
        df = detect_chan_pivot(df)
        df = detect_elliott_wave(df)
        df = detect_confluence(df)
        signals = generate_signal(df)

        non_neutral = [s for s in signals if s.direction != "neutral"]
        assert len(non_neutral) >= 1, "需要至少 1 个信号"

        # 检查含 confluence_xxx 的信号，其方向与 confluence 同向
        for s in non_neutral:
            sources_str = " ".join(s.sources)
            if "confluence_bullish" in sources_str:
                assert s.direction == "long", (
                    f"confluence_bullish 信号方向应为 long，实际 {s.direction}"
                )
            if "confluence_bearish" in sources_str:
                assert s.direction == "short", (
                    f"confluence_bearish 信号方向应为 short，实际 {s.direction}"
                )
