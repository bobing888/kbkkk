"""RiskManager — M3 F2

5 个门控检查（can_open）：
1. 单日亏损未达 2%
2. 当前持仓 < 3
3. 同方向未超 10% 资金
4. signal.confidence >= 0.5
5. signal.sources 至少有 1 个形态或 confluence

返回 (bool, reason)：通过返回 (True, "")，拒绝返回 (False, "原因")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.analytics.signal_direction import Signal


# ── 依赖类型 ────────────────────────────────────────────────────────────────

@dataclass
class Position:
    """持仓信息（用于风控计算）。"""
    symbol: str
    direction: Literal["long", "short"]
    notional: float       # 名义价值（USD）
    entry_price: float
    stop_loss: float


@dataclass
class AccountState:
    """账户状态快照（风控计算用）。"""
    equity: float                    # 总资金
    daily_pnl: float = 0.0          # 当日盈亏（USD，负=亏损）
    daily_pnl_pct: float = 0.0     # 当日盈亏百分比
    positions: list[Position] = field(default_factory=list)


# ── RiskManager ─────────────────────────────────────────────────────────────

class RiskManager:
    """5 门控风控管理器。

    约束（来自 M3 spec）：
    - 单日累计亏损 ≤ 2% 总资金
    - 同时持仓 ≤ 3 笔
    - 同方向持仓 ≤ 10% 总资金
    - 最低 confidence ≥ 0.5
    - 必须有 confluence 或形态来源
    """

    def __init__(
        self,
        max_daily_loss_pct: float = 0.02,
        max_concurrent_positions: int = 3,
        max_correlation_exposure: float = 0.10,
    ) -> None:
        if not 0 < max_daily_loss_pct <= 1:
            raise ValueError("max_daily_loss_pct must be in (0, 1]")
        if not 1 <= max_concurrent_positions:
            raise ValueError("max_concurrent_positions must be >= 1")
        if not 0 < max_correlation_exposure <= 1:
            raise ValueError("max_correlation_exposure must be in (0, 1]")

        self._max_daily_loss_pct = max_daily_loss_pct
        self._max_concurrent = max_concurrent_positions
        self._max_correlation_pct = max_correlation_exposure
        self._min_confidence = 0.5

    def can_open(self, signal: Signal, current_state: AccountState) -> tuple[bool, str]:
        """5 门控检查。

        按顺序检查，全部通过才返回 (True, "")。

        Args:
            signal: 待执行信号
            current_state: 当前账户状态

        Returns:
            (True, "") — 通过
            (False, "原因") — 拒绝
        """
        # ── Gate 1: 单日亏损未达 2% ──────────────────────────────────
        if current_state.daily_pnl_pct <= -self._max_daily_loss_pct:
            return (False, f"daily_loss_limit: {current_state.daily_pnl_pct:.2%} >= {self._max_daily_loss_pct:.2%}")

        # ── Gate 2: 当前持仓 < max_concurrent ─────────────────────────
        if len(current_state.positions) >= self._max_concurrent:
            return (False, f"max_positions: {len(current_state.positions)} >= {self._max_concurrent}")

        # ── Gate 3: 同方向未超 10% 资金 ─────────────────────────────
        same_direction_exposure = self._calc_direction_exposure(
            signal.direction, current_state.positions, current_state.equity
        )
        if same_direction_exposure >= self._max_correlation_pct:
            return (False, f"direction_exposure: {same_direction_exposure:.2%} >= {self._max_correlation_pct:.2%}")

        # ── Gate 4: confidence >= 0.5 ─────────────────────────────────
        if signal.confidence < self._min_confidence:
            return (False, f"low_confidence: {signal.confidence} < {self._min_confidence}")

        # ── Gate 5: sources 至少有 1 个形态或 confluence ─────────────
        if not self._has_valid_source(signal.sources):
            return (False, "no_confluence_or_pattern: sources must include confluence or candle pattern")

        return (True, "")

    def update_daily_pnl(self, pnl: float) -> None:
        """更新当日累计盈亏（外部调用，每日重置）。"""
        # 此处只记录，由 AccountState.daily_pnl_pct 驱动
        pass

    def on_position_closed(self, position: Position) -> None:
        """持仓平仓后清理（可扩展，如更新统计）。"""
        pass

    # ── 内部辅助 ────────────────────────────────────────────────────────

    def _calc_direction_exposure(
        self,
        direction: Literal["long", "short"],
        positions: list[Position],
        equity: float,
    ) -> float:
        """计算同方向持仓占总资金比例。"""
        if not positions or equity <= 0:
            return 0.0
        same_dir_total = sum(
            p.notional for p in positions if p.direction == direction
        )
        return same_dir_total / equity

    def _has_valid_source(self, sources: list[str]) -> bool:
        """检查 sources 是否含 confluence 或形态。"""
        confluence_keywords = {"confluence_bullish", "confluence_bearish"}
        pattern_keywords = {
            "hammer", "morning_star", "three_white_soldiers", "engulfing",
            "harami", "piercing", "tweezer", "counterattack",
            "hanging_man", "evening_star", "three_black_crows", "throwing_star",
        }
        if not sources:
            return False
        for src in sources:
            if src in confluence_keywords:
                return True
            if any(kw in src.lower() for kw in pattern_keywords):
                return True
        return False
