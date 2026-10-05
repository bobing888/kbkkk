"""auto-follow 自动跟单系统 — M3

模块：
- position_sizer  : 仓位计算（Signal → PositionSize）
- risk_manager    : 5 门控风控（RiskManager）
- follow_engine   : 调度器（Signal → Order → TradeLog）
- follow_worker   : asyncio worker（订阅 bus + 监控 SL/TP）
"""
from __future__ import annotations

from app.follow.follow_engine import CloseResult, ExecutionResult, FollowEngine
from app.follow.follow_worker import FollowWorker
from app.follow.position_sizer import PositionSize, PositionSizer
from app.follow.risk_manager import AccountState, Position, RiskManager

__all__ = [
    "PositionSizer",
    "PositionSize",
    "RiskManager",
    "AccountState",
    "Position",
    "FollowEngine",
    "ExecutionResult",
    "CloseResult",
    "FollowWorker",
]
