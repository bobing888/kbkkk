"""API 路由聚合。

参考 KB github-HKUDS-AI-Trader.md §4 "Modular route registration"：
主入口只做组装，每个领域单独 router。M3/M4 上线后（signal/follow/order）只需在此加 import 与 include_router。
"""
from fastapi import FastAPI

from app.routers import kline as kline_module
from app.routers import analysis as analysis_module


def register_routers(app: FastAPI) -> None:
    """注册所有领域路由。"""
    app.include_router(kline_module.router)
    app.include_router(analysis_module.router)


__all__ = ["register_routers"]