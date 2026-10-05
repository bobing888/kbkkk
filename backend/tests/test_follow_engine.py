"""FollowEngine 单元测试 — F3（M3）

12 个测试覆盖：
1. signal 通过风控 → 下单成功 → TradeLog 持久化
2. 多信号幂等
3. signal 被风控拒绝 → 返回 reject ExecutionResult
4. 仓位计算失败 → 返回 sizing_error
5. 下单失败 → 返回 order_failed
6. on_market_update：SL 触发 → 平仓
7. on_market_update：TP 触发 → 平仓
8. on_market_update：未触 → 无平仓
9. on_market_update：多持仓批量检查
10. long SL/TP 边界判断
11. short SL/TP 边界判断
12. 多持仓只平一个（其他不触）
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.analytics.signal_direction import Signal
from app.follow.follow_engine import CloseResult, ExecutionResult, FollowEngine
from app.follow.position_sizer import PositionSize, PositionSizer
from app.follow.risk_manager import AccountState, Position, RiskManager


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_sizer() -> MagicMock:
    sizer = MagicMock(spec=PositionSizer)
    sizer.size.return_value = PositionSize(
        quantity=10.0,
        notional=1000.0,
        risk_amount=10.0,
        risk_pct=0.001,
    )
    return sizer


@pytest.fixture
def mock_rm() -> MagicMock:
    rm = MagicMock(spec=RiskManager)
    rm.can_open.return_value = (True, "")
    return rm


@pytest.fixture
def mock_adapter() -> AsyncMock:
    adapter = AsyncMock()
    adapter.place_market_order.return_value = {"fill_price": 100.0, "order_id": "mock-123"}
    return adapter


# 共享的 session mock（容器方式共享状态）
_session_container: dict = {}


def _reset_session():
    _session_container["add_called"] = False
    _session_container["added_objects"] = []
    _session_container["open_trades"] = []


def _make_session_factory():
    """返回稳定的 mock session factory。"""
    def _factory():
        session = MagicMock()
        session.add = MagicMock(side_effect=lambda obj: _session_container.setdefault("added", obj))
        session.commit = MagicMock()
        # query 返回 open_trades
        query_mock = MagicMock()
        query_mock.filter_by.return_value.all.return_value = _session_container.get("open_trades", [])
        session.query.return_value = query_mock
        return session
    return _factory


@pytest.fixture(autouse=True)
def fresh_session():
    _reset_session()
    yield


@pytest.fixture
def base_signal() -> Signal:
    return Signal(
        name="BTCUSDT",
        direction="long",
        confidence=0.8,
        entry=100.0,
        stop_loss=98.0,
        take_profit=110.0,
        sources=["confluence_bullish", "hammer_bullish"],
    )


@pytest.fixture
def base_account() -> AccountState:
    return AccountState(
        equity=10000.0,
        daily_pnl_pct=0.0,
        positions=[],
    )


# ── 测试 1 & 2：正常下单流水线 ──────────────────────────────────────────

class TestOnSignalSuccess:
    @pytest.mark.asyncio
    async def test_signal_approved_orders_and_persists(
        self,
        mock_sizer: MagicMock,
        mock_rm: MagicMock,
        mock_adapter: AsyncMock,
        base_signal: Signal,
        base_account: AccountState,
    ) -> None:
        """通过风控 → 下单成功 → TradeLog 持久化"""
        engine = FollowEngine(
            signal_service=None,
            sizer=mock_sizer,
            risk_manager=mock_rm,
            market_adapter=mock_adapter,
            db_factory=_make_session_factory(),
        )

        result = await engine.on_signal(base_signal, base_account)

        assert result.success is True
        assert result.quantity == 10.0
        assert result.entry_price == 100.0

        # 验证 RiskManager 调用
        mock_rm.can_open.assert_called_once_with(base_signal, base_account)

        # 验证 PositionSizer 调用
        mock_sizer.size.assert_called_once()

        # 验证下单
        mock_adapter.place_market_order.assert_called_once()

        # 验证 TradeLog 持久化（session.add 被调用）
        assert "added" in _session_container

    @pytest.mark.asyncio
    async def test_idempotent_rejected_by_risk(
        self,
        mock_sizer: MagicMock,
        mock_rm: MagicMock,
        mock_adapter: AsyncMock,
        base_signal: Signal,
        base_account: AccountState,
    ) -> None:
        """重复 signal：风控拒绝（同方向已有持仓超限）"""
        mock_rm.can_open.return_value = (False, "max_positions: 3 >= 3")

        engine = FollowEngine(
            signal_service=None,
            sizer=mock_sizer,
            risk_manager=mock_rm,
            market_adapter=mock_adapter,
            db_factory=_make_session_factory(),
        )

        result = await engine.on_signal(base_signal, base_account)

        assert result.success is False
        assert "max_positions" in result.reason
        # 幂等：不下单
        mock_adapter.place_market_order.assert_not_called()


# ── 测试 3 & 4 & 5：失败路径 ─────────────────────────────────────────────

class TestOnSignalFailure:
    @pytest.mark.asyncio
    async def test_rejected_by_risk_manager(
        self,
        mock_sizer: MagicMock,
        mock_adapter: AsyncMock,
        base_signal: Signal,
        base_account: AccountState,
    ) -> None:
        """风控拒绝 → 不下单"""
        rm = MagicMock(spec=RiskManager)
        rm.can_open.return_value = (False, "low_confidence: 0.3 < 0.5")

        engine = FollowEngine(
            signal_service=None,
            sizer=mock_sizer,
            risk_manager=rm,
            market_adapter=mock_adapter,
            db_factory=_make_session_factory(),
        )

        result = await engine.on_signal(base_signal, base_account)

        assert result.success is False
        assert "low_confidence" in result.reason
        assert result.trade_log_id is None
        mock_sizer.size.assert_not_called()
        mock_adapter.place_market_order.assert_not_called()

    @pytest.mark.asyncio
    async def test_sizing_fails_returns_error(
        self,
        mock_rm: MagicMock,
        mock_adapter: AsyncMock,
        base_signal: Signal,
        base_account: AccountState,
    ) -> None:
        """仓位计算抛异常 → 返回 sizing_error"""
        sizer = MagicMock(spec=PositionSizer)
        sizer.size.side_effect = ValueError("Invalid stop_loss")

        engine = FollowEngine(
            signal_service=None,
            sizer=sizer,
            risk_manager=mock_rm,
            market_adapter=mock_adapter,
            db_factory=_make_session_factory(),
        )

        result = await engine.on_signal(base_signal, base_account)

        assert result.success is False
        assert "sizing_error" in result.reason

    @pytest.mark.asyncio
    async def test_order_fails_returns_error(
        self,
        mock_sizer: MagicMock,
        mock_rm: MagicMock,
        base_signal: Signal,
        base_account: AccountState,
    ) -> None:
        """下单失败 → 返回 order_failed"""
        adapter = AsyncMock()
        adapter.place_market_order.side_effect = Exception("network timeout")

        engine = FollowEngine(
            signal_service=None,
            sizer=mock_sizer,
            risk_manager=mock_rm,
            market_adapter=adapter,
            db_factory=_make_session_factory(),
        )

        result = await engine.on_signal(base_signal, base_account)

        assert result.success is False
        assert "order_failed" in result.reason


# ── 测试 6 & 7 & 8：on_market_update ─────────────────────────────────────

def _make_engine_for_market_update(open_trades: list) -> FollowEngine:
    """为 market_update 测试构造 engine（新版：filter() + with_for_update）。

    关键：filter() 返回自身（与 SQLAlchemy 一致），所有链式调用共享同一对象。
    """
    def _factory():
        session = MagicMock()
        query_chain = MagicMock()
        # 让 filter() 返回自身（与 SQLAlchemy 一致）
        query_chain.filter.return_value = query_chain
        # 第一次调用：query(...).filter(...).all() → open_trades
        query_chain.all.return_value = open_trades
        # 第二次调用：query(...).filter(...).filter(...).with_for_update().first() → first trade
        query_chain.with_for_update.return_value.first.return_value = (
            open_trades[0] if open_trades else None
        )
        session.query.return_value = query_chain
        session.commit = MagicMock()
        return session
    return FollowEngine(
        signal_service=None,
        sizer=MagicMock(),
        risk_manager=MagicMock(),
        market_adapter=AsyncMock(),
        db_factory=_factory,
    )


def _make_engine_for_close(
    trade: MagicMock,
    adapter: AsyncMock,
) -> FollowEngine:
    """为平仓测试构造 engine（含 with_for_update 行锁 mock）。

    新的 on_market_update 用：
        db.query(TradeLogModel).filter(...).filter(...).with_for_update().first()
    filter() 返回自身，所有链式调用共享同一对象。
    all() 返回 [trade]（让 for 循环处理 trade）。
    with_for_update().first() 行为：
    - trade.status == "open" → 返回 trade（允许平仓）
    - trade.status == "closed" → 返回 None（幂等跳过）
    """
    # 用 list 包裹实现 nonlocal 效果（Python 3.14 闭包限制）
    state = {"returned_closed": False}

    def _factory():
        session = MagicMock()
        query_chain = MagicMock()
        query_chain.filter.return_value = query_chain
        query_chain.all.return_value = [trade]

        def _wfu_first():
            if state["returned_closed"]:
                return None
            return trade

        query_chain.with_for_update.return_value.first.side_effect = _wfu_first
        session.query.return_value = query_chain
        session.commit = MagicMock()
        session.rollback = MagicMock()
        return session

    engine = FollowEngine(
        signal_service=None,
        sizer=MagicMock(),
        risk_manager=MagicMock(),
        market_adapter=adapter,
        db_factory=_factory,
    )
    # 将 state 绑定到 engine 上，供测试层控制幂等行为
    engine._close_test_state = state
    return engine


class TestOnMarketUpdate:
    def test_sl_triggers_close(self) -> None:
        """long 持仓：价格跌至 SL → 触发平仓"""
        mock_trade = MagicMock()
        mock_trade.id = 1
        mock_trade.pair = "BTCUSDT"
        mock_trade.direction = "long"
        mock_trade.entry_price = 100.0
        mock_trade.stop_loss = 98.0
        mock_trade.take_profit = 110.0
        mock_trade.notional = 1000.0
        mock_trade.quantity = 10.0

        engine = _make_engine_for_market_update([mock_trade])

        # 价格跌至 97（< SL=98）
        results = engine.on_market_update({"BTCUSDT": 97.0})

        assert len(results) == 1
        assert results[0].exit_reason == "sl"
        assert results[0].exit_price == 97.0

    def test_tp_triggers_close(self) -> None:
        """long 持仓：价格上涨至 TP → 触发平仓"""
        mock_trade = MagicMock()
        mock_trade.id = 2
        mock_trade.pair = "ETHUSDT"
        mock_trade.direction = "long"
        mock_trade.entry_price = 100.0
        mock_trade.stop_loss = 98.0
        mock_trade.take_profit = 110.0
        mock_trade.notional = 1000.0
        mock_trade.quantity = 10.0

        engine = _make_engine_for_market_update([mock_trade])

        # 价格涨至 111（> TP=110）
        results = engine.on_market_update({"ETHUSDT": 111.0})

        assert len(results) == 1
        assert results[0].exit_reason == "tp"

    def test_no_trigger_returns_empty(self) -> None:
        """价格未触 SL/TP → 无平仓"""
        mock_trade = MagicMock()
        mock_trade.id = 3
        mock_trade.pair = "BTCUSDT"
        mock_trade.direction = "long"
        mock_trade.entry_price = 100.0
        mock_trade.stop_loss = 98.0
        mock_trade.take_profit = 110.0
        mock_trade.notional = 1000.0
        mock_trade.quantity = 10.0

        engine = _make_engine_for_market_update([mock_trade])

        # 价格在 SL 和 TP 之间
        results = engine.on_market_update({"BTCUSDT": 105.0})

        assert len(results) == 0

    def test_multiple_positions_batch_check(self) -> None:
        """多持仓批量检查"""
        trade1 = MagicMock()
        trade1.id = 1
        trade1.pair = "BTCUSDT"
        trade1.direction = "long"
        trade1.entry_price = 100.0
        trade1.stop_loss = 98.0
        trade1.take_profit = 110.0
        trade1.notional = 1000.0
        trade1.quantity = 10.0

        trade2 = MagicMock()
        trade2.id = 2
        trade2.pair = "ETHUSDT"
        trade2.direction = "short"
        trade2.entry_price = 100.0
        trade2.stop_loss = 102.0
        trade2.take_profit = 90.0
        trade2.notional = 1000.0
        trade2.quantity = 10.0

        engine = _make_engine_for_market_update([trade1, trade2])

        # BTC SL 触发，ETH 未触
        results = engine.on_market_update({"BTCUSDT": 97.0, "ETHUSDT": 100.0})

        assert len(results) == 1
        assert results[0].pair == "BTCUSDT"
        assert results[0].exit_reason == "sl"


# ── 测试 9 & 10 & 11：SL/TP 边界 ────────────────────────────────────────

class TestSLTPBoundary:
    def test_long_sl_boundary(self) -> None:
        """long: price <= stop_loss → SL"""
        trade = MagicMock()
        trade.direction = "long"
        trade.stop_loss = 98.0
        trade.take_profit = 110.0

        engine = FollowEngine(None, MagicMock(), MagicMock(), MagicMock(), MagicMock())

        assert engine._check_sl_tp(trade, 98.0) == "sl"
        assert engine._check_sl_tp(trade, 97.99) == "sl"
        assert engine._check_sl_tp(trade, 98.01) is None

    def test_long_tp_boundary(self) -> None:
        """long: price >= take_profit → TP"""
        trade = MagicMock()
        trade.direction = "long"
        trade.stop_loss = 98.0
        trade.take_profit = 110.0

        engine = FollowEngine(None, MagicMock(), MagicMock(), MagicMock(), MagicMock())

        assert engine._check_sl_tp(trade, 110.0) == "tp"
        assert engine._check_sl_tp(trade, 110.01) == "tp"
        assert engine._check_sl_tp(trade, 109.99) is None

    def test_short_sl_boundary(self) -> None:
        """short: price >= stop_loss → SL"""
        trade = MagicMock()
        trade.direction = "short"
        trade.stop_loss = 102.0
        trade.take_profit = 90.0

        engine = FollowEngine(None, MagicMock(), MagicMock(), MagicMock(), MagicMock())

        assert engine._check_sl_tp(trade, 102.0) == "sl"
        assert engine._check_sl_tp(trade, 102.01) == "sl"
        assert engine._check_sl_tp(trade, 101.99) is None

    def test_short_tp_boundary(self) -> None:
        """short: price <= take_profit → TP"""
        trade = MagicMock()
        trade.direction = "short"
        trade.stop_loss = 102.0
        trade.take_profit = 90.0

        engine = FollowEngine(None, MagicMock(), MagicMock(), MagicMock(), MagicMock())

        assert engine._check_sl_tp(trade, 90.0) == "tp"
        assert engine._check_sl_tp(trade, 89.99) == "tp"
        assert engine._check_sl_tp(trade, 90.01) is None


# ── 测试 12：多持仓只平一个 ─────────────────────────────────────────────

class TestMultiplePositions:
    def test_only_triggered_position_closed(self) -> None:
        """多持仓中只有 1 个触 SL → 只平 1 个"""
        trade_hit = MagicMock()
        trade_hit.id = 1
        trade_hit.pair = "BTCUSDT"
        trade_hit.direction = "long"
        trade_hit.entry_price = 100.0
        trade_hit.stop_loss = 98.0
        trade_hit.take_profit = 110.0
        trade_hit.notional = 1000.0
        trade_hit.quantity = 10.0

        trade_miss = MagicMock()
        trade_miss.id = 2
        trade_miss.pair = "ETHUSDT"
        trade_miss.direction = "long"
        trade_miss.entry_price = 100.0
        trade_miss.stop_loss = 98.0
        trade_miss.take_profit = 110.0
        trade_miss.notional = 1000.0
        trade_miss.quantity = 10.0

        engine = _make_engine_for_market_update([trade_hit, trade_miss])

        # BTC SL 触发，ETH 未触
        results = engine.on_market_update({"BTCUSDT": 97.0, "ETHUSDT": 105.0})

        assert len(results) == 1
        assert results[0].trade_log_id == 1


# ── 测试 13-17：C2 真实市价平仓 + 行锁幂等 ─────────────────────────────

class TestOnMarketUpdateClosePosition:
    """C2: follow_engine.on_market_update 必须真实市价平仓 + 行锁幂等"""

    def test_close_open_position_calls_market_adapter_with_reverse_direction(self) -> None:
        """SL/TP 触发 → 调用 adapter.place_market_order，反向平仓"""
        mock_trade = MagicMock()
        mock_trade.id = 1
        mock_trade.pair = "BTCUSDT"
        mock_trade.direction = "long"
        mock_trade.entry_price = 100.0
        mock_trade.stop_loss = 98.0
        mock_trade.take_profit = 110.0
        mock_trade.notional = 1000.0
        mock_trade.quantity = 10.0
        mock_trade.status = "open"

        mock_adapter = AsyncMock()
        mock_adapter.place_market_order.return_value = {
            "fill_price": 97.0,
            "order_id": "exit-123",
        }

        engine = _make_engine_for_close(mock_trade, mock_adapter)
        results = engine.on_market_update({"BTCUSDT": 97.0})

        # 验证：adapter 被调用，方向反向（long → short）
        mock_adapter.place_market_order.assert_called_once()
        call_kwargs = mock_adapter.place_market_order.call_args.kwargs
        assert call_kwargs["direction"] == "short", "long 持仓应平 short 方向"
        assert call_kwargs["quantity"] == 10.0

        # 验证：平仓结果
        assert len(results) == 1
        assert results[0].exit_reason == "sl"

    def test_close_failed_does_not_commit(self) -> None:
        """adapter.place_market_order 失败 → 不 commit DB，保留 open 状态"""
        mock_trade = MagicMock()
        mock_trade.id = 2
        mock_trade.pair = "ETHUSDT"
        mock_trade.direction = "long"
        mock_trade.entry_price = 100.0
        mock_trade.stop_loss = 98.0
        mock_trade.take_profit = 110.0
        mock_trade.notional = 1000.0
        mock_trade.quantity = 10.0
        mock_trade.status = "open"

        mock_adapter = AsyncMock()
        mock_adapter.place_market_order.side_effect = RuntimeError("network error")

        engine = _make_engine_for_close(mock_trade, mock_adapter)
        results = engine.on_market_update({"ETHUSDT": 97.0})

        # 验证：adapter 被调用
        mock_adapter.place_market_order.assert_called_once()
        # 验证：无平仓结果（失败）
        assert len(results) == 0
        # 验证：trade 状态仍为 open（失败不 commit）
        assert mock_trade.status == "open"

    def test_close_already_closed_skipped(self) -> None:
        """已 closed 状态不应再次平仓（幂等）"""
        mock_trade = MagicMock()
        mock_trade.id = 3
        mock_trade.pair = "BTCUSDT"
        mock_trade.direction = "long"
        mock_trade.entry_price = 100.0
        mock_trade.stop_loss = 98.0
        mock_trade.take_profit = 110.0
        mock_trade.notional = 1000.0
        mock_trade.quantity = 10.0
        mock_trade.status = "closed"  # 已关闭 → 幂等跳过

        mock_adapter = AsyncMock()
        engine = _make_engine_for_close(mock_trade, mock_adapter)
        # 初始状态 returned_closed=True → lock 返回 None，幂等跳过
        engine._close_test_state["returned_closed"] = True
        results = engine.on_market_update({"BTCUSDT": 97.0})

        # 验证：未调用 adapter（幂等跳过）
        mock_adapter.place_market_order.assert_not_called()
        assert len(results) == 0

    def test_concurrent_close_protected_by_row_lock(self) -> None:
        """并发平仓：with_for_update 行锁防止重复平仓。

        场景：第二个 worker 同时检查同一持仓 → lock 冲突（返回 None）→ 幂等跳过。
        验证：with_for_update() 被调用（行锁保护机制存在）。
        """
        mock_trade = MagicMock()
        mock_trade.id = 4
        mock_trade.pair = "BTCUSDT"
        mock_trade.direction = "long"
        mock_trade.entry_price = 100.0
        mock_trade.stop_loss = 98.0
        mock_trade.take_profit = 110.0
        mock_trade.notional = 1000.0
        mock_trade.quantity = 10.0
        mock_trade.status = "open"

        adapter_called = False

        def _on_adapter(*args, **kwargs):
            nonlocal adapter_called
            adapter_called = True
            return {"fill_price": 97.0, "order_id": "exit-1"}

        mock_adapter = AsyncMock()
        mock_adapter.place_market_order.side_effect = _on_adapter

        wfu_called = False

        def _factory():
            session = MagicMock()
            query_chain = MagicMock()
            query_chain.filter.return_value = query_chain
            query_chain.all.return_value = [mock_trade]

            def _wfu_first():
                nonlocal wfu_called
                wfu_called = True
                # lock 失败（并发冲突），幂等跳过
                return None

            query_chain.with_for_update.return_value.first.side_effect = _wfu_first
            session.query.return_value = query_chain
            session.commit = MagicMock()
            return session

        engine = FollowEngine(
            signal_service=None,
            sizer=MagicMock(),
            risk_manager=MagicMock(),
            market_adapter=mock_adapter,
            db_factory=_factory,
        )

        # lock 冲突 → 不平仓，不调用 adapter
        results = engine.on_market_update({"BTCUSDT": 97.0})
        assert len(results) == 0, "lock conflict should skip close"
        assert not adapter_called, "adapter should NOT be called when lock fails"
        assert wfu_called, "with_for_update must be called for row lock"

    def test_close_persists_exit_order_id(self) -> None:
        """平仓成功后，exit_order_id 必须记录在 trade 上"""
        mock_trade = MagicMock()
        mock_trade.id = 5
        mock_trade.pair = "BTCUSDT"
        mock_trade.direction = "long"
        mock_trade.entry_price = 100.0
        mock_trade.stop_loss = 98.0
        mock_trade.take_profit = 110.0
        mock_trade.notional = 1000.0
        mock_trade.quantity = 10.0
        mock_trade.status = "open"
        mock_trade.exit_order_id = None  # 初始为空

        mock_adapter = AsyncMock()
        mock_adapter.place_market_order.return_value = {
            "fill_price": 97.0,
            "order_id": "exit-456",
        }

        engine = _make_engine_for_close(mock_trade, mock_adapter)
        results = engine.on_market_update({"BTCUSDT": 97.0})

        assert len(results) == 1
        # 验证：exit_order_id 被记录
        assert mock_trade.exit_order_id == "exit-456"
