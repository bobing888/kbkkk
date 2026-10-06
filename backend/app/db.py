"""数据库连接管理 - PostgreSQL / SQLite + SQLAlchemy 2.0 async

PR-3 (SPEC v2): 支持 SQLite 用于 dev/test 环境，无需 PostgreSQL。
通过 DB_BACKEND=sqlite|postgres 切换，默认 postgres（保持生产兼容）。

KB 参考:
- aitrader-implementation-ready.md §"DB backend selection"
- vibetrading-implementation-ready.md §"Local-first DB fallback"
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
import os
from typing import AsyncGenerator
from loguru import logger

# ── 数据库配置 ────────────────────────────────────────────────────────
# 通过 DB_BACKEND 切换：sqlite 用于 dev/test（零依赖），postgres 用于生产
DB_BACKEND = os.getenv("DB_BACKEND", "postgres").lower()

if DB_BACKEND == "sqlite":
    # SQLite 文件路径（默认 ./data/kline.db）
    SQLITE_PATH = os.getenv("SQLITE_PATH", "./data/kline.db")
    # aiosqlite 是异步 driver，支持 SQLAlchemy async
    DATABASE_URL = f"sqlite+aiosqlite:///{SQLITE_PATH}"
    # SQLite 单文件无连接池概念，关闭连接池特性
    _ENGINE_KWARGS = {
        "echo": False,
        "connect_args": {"check_same_thread": False},
    }
else:
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://kline:kline_pass@localhost:5432/kline_db"
    )
    _ENGINE_KWARGS = {
        "echo": False,
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,
        "pool_recycle": 3600,
    }

logger.info(f"[db] backend={DB_BACKEND}, url={DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}")

# ── 异步引擎 ──────────────────────────────────────────────────────────
engine = create_async_engine(DATABASE_URL, **_ENGINE_KWARGS)

# ── 异步 Session 工厂 ──────────────────────────────────────────────────
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

    PR-3 修订:
    - SQLite: 跳过 PG 扩展（uuid-ossp / pg_trgm），仅 create_all
    - Postgres: 原行为不变
    """
    try:
        async with engine.begin() as conn:
            if DB_BACKEND == "sqlite":
                # SQLite 无扩展概念；aiosqlite 通过 PRAGMA 启用外键
                logger.info("[db] SQLite mode: skipping PG extensions, creating tables")
                await conn.execute(text("PRAGMA foreign_keys=ON"))
            else:
                # PostgreSQL: 创建 PG 扩展（幂等）
                await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
                await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pg_trgm"'))
            # 创建表（跨 backend 通用）
            await conn.run_sync(Base.metadata.create_all)
            logger.info(f"Database tables created/verified (backend={DB_BACKEND})")
    except Exception as e:
        logger.warning(f"Database init failed: {e} (继续运行，仅 DB API 不可用)")


async def close_db():
    """关闭数据库连接"""
    await engine.dispose()
    logger.info(f"Database connection closed (backend={DB_BACKEND})")


async def health_check() -> bool:
    """数据库健康检查"""
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False