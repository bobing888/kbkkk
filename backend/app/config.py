"""全局配置 - Pydantic Settings"""
from pydantic_settings import BaseSettings
from typing import Literal
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置"""

    # 应用
    app_name: str = "K线趋势分析系统"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # 服务
    host: str = "0.0.0.0"
    port: int = 8000

    # 数据库
    database_url: str = "postgresql+asyncpg://kline:kline_pass@localhost:5432/kline_db"
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl: int = 300  # 5 分钟

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # 数据获取
    data_request_timeout: int = 30  # 秒
    data_retry_times: int = 3

    # 风控
    max_single_position: float = 0.30  # 单股 ≤ 30%
    max_total_position: float = 0.70   # 总仓 ≤ 70%
    max_single_loss: float = 0.02      # 单笔 ≤ 2%
    min_profit_loss_ratio: float = 2.0  # 盈亏比 ≥ 2:1

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
