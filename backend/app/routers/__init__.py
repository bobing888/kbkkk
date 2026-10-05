"""API 路由聚合。

参考 KB github-HKUDS-AI-Trader.md §4 "Modular route registration"：
主入口只做组装，每个领域单独 router。M3/M4 上线后（signal/follow/order）只需在此加 import 与 include_router。
"""
from fastapi import FastAPI

from app.routers import kline as kline_module


def register_routers(app: FastAPI) -> None:
    """注册所有领域路由。当前仅 kline，未来扩展：

    ```python
    from app.routers import signal, order, follow, backtest
    app.include_router(signal.router, prefix="/api/v1/signal", tags=["信号"])
    app.include_router(order.router, prefix="/api/v1/order", tags=["跟单"])
    app.include_router(follow.router, prefix="/api/v1/follow", tags=["回测"])
    app.include_router(backtest.router, prefix="/api/v1/backtest", tags=["回测"])
    ```
    """
    app.include_router(kline_module.router)


__all__ = ["register_routers"]