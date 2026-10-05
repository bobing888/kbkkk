"""Integration Acceptance Tests — C6

3 个业务测试：
1. test_signal_service_end_to_end（mock df → signal → outcome）
2. test_outcome_tracker_window_boundaries（8 周期全覆盖）
3. test_calibration_brier_score_below_threshold
"""
from __future__ import annotations

import pytest
import pandas as pd
from app.analytics.signal_direction import Signal
from app.services.outcome_tracker import OutcomeTracker
from app.signals.calibration import train_calibrator


# ═══════════════════════════════════════════════════════════════
# 1. signal_service 端到端
# ═══════════════════════════════════════════════════════════════

class TestSignalServiceEndToEnd:
    """mock df → signal → outcome 端到端"""

    @pytest.mark.asyncio
    async def test_df_to_signal_to_outcome_flow(self):
        """完整流水线：df → generate_signal → fill_outcome"""
        from unittest.mock import patch, MagicMock
        from app.services.event_bus import SignalChangeBus
        from app.services.signal_service import SignalService

        db_factory = lambda: MagicMock()
        bus = SignalChangeBus()

        dates = pd.date_range("2024-01-01", periods=10, freq="h")
        df = pd.DataFrame({
            "datetime": dates,
            "close": [100.0 + i for i in range(10)],
            "high": [105.0 + i for i in range(10)],
            "low": [95.0 + i for i in range(10)],
            "volume": [1000.0] * 10,
        })

        with patch("app.analytics.AnalyticsEngine") as MockEng, \
             patch("app.analytics.confluence.detect_confluence") as mock_conf, \
             patch("app.analytics.signal_direction.generate_signal") as mock_gen, \
             patch("app.services.signal_service.RecommendationHistory"):

            MockEng.return_value.calculate_all.return_value = df
            mock_conf.return_value = df

            # 生成一个做多信号
            sig = Signal(
                name="confluence_bullish",
                direction="long",
                confidence=0.7,
                entry=105.0,
                stop_loss=101.0,
                take_profit=113.0,
                sources=["confluence_bullish"],
                datetime=pd.Timestamp("2024-01-01 09:00"),
            )
            mock_gen.return_value = [sig]

            service = SignalService(db_factory, bus)
            signals = await service.process_kline("BTC/USDT", "1h", df)

            assert len(signals) == 1
            assert signals[0].direction == "long"

            # outcome_tracker 回填
            tracker = OutcomeTracker()
            outcome_df = pd.DataFrame({
                "datetime": pd.date_range("2024-01-01 09:01", periods=5, freq="h"),
                "high": [106.0, 108.0, 110.0, 112.0, 113.5],
                "low": [103.0, 104.0, 105.0, 106.0, 107.0],
                "close": [104.0, 105.0, 106.0, 107.0, 108.0],
            })
            result = tracker.fill_outcome(signals[0], outcome_df, period="1h")

            assert result.outcome == "win"
            assert result.exit_price == 113.0


# ═══════════════════════════════════════════════════════════════
# 2. outcome_tracker 8 周期窗口全覆盖
# ═══════════════════════════════════════════════════════════════

class TestOutcomeTrackerWindowBoundaries:
    """8 个时间周期窗口根数验证"""

    @pytest.mark.parametrize("period,expected_bars", [
        ("1m", 60),
        ("5m", 60),
        ("15m", 60),
        ("30m", 60),
        ("1h", 24),
        ("4h", 24),
        ("1d", 5),
        ("1w", 5),
    ])
    def test_window_boundary_for_period(self, period, expected_bars):
        """每个周期的窗口根数与 spec 一致"""
        tracker = OutcomeTracker()
        assert tracker.get_window_for_period(period) == expected_bars

    def test_outcome_hits_in_1h_window(self):
        """1h 周期：窗口内第 5 根触 TP → win"""
        tracker = OutcomeTracker()
        sig = Signal(
            name="test", direction="long", confidence=0.7,
            entry=100.0, stop_loss=98.0, take_profit=108.0,
            sources=["test"], datetime=pd.Timestamp("2024-01-01 09:00"),
        )
        # 5 根 K 线，第 3 根触及 TP
        df = pd.DataFrame({
            "datetime": pd.date_range("2024-01-01 09:01", periods=5, freq="h"),
            "high": [102.0, 104.0, 108.5, 110.0, 111.0],
            "low": [99.0, 100.0, 101.0, 102.0, 103.0],
            "close": [101.0, 102.0, 103.0, 104.0, 105.0],
        })
        result = tracker.fill_outcome(sig, df, period="1h")
        assert result.outcome == "win"

    def test_outcome_hits_in_1d_window(self):
        """1d 周期：窗口内触 SL → loss"""
        tracker = OutcomeTracker()
        sig = Signal(
            name="test", direction="short", confidence=0.6,
            entry=200.0, stop_loss=204.0, take_profit=192.0,
            sources=["test"], datetime=pd.Timestamp("2024-01-01"),
        )
        # 3 根日线，第 2 根触及 SL
        df = pd.DataFrame({
            "datetime": pd.date_range("2024-01-02", periods=3, freq="D"),
            "high": [198.0, 204.5, 203.0],
            "low": [196.0, 200.0, 199.0],
            "close": [197.0, 202.0, 201.0],
        })
        result = tracker.fill_outcome(sig, df, period="1d")
        assert result.outcome == "loss"


# ═══════════════════════════════════════════════════════════════
# 3. calibration Brier score 验收
# ═══════════════════════════════════════════════════════════════

class TestCalibrationBrierScore:
    """Brier score < 0.25 验收"""

    def test_brier_score_below_threshold(self):
        """随机样本训练 → Brier score < 0.25"""
        import random
        random.seed(42)
        samples = []
        for _ in range(150):
            conf = random.uniform(0.5, 0.85)
            # 胜率与 confidence 正相关
            outcome = 1 if random.random() < conf else 0
            samples.append((conf, 0.01 if outcome else -0.01))
        model = train_calibrator("1h", samples)
        assert model.brier_score < 0.25, f"Brier score {model.brier_score} >= 0.25"

    def test_calibration_model_apply_monotonic(self):
        """校准后置信度单调递增"""
        import random
        random.seed(99)
        samples = []
        for _ in range(150):
            conf = random.uniform(0.4, 0.9)
            outcome = 1 if random.random() < conf else 0
            samples.append((conf, 0.02 if outcome else -0.01))
        model = train_calibrator("5m", samples)
        # apply 应单调
        vals = [model.apply(c) for c in [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]]
        for i in range(len(vals) - 1):
            assert vals[i] <= vals[i + 1] + 1e-6, f"单调性违反: {vals}"

    def test_calibration_preserves_timeframe(self):
        """不同 timeframe 训练 → 模型记住 timeframe"""
        import random
        random.seed(7)
        samples = [(random.uniform(0.5, 0.8), 0.01) for _ in range(150)]
        for tf in ["1m", "5m", "15m", "1h", "4h", "1d"]:
            model = train_calibrator(tf, samples)
            assert model.timeframe == tf
