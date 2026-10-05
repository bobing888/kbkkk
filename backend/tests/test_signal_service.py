"""Test for SignalService — C3

TDD: 红灯先亮，再实现 SignalService
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
import pytest
import pandas as pd
from app.analytics.signal_direction import Signal
from app.services.event_bus import SignalChangeBus, SignalChangeEvent
from app.services.signal_service import SignalService


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_db_factory():
    """Mock DB session factory — 每次调用返回同一个 mock session（闭包共享）。"""
    db = MagicMock()
    return lambda: db


@pytest.fixture
def event_bus():
    """Fresh event bus for each test."""
    return SignalChangeBus()


def _mock_df() -> pd.DataFrame:
    """构造满足 generate_signal 所需的 df（含 confluence_direction + ADX14 + ATR14）。"""
    dates = pd.date_range("2024-01-01", periods=10, freq="h")
    return pd.DataFrame({
        "datetime": dates,
        "close": [100.0 + i for i in range(10)],
        "high": [105.0 + i for i in range(10)],
        "low": [95.0 + i for i in range(10)],
        "volume": [1000.0] * 10,
        "confluence_direction": ["bullish"] * 10,
        "ADX14": [30.0] * 10,
        "ATR14": [2.0] * 10,
        "RSI14": [55.0] * 10,
    })


def _make_signal() -> Signal:
    return Signal(
        name="test_long",
        direction="long",
        confidence=0.7,
        entry=105.0,
        stop_loss=101.0,
        take_profit=113.0,
        sources=["confluence_bullish"],
        datetime=pd.Timestamp("2024-01-01 10:00"),
    )


# ── process_kline tests ────────────────────────────────────────────────────────

class TestProcessKline:
    """process_kline 流水线测试"""

    @pytest.mark.asyncio
    async def test_returns_signals_from_generate_signal(self, mock_db_factory, event_bus):
        """df 触发信号 → 返回 Signal 列表"""
        service = SignalService(mock_db_factory, event_bus)
        sig = _make_signal()

        with patch("app.analytics.AnalyticsEngine") as MockEngineCls, \
             patch("app.analytics.confluence.detect_confluence") as mock_conf, \
             patch("app.analytics.signal_direction.generate_signal") as mock_gen, \
             patch("app.services.signal_service.RecommendationHistory") as MockRec:

            mock_df = _mock_df()
            mock_engine = MockEngineCls.return_value
            mock_engine.calculate_all.return_value = mock_df
            mock_conf.return_value = mock_df
            mock_gen.return_value = [sig]

            result = await service.process_kline("BTC/USDT", "1h", mock_df)

            assert len(result) == 1
            assert result[0].direction == "long"
            mock_gen.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_signal_returns_empty(self, mock_db_factory, event_bus):
        """无信号 → 返回空列表"""
        service = SignalService(mock_db_factory, event_bus)

        with patch("app.analytics.AnalyticsEngine") as MockEngineCls, \
             patch("app.analytics.confluence.detect_confluence") as mock_conf, \
             patch("app.analytics.signal_direction.generate_signal") as mock_gen:

            mock_df = _mock_df()
            MockEngineCls.return_value.calculate_all.return_value = mock_df
            mock_conf.return_value = mock_df
            mock_gen.return_value = []

            result = await service.process_kline("BTC/USDT", "1h", mock_df)

            assert result == []

    @pytest.mark.asyncio
    async def test_persists_signal_to_db(self, mock_db_factory, event_bus):
        """有信号 → 持久化到 DB"""
        service = SignalService(mock_db_factory, event_bus)
        sig = _make_signal()

        with patch("app.analytics.AnalyticsEngine") as MockEngineCls, \
             patch("app.analytics.confluence.detect_confluence") as mock_conf, \
             patch("app.analytics.signal_direction.generate_signal") as mock_gen:

            mock_df = _mock_df()
            MockEngineCls.return_value.calculate_all.return_value = mock_df
            mock_conf.return_value = mock_df
            mock_gen.return_value = [sig]

            await service.process_kline("BTC/USDT", "1h", mock_df)

            # 验证 add + commit 被调用
            mock_db_factory().add.assert_called()
            mock_db_factory().commit.assert_called()

    @pytest.mark.asyncio
    async def test_emits_event_bus_on_new_signal(self, mock_db_factory, event_bus):
        """有新信号 → emit 到 event_bus"""
        service = SignalService(mock_db_factory, event_bus)
        sig = _make_signal()

        with patch("app.analytics.AnalyticsEngine") as MockEngineCls, \
             patch("app.analytics.confluence.detect_confluence") as mock_conf, \
             patch("app.analytics.signal_direction.generate_signal") as mock_gen, \
             patch("app.services.signal_service.RecommendationHistory"):

            mock_df = _mock_df()
            MockEngineCls.return_value.calculate_all.return_value = mock_df
            mock_conf.return_value = mock_df
            mock_gen.return_value = [sig]

            # 订阅事件
            q = event_bus.subscribe()

            await service.process_kline("BTC/USDT", "1h", mock_df)

            # 验证事件入队
            got_event = False
            while not q.empty():
                evt = q.get_nowait()
                if evt.pair == "BTC/USDT" and evt.timeframe == "1h":
                    got_event = True
                    break
            assert got_event, "Event should be emitted to bus"


# ── get_latest_signals tests ──────────────────────────────────────────────────

class TestGetLatestSignals:
    """get_latest_signals 测试"""

    @pytest.mark.asyncio
    async def test_returns_db_records(self, mock_db_factory, event_bus):
        """从 DB 读取 → 返回 RecommendationHistory 列表"""
        service = SignalService(mock_db_factory, event_bus)

        mock_records = [MagicMock(), MagicMock()]
        db = mock_db_factory()
        mock_q = MagicMock()
        db.query.return_value = mock_q
        mock_q.where.return_value = mock_q
        mock_q.order_by.return_value = mock_q
        mock_q.limit.return_value = mock_q
        mock_q.all.return_value = mock_records
        db.close = MagicMock()

        result = await service.get_latest_signals("BTC/USDT", "1h", limit=5)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_default_limit_10(self, mock_db_factory, event_bus):
        """不传 limit → 默认 10"""
        service = SignalService(mock_db_factory, event_bus)

        db = mock_db_factory()
        mock_q = MagicMock()
        db.query.return_value = mock_q
        mock_q.where.return_value = mock_q
        mock_q.order_by.return_value = mock_q
        mock_q.limit.return_value = mock_q
        mock_q.all.return_value = []
        db.close = MagicMock()

        await service.get_latest_signals("BTC/USDT", "1h")

        db.query.return_value.limit.assert_called_with(10)

    @pytest.mark.asyncio
    async def test_empty_db_returns_empty_list(self, mock_db_factory, event_bus):
        """DB 无记录 → 返回空列表"""
        service = SignalService(mock_db_factory, event_bus)

        db = mock_db_factory()
        mock_query = MagicMock()
        db.query.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        result = await service.get_latest_signals("BTC/USDT", "1h")

        assert result == []


# ── Error handling ─────────────────────────────────────────────────────────────

class TestSignalServiceErrorHandling:
    """错误处理测试"""

    @pytest.mark.asyncio
    async def test_db_error_rolls_back(self, mock_db_factory, event_bus):
        """DB 写入失败 → rollback + raise"""
        with patch("app.analytics.AnalyticsEngine") as MockEngineCls, \
             patch("app.analytics.confluence.detect_confluence") as mock_conf, \
             patch("app.analytics.signal_direction.generate_signal") as mock_gen, \
             patch("app.services.signal_service.RecommendationHistory"):

            db = mock_db_factory()
            db.commit.side_effect = Exception("DB error")
            db.close = MagicMock()  # 防止 finally 中抛异常

            service = SignalService(mock_db_factory, event_bus)

            mock_df = _mock_df()
            MockEngineCls.return_value.calculate_all.return_value = mock_df
            mock_conf.return_value = mock_df
            mock_gen.return_value = [_make_signal()]

            with pytest.raises(Exception):
                await service.process_kline("BTC/USDT", "1h", mock_df)
            db.rollback.assert_called()
