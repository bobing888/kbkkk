"""K线数据 API 路由"""
from fastapi import APIRouter, HTTPException, Query
from typing import Literal
from loguru import logger

from app.services.data_fetcher import data_fetcher
from app.cache import cache_get, cache_set, CacheKey
from app.db import health_check as db_health
from app.cache import health_check as redis_health

router = APIRouter(prefix="/api/v1", tags=["kline"])


@router.get("/kline/{symbol}")
async def get_kline(
    symbol: str,
    period: Literal['1m', '5m', '15m', '30m', '60m', '1d', '1w', '1M'] = Query("1d"),
    start: str = Query(None, description="起始日期 YYYYMMDD"),
    end: str = Query(None, description="结束日期 YYYYMMDD"),
    market: Literal['cn', 'us', 'crypto'] = Query("cn"),
    adjust: Literal['qfq', 'hfq', 'none'] = Query("qfq"),
):
    """
    获取 K 线数据

    示例:
    - A股日线: GET /api/v1/kline/600519?period=1d&market=cn
    - 美股日线: GET /api/v1/kline/AAPL?period=1d&market=us
    - 加密日线: GET /api/v1/kline/BTC/USDT?period=1d&market=crypto
    """
    # 1. 查缓存
    cache_key = CacheKey.kline(symbol, period, start or "default", end or "default")
    cached = await cache_get(cache_key)
    if cached:
        logger.info(f"Cache hit: {cache_key}")
        return {"source": "cache", "data": cached}

    # 2. 查数据
    try:
        df = data_fetcher.get_kline(symbol, period, start, end, market, adjust)
    except Exception as e:
        logger.error(f"Data fetch error: {e}")
        raise HTTPException(status_code=500, detail=f"数据获取失败: {str(e)}")

    # 3. 转 JSON
    data = df.to_dict(orient="records")
    for row in data:
        if "datetime" in row and hasattr(row["datetime"], "isoformat"):
            row["datetime"] = row["datetime"].isoformat()

    # 4. 写缓存（5 分钟）
    await cache_set(cache_key, data, ttl=300)

    return {"source": "fresh", "count": len(data), "data": data}


@router.get("/health")
async def health():
    """健康检查"""
    db_ok = await db_health()
    redis_ok = await redis_health()
    return {
        "status": "ok" if (db_ok and redis_ok) else "degraded",
        "database": "ok" if db_ok else "down",
        "redis": "ok" if redis_ok else "down"
    }
