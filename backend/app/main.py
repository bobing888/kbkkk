"""FastAPI 主入口"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import get_settings
from app.db import init_db, close_db
from app.cache import init_redis, close_redis
from app.routers import register_routers

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。

    参考 KB github-HKUDS-AI-Trader.md §4 "Async lifespan for services":
    启动顺序与关闭顺序相反，且降级模式不应阻塞启动。
    """
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    # 启动：Redis 失败仅 warn，不 raise（与 init_db 一致）
    redis_ok = await init_redis()
    try:
        await init_db()
    except Exception as e:
        logger.warning(f"Database init failed: {e} (继续运行，仅 API 不可用)")
    logger.info(
        f"Startup complete. redis={'ok' if redis_ok else 'degraded'}."
    )

    yield

    # 关闭：与启动顺序相反
    await close_redis()
    await close_db()
    logger.info("Shutdown complete")


# 创建应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="专业的 K 线趋势分析系统 - 覆盖 A 股 / 美股 / 加密货币",
    lifespan=lifespan,
    debug=settings.debug
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由（聚合所有领域模块，参考 KB github-HKUDS-AI-Trader.md §4）
register_routers(app)


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "agents": [
            "kline-analyst", "kline-frontend", "kline-backend",
            "kline-pm", "kline-learner", "kline-orchestrator"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
