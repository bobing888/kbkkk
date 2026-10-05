"""A4: services/indicators.py 薄封装 — 3 个兼容测试"""
import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timedelta


def _make_random_walk_df(n: int = 300, seed: int = 42) -> pd.DataFrame:
    """生成 n 根随机游走 K 线（用于测试）。"""
    rng = np.random.default_rng(seed)
    base = datetime(2025, 1, 1)
    close_prices = 50000 + np.cumsum(rng.normal(0, 200, n))
    opens = close_prices * (1 + rng.uniform(-0.005, 0.005, n))
    highs = np.maximum(opens, close_prices) * (1 + rng.uniform(0, 0.003, n))
    lows = np.minimum(opens, close_prices) * (1 - rng.uniform(0, 0.003, n))
    volumes = rng.lognormal(10, 1, n)
    return pd.DataFrame({
        "datetime": [base + timedelta(hours=i) for i in range(n)],
        "open": opens,
        "high": highs,
        "low": lows,
        "close": close_prices,
        "volume": volumes,
    })


# ─── 原始 6 指标列名（来自 M1 commit e94c1bd）─────────────────────────────

ORIGINAL_6_COLS = {
    "MA5", "MA10", "MA20", "MA60", "MA120", "MA250",
    "DIF", "DEA", "MACD",
    "RSI",
    "BOLL_MID", "BOLL_UPPER", "BOLL_LOWER",
    "K", "D", "J",
    "OBV",
}


# ─── 测试1：向后兼容 ──────────────────────────────────────────────────────

def test_indicators_backward_compatible():
    """调 IndicatorEngine.calculate_all(df) 输出列名与 M1 commit e94c1bd 验证过的
    原始 6 指标列一致。"""
    from app.services.indicators import IndicatorEngine

    df = _make_random_walk_df(n=300)
    result = IndicatorEngine.calculate_all(df)

    # 只比较指标列（不含原始输入列 datetime/open/high/low/close/volume）
    indicator_cols = set(result.columns) - {
        "datetime", "open", "high", "low", "close", "volume"
    }

    # 不多不少，正好是原始 6 列（不含 ADX14/ATR14/Hurst）
    extra_cols = indicator_cols - ORIGINAL_6_COLS
    missing_cols = ORIGINAL_6_COLS - indicator_cols

    assert extra_cols == set(), f"发现额外指标列：{extra_cols}"
    assert missing_cols == set(), f"缺少原始指标列：{missing_cols}"


# ─── 测试2：委托 AnalyticsEngine ─────────────────────────────────────────

def test_indicators_delegates_to_analytics(monkeypatch):
    """验证 services.indicators.calculate_all 路径包含 AnalyticsEngine.calculate_all。"""
    from app.services.indicators import IndicatorEngine
    import app.analytics as analytics_module

    # 记录调用
    call_log = []

    class FakeAnalyticsEngine:
        @staticmethod
        def calculate_all(df):
            call_log.append(True)
            # 模拟 AnalyticsEngine 返回的 DataFrame（含指标列）
            result = IndicatorEngine._calc_ma(df.copy())
            result = IndicatorEngine._calc_macd(result)
            result = IndicatorEngine._calc_rsi(result)
            result = IndicatorEngine._calc_boll(result)
            result = IndicatorEngine._calc_kdj(result)
            result = IndicatorEngine._calc_obv(result)
            return result

    monkeypatch.setattr(analytics_module, "AnalyticsEngine", FakeAnalyticsEngine)

    df = _make_random_walk_df(n=100)
    result = IndicatorEngine.calculate_all(df)

    # 如果实现正确，AnalyticsEngine 被调用
    assert len(call_log) > 0, "AnalyticsEngine.calculate_all 未被调用"
    # 且结果只有原始指标列（不含 ADX14/ATR14/Hurst）
    indicator_cols = set(result.columns) - {
        "datetime", "open", "high", "low", "close", "volume"
    }
    assert indicator_cols == ORIGINAL_6_COLS


# ─── 测试3：空 df 不抛异常 ───────────────────────────────────────────────

def test_indicators_empty_df_no_crash():
    """空 df → 不抛异常（向后兼容边界）。"""
    from app.services.indicators import IndicatorEngine

    empty = pd.DataFrame(columns=["datetime", "open", "high", "low", "close", "volume"])
    # 不抛异常
    result = IndicatorEngine.calculate_all(empty)
    assert isinstance(result, pd.DataFrame)
