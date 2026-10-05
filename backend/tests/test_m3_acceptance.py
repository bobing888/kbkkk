"""M3 业务验收测试 — F5

5 个端到端业务测试（完全 mock，模拟真实场景）：

1. test_full_signal_to_trade_pipeline    — Signal → Risk → Size → Order → TradeLog
2. test_daily_loss_limit_blocks_trades   — 连续亏损 2% 后拒接
3. test_concurrent_position_limit        — 满 3 仓位后拒接
4. test_sl_tp_auto_close                — SL 触发自动平仓
5. test_confidence_below_threshold       — confidence < 0.5 拒接
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.analytics.signal_direction import Signal
from app.follow.follow_engine import ExecutionResult, FollowEngine
from app.follow.position_sizer import PositionSizer
from app.follow.risk_manager import AccountState, Position, RiskManager


# ── 场景 1：端到端流水线 ────────────────────────────────────────────────

class TestFullPipeline:
    @pytest.mark.asyncio
    async def test_full_signal_to_trade_pipeline(self) -> None:
        """Signal → RiskManager → PositionSizer → Order → TradeLog 全链路"""
        # 构造真实组件（无 mock）
        sizer = PositionSizer(max_position_pct=0.05, max_risk_per_trade_pct=0.01)
        rm = RiskManager(
            max_daily_loss_pct=0.02,
            max_concurrent_positions=3,
            max_correlation_exposure=0.10,
        )
        adapter = AsyncMock()
        adapter.place_market_order.return_value = {"fill_price": 100.0}

        trade_container = {}
        def _factory():
            session = MagicMock()
            session.add = MagicMock(side_effect=lambda obj: trade_container.setdefault("log", obj))
            session.commit = MagicMock()
            return session
        session_factory = _factory

        engine = FollowEngine(
            signal_service=None,
            sizer=sizer,
            risk_manager=rm,
            market_adapter=adapter,
            db_factory=session_factory,
        )

        signal = Signal(
            name="BTCUSDT",
            direction="long",
            confidence=0.8,
            entry=100.0,
            stop_loss=98.0,
            take_profit=110.0,
            sources=["confluence_bullish", "hammer_bullish"],
        )
        account = AccountState(
            equity=10000.0,
            daily_pnl_pct=0.0,
            positions=[],
        )

        result = await engine.on_signal(signal, account)

        # 断言
        assert result.success is True
        assert result.quantity is not None
        assert result.entry_price is not None
        assert trade_container.get("log") is not None


# ── 场景 2：单日亏损 2% 阻断 ─────────────────────────────────────────────

class TestDailyLossLimit:
    @pytest.mark.asyncio
    async def test_daily_loss_limit_blocks_new_trades(self) -> None:
        """连续亏损达到 2% 后，新 signal 被 RiskManager 拒绝"""
        rm = RiskManager(
            max_daily_loss_pct=0.02,
            max_concurrent_positions=3,
            max_correlation_exposure=0.10,
        )

        # 当日已亏损 2.1%
        account = AccountState(
            equity=10000.0,
            daily_pnl_pct=-0.021,
            positions=[],
        )
        signal = Signal(
            name="ETHUSDT",
            direction="long",
            confidence=0.8,
            entry=100.0,
            stop_loss=98.0,
            take_profit=110.0,
            sources=["confluence_bullish"],
        )

        can_open, reason = rm.can_open(signal, account)

        assert can_open is False
        assert "daily_loss_limit" in reason
        assert "-2.10%" in reason

    @pytest.mark.asyncio
    async def test_daily_loss_just_under_limit_passes(self) -> None:
        """亏损 1.99% < 2% → 通过"""
        rm = RiskManager(
            max_daily_loss_pct=0.02,
            max_concurrent_positions=3,
            max_correlation_exposure=0.10,
        )
        account = AccountState(
            equity=10000.0,
            daily_pnl_pct=-0.0199,
            positions=[],
        )
        signal = Signal(
            name="ETHUSDT",
            direction="long",
            confidence=0.8,
            entry=100.0,
            stop_loss=98.0,
            take_profit=110.0,
            sources=["confluence_bullish"],
        )
        can_open, reason = rm.can_open(signal, account)
        assert can_open is True


# ── 场景 3：持仓上限 3 笔 ────────────────────────────────────────────────

class TestPositionLimit:
    @pytest.mark.asyncio
    async def test_concurrent_position_limit(self) -> None:
        """持仓满 3 笔后，新 signal 被拒绝"""
        rm = RiskManager(
            max_daily_loss_pct=0.02,
            max_concurrent_positions=3,
            max_correlation_exposure=0.10,
        )

        # 已有 3 笔持仓
        positions = [
            Position(
                symbol=f"BTC{i}/USDT",
                direction="long",
                notional=100.0,
                entry_price=100.0,
                stop_loss=98.0,
            )
            for i in range(3)
        ]
        account = AccountState(
            equity=10000.0,
            daily_pnl_pct=0.0,
            positions=positions,
        )
        signal = Signal(
            name="DOGEUSDT",
            direction="long",
            confidence=0.8,
            entry=100.0,
            stop_loss=98.0,
            take_profit=110.0,
            sources=["confluence_bullish"],
        )

        can_open, reason = rm.can_open(signal, account)

        assert can_open is False
        assert "max_positions" in reason

    @pytest.mark.asyncio
    async def test_two_positions_still_opens(self) -> None:
        """持仓 2 笔 → 第 3 笔仍可开"""
        rm = RiskManager(
            max_daily_loss_pct=0.02,
            max_concurrent_positions=3,
            max_correlation_exposure=0.10,
        )
        positions = [
            Position(
                symbol=f"BTC{i}/USDT",
                direction="long",
                notional=100.0,
                entry_price=100.0,
                stop_loss=98.0,
            )
            for i in range(2)
        ]
        account = AccountState(
            equity=10000.0,
            daily_pnl_pct=0.0,
            positions=positions,
        )
        signal = Signal(
            name="DOGEUSDT",
            direction="long",
            confidence=0.8,
            entry=100.0,
            stop_loss=98.0,
            take_profit=110.0,
            sources=["confluence_bullish"],
        )
        can_open, reason = rm.can_open(signal, account)
        assert can_open is True


# ── 场景 4：SL/TP 自动平仓 ────────────────────────────────────────────────

class TestSLTPAutoClose:
    def test_sl_auto_close_long(self) -> None:
        """long 持仓触及 SL → 市价平仓"""
        sizer = PositionSizer(max_position_pct=0.05, max_risk_per_trade_pct=0.01)
        rm = RiskManager(
            max_daily_loss_pct=0.02,
            max_concurrent_positions=3,
            max_correlation_exposure=0.10,
        )

        mock_trade = MagicMock()
        mock_trade.id = 1
        mock_trade.pair = "BTCUSDT"
        mock_trade.direction = "long"
        mock_trade.entry_price = 100.0
        mock_trade.stop_loss = 98.0
        mock_trade.take_profit = 110.0
        mock_trade.notional = 500.0
        mock_trade.quantity = 5.0

        def _factory():
            session = MagicMock()
            q = MagicMock()
            q.filter.return_value.all.return_value = [mock_trade]
            q.filter.return_value.filter.return_value.with_for_update.return_value.first.return_value = mock_trade
            session.query.return_value = q
            session.commit = MagicMock()
            return session

        engine = FollowEngine(
            signal_service=None,
            sizer=sizer,
            risk_manager=rm,
            market_adapter=AsyncMock(),
            db_factory=_factory,
        )

        # 模拟当前价格跌至 97（< SL 98）
        results = engine.on_market_update({"BTCUSDT": 97.0})

        assert len(results) == 1
        assert results[0].exit_reason == "sl"
        assert results[0].exit_price == 97.0

    def test_tp_auto_close_long(self) -> None:
        """long 持仓触及 TP → 市价平仓"""
        sizer = PositionSizer(max_position_pct=0.05, max_risk_per_trade_pct=0.01)
        rm = RiskManager(
            max_daily_loss_pct=0.02,
            max_concurrent_positions=3,
            max_correlation_exposure=0.10,
        )

        mock_trade = MagicMock()
        mock_trade.id = 2
        mock_trade.pair = "ETHUSDT"
        mock_trade.direction = "long"
        mock_trade.entry_price = 100.0
        mock_trade.stop_loss = 98.0
        mock_trade.take_profit = 110.0
        mock_trade.notional = 500.0
        mock_trade.quantity = 5.0

        def _factory():
            session = MagicMock()
            q = MagicMock()
            q.filter.return_value.all.return_value = [mock_trade]
            q.filter.return_value.filter.return_value.with_for_update.return_value.first.return_value = mock_trade
            session.query.return_value = q
            session.commit = MagicMock()
            return session

        engine = FollowEngine(
            signal_service=None,
            sizer=sizer,
            risk_manager=rm,
            market_adapter=AsyncMock(),
            db_factory=_factory,
        )

        # 模拟当前价格涨至 111（> TP 110）
        results = engine.on_market_update({"ETHUSDT": 111.0})

        assert len(results) == 1
        assert results[0].exit_reason == "tp"
        assert results[0].exit_price == 111.0


# ── 场景 5：confidence 过滤 ────────────────────────────────────────────────

class TestConfidenceFilter:
    @pytest.mark.asyncio
    async def test_confidence_below_threshold_filtered(self) -> None:
        """confidence < 0.5 → 被 RiskManager 拒绝"""
        rm = RiskManager(
            max_daily_loss_pct=0.02,
            max_concurrent_positions=3,
            max_correlation_exposure=0.10,
        )
        account = AccountState(
            equity=10000.0,
            daily_pnl_pct=0.0,
            positions=[],
        )

        # confidence = 0.49（低于 0.5 阈值）
        signal = Signal(
            name="SHIBUSDT",
            direction="long",
            confidence=0.49,
            entry=100.0,
            stop_loss=98.0,
            take_profit=110.0,
            sources=["confluence_bullish"],
        )

        can_open, reason = rm.can_open(signal, account)

        assert can_open is False
        assert "low_confidence" in reason
        assert "0.49" in reason

    @pytest.mark.asyncio
    async def test_confidence_at_threshold_passes(self) -> None:
        """confidence = 0.5 → 通过"""
        rm = RiskManager(
            max_daily_loss_pct=0.02,
            max_concurrent_positions=3,
            max_correlation_exposure=0.10,
        )
        account = AccountState(
            equity=10000.0,
            daily_pnl_pct=0.0,
            positions=[],
        )
        signal = Signal(
            name="SHIBUSDT",
            direction="long",
            confidence=0.5,
            entry=100.0,
            stop_loss=98.0,
            take_profit=110.0,
            sources=["confluence_bullish"],
        )
        can_open, reason = rm.can_open(signal, account)
        assert can_open is True
