"""OutcomeTracker — C2

动态窗口回填 outcome。
根据 signal.direction + entry 找窗口内最高/最低价：
  - 命中止盈（TP 触及）→ outcome = "win"
  - 命中止损（SL 触及）→ outcome = "loss"
  - 超时未触 → outcome = "timeout"
  - 无数据 → outcome = "pending"

Outcome window 查表：
  1m/5m/15m/30m → 60 根
  1h/4h        → 24 根
  1d/1w        → 5 根
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

import pandas as pd

from app.analytics.signal_direction import Signal


# ── Window lookup table ────────────────────────────────────────────────────────

# period → number of bars to track
_WINDOW_BARS: dict[str, int] = {
    "1m": 60,
    "5m": 60,
    "15m": 60,
    "30m": 60,
    "1h": 24,
    "4h": 24,
    "1d": 5,
    "1w": 5,
}

# Default for unknown periods
_DEFAULT_WINDOW_BARS = 60


# ── OutcomeSignal dataclass ────────────────────────────────────────────────────

@dataclass
class OutcomeSignal:
    """带 outcome 标注的 Signal。"""
    original: Signal
    outcome: Literal["win", "loss", "timeout", "pending"]
    exit_price: Optional[float] = None
    pnl_pct: Optional[float] = None


# ── OutcomeTracker ────────────────────────────────────────────────────────────

class OutcomeTracker:
    """根据时间窗口追踪 signal 结果。"""

    def get_window_for_period(self, period: str) -> int:
        """查表返回窗口根数。"""
        return _WINDOW_BARS.get(period, _DEFAULT_WINDOW_BARS)

    def compute_pnl_pct(self, signal: Signal, exit_price: float) -> float:
        """计算盈亏百分比（%）。

        long:  (exit - entry) / entry * 100
        short: (entry - exit) / entry * 100
        """
        if signal.direction == "long":
            return (exit_price - signal.entry) / signal.entry * 100
        elif signal.direction == "short":
            return (signal.entry - exit_price) / signal.entry * 100
        else:
            return 0.0

    def fill_outcome(
        self,
        signal: Signal,
        current_df: pd.DataFrame,
        period: str = "1h",
    ) -> OutcomeSignal:
        """根据当前 df 填充 signal outcome。

        优先级：TP 先触 → win | SL 先触 → loss | 都未触 → timeout
        止盈/止损触发价格用 signal 的 TP/SL 本身（精确匹配）。

        Args:
            signal: 原始信号
            current_df: 包含历史 K 线（high/low 列）的 DataFrame
            period: 时间周期（决定窗口根数）

        Returns:
            OutcomeSignal，含 outcome + exit_price + pnl_pct
        """
        window = self.get_window_for_period(period)

        # 无数据 → pending
        if current_df.empty:
            return OutcomeSignal(
                original=signal,
                outcome="pending",
                exit_price=None,
                pnl_pct=None,
            )

        # 取 signal.datetime 之后最多 window 根 K 线
        signal_dt = signal.datetime
        if signal_dt is not None:
            mask = current_df["datetime"] > signal_dt
            subset = current_df.loc[mask].head(window)
        else:
            subset = current_df.head(window)

        if subset.empty:
            return OutcomeSignal(
                original=signal,
                outcome="pending",
                exit_price=None,
                pnl_pct=None,
            )

        # ── 按时间顺序扫描 ────────────────────────────────────────────
        first_tp_idx: int | None = None
        first_sl_idx: int | None = None

        for idx, (_, row) in enumerate(subset.iterrows()):
            high = float(row["high"])
            low = float(row["low"])

            if signal.direction == "long":
                if high >= signal.take_profit and first_tp_idx is None:
                    first_tp_idx = idx
                if low <= signal.stop_loss and first_sl_idx is None:
                    first_sl_idx = idx
            elif signal.direction == "short":
                if low <= signal.take_profit and first_tp_idx is None:
                    first_tp_idx = idx
                if high >= signal.stop_loss and first_sl_idx is None:
                    first_sl_idx = idx

        # ── 判定 outcome（按命中时间优先）────────────────────────────────
        last_close = float(subset.iloc[-1]["close"])

        if first_tp_idx is not None and first_sl_idx is not None:
            if first_tp_idx <= first_sl_idx:
                outcome: Literal["win", "loss"] = "win"
                exit_price = signal.take_profit
            else:
                outcome = "loss"
                exit_price = signal.stop_loss
        elif first_tp_idx is not None:
            outcome = "win"
            exit_price = signal.take_profit
        elif first_sl_idx is not None:
            outcome = "loss"
            exit_price = signal.stop_loss
        else:
            outcome = "timeout"
            exit_price = last_close

        pnl = self.compute_pnl_pct(signal, exit_price)

        return OutcomeSignal(
            original=signal,
            outcome=outcome,
            exit_price=round(exit_price, 2),
            pnl_pct=round(pnl, 4),
        )
