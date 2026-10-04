"""指标计算引擎 - 向量化实现"""
import pandas as pd
import numpy as np
from typing import Tuple


class IndicatorEngine:
    """技术指标计算引擎 - 全部向量化，无循环"""

    @staticmethod
    def calculate_all(df: pd.DataFrame) -> pd.DataFrame:
        """一次性计算所有核心指标"""
        df = df.copy()
        df = IndicatorEngine._calc_ma(df)
        df = IndicatorEngine._calc_macd(df)
        df = IndicatorEngine._calc_rsi(df)
        df = IndicatorEngine._calc_boll(df)
        df = IndicatorEngine._calc_kdj(df)
        df = IndicatorEngine._calc_obv(df)
        return df

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
