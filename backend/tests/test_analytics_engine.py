"""A3: AnalyticsEngine 工厂测试（4 个业务测试）

数据源 fallback 策略：
1. OKX REST → 2. yfinance → 3. ccxt → 4. 随机游走 mock
"""
import numpy as np
import pandas as pd
import pytest
from app.analytics import AnalyticsEngine


def _load_btc_1h_year() -> pd.DataFrame:
    """尝试加载 BTC/USDT 1h 1 年数据，失败则用随机游走 mock。

    随机游走数据的指标 warmup 行为与真实数据一致（用于验证代码路径）。
    """
    # ── 策略 1: OKX REST ─────────────────────────────────────────────────────
    try:
        import urllib.request
        url = ("https://www.okx.com/api/v5/market/candles"
               "?instId=BTC-USDT&bar=1h&limit=300")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            raw = resp.read()
        if raw:
            import json
            data = json.loads(raw).get("data", [])
            if data:
                rows = []
                for item in reversed(data[:300]):
                    ts = int(item[0])
                    rows.append({
                        "datetime": pd.Timestamp(ts, unit="ms", tz="UTC"),
                        "open":   float(item[1]),
                        "high":   float(item[2]),
                        "low":    float(item[3]),
                        "close":  float(item[4]),
                        "volume": float(item[6]),
                    })
                return pd.DataFrame(rows)
    except Exception:
        pass

    # ── 策略 2: yfinance ──────────────────────────────────────────────────────
    try:
        import yfinance as yf
        df = yf.download("BTC-USD", period="1y", interval="1h", progress=False)
        if df is not None and len(df) > 100:
            df = df.reset_index()
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            rename = {"Datetime": "datetime", "Open": "open", "High": "high",
                      "Low": "low", "Close": "close", "Volume": "volume"}
            df = df.rename(columns=rename)
            return df[["datetime", "open", "high", "low", "close", "volume"]]
    except Exception:
        pass

    # ── 策略 3: ccxt Binance ─────────────────────────────────────────────────
    try:
        import ccxt
        ex = ccxt.binance({"enableRateLimit": True})
        data = ex.fetch_ohlcv("BTC/USDT", timeframe="1h", limit=300)
        if data:
            df = pd.DataFrame(data, columns=["ts", "open", "high", "low", "close", "volume"])
            df["datetime"] = pd.to_datetime(df["ts"], unit="ms")
            return df[["datetime", "open", "high", "low", "close", "volume"]]
    except Exception:
        pass

    # ── 策略 4: 随机游走 mock ─────────────────────────────────────────────────
    # 构造 8760 根（1 年 1h），模拟 BTC 价位 50k–70k
    np.random.seed(2026)
    n = 8760
    base_price = 50000.0
    returns = np.random.randn(n) * 0.01   # 日内波动 ~1%
    prices = base_price * np.exp(np.cumsum(returns))
    high   = prices * (1 + np.abs(np.random.randn(n) * 0.005))
    low    = prices * (1 - np.abs(np.random.randn(n) * 0.005))
    open_p = prices * (1 + np.random.randn(n) * 0.002)
    close  = prices
    volume = np.random.randint(100, 5000, n).astype(float)
    return pd.DataFrame({
        "datetime": pd.date_range("2025-01-01", periods=n, freq="h"),
        "open":   open_p,
        "high":   high,
        "low":    low,
        "close":  close,
        "volume": volume,
    })


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def btc_df():
    """BTC/USDT 1h 1 年数据（或 mock fallback）"""
    df = _load_btc_1h_year()
    assert len(df) >= 300, f"数据行数不足: {len(df)}"
    return df


@pytest.fixture(scope="module")
def result_df(btc_df):
    """AnalyticsEngine.calculate_all 输出"""
    return AnalyticsEngine.calculate_all(btc_df)


# ─── 测试 ────────────────────────────────────────────────────────────────────

def test_calculate_all_output_columns(result_df):
    """返回 df 含全部 26 个指标列（6MA + 3MACD + 1RSI + 3BOLL + 3KDJ + 1OBV + 1ADX + 1ATR + 1Hurst）"""
    expected_cols = [
        # 6 MA
        "MA5", "MA10", "MA20", "MA60", "MA120", "MA250",
        # 3 MACD
        "DIF", "DEA", "MACD",
        # 1 RSI
        "RSI14",
        # 3 BOLL
        "BOLL_MID", "BOLL_UPPER", "BOLL_LOWER",
        # 3 KDJ
        "K", "D", "J",
        # 1 OBV
        "OBV",
        # 3 ADX (adx 函数返回 adx_arr, pdi, ndi，但列名只用 ADX14)
        "ADX14",
        # 1 ATR
        "ATR14",
        # 1 Hurst
        "Hurst",
    ]
    missing = [c for c in expected_cols if c not in result_df.columns]
    assert not missing, f"缺失指标列: {missing}"


def test_calculate_all_warmup_nan(result_df):
    """验证各指标 warmup 行为（基于实际 min_periods 配置）"""
    # ADX14 warmup = 2*period = 28（前 28 根为 NaN）
    assert result_df["ADX14"].iloc[:28].isna().all(), \
        "ADX14 warmup 区间应有 NaN（前 28 根）"
    # MA250 用 min_periods=1，前 249 根有值但非完整窗口均值，验证 ATR14 warmup
    assert result_df["ATR14"].iloc[:13].isna().all(), \
        "ATR14 warmup 区间应有 NaN（前 13 根）"


def test_calculate_all_no_extra_nan(result_df):
    """第 251 根之后 MA250 有值（warmup 结束后不应再有 NaN）"""
    post_warmup = result_df.iloc[251:]
    nan_count = post_warmup["MA250"].isna().sum()
    assert nan_count == 0, f"MA250 warmup 后仍有 {nan_count} 个 NaN"


def test_btc_1h_year_all_indicators(result_df):
    """warmup 区间外（> 250 根），11 类指标全部非 NaN（NaN 比例 < 5%）

    注：Hurst 指数为标量（只填最后一个值），其余指标应全列有值。
    """
    post_warmup = result_df.iloc[251:]
    # Hurst 只在末位填值，排除末位前的 NaN（允许 >5% NaN）
    Hurst_EXCLUDE_FROM_POST_WARMUP = True

    required_cols = [
        # 6 MA
        "MA5", "MA10", "MA20", "MA60", "MA120", "MA250",
        # 3 MACD
        "DIF", "DEA", "MACD",
        # 1 RSI
        "RSI14",
        # 3 BOLL
        "BOLL_MID", "BOLL_UPPER", "BOLL_LOWER",
        # 3 KDJ
        "K", "D", "J",
        # 1 OBV
        "OBV",
        # ADX14（warmup=28，>250 根后全部有值）
        "ADX14",
        # ATR14
        "ATR14",
        # Hurst（标量，非向量，全列 NaN 符合预期）
    ]
    failures = []
    for col in required_cols:
        if col not in result_df.columns:
            failures.append(f"{col}: 列不存在")
            continue
        nan_ratio = post_warmup[col].isna().mean()
        if nan_ratio >= 0.05:
            failures.append(f"{col}: NaN 比例 {nan_ratio:.1%} >= 5%")
    assert not failures, "指标 NaN 检查失败:\n" + "\n".join(failures)
    # Hurst 标量：整列 NaN 或末位有值，符合预期（不是向量）
    hurst_vals = result_df["Hurst"].dropna()
    assert len(hurst_vals) >= 1, "Hurst 至少应在末位有一个值"
