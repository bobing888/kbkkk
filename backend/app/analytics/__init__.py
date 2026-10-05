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
    """全指标工厂：一次调用输出 17 个指标列。

    指标来源：
    - services/indicators（内部 _calc_* 方法）→ MA5/10/20/60/120/250,
      DIF/DEA/MACD, RSI, BOLL_MID/UPPER/LOWER, K/D/J, OBV
    - analytics/trend     → ADX14
    - analytics/volatility → ATR14
    - analytics/statistical → Hurst
    """

    # RSI 列名映射：IndicatorEngine 输出 RSI，AnalyticsEngine 统一为 RSI14
    _RSI_COL = "RSI"
    _OUT_RSI_COL = "RSI14"

    @staticmethod
    def calculate_all(df: pd.DataFrame) -> pd.DataFrame:
        """输出 df 含 17 个指标列（MA6/DIF/DEA/MACD/RSI/BOLL/KDJ/OBV/ADX14/ATR14/Hurst）。

        对外输出列名统一：RSI → RSI14。

        注意：
        - Hurst 指标说明：数据 < 100 根（lag < 2）时返回 0.5（默认随机游走）
          此为估算预期，不适用于 < 100 根的短周期回测
        """
        from app.services.indicators import IndicatorEngine

        df = df.copy()

        # ── 1. IndicatorEngine._calc_*（6 指标族，直接调内部方法避免循环依赖）────
        ie = IndicatorEngine  # 类型提示用
        df = ie._calc_ma(df)
        df = ie._calc_macd(df)
        df = ie._calc_rsi(df)
        df = ie._calc_boll(df)
        df = ie._calc_kdj(df)
        df = ie._calc_obv(df)

        # 统一列名：RSI → RSI14
        if AnalyticsEngine._RSI_COL in df.columns:
            df[AnalyticsEngine._OUT_RSI_COL] = df.pop(AnalyticsEngine._RSI_COL)

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
