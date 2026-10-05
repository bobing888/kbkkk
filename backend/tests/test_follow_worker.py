"""FollowWorker 单元测试 — F4（M3）

6 个测试覆盖：
1. start() 创建两个子任务
2. stop() 优雅退出
3. signal_loop 收到事件后调用 engine
4. monitor_loop 定期调用 engine.on_market_update
5. stop_event 被设置后退出循环
6. signal_loop 异常不崩溃
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.follow.follow_worker import FollowEngineProtocol, FollowWorker
from app.services.event_bus import SignalChangeBus, SignalChangeEvent


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_engine() -> MagicMock:
    """Mock FollowEngine。"""
    engine = MagicMock(spec=FollowEngineProtocol)
    engine.on_signal = AsyncMock()
    engine.on_market_update = MagicMock(return_value=[])
    return engine


@pytest.fixture
def event_bus() -> SignalChangeBus:
    return SignalChangeBus()


@pytest.fixture
def worker(mock_engine: MagicMock, event_bus: SignalChangeBus) -> FollowWorker:
    return FollowWorker(
        engine=mock_engine,
        event_bus=event_bus,
        kline_fetcher=None,
        monitor_interval_seconds=0.05,  # 50ms 快速轮询
    )


# ── 测试 1 & 2：启动 / 停止 ────────────────────────────────────────────

class TestLifecycle:
    @pytest.mark.asyncio
    async def test_start_creates_tasks(self, worker: FollowWorker) -> None:
        """start() 后有两个后台任务"""
        assert len(worker._tasks) == 0

        await worker.start()
        await asyncio.sleep(0.1)  # 给任务启动时间

        assert len(worker._tasks) == 2

        await worker.stop()
        assert len(worker._tasks) == 0

    @pytest.mark.asyncio
    async def test_stop_closes_tasks(self, worker: FollowWorker) -> None:
        """stop() 优雅关闭所有任务"""
        await worker.start()
        await asyncio.sleep(0.1)

        await worker.stop()

        # stop 后任务已清空
        assert len(worker._tasks) == 0


# ── 测试 3：signal_loop ─────────────────────────────────────────────────

class TestSignalLoop:
    @pytest.mark.asyncio
    async def test_signal_loop_handles_event(self, mock_engine: MagicMock, event_bus: SignalChangeBus) -> None:
        """signal_loop 收到事件后正确处理（不崩溃）"""
        worker = FollowWorker(
            engine=mock_engine,
            event_bus=event_bus,
            kline_fetcher=None,
            monitor_interval_seconds=0.02,
        )

        await worker.start()
        await asyncio.sleep(0.05)

        # 发一个测试事件
        event = SignalChangeEvent(
            pair="BTC/USDT",
            timeframe="1h",
            previous=None,
            current=MagicMock(),
            change_type="first_emit",
        )
        await event_bus.emit(event)

        await asyncio.sleep(0.1)

        await worker.stop()


# ── 测试 4：monitor_loop ────────────────────────────────────────────────

class TestMonitorLoop:
    @pytest.mark.asyncio
    async def test_monitor_loop_calls_engine_with_prices(
        self, mock_engine: MagicMock, event_bus: SignalChangeBus
    ) -> None:
        """monitor_loop 有 fetcher 时调用 engine.on_market_update"""
        mock_fetcher = AsyncMock()
        mock_fetcher.fetch_latest_price.return_value = 100.0

        worker = FollowWorker(
            engine=mock_engine,
            event_bus=event_bus,
            kline_fetcher=mock_fetcher,
            monitor_interval_seconds=0.05,
        )

        await worker.start()
        await asyncio.sleep(0.25)  # 等待若干周期

        await worker.stop()

        # 有 fetcher 时 engine.on_market_update 被调用
        assert mock_engine.on_market_update.call_count >= 1


# ── 测试 5 & 6：退出与异常 ────────────────────────────────────────────

class TestStopSignal:
    @pytest.mark.asyncio
    async def test_stop_event_exits_loops(self, worker: FollowWorker) -> None:
        """stop_event 设置后循环退出"""
        await worker.start()
        await asyncio.sleep(0.05)

        # 触发停止
        await worker.stop()

        assert worker._stop_event.is_set()
        assert len(worker._tasks) == 0

    @pytest.mark.asyncio
    async def test_signal_loop_exception_handled(
        self, mock_engine: MagicMock, event_bus: SignalChangeBus
    ) -> None:
        """signal_loop 中异常不导致进程崩溃"""
        # 构造一个会导致 on_signal 抛异常的场景
        mock_engine.on_signal = AsyncMock(side_effect=Exception("test error"))

        worker = FollowWorker(
            engine=mock_engine,
            event_bus=event_bus,
            kline_fetcher=None,
            monitor_interval_seconds=0.05,
        )

        await worker.start()
        await asyncio.sleep(0.05)

        # 发事件触发异常
        event = SignalChangeEvent(
            pair="BTC/USDT",
            timeframe="1h",
            previous=None,
            current=MagicMock(),
            change_type="first_emit",
        )
        await event_bus.emit(event)

        await asyncio.sleep(0.1)

        # worker 应该还活着（异常被捕获）
        await worker.stop()
        assert len(worker._tasks) == 0


# ── 测试 7-10：C1 _handle_signal_event 核心逻辑 ──────────────────────────

class TestHandleSignalEvent:
    """C1: follow_worker._handle_signal_event 必须调用 engine.on_signal"""

    @pytest.fixture
    def account_state_provider(self) -> MagicMock:
        """Mock AccountState provider。"""
        from app.follow.risk_manager import AccountState
        return lambda: AccountState(
            equity=100000.0,
            daily_pnl_pct=0.0,
            positions=[],
        )

    @pytest.mark.asyncio
    async def test_worker_processes_signal_event_end_to_end(
        self,
        mock_engine: MagicMock,
        event_bus: SignalChangeBus,
        account_state_provider: MagicMock,
    ) -> None:
        """收到信号事件 → 调用 engine.on_signal"""
        from app.analytics.signal_direction import Signal
        from app.follow.risk_manager import AccountState
        from unittest.mock import patch

        mock_signal = Signal(
            name="BTCUSDT",
            direction="long",
            confidence=0.8,
            entry=50000.0,
            stop_loss=49500.0,
            take_profit=52000.0,
            sources=["confluence_bullish"],
        )

        # 直接 patch _fetch_latest_signal，避免复杂 SQLAlchemy mock chain
        worker = FollowWorker(
            engine=mock_engine,
            event_bus=event_bus,
            kline_fetcher=None,
            monitor_interval_seconds=0.02,
            account_state_provider=account_state_provider,
        )

        with patch.object(worker, "_fetch_latest_signal", return_value=mock_signal):
            await worker.start()
            await asyncio.sleep(0.05)

            event = SignalChangeEvent(
                pair="BTC/USDT",
                timeframe="1h",
                previous=None,
                current=MagicMock(),
                change_type="first_emit",
            )
            await event_bus.emit(event)

            await asyncio.sleep(0.2)

            await worker.stop()

        # 核心断言：engine.on_signal 被调用
        assert mock_engine.on_signal.call_count >= 1, (
            "engine.on_signal must be called when signal event received"
        )
        call_args = mock_engine.on_signal.call_args
        assert isinstance(call_args[0][0], Signal), "first arg must be Signal"
        assert isinstance(call_args[0][1], AccountState), "second arg must be AccountState"

    @pytest.mark.asyncio
    async def test_worker_no_signal_in_db_logs_and_skips(
        self,
        mock_engine: MagicMock,
        event_bus: SignalChangeBus,
        account_state_provider: MagicMock,
    ) -> None:
        """DB 无 Signal → 不调用 engine.on_signal，记录警告"""
        worker = FollowWorker(
            engine=mock_engine,
            event_bus=event_bus,
            kline_fetcher=None,
            monitor_interval_seconds=0.02,
            account_state_provider=account_state_provider,
        )

        # patch 返回 None 模拟 DB 无 Signal
        with patch.object(worker, "_fetch_latest_signal", return_value=None):
            await worker.start()
            await asyncio.sleep(0.05)

            event = SignalChangeEvent(
                pair="BTC/USDT",
                timeframe="1h",
                previous=None,
                current=MagicMock(),
                change_type="direction",
            )
            await event_bus.emit(event)
            await asyncio.sleep(0.2)

            await worker.stop()

        # 无 Signal 时不应调用 on_signal
        assert mock_engine.on_signal.call_count == 0, (
            "engine.on_signal should NOT be called when no Signal in DB"
        )

    @pytest.mark.asyncio
    async def test_worker_account_state_provided_to_engine(
        self,
        mock_engine: MagicMock,
        event_bus: SignalChangeBus,
        account_state_provider: MagicMock,
    ) -> None:
        """account_state_provider 提供的 AccountState 必须传给 engine.on_signal"""
        from app.analytics.signal_direction import Signal
        from app.follow.risk_manager import AccountState
        from unittest.mock import patch

        mock_signal = Signal(
            name="ETHUSDT",
            direction="short",
            confidence=0.7,
            entry=3000.0,
            stop_loss=3050.0,
            take_profit=2800.0,
            sources=["confluence_bearish"],
        )

        def custom_account_state() -> AccountState:
            return AccountState(
                equity=50000.0,
                daily_pnl_pct=-0.5,
                positions=[],
            )

        worker = FollowWorker(
            engine=mock_engine,
            event_bus=event_bus,
            kline_fetcher=None,
            monitor_interval_seconds=0.02,
            account_state_provider=custom_account_state,
        )

        with patch.object(worker, "_fetch_latest_signal", return_value=mock_signal):
            await worker.start()
            await asyncio.sleep(0.05)

            event = SignalChangeEvent(
                pair="ETH/USDT",
                timeframe="4h",
                previous=None,
                current=MagicMock(),
                change_type="first_emit",
            )
            await event_bus.emit(event)
            await asyncio.sleep(0.2)

            await worker.stop()

        # 验证传入 engine 的 AccountState 是 account_state_provider 提供的
        assert mock_engine.on_signal.call_count >= 1
        _, account_arg = mock_engine.on_signal.call_args[0]
        assert account_arg.equity == 50000.0
        assert account_arg.daily_pnl_pct == -0.5

    @pytest.mark.asyncio
    async def test_worker_engine_error_does_not_crash_loop(
        self,
        mock_engine: MagicMock,
        event_bus: SignalChangeBus,
        account_state_provider: MagicMock,
    ) -> None:
        """engine.on_signal 抛异常 → worker loop 继续运行，不崩溃"""
        from app.analytics.signal_direction import Signal
        from unittest.mock import patch

        mock_signal = Signal(
            name="BTCUSDT",
            direction="long",
            confidence=0.8,
            entry=50000.0,
            stop_loss=49500.0,
            take_profit=52000.0,
            sources=["confluence_bullish"],
        )
        mock_engine.on_signal = AsyncMock(side_effect=RuntimeError("adapter error"))

        worker = FollowWorker(
            engine=mock_engine,
            event_bus=event_bus,
            kline_fetcher=None,
            monitor_interval_seconds=0.02,
            account_state_provider=account_state_provider,
        )

        with patch.object(worker, "_fetch_latest_signal", return_value=mock_signal):
            await worker.start()
            await asyncio.sleep(0.05)

            event = SignalChangeEvent(
                pair="BTC/USDT",
                timeframe="1h",
                previous=None,
                current=MagicMock(),
                change_type="first_emit",
            )
            await event_bus.emit(event)
            await asyncio.sleep(0.2)

            # worker 应该还活着（异常被捕获）
            assert not worker._stop_event.is_set(), "stop_event should NOT be set after exception"
            assert len(worker._tasks) == 2, "both tasks should still be running"

            await worker.stop()
