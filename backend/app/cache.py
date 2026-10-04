"""Redis 缓存管理"""
import os
import json
from typing import Any, Optional
import redis.asyncio as redis
from loguru import logger

# Redis 配置
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# 创建连接池
pool = redis.ConnectionPool.from_url(REDIS_URL, max_connections=20, decode_responses=True)
client = redis.Redis(connection_pool=pool)


async def init_redis():
    """初始化 Redis 连接"""
    try:
        await client.ping()
        logger.info("Redis connected")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        raise


async def close_redis():
    """关闭 Redis 连接"""
    await client.close()
    await pool.disconnect()
    logger.info("Redis connection closed")


async def cache_get(key: str) -> Optional[Any]:
    """获取缓存"""
    try:
        value = await client.get(key)
        if value:
            return json.loads(value)
        return None
    except Exception as e:
        logger.error(f"Cache get error: {e}")
        return None


async def cache_set(key: str, value: Any, ttl: int = 300) -> bool:
    """设置缓存（默认 5 分钟过期）"""
    try:
        await client.set(key, json.dumps(value, default=str), ex=ttl)
        return True
    except Exception as e:
        logger.error(f"Cache set error: {e}")
        return False


async def cache_delete(key: str) -> bool:
    """删除缓存"""
    try:
        await client.delete(key)
        return True
    except Exception as e:
        logger.error(f"Cache delete error: {e}")
        return False


async def health_check() -> bool:
    """Redis 健康检查"""
    try:
        await client.ping()
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
