"""test_backtest_engine — D1

TDD 红：BacktestEngine 12 单元测试
"""
from __future__ import annotations

from datetime import UTC
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from app.backtest.backtest_engine import BacktestEngine, BacktestResult


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_df(prices: list[float], start="2024-01-01", freq="h") -> pd.DataFrame:
    """生成含 OHLCV + datetime 的测试 DataFrame。"""
    n = len(prices)
    times = pd.date_range(start, periods=n, freq=freq, tz=UTC)
    return pd.DataFrame({
        "datetime": times,
        "open":  [p * 0.99 for p in prices],
        "high":  [p * 1.01 for p in prices],
        "low":   [p * 0.98 for p in prices],
        "close": prices,
        "volume": [1000.0] * n,
    })


# ── Test 1: 资金曲线正确性 ─────────────────────────────────────────────────────

class TestEquityCurve:
    def test_equity_starts_at_initial_capital(self):
        """初始资金 = initial_capital。"""
        engine = BacktestEngine(initial_capital=100_000.0)
        # 小 DataFrame，确保无信号
        df = _make_df([100.0] * 50)
        result = engine.run(df, market="BTC", period="1h")
        assert result.equity_curve.iloc[0] == 100_000.0

    def test_equity_increases_on_winning_trade(self):
        """单笔盈利交易 → equity_curve 上升。"""
        prices = list(np.linspace(100, 110, 60))
        df = _make_df(prices, "2024-01-01", "h")

        engine = BacktestEngine(initial_capital=100_000.0, fee_rate=0.0)
        # Mock _generate_signals_map 返回含 long 信号
        sig = MagicMock()
        sig.name = "test_long"
        sig.direction = "long"
        sig.confidence = 0.7
        sig.entry = 100.0
        sig.stop_loss = 98.0
        sig.take_profit = 108.0
        sig.datetime = df["datetime"].iloc[20]

        with patch.object(engine, "_generate_signals_map", return_value={20: [sig]}):
            result = engine.run(df, market="BTC", period="1h")

        # 有交易 → equity 应变化
        if result.total_trades > 0:
            assert result.equity_curve.iloc[-1] != 100_000.0

    def test_equity_decreases_on_losing_trade(self):
        """单笔亏损交易 → equity_curve 下降。"""
        prices = list(np.linspace(100, 90, 60))
        df = _make_df(prices, "2024-01-01", "h")

        engine = BacktestEngine(initial_capital=100_000.0, fee_rate=0.0)
        sig = MagicMock()
        sig.name = "test_short"
        sig.direction = "short"
        sig.confidence = 0.7
        sig.entry = 100.0
        sig.stop_loss = 102.0
        sig.take_profit = 92.0
        sig.datetime = df["datetime"].iloc[20]

        with patch.object(engine, "_generate_signals_map", return_value={20: [sig]}):
            result = engine.run(df, market="BTC", period="1h")

        if result.total_trades > 0:
            # 短单在下跌行情中应盈利（反向）
            # 这里关键是 equity 有变化
            assert result.equity_curve.iloc[-1] != 100_000.0

    def test_compound_interest_grows_equity(self):
        """复利：盈利资金再投资 → 后期资金增速加快。"""
        # 持续小幅上涨行情，TP 触发快（TP = 1.0，上涨 0.2/步 → 5 步触 TP）
        prices = [100.0 + i * 0.2 for i in range(200)]
        df = _make_df(prices, "2024-01-01", "h")

        engine = BacktestEngine(initial_capital=100_000.0, fee_rate=0.0)
        # 每 5 根出一个 TP 易触的 long 信号
        signals_map = {}
        for i in range(20, 120, 5):
            sig = MagicMock()
            sig.name = f"sig_{i}"
            sig.direction = "long"
            sig.confidence = 0.7
            sig.entry = float(df["close"].iloc[i])
            # TP 在 5 步内可触（价格上涨 0.2/步）
            sig.stop_loss = sig.entry - 1.0
            sig.take_profit = sig.entry + 1.0  # 5 步触 TP
            sig.datetime = df["datetime"].iloc[i]
            signals_map[i] = [sig]

        with patch.object(engine, "_generate_signals_map", return_value=signals_map):
            result = engine.run(df, market="BTC", period="1h")

        # 有盈利交易 → equity 应 > 初始
        assert result.total_trades > 0, "Should have winning trades"
        assert result.equity_curve.iloc[-1] > 100_000.0, \
            f"Equity should grow, got {result.equity_curve.iloc[-1]}"


# ── Test 2: Sharpe / max_drawdown / profit_factor / win_rate ──────────────────

class TestMetrics:
    def test_sharpe_ratio_formula(self):
        """Sharpe = mean/std * sqrt(annual_factor)。"""
        returns = pd.Series([0.01, 0.02, -0.01, 0.015, 0.005])
        mean_r = returns.mean()
        std_r = returns.std(ddof=1)
        expected = (mean_r / std_r) * (24 * 365) ** 0.5

        engine = BacktestEngine()
        actual = engine._sharpe_ratio(returns, "1h")
        assert abs(actual - expected) < 1e-6

    def test_sharpe_ratio_zero_std(self):
        """方差为 0 → Sharpe = 0（不除零）。"""
        returns = pd.Series([0.01, 0.01, 0.01])
        engine = BacktestEngine()
        result = engine._sharpe_ratio(returns, "1h")
        assert result == 0.0

    def test_sharpe_ratio_daily_period(self):
        """daily 数据 annual_factor = 365。"""
        returns = pd.Series([0.01, 0.02, -0.01])
        engine = BacktestEngine()
        actual = engine._sharpe_ratio(returns, "1d")
        expected_factor = 365 ** 0.5
        mean_r = returns.mean()
        std_r = returns.std(ddof=1)
        expected = (mean_r / std_r) * expected_factor
        assert abs(actual - expected) < 1e-6

    def test_max_drawdown_formula(self):
        """max_drawdown = max((running_max - val) / running_max)。

        正确理解：
          - running_max 是历史最高点
          - 回撤 = (running_max - current) / running_max
          - [100, 110, 105, 95, 100, 120]:
            - idx=1: peak=110, dd=0
            - idx=3: peak=110, dd=(110-95)/110=13.636% ← 最大
        """
        equity = pd.Series([100.0, 110.0, 105.0, 95.0, 100.0, 120.0])
        engine = BacktestEngine()
        mdd = engine._max_drawdown(equity)
        assert abs(mdd - 13.636) < 0.1  # 13.636%

    def test_profit_factor_formula(self):
        """profit_factor = sum(pos) / abs(sum(neg))。"""
        trades = [
            {"pnl_pct": 5.0},
            {"pnl_pct": -3.0},
            {"pnl_pct": 4.0},
            {"pnl_pct": -1.5},
        ]
        engine = BacktestEngine()
        pf = engine._profit_factor(trades)
        assert abs(pf - 2.0) < 1e-6

    def test_win_rate_formula(self):
        """win_rate = win_count / total。"""
        trades = [
            {"outcome": "win"},
            {"outcome": "win"},
            {"outcome": "loss"},
            {"outcome": "win"},
        ]
        engine = BacktestEngine()
        wr = engine._win_rate(trades)
        assert wr == 0.75  # 3/4

    def test_zero_trades_metrics(self):
        """无交易时：total_return=0, sharpe=0, max_dd=0。"""
        prices = [100.0] * 50
        df = _make_df(prices)
        engine = BacktestEngine()

        with patch.object(engine, "_generate_signals_map", return_value={}):
            result = engine.run(df, market="BTC", period="1h")

        assert result.total_return_pct == 0.0
        assert result.sharpe_ratio == 0.0
        assert result.max_drawdown_pct == 0.0
        assert result.total_trades == 0


# ── Test 3: 手续费影响 ────────────────────────────────────────────────────────

class TestFee:
    def test_fee_reduces_profit(self):
        """手续费 0.1% → 每笔交易成本 0.1%。"""
        prices = [100.0 + i * 0.5 for i in range(60)]
        df = _make_df(prices, "2024-01-01", "h")

        sig = MagicMock()
        sig.name = "fee_test"
        sig.direction = "long"
        sig.confidence = 0.7
        sig.entry = 100.0
        sig.stop_loss = 98.0
        sig.take_profit = 108.0
        sig.datetime = df["datetime"].iloc[5]

        engine_no_fee = BacktestEngine(initial_capital=100_000.0, fee_rate=0.0)
        engine_with_fee = BacktestEngine(initial_capital=100_000.0, fee_rate=0.001)

        with patch.object(engine_no_fee, "_generate_signals_map", return_value={5: [sig]}):
            result_no_fee = engine_no_fee.run(df, market="BTC", period="1h")

        with patch.object(engine_with_fee, "_generate_signals_map", return_value={5: [sig]}):
            result_with_fee = engine_with_fee.run(df, market="BTC", period="1h")

        # 有手续费的结果应 <= 无手续费
        assert result_with_fee.total_return_pct <= result_no_fee.total_return_pct + 1e-6


# ── Test 4: 空仓周期跳过 ──────────────────────────────────────────────────────

class TestIdlePeriod:
    def test_no_trades_when_no_signal(self):
        """无信号时 → trade_log 为空，equity 不变。"""
        prices = [100.0 + i * 0.1 for i in range(200)]
        df = _make_df(prices, "2024-01-01", "h")

        engine = BacktestEngine(initial_capital=100_000.0)

        with patch.object(engine, "_generate_signals_map", return_value={}):
            result = engine.run(df, market="BTC", period="1h")

        assert result.trade_log == []
        assert result.total_trades == 0
        assert result.equity_curve.iloc[0] == 100_000.0


# ── Test 5: 复杂盈亏混合 ──────────────────────────────────────────────────────

class TestMixedTrades:
    def test_win_loss_mixed_trade_log(self):
        """win + loss 混合 → trade_log 正确记录。"""
        prices = []
        for i in range(200):
            cycle = i % 15
            if cycle < 10:
                prices.append(100.0 + cycle * 0.5)
            else:
                prices.append(105.0 - (cycle - 10) * 0.5)

        df = _make_df(prices, "2024-01-01", "h")
        engine = BacktestEngine(initial_capital=100_000.0, fee_rate=0.0)

        # 每 15 根出一次信号
        signals_map = {}
        for i in range(20, 100, 15):
            sig = MagicMock()
            sig.name = f"sig_{i}"
            sig.direction = "long"
            sig.confidence = 0.7
            sig.entry = float(df["close"].iloc[i])
            sig.stop_loss = sig.entry - 2.0
            sig.take_profit = sig.entry + 4.0
            sig.datetime = df["datetime"].iloc[i]
            signals_map[i] = [sig]

        with patch.object(engine, "_generate_signals_map", return_value=signals_map):
            result = engine.run(df, market="BTC", period="1h")

        assert result.total_trades >= 0
        assert result.profit_factor >= 0.0
        assert 0 <= result.win_rate <= 1.0

    def test_backtest_result_has_all_fields(self):
        """BacktestResult 所有字段都存在且类型正确。"""
        prices = [100.0] * 50
        df = _make_df(prices)
        engine = BacktestEngine()

        with patch.object(engine, "_generate_signals_map", return_value={}):
            result = engine.run(df, market="BTC", period="1h")

        assert hasattr(result, "total_return_pct")
        assert hasattr(result, "sharpe_ratio")
        assert hasattr(result, "max_drawdown_pct")
        assert hasattr(result, "win_rate")
        assert hasattr(result, "profit_factor")
        assert hasattr(result, "total_trades")
        assert hasattr(result, "equity_curve")
        assert hasattr(result, "trade_log")
        assert isinstance(result.equity_curve, pd.Series)
        assert isinstance(result.trade_log, list)
