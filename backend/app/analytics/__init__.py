"""Analytics package — 高级量化指标

来源：bobing888/ai-trader (MIT/Apache-2.0) 复盘后谨慎复用
原始项目：https://github.com/bobing888/ai-trader
原始路径：backend/app/analytics/

复用的具体模块（全部纯 numpy，零外部依赖）：
- trend.py       — ADX / MACD / SMA / 多指标共振 / 信号方向
- statistical.py — Hurst 指数 / 分形维数 / Shannon 熵 / RSI 分数
- volatility.py  — ATR / 波动率分位数

⚠️ 复用规则（kline-system SPEC.md）：
1. 保留原文件的所有 docstring（作者署名）
2. 不与 kline-system/services/indicators.py 的同名函数冲突
3. 添加单元测试覆盖（与 ai-trader 相同测试用例）
4. 任何修改必须更新此 header
"""

from __future__ import annotations

import pandas as pd
import numpy as np

from app.analytics.trend import adx as _adx
from app.analytics.volatility import atr as _atr
from app.analytics.statistical import hurst_exponent as _hurst

# 导出公共 API
__all__ = ["AnalyticsEngine"]


class AnalyticsEngine:
    """全指标工厂：一次调用输出 11 个指标列。

    指标来源：
    - services/indicators → MA5/10/20/60/120/250, DIF/DEA/MACD, RSI,
                             BOLL_MID/UPPER/LOWER, K/D/J, OBV（通过 IndicatorEngine）
    - analytics/trend     → ADX14
    - analytics/volatility → ATR14
    - analytics/statistical → Hurst
    """

    # IndicatorEngine 输出的列名映射到 AnalyticsEngine 标准列名
    _IE_COL_MAP = {
        "RSI": "RSI14",
        # 其他列名相同
        "MA5": "MA5", "MA10": "MA10", "MA20": "MA20",
        "MA60": "MA60", "MA120": "MA120", "MA250": "MA250",
        "DIF": "DIF", "DEA": "DEA", "MACD": "MACD",
        "BOLL_MID": "BOLL_MID", "BOLL_UPPER": "BOLL_UPPER", "BOLL_LOWER": "BOLL_LOWER",
        "K": "K", "D": "D", "J": "J",
        "OBV": "OBV",
    }

    @staticmethod
    def calculate_all(df: pd.DataFrame) -> pd.DataFrame:
        """输出 df 含 17 个指标列（MA6/DIF/DEA/MACD/RSI/BOLL/KDJ/OBV/ADX14/ATR14/Hurst）。

        对外输出列名统一：
        - RSI14 ← IndicatorEngine 输出 RSI
        - 其余列名与 IndicatorEngine 保持一致
        """
        from app.services.indicators import IndicatorEngine

        df = df.copy()

        # ── 1. IndicatorEngine（6 指标族）─────────────────────────────────────
        ie_result = IndicatorEngine.calculate_all(df)

        # 按映射写入（RSI → RSI14，其余直写）
        for ie_col, our_col in AnalyticsEngine._IE_COL_MAP.items():
            df[our_col] = ie_result[ie_col]

        # ── 2. ADX14（analytics/trend）────────────────────────────────────────
        h = df["high"].values.astype(np.float64)
        l = df["low"].values.astype(np.float64)
        c = df["close"].values.astype(np.float64)
        adx_arr, _, _ = _adx(h, l, c, period=14)
        df["ADX14"] = adx_arr

        # ── 3. ATR14（analytics/volatility）───────────────────────────────────
        atr_arr = _atr(h, l, c, period=14)
        df["ATR14"] = atr_arr

        # ── 4. Hurst（analytics/statistical）─────────────────────────────────
        # Hurst 是标量（整个序列），填充到所有行
        h_val = _hurst(c)
        df["Hurst"] = h_val

        return df
