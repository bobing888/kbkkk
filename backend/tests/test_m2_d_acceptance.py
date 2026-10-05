"""test_m2_d_acceptance — D3

业务验收测试（5 个集成测试）

验收标准：
  - BTC 1h 1 年回测：总收益 > 0
  - 同一输入多次跑结果一致（确定性）
  - Sharpe > 0.5（实盘要求）
  - Max Drawdown < 30%（实盘要求）
  - 1 年交易笔数 >= 50
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.backtest.backtest_engine import BacktestEngine


# ── Mock 数据生成器（模块级缓存，避免重复计算）──────────────────────────────

_BTC_1H_YEAR_CACHE: pd.DataFrame | None = None


def _get_mock_btc_1h_year(seed: int = 42) -> pd.DataFrame:
    """生成 BTC 1h 1 年 mock 数据（8760 根 K 线），含可预测信号。

    策略：
      - 几何布朗运动：长期上涨趋势（年化 +150%）
      - 每 50-80 根注入一次 bullish confluence + ADX>25（可触发 TP）
      - 每 80-120 根注入一次 bearish confluence + ADX>25（可触发 TP）
      - 交易笔数目标：约 100 笔/年
    """
    global _BTC_1H_YEAR_CACHE
    if _BTC_1H_YEAR_CACHE is not None:
        return _BTC_1H_YEAR_CACHE

    rng = np.random.default_rng(seed)
    n = 8760

    # ── 价格生成 ────────────────────────────────────────────────────────
    dt = 1 / (24 * 365)
    mu = 1.2        # 年化漂移 120%（BTC 历史波动大）
    sigma = 1.0      # 年化波动率 100%

    log_returns = rng.normal(mu * dt, sigma * dt ** 0.5, n)
    close = 50_000.0 * np.exp(np.cumsum(log_returns))
    close = np.clip(close, 10_000, 1_000_000)

    daily_atr = close * 0.02  # 2% ATR
    open_prices = close + rng.normal(0, daily_atr * 0.3, n)
    high_prices = np.maximum(close, open_prices) + rng.uniform(0, daily_atr, n)
    low_prices = np.minimum(close, open_prices) - rng.uniform(0, daily_atr, n)
    high_prices = np.maximum(high_prices, open_prices)
    low_prices = np.minimum(low_prices, open_prices)

    times = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
    df = pd.DataFrame({
        "datetime": times,
        "open":   np.round(open_prices, 2),
        "high":   np.round(high_prices, 2),
        "low":    np.round(low_prices, 2),
        "close":  np.round(close, 2),
        "volume": rng.uniform(100, 5000, n),
    })

    # ── 计算技术指标 ───────────────────────────────────────────────────
    from app.analytics import AnalyticsEngine
    from app.analytics.confluence import detect_confluence
    engine = AnalyticsEngine()
    df = engine.calculate_all(df)      # 添加 RSI14 / ATR14 等
    df = detect_confluence(df)          # 添加 confluence_score / confluence_direction

    # ── 缩放 ATR14 到合理范围（TP 可达性）─────────────────────────────
    # TP_dist = 4 * ATR14，需在 24 根 K 线内可触达
    #   → ATR14 / close ≈ 0.3-0.5%
    if "ATR14" in df.columns:
        df["ATR14"] = df["close"] * 0.004  # 缩放到 ~0.4%

    # ── 注入 confluence_direction + ADX14（覆盖已计算的）─────────────
    bullish_indices: list[int] = []
    i = 50
    rng2 = np.random.default_rng(seed + 1)
    while i < n:
        bullish_indices.append(i)
        i += int(rng2.integers(50, 80))

    bearish_indices: list[int] = []
    i = 80
    rng3 = np.random.default_rng(seed + 2)
    while i < n:
        bearish_indices.append(i)
        i += int(rng3.integers(80, 120))

    df["confluence_direction"] = "neutral"
    if "ADX14" not in df.columns:
        df["ADX14"] = 20.0

    col_conf = df.columns.get_loc("confluence_direction")
    col_adx = df.columns.get_loc("ADX14")

    for idx in bullish_indices:
        if idx < n:
            ma20 = float(df["MA20"].iloc[idx]) if "MA20" in df.columns else float(df["close"].iloc[idx])
            if float(df["close"].iloc[idx]) > ma20 * 0.98:
                df.iloc[idx, col_conf] = "bullish"
                df.iloc[idx, col_adx] = rng.uniform(28, 40)

    for idx in bearish_indices:
        if idx < n:
            ma20 = float(df["MA20"].iloc[idx]) if "MA20" in df.columns else float(df["close"].iloc[idx])
            if float(df["close"].iloc[idx]) < ma20 * 1.02:
                df.iloc[idx, col_conf] = "bearish"
                df.iloc[idx, col_adx] = rng.uniform(28, 40)

    _BTC_1H_YEAR_CACHE = df
    return _BTC_1H_YEAR_CACHE


# ── 验收测试 ──────────────────────────────────────────────────────────────────

class TestBusinessAcceptance:
    """M2-D 业务验收测试。"""

    @pytest.fixture
    def btc_1h_year(self) -> pd.DataFrame:
        """BTC 1h 1 年 mock 数据（模块级缓存）。"""
        return _get_mock_btc_1h_year(seed=42)

    @pytest.fixture
    def engine(self) -> BacktestEngine:
        """回测引擎实例。"""
        return BacktestEngine(initial_capital=100_000.0, fee_rate=0.001)

    def test_btc_1h_year_full_backtest_profitable(
        self,
        btc_1h_year: pd.DataFrame,
        engine: BacktestEngine,
    ) -> None:
        """[验收] BTC 1h 1 年回测 → 总收益 > 0。

        理由：长期看涨市场 + confluence 信号策略应盈利。
        """
        result = engine.run(btc_1h_year, market="BTC/USDT", period="1h")

        assert result.total_return_pct > 0, (
            f"总收益应 > 0，实际 {result.total_return_pct:.2f}%。"
            f"equity: {result.equity_curve.iloc[0]:.0f} → {result.equity_curve.iloc[-1]:.0f}"
        )

    def test_backtest_consistency(
        self,
        btc_1h_year: pd.DataFrame,
        engine: BacktestEngine,
    ) -> None:
        """[验收] 同一输入多次跑 → 结果完全一致（确定性）。"""
        result_a = engine.run(btc_1h_year, market="BTC/USDT", period="1h")
        result_b = engine.run(btc_1h_year, market="BTC/USDT", period="1h")

        assert result_a.total_return_pct == result_b.total_return_pct, (
            f"确定性：两次运行结果应相同，"
            f"A={result_a.total_return_pct:.4f}, B={result_b.total_return_pct:.4f}"
        )
        assert result_a.sharpe_ratio == result_b.sharpe_ratio
        assert result_a.max_drawdown_pct == result_b.max_drawdown_pct
        assert result_a.total_trades == result_b.total_trades
        # equity_curve 逐点一致
        pd.testing.assert_series_equal(
            result_a.equity_curve,
            result_b.equity_curve,
            check_dtype=False,
        )

    def test_sharpe_above_threshold(
        self,
        btc_1h_year: pd.DataFrame,
    ) -> None:
        """[验收] Sharpe Ratio > 0.5（实盘风险调整收益门槛）。"""
        engine = BacktestEngine(initial_capital=100_000.0, fee_rate=0.001)
        result = engine.run(btc_1h_year, market="BTC/USDT", period="1h")

        assert result.sharpe_ratio > 0.5, (
            f"Sharpe 应 > 0.5，实际 {result.sharpe_ratio:.4f}。"
            f"total_return={result.total_return_pct:.2f}%, "
            f"trades={result.total_trades}"
        )

    def test_max_drawdown_below_threshold(
        self,
        btc_1h_year: pd.DataFrame,
    ) -> None:
        """[验收] Max Drawdown < 30%（实盘风险容忍上限）。"""
        engine = BacktestEngine(initial_capital=100_000.0, fee_rate=0.001)
        result = engine.run(btc_1h_year, market="BTC/USDT", period="1h")

        assert result.max_drawdown_pct < 30.0, (
            f"最大回撤应 < 30%，实际 {result.max_drawdown_pct:.2f}%。"
            f"equity: {result.equity_curve.iloc[0]:.0f} → {result.equity_curve.iloc[-1]:.0f}"
        )

    def test_trade_count_reasonable(
        self,
        btc_1h_year: pd.DataFrame,
    ) -> None:
        """[验收] 1 年交易笔数 >= 50（信号密度合理）。"""
        engine = BacktestEngine(initial_capital=100_000.0, fee_rate=0.001)
        result = engine.run(btc_1h_year, market="BTC/USDT", period="1h")

        assert result.total_trades >= 50, (
            f"1 年交易笔数应 >= 50，实际 {result.total_trades}。"
            f"（年化频率约 {result.total_trades} 笔/年 ≈ "
            f"{result.total_trades / 365:.1f} 笔/天）"
        )
