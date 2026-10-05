"""SignalService — C3

协调服务：K线 → AnalyticsEngine → confluence → generate_signal → 持久化 → event_bus

流水线：
  process_kline(symbol, period, df)
    1. AnalyticsEngine.calculate_all(df)
    2. detect_confluence(df)
    3. generate_signal(df)
    4. 持久化到 RecommendationHistory
    5. emit SignalChangeEvent 到 event_bus
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Callable

from sqlalchemy.orm import Session

from app.analytics.signal_direction import Signal
from app.models import RecommendationHistory

from .event_bus import SignalChangeBus, SignalChangeEvent

logger = logging.getLogger(__name__)


class SignalService:
    """信号服务协调器。"""

    def __init__(
        self,
        db_factory: Callable[[], Session],
        event_bus: SignalChangeBus,
    ) -> None:
        """
        Args:
            db_factory: session 工厂（sync Session）
            event_bus: SignalChangeBus 实例（用于发布信号变化事件）
        """
        self._db_factory = db_factory
        self._bus = event_bus

    async def process_kline(
        self,
        symbol: str,
        period: str,
        df,
    ) -> list[Signal]:
        """流水线：K线 → 信号 → 持久化 → 发布。

        Args:
            symbol: 交易对，如 "BTC/USDT"
            period: 时间周期，如 "1h"
            df: 含 OHLCV 的 DataFrame

        Returns:
            生成的 Signal 列表
        """
        # 1. AnalyticsEngine
        from app.analytics import AnalyticsEngine
        engine = AnalyticsEngine()
        df = engine.calculate_all(df)

        # 2. detect_confluence
        from app.analytics.confluence import detect_confluence
        df = detect_confluence(df)

        # 3. generate_signal
        from app.analytics.signal_direction import generate_signal as _gen_sig
        signals = _gen_sig(df)
        if not signals:
            return []

        # 4. 持久化 + 发布
        await self._persist_and_emit(symbol, period, signals)
        return signals

    async def _persist_and_emit(
        self,
        pair: str,
        timeframe: str,
        signals: list[Signal],
    ) -> None:
        """持久化信号到 DB 并发布事件。"""
        db = self._db_factory()
        try:
            for sig in signals:
                rec = RecommendationHistory(
                    pair=pair,
                    timeframe=timeframe,
                    direction=sig.direction,
                    confidence=sig.confidence,
                    entry_price=sig.entry,
                    stop_loss=sig.stop_loss,
                    take_profit=sig.take_profit,
                    signal_sources=",".join(sig.sources),
                    outcome_label="pending",
                    created_at=datetime.now(UTC),
                )
                db.add(rec)

            db.commit()
            logger.info("[signal_service] persisted %d signals for %s %s", len(signals), pair, timeframe)

            # 5. 发布事件
            for sig in signals:
                event = SignalChangeEvent(
                    pair=pair,
                    timeframe=timeframe,
                    previous=None,
                    current=None,  # type: ignore[assignment]
                    change_type="first_emit",
                )
                await self._bus.emit(event)

        except Exception as e:
            logger.warning("[signal_service] persist failed: %s", e)
            db.rollback()
            raise

    async def get_latest_signals(
        self,
        symbol: str,
        period: str,
        limit: int = 10,
    ) -> list[RecommendationHistory]:
        """从 DB 读最近信号。

        Args:
            symbol: 交易对
            period: 时间周期
            limit: 返回条数

        Returns:
            RecommendationHistory 列表（按 created_at 降序）
        """
        db = self._db_factory()
        try:
            rows = (
                db.query(RecommendationHistory)
                .where(RecommendationHistory.pair == symbol)
                .where(RecommendationHistory.timeframe == period)
                .order_by(RecommendationHistory.created_at.desc())
                .limit(limit)
                .all()
            )
            return list(rows)
        finally:
            db.close()
