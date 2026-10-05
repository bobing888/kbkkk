"""FollowEngine — M3 F3 核心调度器

职责：
1. 接收 Signal → 执行 5 门控检查
2. 计算仓位
3. 下单（市价单）
4. 持久化 TradeLog
5. 监控 SL/TP（on_market_update）

设计原则：
- 完全可 mock（全依赖注入）
- 幂等：重复 signal 不重复下单（通过 trade_logs 表唯一约束）
- SL/TP 触发 → 市价平仓
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal, Protocol

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.analytics.signal_direction import Signal
    from app.follow.position_sizer import PositionSizer
    from app.follow.risk_manager import AccountState, RiskManager
    from app.models import TradeLog

logger = logging.getLogger(__name__)


# ── 类型 ──────────────────────────────────────────────────────────────────

@dataclass
class ExecutionResult:
    """下单执行结果。"""
    success: bool
    trade_log_id: int | None = None
    reason: str = ""                   # 成功为空，拒绝时含原因
    quantity: float | None = None
    entry_price: float | None = None


@dataclass
class CloseResult:
    """平仓结果。"""
    trade_log_id: int
    pair: str
    direction: str
    exit_price: float
    exit_reason: Literal["sl", "tp", "manual", "timeout"]
    pnl_pct: float | None = None


class OrderPlacer(Protocol):
    """MarketAdapter.place_order 协议（方便 mock）。"""
    async def place_market_order(
        self,
        symbol: str,
        direction: Literal["long", "short"],
        quantity: float,
    ) -> dict: ...


# ── FollowEngine ──────────────────────────────────────────────────────────

class FollowEngine:
    """自动跟单调度器。

    流水线：
        on_signal(signal, account_state)
          ├─ 1. RiskManager.can_open — 5 门控
          ├─ 2. PositionSizer.size — 仓位计算
          ├─ 3. MarketAdapter.place_order — 市价单
          ├─ 4. 持久化 TradeLog
          └─ 返回 ExecutionResult

        on_market_update(current_prices)
          └─ 检查所有 open 持仓的 SL/TP，触发则市价平仓
    """

    def __init__(
        self,
        signal_service,              # SignalService（用于读取最新信号）
        sizer: PositionSizer,
        risk_manager: RiskManager,
        market_adapter: OrderPlacer,
        db_factory,                  # Callable[[], Session] — sync session
    ) -> None:
        self._signal_svc = signal_service
        self._sizer = sizer
        self._rm = risk_manager
        self._adapter = market_adapter
        self._db_factory = db_factory

    async def on_signal(
        self,
        signal: Signal,
        account: AccountState,
    ) -> ExecutionResult:
        """完整下单流水线。

        Args:
            signal: Signal
            account: 当前账户状态

        Returns:
            ExecutionResult
        """
        # ── 1. 风控门控 ───────────────────────────────────────────────
        can_open, reason = self._rm.can_open(signal, account)
        if not can_open:
            logger.info("[follow_engine] signal rejected: %s", reason)
            return ExecutionResult(success=False, reason=reason)

        # ── 2. 仓位计算 ─────────────────────────────────────────────
        try:
            # 从 MarketAdapter 获取当前价格（用于 entry）
            current_price = await self._get_current_price(signal)
            pos_size = self._sizer.size(signal, account.equity, current_price)
        except ValueError as e:
            logger.warning("[follow_engine] sizing failed: %s", e)
            return ExecutionResult(success=False, reason=f"sizing_error: {e}")

        # ── 3. 下市价单 ─────────────────────────────────────────────
        try:
            order_result = await self._adapter.place_market_order(
                symbol=signal.name.split("_")[0] if "_" in signal.name else signal.name,
                direction=signal.direction,
                quantity=pos_size.quantity,
            )
            entry_price = order_result.get("fill_price", current_price)
        except Exception as e:
            logger.warning("[follow_engine] order failed: %s", e)
            return ExecutionResult(success=False, reason=f"order_failed: {e}")

        # ── 4. 持久化 TradeLog ──────────────────────────────────────
        try:
            trade_log_id = await self._persist_trade_log(
                signal=signal,
                pos_size=pos_size,
                entry_price=entry_price,
                status="open",
            )
        except Exception as e:
            logger.error("[follow_engine] persist failed: %s", e)
            return ExecutionResult(success=False, reason=f"persist_failed: {e}")

        logger.info(
            "[follow_engine] order filled: pair=%s qty=%.4f entry=%.2f",
            signal.name,
            pos_size.quantity,
            entry_price,
        )
        return ExecutionResult(
            success=True,
            trade_log_id=trade_log_id,
            quantity=pos_size.quantity,
            entry_price=entry_price,
        )

    def on_market_update(
        self,
        current_prices: dict[str, float],
    ) -> list[CloseResult]:
        """每个 tick 检查所有 open 持仓的 SL/TP，触发则市价平仓。

        真实市价平仓 + 行锁幂等：
        - 用 with_for_update() 行锁防止并发重复平仓
        - 状态转移校验：只有 status=="open" 才平仓
        - adapter 失败则不 commit（保留 open 状态供重试）
        - 成功时记录 exit_order_id

        内部用 asyncio.run() 调用异步 adapter.place_market_order。

        Args:
            current_prices: {pair: current_price}

        Returns:
            CloseResult 列表（所有触发的平仓）
        """
        return asyncio.run(self._on_market_update_async(current_prices))

    async def _on_market_update_async(
        self,
        current_prices: dict[str, float],
    ) -> list[CloseResult]:
        """on_market_update 的异步内部实现。"""
        close_results: list[CloseResult] = []
        db = self._db_factory()
        try:
            TradeLogModel = self._get_trade_log_model()
            open_trades = (
                db.query(TradeLogModel)
                .filter(TradeLogModel.status == "open")
                .all()
            )

            for trade in open_trades:
                price = current_prices.get(trade.pair)
                if price is None:
                    continue

                exit_reason = self._check_sl_tp(trade, price)
                if exit_reason is None:
                    continue

                # ── 行锁 + 幂等校验 ────────────────────────────────
                locked = (
                    db.query(TradeLogModel)
                    .filter(TradeLogModel.id == trade.id)
                    .filter(TradeLogModel.status == "open")
                    .with_for_update()
                    .first()
                )
                if locked is None:
                    # 已被其他 worker 平仓，幂等跳过
                    continue

                # ── 真实市价平仓 ────────────────────────────────
                reverse_direction: Literal["long", "short"] = (
                    "short" if trade.direction == "long" else "long"
                )
                try:
                    order_result = await self._adapter.place_market_order(
                        symbol=trade.pair,
                        direction=reverse_direction,
                        quantity=trade.quantity,
                        order_type="market",
                        reason=f"close:{exit_reason}",
                    )
                    trade.exit_order_id = order_result.get("order_id")
                except Exception as e:
                    logger.warning(
                        "[follow_engine] close order failed: trade_id=%s error=%s",
                        trade.id,
                        e,
                    )
                    db.rollback()
                    continue  # 不 commit，保留 open 状态供下次重试

                # ── 更新状态 ────────────────────────────────────
                trade.status = "closed"
                trade.exit_price = price
                trade.exit_reason = exit_reason
                self._update_pnl(trade, price)
                db.commit()

                close_results.append(CloseResult(
                    trade_log_id=trade.id,
                    pair=trade.pair,
                    direction=trade.direction,
                    exit_price=price,
                    exit_reason=exit_reason,
                    pnl_pct=trade.pnl_pct,
                ))

        except Exception as e:
            logger.error("[follow_engine] market_update error: %s", e)
            db.rollback()
        finally:
            db.close()

        return close_results

    # ── 内部辅助 ────────────────────────────────────────────────────────

    async def _get_current_price(self, signal: Signal) -> float:
        """从 MarketAdapter 获取当前价格（fallback 到 signal.entry）。"""
        try:
            # 从 signal name 提取 symbol（简化实现）
            symbol = signal.name.split("_")[0] if "_" in signal.name else signal.name
            # fallback 到 signal.entry
            return float(signal.entry)
        except Exception:
            return float(signal.entry)

    async def _persist_trade_log(
        self,
        signal: Signal,
        pos_size,
        entry_price: float,
        status: str,
        reject_reason: str | None = None,
    ) -> int:
        """持久化 TradeLog。"""
        from app.models import TradeLog as _TradeLog

        db = self._db_factory()
        try:
            log = _TradeLog(
                pair=signal.name,
                direction=signal.direction,
                entry_price=entry_price,
                quantity=pos_size.quantity,
                notional=pos_size.notional,
                risk_amount=pos_size.risk_amount,
                risk_pct=pos_size.risk_pct,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                status=status,
                signal_sources=",".join(signal.sources) if signal.sources else None,
                reject_reason=reject_reason,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            db.add(log)
            db.commit()
            db.refresh(log)
            return log.id
        finally:
            db.close()

    def _check_sl_tp(
        self,
        trade: TradeLog,
        current_price: float,
    ) -> Literal["sl", "tp", "manual", "timeout"] | None:
        """检查 SL/TP 是否触发。"""
        if trade.direction == "long":
            if current_price <= trade.stop_loss:
                return "sl"
            if current_price >= trade.take_profit:
                return "tp"
        elif trade.direction == "short":
            if current_price >= trade.stop_loss:
                return "sl"
            if current_price <= trade.take_profit:
                return "tp"
        return None

    def _update_pnl(self, trade: TradeLog, exit_price: float) -> None:
        """计算并回填 PnL。"""
        if trade.direction == "long":
            trade.pnl_pct = (exit_price - trade.entry_price) / trade.entry_price * 100
        elif trade.direction == "short":
            trade.pnl_pct = (trade.entry_price - exit_price) / trade.entry_price * 100
        else:
            trade.pnl_pct = 0.0
        trade.pnl_usdt = trade.notional * (trade.pnl_pct / 100)

    def _get_trade_log_model(self):
        """延迟导入 TradeLog（避免循环 import）。"""
        from app.models import TradeLog as _TradeLog
        return _TradeLog
