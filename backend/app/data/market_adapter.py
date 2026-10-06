"""多市场适配层 - MarketAdapter 抽象基类 + 仅 CryptoMarketAdapter 实现

SPEC v2 §1：聚焦 BTC/ETH（crypto），CnMarketAdapter / UsMarketAdapter 已删除。
Crypto 24/7 流动性检测、复权（币本位天然复权）、配色方案保留。
"""
from __future__ import annotations

import os
import pandas as pd
from abc import ABC, abstractmethod
from datetime import date, datetime, time, timedelta
from typing import Literal, TypedDict


# ──────────────── 类型定义 ────────────────

class NormalizedSymbol(TypedDict):
    """规范化后的 symbol 元信息"""
    exchange: str
    ticker: str
    market: str


class ColorScheme(TypedDict):
    """多市场配色方案"""
    up_color: str       # 上涨颜色（hex）
    down_color: str     # 下跌颜色（hex）
    bullish: str        # 看涨别名


# ──────────────── 抽象基类（保留供 v3 扩展）────────────

class MarketAdapter(ABC):
    """市场适配器抽象基类（仅 crypto 实现；为未来扩展保留接口）

    统一接口：
    - Symbol 格式差异
    - 交易时间差异（含午休 / 盘前盘后 / 24/7）
    - 复权规则差异
    - 涨跌停规则差异
    """

    @abstractmethod
    def normalize_symbol(self, symbol: str) -> NormalizedSymbol:
        ...

    @abstractmethod
    def get_trading_hours(self, trading_date: date) -> tuple[datetime, datetime]:
        ...

    @abstractmethod
    def get_adjust_factor(
        self,
        symbol: str,
        target_date: date,
        adjust: Literal["qfq", "hfq", "none"] = "qfq",
    ) -> float:
        ...

    @abstractmethod
    def detect_limit_up_down(
        self,
        df: pd.DataFrame,
        trading_date: date,
        symbol: str = "",
    ) -> pd.DataFrame:
        ...

    @abstractmethod
    def is_trading_day(self, target_date: date) -> bool:
        ...

    # ── 子类共享辅助方法 ──

    def _pct_change(self, df: pd.DataFrame) -> pd.Series:
        """从 DataFrame 计算涨跌幅（pct_change 列存在则用，不存在则算）"""
        if "pct_change" in df.columns:
            return df["pct_change"]
        if "close" not in df.columns:
            return pd.Series(0.0, index=df.index)
        return df["close"].pct_change().fillna(0) * 100


# ──────────────── 加密货币适配器（v2 唯一实现）────────────

class CryptoMarketAdapter(MarketAdapter):
    """加密货币市场适配器（SPEC v2 §1 唯一实现）

    规则：
    - Symbol：交易所:base/quote（如 OKX:BTC/USDT）
    - 交易时间：24/7 无休
    - 涨跌停：无涨跌停
    - 复权：无复权（币本位天然复权）

    部署（feat/okx-default-exchange）：
    - 默认交易所读 KBKKK_CRYPTO_EXCHANGE 环境变量，缺省 "okx"
    - 显式前缀（OKX:BTC/USDT / BINANCE:BTC/USDT）优先级高于环境变量
    - 回滚：设 KBKKK_CRYPTO_EXCHANGE=binance
    """

    def normalize_symbol(self, symbol: str) -> NormalizedSymbol:
        sym = symbol.strip().upper()
        if "/" in sym:
            ticker = sym
            exchange = self._detect_exchange(sym)
        else:
            ticker = f"{sym}/USDT"
            exchange = self._default_exchange()
        return NormalizedSymbol(exchange=exchange, ticker=ticker, market="crypto")

    def _default_exchange(self) -> str:
        """每次调用读环境变量（支持 monkeypatch / hot reload）"""
        return os.getenv("KBKKK_CRYPTO_EXCHANGE", "okx").lower()

    def _detect_exchange(self, symbol: str) -> str:
        """根据 symbol 推断交易所（显式前缀优先于环境变量）"""
        upper = symbol.upper()
        if "BINANCE" in upper:
            return "binance"
        if "OKX" in upper or "OKEX" in upper:
            return "okx"
        if "BYBIT" in upper:
            return "bybit"
        return self._default_exchange()

    def get_trading_hours(self, trading_date: date) -> list[tuple[datetime, datetime]]:
        """加密 24/7：返回全天（单段 list[tuple] 保持与历史 Adapter 契约一致）"""
        return [
            (
                datetime.combine(trading_date, time(0, 0)),
                datetime.combine(trading_date, time(23, 59, 59)),
            )
        ]

    def get_adjust_factor(
        self,
        symbol: str,
        target_date: date,
        adjust: Literal["qfq", "hfq", "none"] = "qfq",
    ) -> float:
        # 加密货币不复权（币本位天然复权）
        return 1.0

    def detect_limit_up_down(
        self,
        df: pd.DataFrame,
        trading_date: date,
        symbol: str = "",
    ) -> pd.DataFrame:
        df = df.copy()
        df["limit_type"] = "none"
        return df

    def is_trading_day(self, target_date: date) -> bool:
        # 加密货币 24/7 每天都是交易日
        return True


# ──────────────── 工厂函数（v2：仅 crypto）────────────

def get_market_adapter(market: Literal["crypto"]) -> MarketAdapter:
    """工厂函数：v2 仅支持 crypto，其他市场抛 ValueError（fail-fast）。"""
    if market != "crypto":
        raise ValueError(
            f"Unsupported market: {market!r}. "
            "SPEC v2 §1: kbkkk only supports BTC/ETH (crypto). "
            "cn/us 已删除。"
        )
    return CryptoMarketAdapter()


# ──────────────── 颜色方案（v2：仅 crypto 1 套）────────────

_CRYPTO_COLOR: ColorScheme = ColorScheme(
    up_color="#00FF00",    # 加密绿涨
    down_color="#FF0000",   # 加密红跌
    bullish="green",
)


def get_color_scheme(market: Literal["crypto"]) -> ColorScheme:
    """v2：仅返回 crypto 配色方案，其他 market 抛 ValueError。"""
    if market != "crypto":
        raise ValueError(
            f"Unsupported market: {market!r}. "
            "SPEC v2 §1: kbkkk only supports BTC/ETH (crypto)."
        )
    return _CRYPTO_COLOR