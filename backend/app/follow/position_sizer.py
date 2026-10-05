"""自动跟单系统 — M3 auto-follow

模块结构：
- position_sizer  : 仓位计算（Signal → PositionSize）
- risk_manager    : 5 门控风控（RiskManager）
- follow_engine   : 调度器（Signal → Order → TradeLog）
- follow_worker   : asyncio worker（订阅 bus + 监控 SL/TP）

设计原则（来自 backend-architect 决策框架）：
- 仓位公式：quantity = (equity * risk_pct) / abs(entry - stop_loss)
- 单仓位 ≤ max_position_pct 总资金，单交易风险 ≤ max_risk_per_trade_pct 总资金
- confidence 加权（0.5 → 50% 基础仓位，1.0 → 100%）
- ATR-based 止损距离
- 执行顺序：风险公式 → position cap → confidence 加权
"""
from __future__ import annotations

from dataclasses import dataclass

from app.analytics.signal_direction import Signal


@dataclass
class PositionSize:
    """仓位计算结果。"""
    quantity: float       # 下单数量
    notional: float      # 名义价值（quantity × entry）
    risk_amount: float   # 风险金额（USD）
    risk_pct: float     # 风险占比（相对总资金）


class PositionSizer:
    """根据 Signal + ATR 止损距离 + confidence 加权计算仓位。

    约束：
    - 单交易风险 ≤ max_risk_per_trade_pct 总资金（默认 1%）
    - 单仓位 ≤ max_position_pct 总资金（默认 5%）

    公式（执行顺序）：
        1. risk_distance = abs(entry - stop_loss)
        2. base_quantity = (equity × max_risk_pct) / risk_distance
        3. base_notional = base_quantity × current_price
        4. if base_notional > max_position_pct × equity:
               base_quantity = (max_position_pct × equity) / current_price
               base_notional = max_position_pct × equity
        5. confidence_ratio = max(0.5, signal.confidence)
        6. final_quantity = base_quantity × confidence_ratio
        7. final_notional = final_quantity × current_price
        8. risk_amount = final_quantity × risk_distance
    """

    _MIN_CONFIDENCE_RATIO = 0.5  # 最低 50% 仓位

    def __init__(
        self,
        max_position_pct: float = 0.05,
        max_risk_per_trade_pct: float = 0.01,
    ) -> None:
        if not 0 < max_position_pct <= 1:
            raise ValueError("max_position_pct must be in (0, 1]")
        if not 0 < max_risk_per_trade_pct <= max_position_pct:
            raise ValueError("max_risk_per_trade_pct must be in (0, max_position_pct]")
        self._max_pos_pct = max_position_pct
        self._max_risk_pct = max_risk_per_trade_pct

    def size(
        self,
        signal: Signal,
        equity: float,
        current_price: float,
    ) -> PositionSize:
        """计算仓位。

        Args:
            signal: Signal（含 entry / stop_loss / confidence）
            equity: 账户总资金（USD）
            current_price: 当前价格（作为 entry 使用）

        Returns:
            PositionSize

        Raises:
            ValueError: signal.direction == "neutral" 或 equity <= 0
        """
        if signal.direction == "neutral":
            raise ValueError("Cannot size neutral signal")
        if equity <= 0:
            raise ValueError("equity must be positive")

        # 止损距离
        risk_distance = abs(current_price - signal.stop_loss)
        if risk_distance <= 0:
            raise ValueError(f"Invalid stop_loss distance: {risk_distance}")

        # 基础数量（按 1% 风险公式）
        base_quantity = (equity * self._max_risk_pct) / risk_distance
        base_notional = base_quantity * current_price

        # 上限保护：单仓位 ≤ max_position_pct（在 confidence 之前）
        max_notional = equity * self._max_pos_pct
        if base_notional > max_notional:
            base_quantity = max_notional / current_price
            base_notional = max_notional

        # confidence 加权（越低越保守）
        confidence_ratio = max(self._MIN_CONFIDENCE_RATIO, signal.confidence)
        quantity = base_quantity * confidence_ratio
        notional = quantity * current_price

        # 重新计算风险
        risk_amount = quantity * risk_distance
        final_risk_pct = risk_amount / equity

        return PositionSize(
            quantity=round(quantity, 8),
            notional=round(notional, 2),
            risk_amount=round(risk_amount, 2),
            risk_pct=round(final_risk_pct, 4),
        )
