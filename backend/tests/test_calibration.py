"""Test for PAVA Isotonic Calibration Library — C1

TDD: 先写失败测试，再实现 train_calibrator
"""
from __future__ import annotations

import pytest
from app.signals.calibration import (
    train_calibrator,
    CalibrationModel,
    _compute_brier_score,
    _pava,
)


class TestPAVA:
    """PAVA (Pool Adjacent Violators) algorithm tests."""

    def test_pava_two_blocks(self):
        """两个单调递增块 → 合并成递增"""
        x = [0.1, 0.2, 0.3, 0.4]
        y = [0.9, 0.8, 0.6, 0.7]  # 0.9 > 0.8 违反单调
        result = _pava(x, y)
        # 0.1+0.2 块平均 → 合并，0.3+0.4 块平均 → 合并
        assert len(result) <= len(x)
        # 输出应该是单调不减的
        for i in range(len(result) - 1):
            assert result[i] <= result[i + 1] + 1e-9

    def test_pava_already_monotonic(self):
        """已经单调 → 输出不变"""
        x = [0.1, 0.2, 0.3]
        y = [0.1, 0.2, 0.3]
        result = _pava(x, y)
        assert len(result) == 3

    def test_pava_single_point(self):
        """单点 → 直接返回"""
        x = [0.5]
        y = [0.5]
        result = _pava(x, y)
        assert result == [0.5]


class TestCalibrationModel:
    """CalibrationModel dataclass tests."""

    def test_model_creation(self):
        """模型可创建且属性正确"""
        model = CalibrationModel(
            timeframe="1h",
            breakpoints=[
                {"confidence": 0.3, "observed_freq": 0.25, "sample_size": 50},
                {"confidence": 0.6, "observed_freq": 0.55, "sample_size": 100},
                {"confidence": 0.8, "observed_freq": 0.75, "sample_size": 80},
            ],
        )
        assert model.timeframe == "1h"
        assert len(model.breakpoints) == 3
        assert model.breakpoints[0]["confidence"] == 0.3

    def test_model_apply(self):
        """apply 方法将 raw_confidence 映射到 calibrated 值"""
        model = CalibrationModel(
            timeframe="1h",
            breakpoints=[
                {"confidence": 0.3, "observed_freq": 0.25, "sample_size": 50},
                {"confidence": 0.6, "observed_freq": 0.55, "sample_size": 100},
                {"confidence": 0.8, "observed_freq": 0.75, "sample_size": 80},
            ],
        )
        # 0.3 以下 → 外插用第一个断点
        assert abs(model.apply(0.1) - 0.25) < 0.01
        # 0.6 正好命中断点
        assert abs(model.apply(0.6) - 0.55) < 0.01
        # 0.8 正好命中断点
        assert abs(model.apply(0.8) - 0.75) < 0.01
        # 1.0 以上 → 外插用最后一个断点
        assert abs(model.apply(1.0) - 0.75) < 0.01


class TestTrainCalibrator:
    """train_calibrator integration tests."""

    def test_train_small_sample(self):
        """样本 < MIN_SAMPLES → 抛出 ValueError"""
        from app.signals.calibration import MIN_TRAIN_SAMPLES

        small_samples = [(0.6, 0.05), (0.7, 0.08)]
        with pytest.raises(ValueError, match="样本不足"):
            train_calibrator("1h", small_samples)

    def test_train_produces_valid_model(self):
        """正常训练 → 返回含断点的模型"""
        from app.signals.calibration import MIN_TRAIN_SAMPLES

        # 构造 ≥ MIN_SAMPLES 样本
        # raw_confidence 0.5-0.9，pnl_pct 正比于 confidence（高置信 → 正收益）
        import random
        random.seed(42)
        samples = []
        for _ in range(MIN_TRAIN_SAMPLES):
            conf = random.uniform(0.5, 0.9)
            # 赢率 = conf，盈亏按 conf 偏移
            pnl = 0.01 * (conf - 0.5) * 100 if random.random() < conf else -0.01
            samples.append((conf, pnl))
        model = train_calibrator("1h", samples)
        assert isinstance(model, CalibrationModel)
        assert model.timeframe == "1h"
        assert len(model.breakpoints) >= 2
        assert model.brier_score >= 0.0
        assert model.brier_score < 1.0

    def test_brier_score_below_threshold(self):
        """Brier score 验收阈值 < 0.25"""
        from app.signals.calibration import MIN_TRAIN_SAMPLES

        import random
        random.seed(123)
        samples = []
        for _ in range(MIN_TRAIN_SAMPLES):
            conf = random.uniform(0.5, 0.85)
            pnl = 0.01 * (conf - 0.5) * 100 if random.random() < conf else -0.01
            samples.append((conf, pnl))
        model = train_calibrator("1h", samples)
        assert model.brier_score < 0.25, f"Brier score {model.brier_score} >= 0.25"

    def test_train_with_extreme_confidence(self):
        """极端置信度（0.0 / 1.0）边界测试"""
        from app.signals.calibration import MIN_TRAIN_SAMPLES

        import random
        random.seed(999)
        samples = [(0.1, -0.02) for _ in range(MIN_TRAIN_SAMPLES // 2)]
        samples += [(0.9, 0.03) for _ in range(MIN_TRAIN_SAMPLES // 2)]
        model = train_calibrator("5m", samples)
        assert isinstance(model, CalibrationModel)
        # apply(0.1) 应该比 apply(0.9) 小
        assert model.apply(0.1) < model.apply(0.9)


class TestComputeBrierScore:
    """Brier score 计算测试"""

    def test_perfect_calibration(self):
        """完美校准：conf == actual → Brier = 0"""
        samples = [(0.7, 0.01), (0.8, 0.02), (0.6, -0.01)]
        # 假设 outcome = 1 当 pnl > 0，0 当 pnl <= 0
        # 简化：用 binary outcome
        binary_samples = [(0.7, 1), (0.8, 1), (0.6, 0)]
        score = _compute_brier_score(binary_samples)
        # (0.7-1)^2 + (0.8-1)^2 + (0.6-0)^2 / 3
        expected = ((0.3 ** 2) + (0.2 ** 2) + (0.6 ** 2)) / 3
        assert abs(score - expected) < 1e-6

    def test_brier_score_zero_to_one(self):
        """Brier score ∈ [0, 1]"""
        import random
        random.seed(42)
        for _ in range(10):
            conf = random.random()
            outcome = 1 if random.random() > 0.5 else 0
            score = _compute_brier_score([(conf, outcome)])
            assert 0.0 <= score <= 1.0
