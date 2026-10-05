"""多市场适配层 - MarketAdapter 抽象基类与三个市场实现

借鉴 ai-trader 多市场交互矩阵教训 #9（多市场配色 × 数据格式 × 涨跌停逻辑）。

本模块设计原则（来自 backend-architect 决策框架）：
- 抽象基类定义统一接口（normalize_symbol / get_trading_hours / get_adjust_factor / detect_limit_up_down / is_trading_day）
- 三个市场各实现差异（A股含涨跌停+午休+复权 / 美股含盘前盘后 / 加密 24/7）
- 工厂函数根据 market 参数返回对应实现（依赖注入友好）
- 颜色方案根据市场返回配色规则（A 股红涨绿跌 / 美股加密绿涨红跌）
"""
from __future__ import annotations

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


# ──────────────── 抽象基类 ────────────────

class MarketAdapter(ABC):
    """多市场适配器抽象基类

    统一接口适配 A 股 / 美股 / 加密三个市场，屏蔽：
    - Symbol 格式差异（600519 vs AAPL vs BTC/USDT）
    - 交易时间差异（含午休 / 盘前盘后 / 24/7）
    - 复权规则差异（qfq/hfq vs 无复权）
    - 涨跌停规则差异（A股±10% vs 无涨跌停）
    """

    @abstractmethod
    def normalize_symbol(self, symbol: str) -> NormalizedSymbol:
        """将原始 symbol 规范化为 {exchange, ticker, market}"""
        ...

    @abstractmethod
    def get_trading_hours(self, trading_date: date) -> tuple[datetime, datetime] | tuple[None, None]:
        """返回指定日期的交易时段（UTC）

        Args:
            trading_date: 目标日期

        Returns:
            (start, end): 交易时段（Naive datetime，本地时间）
            (None, None): 非交易日
        """
        ...

    @abstractmethod
    def get_adjust_factor(
        self,
        symbol: str,
        target_date: date,
        adjust: Literal["qfq", "hfq", "none"] = "qfq",
    ) -> float:
        """获取复权因子

        Args:
            symbol: 标的代码
            target_date: 目标日期
            adjust: 复权方式（部分市场忽略此参数）

        Returns:
            复权因子（A股 qfq>1, hfq>1；美股/加密恒为 1.0）
        """
        ...

    @abstractmethod
    def detect_limit_up_down(
        self,
        df: pd.DataFrame,
        trading_date: date,
    ) -> pd.DataFrame:
        """识别涨跌停并在 DataFrame 新增 limit_type 列

        Args:
            df: K 线 DataFrame（须含 close / pct_change 列，或可从 close 计算）
            trading_date: 交易日期

        Returns:
            新增 limit_type 列（"up" / "down" / "none"）
        """
        ...

    @abstractmethod
    def is_trading_day(self, target_date: date) -> bool:
        """判断是否为交易日

        Args:
            target_date: 目标日期

        Returns:
            True: 交易日
            False: 非交易日（周末 / 节假日 / 特殊休市）
        """
        ...

    # ── 子类共享辅助方法 ──

    def _pct_change(self, df: pd.DataFrame) -> pd.Series:
        """从 DataFrame 计算涨跌幅（pct_change 列存在则用，不存在则算）"""
        if "pct_change" in df.columns:
            return df["pct_change"]
        if "close" not in df.columns:
            return pd.Series(0.0, index=df.index)
        return df["close"].pct_change().fillna(0) * 100


# ──────────────── A 股适配器 ────────────────

class CnMarketAdapter(MarketAdapter):
    """A 股市场适配器

    规则：
    - Symbol：6 开头上证 / 0 开头深证 / 3 开头创业板
    - 交易时间：09:30-11:30 / 13:00-15:00（含午休）
    - 涨跌停：主板 ±10%，创业板 ±20%（简化版取 ±10%）
    - 复权：支持 qfq（默认）/ hfq
    - 节假日：通过 _get_holidays 扩展
    """

    def normalize_symbol(self, symbol: str) -> NormalizedSymbol:
        sym = symbol.strip().upper()
        if sym.startswith("6"):
            exchange = "shanghai"
        elif sym.startswith(("0", "3")):
            if sym.startswith("3"):
                exchange = "chi_next"
            else:
                exchange = "shenzhen"
        else:
            exchange = "shanghai"  # 默认

        return NormalizedSymbol(exchange=exchange, ticker=sym, market="cn")

    def get_trading_hours(self, trading_date: date) -> tuple[datetime, datetime] | tuple[None, None]:
        if not self.is_trading_day(trading_date):
            return None, None
        start = datetime.combine(trading_date, time(9, 30))
        end = datetime.combine(trading_date, time(15, 0))
        return start, end

    def get_adjust_factor(
        self,
        symbol: str,
        target_date: date,
        adjust: Literal["qfq", "hfq", "none"] = "qfq",
    ) -> float:
        if adjust == "none":
            return 1.0
        # A 股复权因子：简化实现（实际需查数据库）
        # qfq: 历史价格被压缩，因子 > 1
        # hfq: 历史价格被放大，因子 > 1
        # 此处用固定值模拟真实场景，实际项目应从 tushare / akshare 获取
        days_since_2000 = (target_date - date(2000, 1, 1)).days
        if adjust == "qfq":
            # 前复权因子随时间增长（模拟股价除权压缩）
            return round(1.0 + days_since_2000 * 0.0001, 4)
        else:  # hfq
            return round(1.0 + days_since_2000 * 0.0002, 4)

    def detect_limit_up_down(
        self,
        df: pd.DataFrame,
        trading_date: date,
    ) -> pd.DataFrame:
        df = df.copy()
        pct = self._pct_change(df)
        # A 股主板 ±10% 涨跌停（创业板 ±20%，此处取 ±10% 简化）
        # 用 < -9.99 / > 9.99 容差避免浮点精度问题
        threshold = 9.99
        df["limit_type"] = "none"
        df.loc[pct > threshold, "limit_type"] = "up"
        df.loc[pct < -threshold, "limit_type"] = "down"
        return df

    def is_trading_day(self, target_date: target_date.__class__) -> bool:  # type: ignore[name-defined]
        # 周末
        if target_date.weekday() >= 5:
            return False
        # 节假日（可扩展）
        holidays = self._get_holidays(target_date.year)
        if target_date in holidays:
            return False
        return True

    def _get_holidays(self, year: int) -> set[date]:
        """获取 A 股年度节假日（简化版：春节 + 国庆，完整应调 akshare）"""
        # 简化：春节假期首日 + 国庆首日
        return {
            date(year, 1, 1),    # 元旦
            date(year, 5, 1),    # 劳动节
            date(year, 10, 1),   # 国庆
            date(year, 10, 2),
            date(year, 10, 3),
        }


# ──────────────── 美股适配器 ────────────────

class UsMarketAdapter(MarketAdapter):
    """美股市场适配器

    规则：
    - Symbol：直接使用（yfinance 格式）
    - 交易时间：04:00-20:00 ET（含盘前 04:00-09:30 + 盘后 16:00-20:00）
    - 涨跌停：无涨跌停限制
    - 复权：美股不复权（yfinance 自动处理 split/adjustment）
    """

    def normalize_symbol(self, symbol: str) -> NormalizedSymbol:
        sym = symbol.strip().upper()
        return NormalizedSymbol(exchange="US", ticker=sym, market="us")

    def get_trading_hours(self, trading_date: date) -> tuple[datetime, datetime] | tuple[None, None]:
        if not self.is_trading_day(trading_date):
            return None, None
        # 盘前 04:00 到盘后 20:00（美东时间，转本地简化处理）
        # 实际项目应处理夏令时，此处用固定时段
        start = datetime.combine(trading_date, time(4, 0))
        end = datetime.combine(trading_date, time(20, 0))
        return start, end

    def get_adjust_factor(
        self,
        symbol: str,
        target_date: date,
        adjust: Literal["qfq", "hfq", "none"] = "qfq",
    ) -> float:
        # 美股不复权
        return 1.0

    def detect_limit_up_down(
        self,
        df: pd.DataFrame,
        trading_date: date,
    ) -> pd.DataFrame:
        df = df.copy()
        df["limit_type"] = "none"
        return df

    def is_trading_day(self, target_date: target_date.__class__) -> bool:  # type: ignore[name-defined]
        # 周末非交易日
        if target_date.weekday() >= 5:
            return False
        # 美国主要节假日（简化）
        holidays = self._us_holidays(target_date.year)
        if target_date in holidays:
            return False
        return True

    def _us_holidays(self, year: int) -> set[date]:
        """美股年度节假日（简化版）"""
        return {
            date(year, 1, 1),       # New Year's Day
            date(year, 7, 4),      # Independence Day
            date(year, 12, 25),    # Christmas
        }


# ──────────────── 加密货币适配器 ────────────────

class CryptoMarketAdapter(MarketAdapter):
    """加密货币市场适配器

    规则：
    - Symbol：交易所:base/quote（如 Binance: BTC/USDT）
    - 交易时间：24/7 无休
    - 涨跌停：无涨跌停
    - 复权：无复权（币本位天然复权）
    """

    def normalize_symbol(self, symbol: str) -> NormalizedSymbol:
        sym = symbol.strip().upper()
        # 提取交易所前缀
        if "/" in sym:
            ticker = sym
            exchange = self._detect_exchange(sym)
        else:
            ticker = f"{sym}/USDT"
            exchange = "binance"  # 默认
        return NormalizedSymbol(exchange=exchange, ticker=ticker, market="crypto")

    def _detect_exchange(self, symbol: str) -> str:
        """根据 symbol 推断交易所"""
        upper = symbol.upper()
        if "BINANCE" in upper:
            return "binance"
        if "OKX" in upper or "OKEX" in upper:
            return "okx"
        if "BYBIT" in upper:
            return "bybit"
        return "binance"  # 默认

    def get_trading_hours(self, trading_date: date) -> tuple[datetime, datetime]:
        """加密 24/7：全天都是交易时段"""
        start = datetime.combine(trading_date, time(0, 0))
        end = datetime.combine(trading_date, time(23, 59, 59))
        return start, end

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
    ) -> pd.DataFrame:
        df = df.copy()
        df["limit_type"] = "none"
        return df

    def is_trading_day(self, target_date: date) -> bool:
        # 加密货币 24/7 每天都是交易日
        return True


# ──────────────── 工厂函数 ────────────────

def get_market_adapter(market: Literal["cn", "us", "crypto"]) -> MarketAdapter:
    """工厂函数：根据市场类型返回对应适配器实例

    Args:
        market: 市场标识符

    Returns:
        对应市场的 MarketAdapter 实例

    Raises:
        ValueError: 不支持的市场类型
    """
    adapters: dict[Literal["cn", "us", "crypto"], MarketAdapter] = {
        "cn": CnMarketAdapter(),
        "us": UsMarketAdapter(),
        "crypto": CryptoMarketAdapter(),
    }
    if market not in adapters:
        raise ValueError(f"Unsupported market: {market}. Available: {list(adapters.keys())}")
    return adapters[market]


# ──────────────── 颜色方案 ────────────────

_COLOR_SCHEMES: dict[Literal["cn", "us", "crypto"], ColorScheme] = {
    "cn": ColorScheme(
        up_color="#FF0000",    # A 股红涨
        down_color="#00FF00",   # A 股绿跌
        bullish="red",
    ),
    "us": ColorScheme(
        up_color="#00FF00",    # 美股绿涨
        down_color="#FF0000",   # 美股红跌
        bullish="green",
    ),
    "crypto": ColorScheme(
        up_color="#00FF00",    # 加密绿涨
        down_color="#FF0000",   # 加密红跌
        bullish="green",
    ),
}


def get_color_scheme(market: Literal["cn", "us", "crypto"]) -> ColorScheme:
    """获取多市场配色方案

    来自 ai-trader 教训 #9：多市场交互矩阵（颜色 × 数据格式 × 涨跌停逻辑）

    Args:
        market: 市场类型

    Returns:
        ColorScheme（含 up_color / down_color / bullish）
    """
    if market not in _COLOR_SCHEMES:
        raise ValueError(f"Unsupported market: {market}")
    return _COLOR_SCHEMES[market]
