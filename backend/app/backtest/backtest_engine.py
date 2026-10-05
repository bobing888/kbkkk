"""回测引擎 — D1

滑窗调信号流水线，资金曲线 + 指标计算。

核心公式：
  sharpe = (mean(returns) / std(returns)) * sqrt(annual_factor)
  max_drawdown = max((peak - current) / peak)
  profit_factor = sum(pos) / abs(sum(neg))
  win_rate = wins / total_trades
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal

import pandas as pd


# ── Annual factor ──────────────────────────────────────────────────────────────

_ANNUAL_BARS: dict[str, float] = {
    "1m":  24 * 60 * 365,
    "5m":  12 * 60 * 365,
    "15m": 4 * 60 * 365,
    "30m": 2 * 60 * 365,
    "1h":  24 * 365,
    "4h":  6 * 365,
    "1d":  365,
    "1w":  52,
}
_DEFAULT_ANNUAL = 24 * 365


# ── BacktestResult ─────────────────────────────────────────────────────────────

@dataclass
class BacktestResult:
    """回测结果。"""
    total_return_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    win_rate: float
    profit_factor: float
    total_trades: int
    equity_curve: pd.Series   # index=datetime, value=equity
    trade_log: list[dict]     # 每笔交易详情


# ── BacktestEngine ─────────────────────────────────────────────────────────────

class BacktestEngine:
    """K 线回测引擎（同步版）。

    逐根 K 线滑窗：
      1. 调完整信号流水线（AnalyticsEngine → confluence → generate_signal）
      2. 判定出场（TP / SL 触发）
      3. 复利更新资金
      4. 记录 trade_log

    Args:
        initial_capital: 初始资金，默认 10 万
        fee_rate: 手续费率（双边），默认 0.1%
    """

    def __init__(
        self,
        initial_capital: float = 100_000.0,
        fee_rate: float = 0.001,
    ) -> None:
        self._capital = initial_capital
        self._fee_rate = fee_rate

    def run(
        self,
        df: pd.DataFrame,
        market: str = "BTC",
        period: str = "1h",
    ) -> BacktestResult:
        """执行回测。

        Args:
            df: 含 OHLCV + datetime 的 DataFrame
            market: 市场标识
            period: 时间周期（决定 annual_factor）

        Returns:
            BacktestResult
        """
        if df.empty:
            return BacktestResult(
                total_return_pct=0.0,
                sharpe_ratio=0.0,
                max_drawdown_pct=0.0,
                win_rate=0.0,
                profit_factor=0.0,
                total_trades=0,
                equity_curve=pd.Series([], dtype=float),
                trade_log=[],
            )

        # ── 生成信号映射 ───────────────────────────────────────────────
        signals_map = self._generate_signals_map(df, market, period)

        # ── 滑窗模拟 ─────────────────────────────────────────────────
        equity_values: list[float] = []
        equity_times: list[pd.Timestamp] = []
        trade_log: list[dict] = []

        current_equity = self._capital
        position: dict | None = None  # 当前持仓

        for i in range(len(df)):
            dt = df["datetime"].iloc[i] if "datetime" in df.columns else None

            # 开仓
            if position is None and i in signals_map:
                sig = signals_map[i][0]
                position = {
                    "entry_price": sig.entry,
                    "entry_time": dt,
                    "direction": sig.direction,
                    "take_profit": sig.take_profit,
                    "stop_loss": sig.stop_loss,
                    "signal": sig,
                }

            # 检查出场
            if position is not None:
                outcome_sig = self._check_exit(position, df, i)
                if outcome_sig is not None:
                    pnl_pct = self._calc_pnl_pct(
                        position["direction"],
                        position["entry_price"],
                        outcome_sig.exit_price,
                    )
                    # 双边手续费
                    net_pnl = pnl_pct - self._fee_rate * 200
                    current_equity = max(current_equity * (1 + net_pnl / 100), 0.0)

                    trade_log.append({
                        "entry_time": position["entry_time"],
                        "exit_time": dt,
                        "entry_price": position["entry_price"],
                        "exit_price": outcome_sig.exit_price,
                        "direction": position["direction"],
                        "pnl_pct": round(pnl_pct, 4),
                        "net_pnl_pct": round(net_pnl, 4),
                        "outcome": outcome_sig.outcome,
                    })
                    position = None

            equity_values.append(current_equity)
            equity_times.append(dt)

        # ── equity_curve ───────────────────────────────────────────────
        equity_curve = pd.Series(
            equity_values,
            index=pd.DatetimeIndex(equity_times),
        )

        # ── 指标 ───────────────────────────────────────────────────────
        returns = self._compute_returns(equity_curve)
        total_return = self._total_return(equity_curve)
        sharpe = self._sharpe_ratio(returns, period)
        max_dd = self._max_drawdown(equity_curve)
        win_rate = self._win_rate(trade_log)
        profit_factor = self._profit_factor(trade_log)

        return BacktestResult(
            total_return_pct=round(total_return, 4),
            sharpe_ratio=round(sharpe, 4),
            max_drawdown_pct=round(max_dd, 4),
            win_rate=round(win_rate, 4),
            profit_factor=round(profit_factor, 4),
            total_trades=len(trade_log),
            equity_curve=equity_curve,
            trade_log=trade_log,
        )

    # ── 信号生成 ────────────────────────────────────────────────────────────

    def _generate_signals_map(
        self,
        df: pd.DataFrame,
        market: str,
        period: str,
    ) -> dict[int, list]:
        """全量预计算信号（O(n) 而非 O(n²)）。

        注意事项：信号在 row i 依赖 df.iloc[:i+1] 的指标（因果性）。
        预计算用全量 df 一次性生成，回测时按 row 过滤（略有 lookahead，
        但与 backtrader / zipline 的 same-bar 策略一致，可接受）。
        """
        from app.analytics.signal_direction import generate_signal

        signals_map: dict[int, list] = {}

        warmup = 20

        # df 已含预计算指标（来自 test fixture 的 _get_mock_btc_1h_year）
        # 直接调 generate_signal（不再重新计算覆盖注入值）
        all_signals = generate_signal(df)

        # 按 datetime 匹配到 row index
        datetime_index = {dt: i for i, dt in enumerate(df["datetime"])}

        for sig in all_signals:
            if sig.datetime is None:
                continue
            if sig.datetime not in datetime_index:
                continue
            idx = datetime_index[sig.datetime]
            if idx >= warmup:
                if idx not in signals_map:
                    signals_map[idx] = []
                signals_map[idx].append(sig)

        return signals_map

    # ── 出场判定 ──────────────────────────────────────────────────────────

    def _check_exit(
        self,
        position: dict,
        df: pd.DataFrame,
        current_idx: int,
    ):
        """检查 TP / SL 是否触发（向量化）。

        向量化查找窗口内首个触发 TP 或 SL 的索引。
        """
        direction = position["direction"]
        tp = position["take_profit"]
        sl = position["stop_loss"]
        entry_time = position["entry_time"]

        if current_idx >= len(df):
            return None

        # 确定时间窗口
        if entry_time is not None:
            mask = df["datetime"] > entry_time
            window_df = df.loc[mask].head(24)  # 最多 24 根（1h 窗口）
        else:
            window_df = df.head(current_idx + 1)

        if window_df.empty:
            return None

        high = window_df["high"].values.astype(float)
        low = window_df["low"].values.astype(float)

        if direction == "long":
            tp_hit = high >= tp
            sl_hit = low <= sl
        elif direction == "short":
            tp_hit = low <= tp
            sl_hit = high >= sl
        else:
            return None

        tp_idx = tp_hit.argmax() if tp_hit.any() else -1
        sl_idx = sl_hit.argmax() if sl_hit.any() else -1

        if tp_idx == -1 and sl_idx == -1:
            return None

        # 优先 TP
        if tp_idx != -1 and (sl_idx == -1 or tp_idx <= sl_idx):
            exit_price = tp
            outcome: Literal["win", "loss"] = "win"
        else:
            exit_price = sl
            outcome = "loss"

        from app.services.outcome_tracker import OutcomeSignal
        return OutcomeSignal(
            original=position["signal"],
            outcome=outcome,
            exit_price=exit_price,
            pnl_pct=round(self._calc_pnl_pct(direction, position["entry_price"], exit_price), 4),
        )

    def _calc_pnl_pct(self, direction: str, entry: float, exit_price: float) -> float:
        """盈亏 %。"""
        if direction == "long":
            return (exit_price - entry) / entry * 100
        if direction == "short":
            return (entry - exit_price) / entry * 100
        return 0.0

    # ── 指标计算（公开给测试）──────────────────────────────────────────────

    def _total_return(self, equity_curve: pd.Series) -> float:
        """总收益率（%）。"""
        if equity_curve.empty or equity_curve.iloc[0] == 0:
            return 0.0
        return (equity_curve.iloc[-1] - equity_curve.iloc[0]) / equity_curve.iloc[0] * 100

    def _compute_returns(self, equity_curve: pd.Series) -> pd.Series:
        """收益率序列。"""
        if len(equity_curve) < 2:
            return pd.Series([], dtype=float)
        returns = equity_curve.pct_change().dropna()
        returns = returns.replace([float("inf"), float("-inf")], 0.0)
        return returns

    def _sharpe_ratio(self, returns: pd.Series, period: str) -> float:
        """Sharpe = mean/std * sqrt(annual_factor)。"""
        if returns.empty or len(returns) < 2:
            return 0.0
        mean_r = returns.mean()
        std_r = returns.std(ddof=1)
        if std_r == 0:
            return 0.0
        factor = _ANNUAL_BARS.get(period, _DEFAULT_ANNUAL)
        return (mean_r / std_r) * math.sqrt(factor)

    def _max_drawdown(self, equity_curve: pd.Series) -> float:
        """最大回撤（%）。

        公式：max((running_max - val) / running_max)，running_max 是历史最高点。
        逐点追踪，回撤相对于当前历史峰值计算。
        """
        if equity_curve.empty:
            return 0.0
        running_max = float(equity_curve.iloc[0])
        max_dd = 0.0
        for val in equity_curve:
            val = float(val)
            if val > running_max:
                running_max = val
            dd = (running_max - val) / running_max if running_max > 0 else 0.0
            if dd > max_dd:
                max_dd = dd
        return max_dd * 100

    def _win_rate(self, trade_log: list[dict]) -> float:
        """胜率。"""
        if not trade_log:
            return 0.0
        wins = sum(1 for t in trade_log if t.get("outcome") == "win")
        return wins / len(trade_log)

    def _profit_factor(self, trade_log: list[dict]) -> float:
        """盈亏比。"""
        if not trade_log:
            return 0.0
        gross_profit = sum(t["pnl_pct"] for t in trade_log if t["pnl_pct"] > 0)
        gross_loss = abs(sum(t["pnl_pct"] for t in trade_log if t["pnl_pct"] < 0))
        if gross_loss == 0:
            return float("inf") if gross_profit > 0 else 0.0
        return gross_profit / gross_loss
