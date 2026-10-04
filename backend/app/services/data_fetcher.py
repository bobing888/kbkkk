"""数据获取服务 - 统一封装 akshare / yfinance / ccxt"""
import asyncio
from datetime import datetime, timedelta
from typing import Literal, Optional
import pandas as pd
from loguru import logger

# 延迟导入（避免启动时的依赖问题）
try:
    import akshare as ak
except ImportError:
    logger.warning("akshare not installed, A股数据不可用")
    ak = None

try:
    import yfinance as yf
except ImportError:
    logger.warning("yfinance not installed, 美股数据不可用")
    yf = None

try:
    import ccxt
except ImportError:
    logger.warning("ccxt not installed, 加密数据不可用")
    ccxt = None


class DataFetcher:
    """统一数据获取接口 - 屏蔽不同市场 API 差异"""

    def get_kline(
        self,
        symbol: str,
        period: Literal['1m', '5m', '15m', '30m', '60m', '1d', '1w', '1M'] = '1d',
        start: Optional[str] = None,
        end: Optional[str] = None,
        market: Literal['cn', 'us', 'crypto'] = 'cn',
        adjust: Literal['qfq', 'hfq', 'none'] = 'qfq',
    ) -> pd.DataFrame:
        """
        统一 K 线数据获取接口

        Args:
            symbol: 标的代码
                - A 股: '600519' (不带市场前缀)
                - 美股: 'AAPL' (不带交易所)
                - 加密: 'BTC/USDT'
            period: K线周期
            start: 起始日期 YYYYMMDD
            end: 结束日期 YYYYMMDD
            market: 市场类型
            adjust: 复权方式（仅 A 股）

        Returns:
            DataFrame: [datetime, open, high, low, close, volume, amount, ...]
        """
        if market == 'cn':
            return self._get_cn_kline(symbol, period, start, end, adjust)
        elif market == 'us':
            return self._get_us_kline(symbol, period, start, end)
        elif market == 'crypto':
            return self._get_crypto_kline(symbol, period, start, end)
        else:
            raise ValueError(f"Unsupported market: {market}")

    # ──────────────── A 股 ────────────────

    def _get_cn_kline(self, symbol, period, start, end, adjust):
        """A 股数据 - akshare"""
        if ak is None:
            raise ImportError("akshare is required for CN market data")

        if not start:
            start = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
        if not end:
            end = datetime.now().strftime('%Y%m%d')

        logger.info(f"Fetching CN kline: {symbol} {period} {start} - {end} {adjust}")

        try:
            if period in ['1m', '5m', '15m', '30m', '60m']:
                df = ak.stock_zh_a_hist_min_em(
                    symbol=symbol,
                    period=period,
                    start_date=start,
                    end_date=end,
                    adjust=adjust
                )
            else:  # 日/周/月
                period_map = {'1d': 'daily', '1w': 'weekly', '1M': 'monthly'}
                df = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period=period_map.get(period, 'daily'),
                    start_date=start,
                    end_date=end,
                    adjust=adjust
                )
            return self._clean_cn_data(df)
        except Exception as e:
            logger.error(f"akshare error: {e}")
            raise

    def _clean_cn_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """A 股数据清洗"""
        if df.empty:
            return df

        # 列名标准化
        column_map = {
            '日期': 'datetime', '时间': 'datetime',
            '开盘': 'open', '最高': 'high', '最低': 'low', '收盘': 'close',
            '成交量': 'volume', '成交额': 'amount',
            '涨跌幅': 'pct_change',
        }
        df = df.rename(columns=column_map)

        # 必填列检查
        required = ['datetime', 'open', 'high', 'low', 'close', 'volume']
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        # 数据类型转换
        df['datetime'] = pd.to_datetime(df['datetime'])
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # 缺失值处理
        df = df.sort_values('datetime').reset_index(drop=True)
        df = df.ffill().fillna(0)

        # A 股特殊标记
        if 'pct_change' in df.columns:
            df['is_limit_up'] = df['pct_change'] >= 9.5
            df['is_limit_down'] = df['pct_change'] <= -9.5
        else:
            df['is_limit_up'] = False
            df['is_limit_down'] = False
        df['is_suspended'] = df['volume'] == 0

        return df

    # ──────────────── 美股 ────────────────

    def _get_us_kline(self, symbol, period, start, end):
        """美股数据 - yfinance"""
        if yf is None:
            raise ImportError("yfinance is required for US market data")

        if not start:
            start = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        if not end:
            end = datetime.now().strftime('%Y-%m-%d')

        # yfinance 周期映射
        period_map = {
            '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m', '60m': '60m',
            '1d': '1d', '1w': '1wk', '1M': '1mo'
        }

        logger.info(f"Fetching US kline: {symbol} {period} {start} - {end}")

        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(
                start=start,
                end=end,
                interval=period_map.get(period, '1d')
            )
            return self._clean_us_data(df)
        except Exception as e:
            logger.error(f"yfinance error: {e}")
            raise

    def _clean_us_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """美股数据清洗"""
        if df.empty:
            return df

        # yfinance 返回 MultiIndex 列名，扁平化
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.reset_index()
        df = df.rename(columns={
            'Date': 'datetime', 'Datetime': 'datetime',
            'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close',
            'Volume': 'volume'
        })

        # 处理时区
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
            if df['datetime'].dt.tz is not None:
                df['datetime'] = df['datetime'].dt.tz_localize(None)

        # 数据类型
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # 缺失值
        df = df.ffill().fillna(0)
        df['is_suspended'] = df['volume'] == 0

        return df

    # ──────────────── 加密货币 ────────────────

    def _get_crypto_kline(self, symbol, period, start, end):
        """加密货币数据 - ccxt"""
        if ccxt is None:
            raise ImportError("ccxt is required for crypto data")

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
            exchange = ccxt.binance()
            since = int(start_dt.timestamp() * 1000)
            end_ms = int(end_dt.timestamp() * 1000)
            timeframe = timeframe_map.get(period, '1d')

            all_ohlcv = []
            while since < end_ms:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
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
        """异步获取 K 线（在事件循环中执行同步 IO）"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_kline, *args, **kwargs)


# 单例
data_fetcher = DataFetcher()
