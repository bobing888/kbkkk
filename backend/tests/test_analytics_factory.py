"""A3: AnalyticsEngine 工厂 — 5 个业务测试"""
import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timedelta


def _make_random_walk_df(n: int = 1000, seed: int = 42) -> pd.DataFrame:
    """生成 n 根随机游走 K 线（用于测试）。"""
    rng = np.random.default_rng(seed)
    base = datetime(2025, 1, 1)
    # 价格从 50000 开始
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


# ─── 测试1：输出 11 列 ──────────────────────────────────────────────────────

def test_calculate_all_returns_11_columns():
    """calculate_all 输出 df 必须含 17 个指标列。"""
    from app.analytics import AnalyticsEngine

    df = _make_random_walk_df(n=1000)
    result = AnalyticsEngine.calculate_all(df)

    # AnalyticsEngine 统一输出列名（RSI 映射为 RSI14）
    EXPECTED = {
        # services/indicators（通过 IndicatorEngine）
        "MA5", "MA10", "MA20", "MA60", "MA120", "MA250",
        "DIF", "DEA", "MACD",
        "RSI14",  # ← IndicatorEngine 输出 RSI，AnalyticsEngine 统一为 RSI14
        "BOLL_MID", "BOLL_UPPER", "BOLL_LOWER",
        "K", "D", "J",
        "OBV",
        # analytics/trend
        "ADX14",
        # analytics/volatility
        "ATR14",
        # analytics/statistical
        "Hurst",
    }
    assert EXPECTED.issubset(set(result.columns)), (
        f"缺少指标列。期望: {EXPECTED}, 实际: {set(result.columns)}"
    )
    assert len(result) == len(df), "行数应与输入一致"


# ─── 测试2a：OKX 路径 ─────────────────────────────────────────────────────────

def test_calculate_all_btc_1h_year_okx_fetches(monkeypatch):
    """OKX REST 可达时，验证解析路径正确（monkeypatch 模拟）。"""
    from app.analytics import AnalyticsEngine

    # 模拟 OKX 返回格式的数据
    fake_okx_data = {
        "data": [
            # OKX 格式：[ts, open, high, low, close, vol, quote_vol, ...]
            # 最新在前，随机生成 8760 根
            [str(int((pd.Timestamp("2025-01-01") + pd.Timedelta(hours=i)).value / 1e6)),
             "50000.0", "50500.0", "49500.0", "50200.0", "100.5"]
            for i in range(8760)
        ]
    }

    def _mock_urlopen(req, timeout=None):
        class FakeResp:
            def read(self):
                import json
                return json.dumps(fake_okx_data).encode()
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
        return FakeResp()

    monkeypatch.setattr("urllib.request.urlopen", _mock_urlopen)

    import urllib.request
    url = (
        "https://www.okx.com/api/v5/market/candles"
        "?instId=BTC-USDT&bar=1h&limit=8760"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        import json
        data = json.loads(resp.read())

    assert data.get("data"), "OKX mock 应返回 data"
    rows = list(reversed(data["data"]))
    btc_df = pd.DataFrame(rows, columns=[
        "datetime", "open", "high", "low", "close", "volume"
    ])
    btc_df["datetime"] = pd.to_datetime(
        btc_df["datetime"].astype(float) / 1000, unit="s"
    )
    for col in ["open", "high", "low", "close", "volume"]:
        btc_df[col] = pd.to_numeric(btc_df[col])

    # 验证解析正确：应有 8760 根 K 线
    assert len(btc_df) == 8760, f"OKX 解析后应为 8760 行，实际 {len(btc_df)}"
    # 验证 calculate_all 在 OKX 数据上不抛异常
    result = AnalyticsEngine.calculate_all(btc_df)
    assert len(result) == 8760


# ─── 测试2b：OKX 不可达时回退到 mock ─────────────────────────────────────────

def test_calculate_all_btc_1h_year_fallback_to_mock(monkeypatch):
    """OKX 不可达时，走 mock 回退，验证 17 列全输出（warmup 除外）。
    
    monkeypatch 让 urlopen 抛出 URLError，强制走回退路径。
    """
    from app.analytics import AnalyticsEngine
    import urllib.error

    def _mock_urlopen_fail(req, timeout=None):
        raise urllib.error.URLError("Connection refused")

    monkeypatch.setattr("urllib.request.urlopen", _mock_urlopen_fail)

    import urllib.request
    btc_df = None
    try:
        url = (
            "https://www.okx.com/api/v5/market/candles"
            "?instId=BTC-USDT&bar=1h&limit=8760"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            import json
            data = json.loads(resp.read())
        if data.get("data"):
            rows = data["data"]
            rows = list(reversed(rows))
            btc_df = pd.DataFrame(rows, columns=[
                "datetime", "open", "high", "low", "close", "volume"
            ])
            btc_df["datetime"] = pd.to_datetime(
                btc_df["datetime"].astype(float) / 1000, unit="s"
            )
            for col in ["open", "high", "low", "close", "volume"]:
                btc_df[col] = pd.to_numeric(btc_df[col])
            print(f"[OKX] 成功获取 {len(btc_df)} 根 K 线")
    except Exception as e:
        print(f"[OKX] 获取失败，回退到 mock：{e}")

    # 回退：随机游走 1000 根
    if btc_df is None or len(btc_df) < 1000:
        btc_df = _make_random_walk_df(n=1000)
        print(f"[MOCK] 使用随机游走 {len(btc_df)} 根 K 线")

    result = AnalyticsEngine.calculate_all(btc_df)

    EXPECTED_COLS = {
        "MA5", "MA10", "MA20", "MA60", "MA120", "MA250",
        "DIF", "DEA", "MACD",
        "RSI14",
        "BOLL_MID", "BOLL_UPPER", "BOLL_LOWER",
        "K", "D", "J",
        "OBV",
        "ADX14",
        "ATR14",
        "Hurst",
    }

    # warmup 索引：取最后 500 根（warmup 后）
    warmup_end = max(250, 2 * 14 + 20)  # max(250, ADX_warmup=28, BOLL_warmup=20)
    post_warmup = result.iloc[warmup_end:]

    for col in EXPECTED_COLS:
        nan_count = post_warmup[col].isna().sum()
        pct_nan = nan_count / len(post_warmup) * 100
        assert nan_count == 0, (
            f"列 {col} 在 warmup 后仍有 {nan_count} 个 NaN（{pct_nan:.1f}%）"
        )


# ─── 测试3：空 DataFrame 边界 ───────────────────────────────────────────────

def test_calculate_all_empty_df_returns_empty():
    """空 df → 返回空或仅含 NaN 行（不抛异常）。"""
    from app.analytics import AnalyticsEngine

    empty = pd.DataFrame(columns=["datetime", "open", "high", "low", "close", "volume"])
    result = AnalyticsEngine.calculate_all(empty)
    # rolling(min_periods=1) 在空 Series 上返回 1 行 NaN → 行数 ≤ 1
    assert len(result) <= 1, f"空 df 应无数据行，实际 {len(result)} 行"
    # 列名应存在
    assert "MA5" in result.columns
    assert "ADX14" in result.columns
    assert "Hurst" in result.columns


# ─── 测试4：原 df 列不被修改 ────────────────────────────────────────────────

def test_calculate_all_preserves_original_columns():
    """调用后原 df 的 datetime / open / close / volume 列不变。"""
    from app.analytics import AnalyticsEngine

    df = _make_random_walk_df(n=300)
    df_orig = df.copy()

    AnalyticsEngine.calculate_all(df)

    assert (df["datetime"] == df_orig["datetime"]).all()
    assert (df["open"] == df_orig["open"]).all()
    assert (df["close"] == df_orig["close"]).all()
    assert (df["volume"] == df_orig["volume"]).all()


# ─── 测试5：幂等性 ─────────────────────────────────────────────────────────

def test_calculate_all_idempotent():
    """多次调用结果一致（指标只读，不修改索引）。"""
    from app.analytics import AnalyticsEngine

    df = _make_random_walk_df(n=300)
    r1 = AnalyticsEngine.calculate_all(df)
    r2 = AnalyticsEngine.calculate_all(df)

    pd.testing.assert_frame_equal(r1, r2)
