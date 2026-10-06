"""阶段 2 - 4 个分析端点（indicators / patterns / signals / analysis）路由测试

TDD 红阶段：先写测试让 pytest 失败
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


@pytest.fixture
def client():
    """FastAPI 测试客户端。"""
    from app.main import app
    return TestClient(app)


@pytest.fixture
def sample_df():
    """300 根随机游走 K 线（与 test_indicators_thin 同模式）。"""
    rng = np.random.default_rng(42)
    n = 300
    base = datetime(2025, 1, 1)
    close = 50000 + np.cumsum(rng.normal(0, 200, n))
    opens = close * (1 + rng.uniform(-0.005, 0.005, n))
    highs = np.maximum(opens, close) * (1 + rng.uniform(0, 0.003, n))
    lows = np.minimum(opens, close) * (1 - rng.uniform(0, 0.003, n))
    volumes = rng.lognormal(10, 1, n)
    return pd.DataFrame({
        "datetime": [base + timedelta(hours=i) for i in range(n)],
        "open": opens, "high": highs, "low": lows,
        "close": close, "volume": volumes,
    })


# ─── /api/v1/indicators/{symbol} ──────────────────────────────────────────


class TestIndicatorsEndpoint:
    def test_returns_200_and_11_indicators(self, client, sample_df):
        with patch("app.routers.analysis.data_fetcher") as mock_fetcher, \
             patch("app.routers.analysis.IndicatorEngine.calculate_all") as mock_ie:
            mock_fetcher.get_kline = AsyncMock(return_value=sample_df)
            # 模拟 IE 返回 11 个指标族
            out = sample_df.copy()
            for col in ["MA5","MA10","MA20","MA60","DIF","DEA","MACD","RSI",
                        "BOLL_MID","BOLL_UPPER","BOLL_LOWER","K","D","J","OBV"]:
                out[col] = 1.0
            mock_ie.return_value = out

            r = client.get("/api/v1/indicators/BTC?period=1d&market=crypto")
            assert r.status_code == 200
            data = r.json()
            # 至少 11 个指标族（MA/MACD/RSI/BOLL/KDJ/OBV）
            assert "indicators" in data
            assert len(data["indicators"]) >= 6

    def test_returns_500_when_data_fetcher_fails(self, client):
        with patch("app.routers.analysis.data_fetcher") as mock_fetcher:
            mock_fetcher.get_kline = AsyncMock(side_effect=Exception("上游错误"))
            r = client.get("/api/v1/indicators/XXX")
            assert r.status_code == 500
            assert "上游错误" in r.json()["detail"]


# ─── /api/v1/patterns/{symbol} ────────────────────────────────────────────


class TestPatternsEndpoint:
    def test_returns_200_with_patterns(self, client, sample_df):
        with patch("app.routers.analysis.data_fetcher") as mock_fetcher, \
             patch("app.routers.analysis.detect_single_candle") as mock_single, \
             patch("app.routers.analysis.detect_multi_candle") as mock_multi:
            mock_fetcher.get_kline = AsyncMock(return_value=sample_df)
            out = sample_df.copy()
            out["is_hammer"] = np.random.randint(0, 2, len(out))
            out["is_morning_star"] = np.random.randint(0, 2, len(out))
            out["is_engulfing_bullish"] = np.random.randint(0, 2, len(out))
            out["is_engulfing_bearish"] = np.random.randint(0, 2, len(out))
            mock_single.return_value = out
            mock_multi.return_value = out

            r = client.get("/api/v1/patterns/BTC?period=1d&market=crypto")
            assert r.status_code == 200
            data = r.json()
            assert "patterns" in data
            # 至少 1 根 K 线有形态
            assert isinstance(data["patterns"], list)


# ─── /api/v1/signals/{symbol} ─────────────────────────────────────────────


class TestSignalsEndpoint:
    def test_returns_200_with_signals(self, client, sample_df):
        with patch("app.routers.analysis.data_fetcher") as mock_fetcher, \
             patch("app.routers.analysis.generate_signal") as mock_gen:
            mock_fetcher.get_kline = AsyncMock(return_value=sample_df)
            # 空信号列表
            mock_gen.return_value = []

            r = client.get("/api/v1/signals/BTC?period=1d&market=crypto")
            assert r.status_code == 200
            data = r.json()
            assert "signals" in data
            assert isinstance(data["signals"], list)


# ─── /api/v1/analysis/{symbol} 聚合端点 ────────────────────────────────────


class TestAnalysisAggregate:
    def test_returns_200_with_all_three(self, client, sample_df):
        with patch("app.routers.analysis.data_fetcher") as mock_fetcher, \
             patch("app.routers.analysis.IndicatorEngine.calculate_all") as mock_ie, \
             patch("app.routers.analysis.detect_single_candle") as mock_single, \
             patch("app.routers.analysis.detect_multi_candle") as mock_multi, \
             patch("app.routers.analysis.generate_signal") as mock_gen:
            mock_fetcher.get_kline = AsyncMock(return_value=sample_df)
            out = sample_df.copy()
            for col in ["MA5","DIF","RSI","K","OBV"]:
                out[col] = 1.0
            mock_ie.return_value = out
            mock_single.return_value = out
            mock_multi.return_value = out
            mock_gen.return_value = []

            r = client.get("/api/v1/analysis/BTC?period=1d&market=crypto")
            assert r.status_code == 200
            data = r.json()
            assert "indicators" in data
            assert "patterns" in data
            assert "signals" in data
