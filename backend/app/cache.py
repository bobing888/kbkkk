"""Redis 缓存管理"""
import os
import json
from typing import Any, Optional
import redis.asyncio as redis
from loguru import logger

# Redis 配置
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# 创建连接池（init_redis 之前 client 可能未就绪；用 None 标记降级）
pool: Optional[redis.ConnectionPool] = None
client: Optional[redis.Redis] = None


async def init_redis() -> bool:
    """初始化 Redis 连接。

    Redis **可选**——连接失败时记录警告而非抛异常，
    并将 client 设为 None，后续 cache_* 自动降级。
    参考：KB github-HKUDS-AI-Trader.md §4 "Redis is optional"

    Returns:
        True 连接成功；False 服务降级到无 Redis 模式（仅 cache_* 失效，业务继续）。
    """
    global pool, client
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    pool = redis.ConnectionPool.from_url(redis_url, max_connections=20, decode_responses=True)
    client = redis.Redis(connection_pool=pool)
    try:
        await client.ping()
        logger.info("Redis connected")
        return True
    except Exception as e:
        logger.warning(
            f"Redis connection failed: {e}. "
            "Service continues in degraded mode (cache disabled)."
        )
        client = None  # 降级：后续 cache_* 走 None 分支
        return False


async def close_redis():
    """关闭 Redis 连接（无 client 时跳过）"""
    global client, pool
    if client is not None:
        try:
            await client.close()
        except Exception as e:
            logger.warning(f"Redis close error (ignored): {e}")
        client = None
    if pool is not None:
        try:
            await pool.disconnect()
        except Exception as e:
            logger.warning(f"Redis pool disconnect error (ignored): {e}")
        pool = None
    logger.info("Redis connection closed")


def _is_available() -> bool:
    """client 是否可用（未降级）。"""
    return client is not None


async def cache_get(key: str) -> Optional[Any]:
    """获取缓存（client 不可用时直接返回 None，业务继续）。"""
    if not _is_available():
        return None
    try:
        value = await client.get(key)  # type: ignore[union-attr]
        if value:
            return json.loads(value)
        return None
    except Exception as e:
        logger.error(f"Cache get error: {e}")
        return None


async def cache_set(key: str, value: Any, ttl: int = 300) -> bool:
    """设置缓存（默认 5 分钟过期；client 不可用时返回 False 但不抛异常）。"""
    if not _is_available():
        return False
    try:
        await client.set(key, json.dumps(value, default=str), ex=ttl)  # type: ignore[union-attr]
        return True
    except Exception as e:
        logger.error(f"Cache set error: {e}")
        return False


async def cache_delete(key: str) -> bool:
    """删除缓存（client 不可用时返回 False 但不抛异常）。"""
    if not _is_available():
        return False
    try:
        await client.delete(key)  # type: ignore[union-attr]
        return True
    except Exception as e:
        logger.error(f"Cache delete error: {e}")
        return False


async def health_check() -> bool:
    """Redis 健康检查（client 不可用时返回 False 而非抛异常）。"""
    if not _is_available():
        return False
    try:
        await client.ping()  # type: ignore[union-attr]
        return True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return False


# 缓存 key 约定
class CacheKey:
    """统一缓存 key 管理"""

    @staticmethod
    def kline(symbol: str, period: str, start: str, end: str) -> str:
        """K线数据缓存"""
        return f"kline:{symbol}:{period}:{start}:{end}"

    @staticmethod
    def realtime_quote(symbol: str) -> str:
        """实时行情"""
        return f"quote:{symbol}"

    @staticmethod
    def signal(symbol: str) -> str:
        """最新信号"""
        return f"signal:{symbol}"

    @staticmethod
    def indicator(symbol: str, period: str) -> str:
        """指标数据"""
        return f"indicator:{symbol}:{period}"
