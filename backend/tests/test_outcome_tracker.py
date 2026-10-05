"""Test for OutcomeTracker — C2

TDD: 红灯先亮，再实现 OutcomeTracker
"""
from __future__ import annotations

import pytest
import pandas as pd
from app.analytics.signal_direction import Signal
from app.services.outcome_tracker import OutcomeTracker


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_signal(
    direction: str,
    entry: float,
    stop_loss: float,
    take_profit: float,
) -> Signal:
    return Signal(
        name="test_signal",
        direction=direction,
        confidence=0.7,
        entry=entry,
        stop_loss=stop_loss,
        take_profit=take_profit,
        sources=["test"],
        datetime=pd.Timestamp("2024-01-01 09:00"),
    )


def _make_df(rows: list[dict]) -> pd.DataFrame:
    """构造 OHLCV DataFrame，datetime 列用于定位。"""
    # 确保有 close 列
    for row in rows:
        if "close" not in row:
            row["close"] = row.get("close", (row.get("high", 0) + row.get("low", 0)) / 2)
    return pd.DataFrame(rows)


# ── get_window_for_period ─────────────────────────────────────────────────────

class TestGetWindowForPeriod:
    """8 个周期的窗口根数映射测试"""

    @pytest.mark.parametrize("period,expected", [
        ("1m", 60),
        ("5m", 60),
        ("15m", 60),
        ("30m", 60),
        ("1h", 24),
        ("4h", 24),
        ("1d", 5),
        ("1w", 5),
    ])
    def test_all_periods(self, period, expected):
        tracker = OutcomeTracker()
        assert tracker.get_window_for_period(period) == expected


# ── compute_pnl_pct ──────────────────────────────────────────────────────────

class TestComputePnL:
    """PnL 计算测试"""

    def test_long_win(self):
        tracker = OutcomeTracker()
        signal = _make_signal("long", entry=100.0, stop_loss=98.0, take_profit=108.0)
        # 涨到 108，盈 8%
        pnl = tracker.compute_pnl_pct(signal, exit_price=108.0)
        assert abs(pnl - 8.0) < 0.001

    def test_long_loss(self):
        tracker = OutcomeTracker()
        signal = _make_signal("long", entry=100.0, stop_loss=98.0, take_profit=108.0)
        # 跌到 98，亏 2%
        pnl = tracker.compute_pnl_pct(signal, exit_price=98.0)
        assert abs(pnl + 2.0) < 0.001

    def test_short_win(self):
        tracker = OutcomeTracker()
        signal = _make_signal("short", entry=100.0, stop_loss=102.0, take_profit=92.0)
        # 做空跌到 92，盈 8%
        pnl = tracker.compute_pnl_pct(signal, exit_price=92.0)
        assert abs(pnl - 8.0) < 0.001

    def test_short_loss(self):
        tracker = OutcomeTracker()
        signal = _make_signal("short", entry=100.0, stop_loss=102.0, take_profit=92.0)
        # 做空涨到 102，亏 2%
        pnl = tracker.compute_pnl_pct(signal, exit_price=102.0)
        assert abs(pnl + 2.0) < 0.001


# ── fill_outcome ─────────────────────────────────────────────────────────────

class TestFillOutcomeWin:
    """命中止盈场景"""

    def test_long_hits_take_profit(self):
        tracker = OutcomeTracker()
        signal = _make_signal("long", entry=100.0, stop_loss=98.0, take_profit=108.0)
        # 在窗口内，high 触及 take_profit
        df = _make_df([
            {"datetime": pd.Timestamp("2024-01-01 09:01"), "high": 105.0, "low": 104.0, "close": 104.5},
            {"datetime": pd.Timestamp("2024-01-01 09:02"), "high": 108.1, "low": 106.0, "close": 107.0},  # 触及 TP
            {"datetime": pd.Timestamp("2024-01-01 09:03"), "high": 106.0, "low": 105.0, "close": 105.5},
        ])
        result = tracker.fill_outcome(signal, df)
        assert result.outcome == "win"
        assert result.exit_price == 108.0

    def test_short_hits_take_profit(self):
        tracker = OutcomeTracker()
        signal = _make_signal("short", entry=100.0, stop_loss=102.0, take_profit=92.0)
        # 在窗口内，low 触及 take_profit
        df = _make_df([
            {"datetime": pd.Timestamp("2024-01-01 09:01"), "high": 95.0, "low": 94.0, "close": 94.5},
            {"datetime": pd.Timestamp("2024-01-01 09:02"), "high": 93.0, "low": 91.9, "close": 92.0},  # 触及 TP
            {"datetime": pd.Timestamp("2024-01-01 09:03"), "high": 93.5, "low": 93.0, "close": 93.2},
        ])
        result = tracker.fill_outcome(signal, df)
        assert result.outcome == "win"
        assert result.exit_price == 92.0


class TestFillOutcomeLoss:
    """命中止损场景"""

    def test_long_hits_stop_loss(self):
        tracker = OutcomeTracker()
        signal = _make_signal("long", entry=100.0, stop_loss=98.0, take_profit=108.0)
        # 在窗口内，low 触及 stop_loss
        df = _make_df([
            {"datetime": pd.Timestamp("2024-01-01 09:01"), "high": 99.5, "low": 99.0, "close": 99.2},
            {"datetime": pd.Timestamp("2024-01-01 09:02"), "high": 98.5, "low": 97.9, "close": 98.0},  # 触及 SL
            {"datetime": pd.Timestamp("2024-01-01 09:03"), "high": 98.5, "low": 98.0, "close": 98.2},
        ])
        result = tracker.fill_outcome(signal, df)
        assert result.outcome == "loss"
        assert result.exit_price == 98.0

    def test_short_hits_stop_loss(self):
        tracker = OutcomeTracker()
        signal = _make_signal("short", entry=100.0, stop_loss=102.0, take_profit=92.0)
        # 在窗口内，high 触及 stop_loss
        df = _make_df([
            {"datetime": pd.Timestamp("2024-01-01 09:01"), "high": 101.0, "low": 100.0, "close": 100.5},
            {"datetime": pd.Timestamp("2024-01-01 09:02"), "high": 102.1, "low": 101.0, "close": 101.5},  # 触及 SL
            {"datetime": pd.Timestamp("2024-01-01 09:03"), "high": 101.5, "low": 101.0, "close": 101.2},
        ])
        result = tracker.fill_outcome(signal, df)
        assert result.outcome == "loss"
        assert result.exit_price == 102.0


class TestFillOutcomeTimeout:
    """超时未触场景"""

    def test_long_timeout(self):
        tracker = OutcomeTracker()
        signal = _make_signal("long", entry=100.0, stop_loss=98.0, take_profit=108.0)
        # 窗口内既没触 TP 也没触 SL
        df = _make_df([
            {"datetime": pd.Timestamp("2024-01-01 09:01"), "high": 102.0, "low": 99.0, "close": 100.5},
            {"datetime": pd.Timestamp("2024-01-01 09:02"), "high": 103.0, "low": 100.0, "close": 101.5},
            {"datetime": pd.Timestamp("2024-01-01 09:03"), "high": 104.0, "low": 101.0, "close": 103.0},
        ])
        result = tracker.fill_outcome(signal, df)
        assert result.outcome == "timeout"
        # 超时用窗口最后收盘价
        assert result.exit_price == 103.0

    def test_short_timeout(self):
        tracker = OutcomeTracker()
        signal = _make_signal("short", entry=100.0, stop_loss=102.0, take_profit=92.0)
        df = _make_df([
            {"datetime": pd.Timestamp("2024-01-01 09:01"), "high": 99.0, "low": 97.0, "close": 98.0},
            {"datetime": pd.Timestamp("2024-01-01 09:02"), "high": 100.0, "low": 98.0, "close": 99.0},
            {"datetime": pd.Timestamp("2024-01-01 09:03"), "high": 101.0, "low": 99.0, "close": 100.0},
        ])
        result = tracker.fill_outcome(signal, df)
        assert result.outcome == "timeout"
        assert result.exit_price == 100.0


class TestFillOutcomeEdge:
    """边界：空 DataFrame"""

    def test_empty_df_returns_pending(self):
        tracker = OutcomeTracker()
        signal = _make_signal("long", entry=100.0, stop_loss=98.0, take_profit=108.0)
        df = _make_df([])
        result = tracker.fill_outcome(signal, df)
        assert result.outcome == "pending"
        assert result.exit_price is None
        assert result.pnl_pct is None


class TestFillOutcomePriority:
    """优先级：止盈 > 止损 > 超时"""

    def test_take_profit_before_stop_loss(self):
        """long：TP=105, SL=98，窗口内同时触及时，先触 TP → win"""
        tracker = OutcomeTracker()
        signal = _make_signal("long", entry=100.0, stop_loss=98.0, take_profit=105.0)
        # 按时间顺序：第2根触 TP，第3根触 SL
        df = _make_df([
            {"datetime": pd.Timestamp("2024-01-01 09:01"), "high": 102.0, "low": 99.0, "close": 100.5},
            {"datetime": pd.Timestamp("2024-01-01 09:02"), "high": 105.5, "low": 100.0, "close": 102.5},  # 触 TP
            {"datetime": pd.Timestamp("2024-01-01 09:03"), "high": 110.0, "low": 97.0, "close": 103.5},  # 触 SL
        ])
        result = tracker.fill_outcome(signal, df)
        assert result.outcome == "win"
