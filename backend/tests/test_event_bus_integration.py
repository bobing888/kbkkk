"""Event Bus Integration Tests — C4

验证 signal_service 与 event_bus 正确集成。
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from app.services.event_bus import SignalChangeBus, SignalChangeEvent
from app.services.signal_service import SignalService


def _mock_df() -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=5, freq="h")
    return pd.DataFrame({
        "datetime": dates,
        "close": [100.0 + i for i in range(5)],
        "high": [105.0 + i for i in range(5)],
        "low": [95.0 + i for i in range(5)],
        "volume": [1000.0] * 5,
    })


class TestEventBusIntegration:
    """验证 event_bus 在 signal_service 中的行为"""

    @pytest.mark.asyncio
    async def test_bus_receives_event_on_signal_emit(self):
        """signal_service.process_kline → emit → event_bus 收到事件"""
        db = MagicMock()
        db_factory = lambda: db
        bus = SignalChangeBus()
        service = SignalService(db_factory, bus)

        with patch("app.analytics.AnalyticsEngine") as MockEng, \
             patch("app.analytics.confluence.detect_confluence") as mock_conf, \
             patch("app.analytics.signal_direction.generate_signal") as mock_gen, \
             patch("app.services.signal_service.RecommendationHistory"):

            from app.analytics.signal_direction import Signal
            sig = Signal(
                name="test", direction="long", confidence=0.7,
                entry=100.0, stop_loss=98.0, take_profit=108.0,
                sources=["confluence_bullish"],
                datetime=pd.Timestamp("2024-01-01 10:00"),
            )
            mock_df = _mock_df()
            MockEng.return_value.calculate_all.return_value = mock_df
            mock_conf.return_value = mock_df
            mock_gen.return_value = [sig]

            q = bus.subscribe()
            await service.process_kline("ETH/USDT", "1h", mock_df)

            events = []
            while not q.empty():
                events.append(q.get_nowait())

            assert len(events) == 1
            assert events[0].pair == "ETH/USDT"
            assert events[0].timeframe == "1h"
            assert events[0].change_type == "first_emit"

    @pytest.mark.asyncio
    async def test_multiple_subscribers_all_receive(self):
        """多 subscriber 都收到同一事件"""
        db_factory = lambda: MagicMock()
        bus = SignalChangeBus()
        service = SignalService(db_factory, bus)

        with patch("app.analytics.AnalyticsEngine") as MockEng, \
             patch("app.analytics.confluence.detect_confluence") as mock_conf, \
             patch("app.analytics.signal_direction.generate_signal") as mock_gen, \
             patch("app.services.signal_service.RecommendationHistory"):

            from app.analytics.signal_direction import Signal
            sig = Signal(
                name="test", direction="short", confidence=0.6,
                entry=200.0, stop_loss=204.0, take_profit=192.0,
                sources=["confluence_bearish"],
                datetime=pd.Timestamp("2024-01-01 10:00"),
            )
            mock_df = _mock_df()
            MockEng.return_value.calculate_all.return_value = mock_df
            mock_conf.return_value = mock_df
            mock_gen.return_value = [sig]

            q1 = bus.subscribe()
            q2 = bus.subscribe()

            await service.process_kline("BTC/USDT", "4h", mock_df)

            assert not q1.empty()
            assert not q2.empty()
            assert q1.get_nowait().pair == "BTC/USDT"
            assert q2.get_nowait().pair == "BTC/USDT"

    @pytest.mark.asyncio
    async def test_no_signal_no_event(self):
        """无信号时不 emit"""
        db_factory = lambda: MagicMock()
        bus = SignalChangeBus()
        service = SignalService(db_factory, bus)

        with patch("app.analytics.AnalyticsEngine") as MockEng, \
             patch("app.analytics.confluence.detect_confluence") as mock_conf, \
             patch("app.analytics.signal_direction.generate_signal") as mock_gen:

            mock_df = _mock_df()
            MockEng.return_value.calculate_all.return_value = mock_df
            mock_conf.return_value = mock_df
            mock_gen.return_value = []

            q = bus.subscribe()
            result = await service.process_kline("BTC/USDT", "1d", mock_df)

            assert result == []
            assert q.empty()

    @pytest.mark.asyncio
    async def test_signal_change_event_structure(self):
        """SignalChangeEvent 内容完整"""
        db_factory = lambda: MagicMock()
        bus = SignalChangeBus()
        service = SignalService(db_factory, bus)

        with patch("app.analytics.AnalyticsEngine") as MockEng, \
             patch("app.analytics.confluence.detect_confluence") as mock_conf, \
             patch("app.analytics.signal_direction.generate_signal") as mock_gen, \
             patch("app.services.signal_service.RecommendationHistory"):

            from app.analytics.signal_direction import Signal
            sig = Signal(
                name="test", direction="long", confidence=0.75,
                entry=50.0, stop_loss=48.0, take_profit=58.0,
                sources=["confluence_bullish", "hammer_bullish"],
                datetime=pd.Timestamp("2024-01-02 08:00"),
            )
            mock_df = _mock_df()
            MockEng.return_value.calculate_all.return_value = mock_df
            mock_conf.return_value = mock_df
            mock_gen.return_value = [sig]

            q = bus.subscribe()
            await service.process_kline("SOL/USDT", "15m", mock_df)

            evt = q.get_nowait()
            assert isinstance(evt, SignalChangeEvent)
            assert evt.pair == "SOL/USDT"
            assert evt.timeframe == "15m"
            assert evt.previous is None
            assert evt.change_type == "first_emit"
