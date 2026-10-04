"""FastAPI 主入口"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import get_settings
from app.db import init_db, close_db
from app.cache import init_redis, close_redis
from app.routers import kline

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    # 启动
    await init_redis()
    try:
        await init_db()
    except Exception as e:
        logger.warning(f"Database init failed: {e} (继续运行，仅 API 不可用)")

    yield

    # 关闭
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

# 路由
app.include_router(kline.router)


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
