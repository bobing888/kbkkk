"""K线 router cache 弹性测试 — PR-4 回归测试

验证即使 Redis 缓存层完全不可用（mock 抛异常），
K线 endpoint 仍能返回 200 + 业务数据，不应返回 5xx。

覆盖场景：
1. cache_get 抛异常 → 走 fresh 路径
2. cache_set 抛异常 → 仍返回 200
3. cache 全挂（get 和 set 都异常）→ 仍返回 200
4. cache 正常工作（smoke test，确保改动不破坏 hit 路径）

注: 直接测 kline router 而非 main app，避开 .env 中
GRAFANA_PASSWORD 与 pydantic v2 Settings 校验冲突（已有问题，
不在本 PR 范围）。
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.routers.kline import router as kline_router
from fastapi import FastAPI


# ── 客户端 fixture ────────────────────────────────────────────────────────

@pytest.fixture
def app() -> FastAPI:
    """构造最小 FastAPI app（只含 kline router，避开 main app 的 .env 校验问题）。"""
    app = FastAPI()
    app.include_router(kline_router)
    return app


@pytest_asyncio.fixture
async def client(app: FastAPI):
    """Async HTTP 客户端（httpx + ASGITransport，无 TestClient 启动开销）。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_kline_df() -> pd.DataFrame:
    """构造 K线 DataFrame（mock data_fetcher 返回）。"""
    return pd.DataFrame({
        "datetime": pd.date_range("2024-01-01", periods=3),
        "open": [100.0, 102.0, 101.0],
        "high": [101.0, 103.0, 102.5],
        "low": [99.5, 101.5, 100.5],
        "close": [100.5, 102.5, 101.5],
        "volume": [1000.0, 1200.0, 1100.0],
    })


# ── 测试 1：cache_get 抛异常 → 走 fresh 路径 ──────────────────────────

@pytest.mark.asyncio
async def test_cache_get_failure_falls_through_to_fresh(
    client: AsyncClient, sample_kline_df: pd.DataFrame
) -> None:
    """cache_get 抛异常时，不应返回 5xx，应走 fresh 路径返回 200。"""
    with patch("app.routers.kline.cache_get", new_callable=AsyncMock,
               side_effect=ConnectionError("Redis pool exhausted")):
        with patch("app.routers.kline.data_fetcher") as mock_fetcher:
            mock_fetcher.get_kline.return_value = sample_kline_df
            with patch("app.routers.kline.get_market_adapter") as mock_adapter:
                mock_adapter.return_value.detect_limit_up_down.return_value = sample_kline_df

                response = await client.get("/api/v1/kline/BTCUSDT?period=1d&market=crypto")

    assert response.status_code == 200, f"应返回 200，实际 {response.status_code}: {response.text}"
    body = response.json()
    assert body["source"] == "fresh", f"cache 失败应走 fresh，实际 {body['source']}"
    assert body["count"] == 3
    assert len(body["data"]) == 3


# ── 测试 2：cache_set 抛异常 → 仍返回 200 ──────────────────────────

@pytest.mark.asyncio
async def test_cache_set_failure_still_returns_data(
    client: AsyncClient, sample_kline_df: pd.DataFrame
) -> None:
    """cache_set 抛异常时，K线响应不应被破坏。"""
    with patch("app.routers.kline.cache_get", new_callable=AsyncMock, return_value=None):
        with patch("app.routers.kline.cache_set", new_callable=AsyncMock,
                   side_effect=ConnectionError("Redis disconnected")):
            with patch("app.routers.kline.data_fetcher") as mock_fetcher:
                mock_fetcher.get_kline.return_value = sample_kline_df
                with patch("app.routers.kline.get_market_adapter") as mock_adapter:
                    mock_adapter.return_value.detect_limit_up_down.return_value = sample_kline_df

                    response = await client.get("/api/v1/kline/ETHUSDT?period=1d&market=crypto")

    assert response.status_code == 200, f"应返回 200，实际 {response.status_code}: {response.text}"
    body = response.json()
    assert body["source"] == "fresh"
    assert body["count"] == 3


# ── 测试 3：cache 全挂（get 和 set 都异常）→ 仍返回 200 ───────────

@pytest.mark.asyncio
async def test_cache_completely_dead_still_responds(
    client: AsyncClient, sample_kline_df: pd.DataFrame
) -> None:
    """cache_get 和 cache_set 都抛异常 → endpoint 仍 200。"""
    with patch("app.routers.kline.cache_get", new_callable=AsyncMock,
               side_effect=RuntimeError("Redis down")):
        with patch("app.routers.kline.cache_set", new_callable=AsyncMock,
                   side_effect=RuntimeError("Redis down")):
            with patch("app.routers.kline.data_fetcher") as mock_fetcher:
                mock_fetcher.get_kline.return_value = sample_kline_df
                with patch("app.routers.kline.get_market_adapter") as mock_adapter:
                    mock_adapter.return_value.detect_limit_up_down.return_value = sample_kline_df

                    response = await client.get("/api/v1/kline/SOLUSDT?period=60m&market=crypto")

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "fresh"
    assert body["count"] == 3


# ── 测试 4：cache hit 路径（smoke test，防 regression）─────────────

@pytest.mark.asyncio
async def test_cache_hit_path_unchanged(client: AsyncClient) -> None:
    """cache 命中时（return 非 None），不应调用 data_fetcher。"""
    cached_data = [{"datetime": "2024-01-01T00:00:00", "close": 100.0}]
    with patch("app.routers.kline.cache_get", new_callable=AsyncMock, return_value=cached_data):
        with patch("app.routers.kline.data_fetcher") as mock_fetcher:
            # data_fetcher 不应被调用
            response = await client.get("/api/v1/kline/AAPL?period=1d&market=us")

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "cache"
    assert body["data"] == cached_data
    mock_fetcher.get_kline.assert_not_called()


# ── 测试 5：data_fetcher 失败 → 500（确认错误处理未破坏）────────

@pytest.mark.asyncio
async def test_data_fetcher_failure_returns_500(client: AsyncClient) -> None:
    """data_fetcher 抛业务异常时（不是 cache 错误），仍应返回 500。

    防止 PR-4 改动误把 data_fetcher 异常也吞掉。
    """
    with patch("app.routers.kline.cache_get", new_callable=AsyncMock, return_value=None):
        with patch("app.routers.kline.data_fetcher") as mock_fetcher:
            mock_fetcher.get_kline.side_effect = ValueError("invalid symbol")

            response = await client.get("/api/v1/kline/INVALID?period=1d&market=us")

    assert response.status_code == 500
    assert "数据获取失败" in response.json()["detail"]
