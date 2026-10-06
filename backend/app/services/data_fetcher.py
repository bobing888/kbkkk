"""数据获取服务 - 统一封装 ccxt（Binance/OKX，优先 OKX）。

SPEC v2 §1：聚焦 BTC/ETH（crypto），A 股 akshare / 美股 yfinance 链路已砍。
"""
import asyncio
import os
from datetime import datetime, timedelta
from typing import Literal, Optional
import pandas as pd
from loguru import logger

# 延迟导入（避免启动时的依赖问题）
try:
    import ccxt
except ImportError:
    logger.warning("ccxt not installed, 加密数据不可用")
    ccxt = None


class DataFetcher:
    """统一数据获取接口 - 仅支持加密市场（BTC/ETH）。

    Provider 注册表（KB github-openbq-org-OpenBB.md §5 "Plugin discovery from metadata"）：
    新增市场/数据源只需在 _PROVIDERS 注册，无需改 get_kline。
    当前仅含 crypto 一个 provider（SPEC v2 §1 砍 cn/us）。
    """

    # ──────────────── Provider 注册表 ────────────────
    _PROVIDERS: dict[str, callable] = {}  # type: ignore[type-arg]

    def get_kline(
        self,
        symbol: str,
        period: Literal['1m', '5m', '15m', '30m', '60m', '1d', '1w', '1M'] = '1d',
        start: Optional[str] = None,
        end: Optional[str] = None,
        market: Literal['crypto'] = 'crypto',
        adjust: Literal['qfq', 'hfq', 'none'] = 'qfq',
    ) -> pd.DataFrame:
        """实例方法：与类方法等价，供单例 data_fetcher 调用。

        所有路由都走 Provider 注册表，避免重复 if/elif。
        SPEC v2：market 仅允许 'crypto'。
        """
        return DataFetcher.get_kline_route(
            symbol, period, start, end, market, adjust
        )

    @classmethod
    def get_kline_route(
        cls,
        symbol: str,
        period: Literal['1m', '5m', '15m', '30m', '60m', '1d', '1w', '1M'] = '1d',
        start: Optional[str] = None,
        end: Optional[str] = None,
        market: Literal['crypto'] = 'crypto',
        adjust: Literal['qfq', 'hfq', 'none'] = 'qfq',
    ) -> pd.DataFrame:
        """类方法版本（Provider 路由核心实现）。

        通过 _PROVIDERS 注册表路由到对应市场的 fetch 方法。
        出口统一调用 normalize_kline_df（KB github-openbq-org-OpenBB.md §2
        "Output normalization adapters"），保证字段名一致。
        """
        from app.data.normalize import normalize_kline_df

        provider = cls._PROVIDERS.get(market)
        if provider is None:
            available = ", ".join(sorted(cls._PROVIDERS.keys()))
            raise ValueError(
                f"Unsupported market: {market}. Available: {available}"
            )
        # provider 是 function（未绑定），需要传实例
        instance = cls()
        raw_df = provider(instance, symbol, period, start, end, adjust)
        return normalize_kline_df(raw_df, market)

    # ──────────────── 加密货币（仅保留）────────────

    def _get_crypto_kline(self, symbol, period, start, end, adjust="qfq"):
        """加密货币数据 - ccxt（adjust 参数对加密无效，无复权概念）"""
        if ccxt is None:
            raise ImportError("ccxt is required for crypto data")
        _ = adjust  # 加密仅签名无效

        if not start:
            start_dt = datetime.now() - timedelta(days=365)
        else:
            start_dt = datetime.strptime(start, '%Y%m%d')
        if not end:
            end_dt = datetime.now()
        else:
            end_dt = datetime.strptime(end, '%Y%m%d')

        # ccxt timeframe 映射
        timeframe_map = {
            '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m', '60m': '1h',
            '1d': '1d', '1w': '1w', '1M': '1M'
        }

        logger.info(f"Fetching crypto kline: {symbol} {period} {start} - {end}")

        try:
            # M5 部署：读 KBKKK_CRYPTO_EXCHANGE 环境变量，默认 okx（PR #19 已改默认值）
            exchange_name = os.getenv("KBKKK_CRYPTO_EXCHANGE", "okx").lower()
            exchange_cls = getattr(ccxt, exchange_name, None)
            if exchange_cls is None:
                raise ValueError(f"Unsupported ccxt exchange: {exchange_name}")
            exchange = exchange_cls({"enableRateLimit": True})

            # OKX 现货要求 "BTC/USDT" 格式，无斜杠时自动补 /USDT（PR #25 部署修复）
            ccxt_symbol = symbol if "/" in symbol else f"{symbol}/USDT"
            logger.debug(f"ccxt symbol: {symbol} -> {ccxt_symbol}")

            since = int(start_dt.timestamp() * 1000)
            end_ms = int(end_dt.timestamp() * 1000)
            timeframe = timeframe_map.get(period, '1d')

            all_ohlcv = []
            while since < end_ms:
                ohlcv = exchange.fetch_ohlcv(ccxt_symbol, timeframe, since=since, limit=1000)
                if not ohlcv:
                    break
                all_ohlcv.extend(ohlcv)
                since = ohlcv[-1][0] + 1

            df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df[['datetime', 'open', 'high', 'low', 'close', 'volume']]
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            df = df.ffill().fillna(0)
            df['is_suspended'] = df['volume'] == 0

            return df
        except Exception as e:
            logger.error(f"ccxt error: {e}")
            raise

    # ──────────────── 异步封装 ────────────────

    async def get_kline_async(self, *args, **kwargs) -> pd.DataFrame:
        """异步获取 K 线（在事件循环中执行同步 IO）

        保持向后兼容：内部调用类方法 DataFetcher.get_kline_route 走 Provider 注册表。
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: DataFetcher.get_kline_route(*args, **kwargs)
        )


# ──────────────── Provider 注册（KB github-openbq-org-OpenBB.md §5）──
# SPEC v2 §1：只做 BTC/ETH（crypto）。cn/us 已删除，不再注册。
DataFetcher._PROVIDERS = {
    "crypto": DataFetcher._get_crypto_kline,
}


# 单例（保留向后兼容：kline.py 直接用 data_fetcher.get_kline(...)）
data_fetcher = DataFetcher()
