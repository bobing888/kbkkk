"""A1: trend.py 单元测试（8 个）"""
import numpy as np
import pytest
from app.analytics.trend import adx, macd, sma

# calculate_ma 待实现（在 trend.py 中补）
try:
    from app.analytics.trend import calculate_ma
except ImportError:
    calculate_ma = None


# ─── ADX ───────────────────────────────────────────────────────────────────────

def test_adx_returns_nan_for_insufficient_data():
    """数据量 < period，返回全 NaN"""
    high = np.array([100.0, 101.0, 102.0, 103.0])
    low  = np.array([99.0, 100.0, 101.0, 102.0])
    close = np.array([99.5, 100.5, 101.5, 102.5])
    adx_arr, pdi_arr, ndi_arr = adx(high, low, close, period=14)
    assert np.all(np.isnan(adx_arr))


def test_adx_strong_trend_detection():
    """强趋势数据 ADX > 25"""
    np.random.seed(42)
    n = 100
    base = np.linspace(100, 200, n)
    noise = np.random.randn(n) * 0.5
    close = base + noise
    high = close + np.abs(np.random.randn(n) * 2)
    low  = close - np.abs(np.random.randn(n) * 2)

    adx_arr, pdi_arr, ndi_arr = adx(high, low, close, period=14)
    # ADX warmup = 2*period = 28，跳过
    valid = adx_arr[28:]
    assert len(valid) > 0, "ADX warmup 后无数据"
    assert not np.all(np.isnan(valid)), "ADX warmup 后仍全 NaN"
    assert np.nanmax(valid) > 25, f"强趋势 ADX 应 > 25，实际 max={np.nanmax(valid):.2f}"


# ─── MACD ──────────────────────────────────────────────────────────────────────

def test_macd_bullish_cross():
    """快线从下穿越慢线 → histogram 经历由负转正的过程"""
    # 用阶跃数据：先平稳→急跌→急涨，制造清晰金叉
    # EMA(12) 比 EMA(26) 响应更快，急跌后急涨会产生金叉
    close = np.concatenate([
        np.full(40, 100.0),           # 平稳期
        np.linspace(100, 60, 30),      # 急跌（EMA12 快速下降）
        np.linspace(60, 120, 60),     # 急涨（EMA12 快速上升，超过 EMA26 → 金叉）
    ], dtype=float)
    macd_line, signal_line, histogram = macd(close, fast=12, slow=26, signal=9)
    post_warmup = histogram[50:]  # warmup 后
    assert len(post_warmup) > 0, "warmup 后无数据"
    # 急跌阶段 histogram 应负，急涨后段 histogram 应正
    assert np.nanmin(post_warmup[:20]) < 0, "急跌阶段 histogram 应 < 0"
    assert np.nanmax(post_warmup[-20:]) > 0, "急涨后段 histogram 应 > 0"


def test_macd_bearish_cross():
    """快线从上穿越慢线 → histogram 经历由正转负的过程"""
    # 用阶跃数据：先平稳→急涨→急跌，制造清晰死叉
    close = np.concatenate([
        np.full(40, 100.0),           # 平稳期
        np.linspace(100, 150, 30),    # 急涨（EMA12 快速上升）
        np.linspace(150, 80, 60),    # 急跌（EMA12 快速下降，跌破 EMA26 → 死叉）
    ], dtype=float)
    macd_line, signal_line, histogram = macd(close, fast=12, slow=26, signal=9)
    post_warmup = histogram[50:]
    assert len(post_warmup) > 0, "warmup 后无数据"
    # 急涨阶段 histogram 应正，急跌后段 histogram 应负
    assert np.nanmax(post_warmup[:20]) > 0, "急涨阶段 histogram 应 > 0"
    assert np.nanmin(post_warmup[-20:]) < 0, "急跌后段 histogram 应 < 0"


# ─── SMA ──────────────────────────────────────────────────────────────────────

def test_sma_moving_average_correct():
    """[1,2,3,4,5,6] period=5 → 第5根=3.0，第6根=4.0"""
    close = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0], dtype=float)
    result = sma(close, period=5)
    assert np.isnan(result[0]), "SMA 前 4 根应为 NaN"
    assert np.isnan(result[1]), "SMA 前 4 根应为 NaN"
    assert np.isnan(result[2]), "SMA 前 4 根应为 NaN"
    assert np.isnan(result[3]), "SMA 前 4 根应为 NaN"
    assert result[4] == 3.0, f"第5根 SMA 应=3.0，实际 {result[4]}"
    assert result[5] == 4.0, f"第6根 SMA 应=4.0，实际 {result[5]}"


def test_sma_nan_warmup():
    """数据不足 period 时返回全 NaN"""
    close = np.array([1.0, 2.0, 3.0], dtype=float)
    result = sma(close, period=5)
    assert np.all(np.isnan(result)), "数据不足 period 时应全 NaN"


# ─── calculate_ma (pandas Series 包装) ────────────────────────────────────────

def test_calculate_ma_returns_series():
    """calculate_ma 返回 pd.Series"""
    import pandas as pd
    close = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0])
    if calculate_ma is None:
        pytest.fail("calculate_ma 尚未实现，请先在 trend.py 补函数")
    result = calculate_ma(close, period=5)
    assert isinstance(result, pd.Series), "应返回 pd.Series"
    assert len(result) == len(close), "长度应与输入一致"


def test_calculate_ma_warmup():
    """前 period-1 个值为 NaN"""
    import pandas as pd
    close = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    if calculate_ma is None:
        pytest.fail("calculate_ma 尚未实现，请先在 trend.py 补函数")
    result = calculate_ma(close, period=5)
    assert np.isnan(result.iloc[0]), "前 4 根应为 NaN"
    assert np.isnan(result.iloc[3]), "前 4 根应为 NaN"
    assert result.iloc[4] == 3.0, f"第5根应为 3.0，实际 {result.iloc[4]}"
    assert result.iloc[5] == 4.0, f"第6根应为 4.0，实际 {result.iloc[5]}"
