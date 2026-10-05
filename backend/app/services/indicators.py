"""指标计算引擎 - 向量化实现

A4 改造：calculate_all 委托 AnalyticsEngine，filter 为原始 6 列。
其他静态方法保持不变（向后兼容）。
"""
import pandas as pd
import numpy as np
from typing import Tuple


class IndicatorEngine:
    """技术指标计算引擎 - 全部向量化，无循环"""

    # 原始 6 指标族列名（与 M1 commit e94c1bd 一致）
    _ORIGINAL_COLS = frozenset({
        "MA5", "MA10", "MA20", "MA60", "MA120", "MA250",
        "DIF", "DEA", "MACD",
        "RSI",
        "BOLL_MID", "BOLL_UPPER", "BOLL_LOWER",
        "K", "D", "J",
        "OBV",
    })

    # AnalyticsEngine 输出列名 → IndicatorEngine 原始列名
    # AnalyticsEngine 统一把 RSI 改名为 RSI14，这里反向映射回来
    _AE_TO_IE_COL_MAP = {
        "RSI14": "RSI",
    }

    @staticmethod
    def calculate_all(df: pd.DataFrame) -> pd.DataFrame:
        """一次性计算所有核心指标（仅原始 6 指标族，不含 ADX/ATR/Hurst）。

        实现路径：
        1. 调用 AnalyticsEngine.calculate_all（全量 17 列）
        2. Filter → 只保留原始 6 列
        3. 反向映射：RSI14 → RSI（恢复原始列名，向后兼容）
        """
        # 延迟导入避免循环依赖
        # analytics/__init__.py → 导入 services.indicators.IndicatorEngine
        # 若此处直接 import analytics，会产生循环依赖
        from app.analytics import AnalyticsEngine

        full = AnalyticsEngine.calculate_all(df)
        # 只保留原始列（过滤掉 ADX14 / ATR14 / Hurst）
        # 注意事项：AnalyticsEngine 将 RSI 重命名为 RSI14，所以这里用原始列名过滤
        # 时，RSI 不会被保留；需要先按 AnalyticsEngine 列名（RSI14）暂留，
        # 再通过反向映射恢复为原始列名 RSI
        keep_cols = [
            col for col in full.columns
            if col in IndicatorEngine._ORIGINAL_COLS
            or col in ["datetime", "open", "high", "low", "close", "volume"]
            # AnalyticsEngine 列名也暂留（RSI14），后续反向映射
            or col in IndicatorEngine._AE_TO_IE_COL_MAP
        ]
        result = full[keep_cols].copy()
        # 反向映射：AnalyticsEngine.rename → 恢复 IndicatorEngine 原始列名
        for ae_col, ie_col in IndicatorEngine._AE_TO_IE_COL_MAP.items():
            if ae_col in result.columns and ie_col not in result.columns:
                result[ie_col] = result.pop(ae_col)
        return result

    @staticmethod
    def _calc_ma(df: pd.DataFrame, periods: Tuple[int, ...] = (5, 10, 20, 60, 120, 250)) -> pd.DataFrame:
        """移动平均线"""
        for p in periods:
            df[f'MA{p}'] = df['close'].rolling(window=p, min_periods=1).mean()
        return df

    @staticmethod
    def _calc_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """MACD 指标"""
        ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
        df['DIF'] = ema_fast - ema_slow
        df['DEA'] = df['DIF'].ewm(span=signal, adjust=False).mean()
        df['MACD'] = (df['DIF'] - df['DEA']) * 2
        return df

    @staticmethod
    def _calc_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """RSI 指标"""
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=period, min_periods=1).mean()
        avg_loss = loss.rolling(window=period, min_periods=1).mean()
        rs = avg_gain / (avg_loss + 1e-10)
        df['RSI'] = 100 - (100 / (1 + rs))
        return df

    @staticmethod
    def _calc_boll(df: pd.DataFrame, period: int = 20, std_dev: int = 2) -> pd.DataFrame:
        """布林带"""
        df['BOLL_MID'] = df['close'].rolling(window=period, min_periods=1).mean()
        std = df['close'].rolling(window=period, min_periods=1).std()
        df['BOLL_UPPER'] = df['BOLL_MID'] + std_dev * std
        df['BOLL_LOWER'] = df['BOLL_MID'] - std_dev * std
        return df

    @staticmethod
    def _calc_kdj(df: pd.DataFrame, n: int = 9, m1: int = 3, m2: int = 3) -> pd.DataFrame:
        """KDJ 随机指标"""
        low_n = df['low'].rolling(window=n, min_periods=1).min()
        high_n = df['high'].rolling(window=n, min_periods=1).max()
        rsv = (df['close'] - low_n) / (high_n - low_n + 1e-10) * 100
        df['K'] = rsv.ewm(alpha=1/m1, adjust=False).mean()
        df['D'] = df['K'].ewm(alpha=1/m2, adjust=False).mean()
        df['J'] = 3 * df['K'] - 2 * df['D']
        return df

    @staticmethod
    def _calc_obv(df: pd.DataFrame) -> pd.DataFrame:
        """OBV 能量潮"""
        obv = [0]
        for i in range(1, len(df)):
            if df['close'].iloc[i] > df['close'].iloc[i-1]:
                obv.append(obv[-1] + df['volume'].iloc[i])
            elif df['close'].iloc[i] < df['close'].iloc[i-1]:
                obv.append(obv[-1] - df['volume'].iloc[i])
            else:
                obv.append(obv[-1])
        df['OBV'] = obv
        return df


# 单例
indicator_engine = IndicatorEngine()
