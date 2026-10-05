"""
test_kdj_cross.py — KDJ 金叉死叉单元测试
=========================================

TDD 红绿重构：先写测试 → 跑通 → 覆盖所有函数。
"""
import numpy as np
import pytest
import sys
sys.path.insert(0, '/Users/hahaha/Desktop/CODE/kbkkk/backend/scripts')

from backtest_kdj_cross import (
    calc_kdj,
    detect_kdj_golden_cross,
    detect_kdj_death_cross,
    calc_j_confidence,
    generate_kdj_signal,
    backtest_kdj_cross_type,
    generate_bullish_trend_with_crossover,
    generate_bearish_trend_with_crossover,
)


class TestCalcKDJ:
    """KDJ 指标计算"""

    def test_returns_three_arrays(self):
        """返回 K/D/J 三个数组"""
        high = np.array([10, 11, 12, 13, 14, 15, 16, 17, 18, 19])
        low = np.array([9, 10, 11, 12, 13, 14, 15, 16, 17, 18])
        close = np.array([9.5, 10.5, 11.5, 12.5, 13.5, 14.5, 15.5, 16.5, 17.5, 18.5])

        k, d, j = calc_kdj(high, low, close, n=9, m1=3, m2=3)

        assert len(k) == 10
        assert len(d) == 10
        assert len(j) == 10
        # J = 3K - 2D
        np.testing.assert_array_almost_equal(j, 3 * k - 2 * d)

    def test_kdj_in_valid_range(self):
        """K/D/J 通常在 0-100 之间（J 可能超出）"""
        np.random.seed(42)
        n = 100
        close = np.random.uniform(100, 200, n)
        high = close + 1
        low = close - 1

        k, d, j = calc_kdj(high, low, close)

        # K/D 应该在 0-100（边界 +0/+100）
        assert np.all(k >= 0) and np.all(k <= 100)
        assert np.all(d >= 0) and np.all(d <= 100)
        # J 可能超出 [0, 100]
        assert np.all(np.isfinite(j))


class TestDetectGoldenCross:
    """金叉检测"""

    def test_no_cross_when_k_below_d(self):
        """K 一直 < D 时不应检测到金叉"""
        k = np.array([10, 15, 20, 25, 30])
        d = np.array([20, 25, 30, 35, 40])
        assert bool(detect_kdj_golden_cross(k, d)) is False

    def test_no_cross_when_k_above_d_continuously(self):
        """K 一直 > D 时不应检测到金叉（不是"刚"上穿）"""
        k = np.array([40, 45, 50, 55, 60])
        d = np.array([30, 35, 40, 45, 50])
        assert bool(detect_kdj_golden_cross(k, d)) is False

    def test_detects_cross_at_last_bar(self):
        """最后一根 K 上穿 D 应检测到金叉"""
        # k[4]=50 <= d[4]=55（前一根 K <= D）
        # k[5]=55 > d[5]=50（当前 K > D）
        k = np.array([30, 35, 40, 45, 50, 55])
        d = np.array([35, 40, 45, 50, 55, 50])
        assert bool(detect_kdj_golden_cross(k, d)) is True

    def test_insufficient_data(self):
        """数据不足时应返回 False"""
        k = np.array([50])
        d = np.array([30])
        assert bool(detect_kdj_golden_cross(k, d)) is False


class TestDetectDeathCross:
    """死叉检测"""

    def test_no_cross_when_k_above_d(self):
        """K 一直 > D 时不应检测到死叉"""
        # 全部 K > D（不是末尾 D 反超）
        k = np.array([60, 65, 70, 75, 80])
        d = np.array([30, 35, 40, 45, 50])
        assert bool(detect_kdj_death_cross(k, d)) is False

    def test_detects_death_cross(self):
        """K 刚刚下穿 D 应检测到死叉"""
        # k[1]=55 >= d[1]=45（前一根 K >= D）
        # k[2]=50 < d[2]=55（当前 K < D）
        k = np.array([50, 55, 50])
        d = np.array([40, 45, 55])
        assert bool(detect_kdj_death_cross(k, d)) is True


class TestJConfidence:
    """J 值置信度"""

    def test_oversold_golden_cross_high_confidence(self):
        """J < 0 + 金叉 = 高置信度"""
        assert calc_j_confidence(-10) == 0.9

    def test_overbought_golden_cross_low_confidence(self):
        """J > 100 + 金叉 = 低置信度（可能假突破）"""
        assert calc_j_confidence(110) == 0.4

    def test_neutral_zone_medium_confidence(self):
        """20 < J < 80 = 中性区"""
        assert calc_j_confidence(50) == 0.5


class TestGenerateSignal:
    """综合信号生成"""

    def test_no_signal_when_no_cross(self):
        """无交叉时返回空 dict"""
        k = np.array([40, 45, 50, 55, 60])
        d = np.array([50, 55, 60, 65, 70])
        j = 3 * k - 2 * d
        prices = np.array([100, 101, 102, 103, 104])
        signal = generate_kdj_signal(k, d, j, prices)
        # 无交叉时 type=None, direction=None（但 entry_price 仍在）
        assert signal['type'] is None
        assert signal['direction'] is None
        assert signal['confidence'] == 0.0

    def test_golden_cross_signal(self):
        """金叉信号"""
        k = np.array([50, 55])
        d = np.array([60, 50])  # k[1]=55 > d[1]=50, k[0]=50 <= d[0]=60
        j = 3 * k - 2 * d
        prices = np.array([100, 105])
        signal = generate_kdj_signal(k, d, j, prices)
        assert signal['type'] == 'golden_cross'
        assert signal['direction'] == 'up'
        assert signal['entry_price'] == 105

    def test_death_cross_signal(self):
        """死叉信号"""
        k = np.array([60, 50])
        d = np.array([50, 60])  # k[1]=50 < d[1]=60, k[0]=60 >= d[0]=50
        j = 3 * k - 2 * d
        prices = np.array([100, 95])
        signal = generate_kdj_signal(k, d, j, prices)
        assert signal['type'] == 'death_cross'
        assert signal['direction'] == 'down'


class TestBacktest:
    """回测函数"""

    def test_backtest_returns_valid_structure(self):
        """回测返回标准结构"""
        result = backtest_kdj_cross_type(
            'golden_cross',
            generate_bullish_trend_with_crossover,
            n_samples=50,
        )
        assert 'signal_type' in result
        assert 'total_signals' in result
        assert 'hit_rate_10d' in result
        assert 'avg_return_10d' in result
        assert 0.0 <= result['hit_rate_10d'] <= 1.0
        assert result['expected_direction'] == 'up'

    def test_death_cross_expected_down(self):
        """死叉预期方向 = down"""
        result = backtest_kdj_cross_type(
            'death_cross',
            generate_bearish_trend_with_crossover,
            n_samples=50,
        )
        assert result['expected_direction'] == 'down'


class TestTrendGeneration:
    """合成 K 线生成"""

    def test_bullish_trend_ascending(self):
        """上升趋势应总体上升"""
        df = generate_bullish_trend_with_crossover(n=100, seed=42)
        assert df['close'].iloc[-1] > df['close'].iloc[0]

    def test_bearish_trend_descending(self):
        """下降趋势应总体下降"""
        df = generate_bearish_trend_with_crossover(n=100, seed=42)
        assert df['close'].iloc[-1] < df['close'].iloc[0]

    def test_with_pullback_reduces_price(self):
        """末段回撤应降低价格"""
        df_no = generate_bullish_trend_with_crossover(n=200, seed=42, with_pullback=False)
        df_yes = generate_bullish_trend_with_crossover(n=200, seed=42, with_pullback=True)
        assert df_yes['close'].iloc[-1] < df_no['close'].iloc[-1]

    def test_pullback_scenario_detects_cross(self):
        """上升趋势末段回撤场景：能识别金叉或死叉（用于假信号场景）"""
        df = generate_bullish_trend_with_crossover(n=350, seed=42, with_pullback=True)
        k, d, j = calc_kdj(df['high'].values, df['low'].values, df['close'].values)
        # 末段回撤场景，应能识别至少一个交叉信号（用于假信号测试）
        has_golden = bool(detect_kdj_golden_cross(k, d))
        has_death = bool(detect_kdj_death_cross(k, d))
        assert has_golden or has_death, "末段回撤场景应至少有一个交叉信号"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
