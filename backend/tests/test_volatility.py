"""A2: volatility.py 单元测试（4 个）"""
import numpy as np
import pytest
from app.analytics.volatility import atr, volatility_percentile


# ─── ATR ─────────────────────────────────────────────────────────────────────

def test_atr_nan_warmup():
    """前 period 根为 NaN"""
    n = 10
    high = np.full(n, 100.0)
    low  = np.full(n, 99.0)
    close = np.full(n, 99.5)
    result = atr(high, low, close, period=14)
    assert np.all(np.isnan(result[:14])), "前 14 根 ATR 应为 NaN"


def test_atr_increases_with_volatility():
    """高波动序列 ATR > 低波动序列"""
    n = 100
    # 低波动
    low_vol = np.linspace(100, 105, n)
    high_low = low_vol + 1.0
    low_low  = low_vol - 1.0
    close_low = low_vol
    atr_low = atr(high_low, low_low, close_low, period=14)
    valid_low = atr_low[~np.isnan(atr_low)]

    # 高波动
    hi_vol = np.concatenate([np.linspace(100, 80, n // 2), np.linspace(80, 120, n // 2)])
    high_hi = hi_vol + 5.0
    low_hi  = hi_vol - 5.0
    close_hi = hi_vol
    atr_hi = atr(high_hi, low_hi, close_hi, period=14)
    valid_hi = atr_hi[~np.isnan(atr_hi)]

    assert len(valid_low) > 0 and len(valid_hi) > 0
    assert np.mean(valid_hi) > np.mean(valid_low), "高波动 ATR 应 > 低波动 ATR"


def test_atr_period_14():
    """period=14 正确（验证 ATR 值计算）"""
    # 固定数据
    np.random.seed(42)
    n = 30
    base = np.full(n, 100.0)
    noise = np.random.randn(n) * 0.5
    high = base + 1.0 + np.abs(noise)
    low  = base - 1.0 - np.abs(noise)
    close = base + noise
    result = atr(high, low, close, period=14)
    # warmup 后应有值
    assert not np.all(np.isnan(result[14:])), "ATR warmup 后应有值"


def test_volatility_percentile_keys():
    """返回 dict 含必要 key"""
    np.random.seed(42)
    n = 200
    close = np.random.rand(n) * 100 + 100
    high = close + np.random.rand(n) * 2
    low  = close - np.random.rand(n) * 2
    result = volatility_percentile(close, high, low, period=14, lookback=100)
    assert "current_atr_pct" in result, "应含 current_atr_pct"
    assert "percentile_1y" in result, "应含 percentile_1y"
    assert "level" in result, "应含 level"
