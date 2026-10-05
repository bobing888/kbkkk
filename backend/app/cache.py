"""Redis 缓存管理"""
import os
import json
import hashlib
from typing import Any, Optional
import redis.asyncio as redis
from loguru import logger

# Redis 配置
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# 创建连接池
pool = redis.ConnectionPool.from_url(REDIS_URL, max_connections=20, decode_responses=True)
client = redis.Redis(connection_pool=pool)


async def init_redis() -> bool:
    """初始化 Redis 连接。

    Redis **可选**——连接失败时记录警告而非抛异常。
    参考：KB github-HKUDS-AI-Trader.md §4 "Redis is optional"

    Returns:
        True 连接成功；False 服务降级到无 Redis 模式（仅 cache_* 失效，业务继续）。
    """
    try:
        await client.ping()
        logger.info("Redis connected")
        return True
    except Exception as e:
        logger.warning(
            f"Redis connection failed: {e}. "
            "Service continues in degraded mode (cache disabled)."
        )
        return False


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
    """统一缓存 key 管理。

    移植自 KB github-HKUDS-AI-Trader.md §4 "Database-scoped cache keys":
    > Keys include a configured prefix and database-scope hash,
    > preventing accidental reuse across deployments sharing Redis.

    三段式：`{PREFIX}:{SCOPE}:{...}`
    - PREFIX: 环境变量 KBKK_CACHE_PREFIX，默认 "kbkk"
    - SCOPE: KBKK_DB_URL 的前 8 位 md5（按部署隔离，多环境共享 Redis 不撞 key）
    - ...: 具体 key 内容

    SCOPE 在每次访问时**重新读取**环境变量，支持 monkeypatch（process / dev)
    """

    PREFIX = os.getenv("KBKK_CACHE_PREFIX", "kbkk")

    @classmethod
    def _scope(cls) -> str:
        """每次访问时计算 SCOPE（支持 monkeypatch + 配置变更）。"""
        return hashlib.md5(
            os.getenv("KBKK_DB_URL", "").encode()
        ).hexdigest()[:8]

    @classmethod
    def _wrap(cls, suffix: str) -> str:
        """三段式拼接。"""
        return f"{cls.PREFIX}:{cls._scope()}:{suffix}"

    @staticmethod
    def kline(symbol: str, period: str, start: str, end: str) -> str:
        """K线数据缓存"""
        return CacheKey._wrap(f"kline:{symbol}:{period}:{start}:{end}")

    @staticmethod
    def realtime_quote(symbol: str) -> str:
        """实时行情"""
        return CacheKey._wrap(f"quote:{symbol}")

    @staticmethod
    def signal(symbol: str) -> str:
        """最新信号"""
        return CacheKey._wrap(f"signal:{symbol}")

    @staticmethod
    def indicator(symbol: str, period: str) -> str:
        """指标数据"""
        return CacheKey._wrap(f"indicator:{symbol}:{period}")

    # 向后兼容：保留旧的 _SCOPE 静态访问（测试可能引用）
    @classmethod
    @property
    def _SCOPE(cls) -> str:  # type: ignore[override]
        return cls._scope()
