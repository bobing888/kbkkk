"""数据库连接管理 - PostgreSQL + SQLAlchemy 2.0 async"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
import os
from typing import AsyncGenerator
from loguru import logger

# 数据库配置
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://kline:kline_pass@localhost:5432/kline_db"
)

# 异步引擎
engine = create_async_engine(
    DATABASE_URL,
    echo=False,                    # 生产环境关闭 SQL 日志
    pool_size=10,                  # 连接池大小
    max_overflow=20,               # 超出时最大连接数
    pool_pre_ping=True,            # 连接前 ping（避免断连）
    pool_recycle=3600,             # 1 小时回收连接
)

# 异步 Session 工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# ORM 基类（从 models 导入以避免循环 + 保证 metadata 完整）
from app.models import Base as _ModelBase

# 兼容旧代码：用 _ModelBase 作为 db.Base
Base = _ModelBase


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：获取数据库 session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


async def init_db():
    """初始化数据库（创建表）

    ⚠️ ai-trader 教训：之前 main.py 在数据库不可用时直接 raise，
    导致整个服务挂掉。kline-system 改成：warn + 继续启动，让 API 至少可访问 /docs
    """
    try:
        async with engine.begin() as conn:
            # 检查扩展
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pg_trgm"'))
            # 创建表
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created/verified (5 tables: klines/indicators/signals/orders/calibration_models)")
    except Exception as e:
        logger.warning(f"Database init failed: {e} (继续运行，仅 DB API 不可用)")
        # 不 raise，让服务至少能启动


async def close_db():
    """关闭数据库连接"""
    await engine.dispose()
    logger.info("Database connection closed")


async def health_check() -> bool:
    """数据库健康检查"""
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False