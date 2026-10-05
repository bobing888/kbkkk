"""多指标共振识别 — B5

来源：kline-system M2-B confluence 层
基于 M2-A 的 17 个指标列 + B1-B4 形态列
输出 confluence_score (0-1) + confluence_direction (bullish/bearish/neutral)

共振规则：≥3 同向指标触发信号
"""
from __future__ import annotations

import pandas as pd
import numpy as np


def detect_confluence(df: pd.DataFrame) -> pd.DataFrame:
    """多指标共振识别。

    输入 df 必须含以下列（由 AnalyticsEngine.calculate_all 产出）：
      MA5/MA10/MA20/MA60/MA120/MA250
      DIF/DEA/MACD, RSI14, BOLL_MID/UPPER/LOWER
      K/D/J, OBV, ADX14, ATR14, Hurst
      以及形态列（可选）：is_hammer / is_morning_star / is_three_white_soldiers 等

    新增列：
      confluence_score     (float 0-1): 共振得分
      confluence_direction (str): 'bullish' | 'bearish' | 'neutral'

    共振规则（≥3 同向 → 出信号）：
      bullish: 指标读数暗示价格上涨
      bearish: 指标读数暗示价格下跌
    """
    df = df.copy()
    c = df["close"]

    bullish_count = 0
    bearish_count = 0
    total = 0

    # ── 1. MA 多头排列 ───────────────────────────────────────────────────
    if "MA5" in df.columns and "MA20" in df.columns and "MA60" in df.columns:
        total += 1
        if df["MA5"].iloc[-1] > df["MA20"].iloc[-1] > df["MA60"].iloc[-1]:
            bullish_count += 1
        elif df["MA5"].iloc[-1] < df["MA20"].iloc[-1] < df["MA60"].iloc[-1]:
            bearish_count += 1

    # ── 2. MACD ──────────────────────────────────────────────────────────
    if "DIF" in df.columns and "DEA" in df.columns and "MACD" in df.columns:
        total += 1
        if df["DIF"].iloc[-1] > df["DEA"].iloc[-1] and df["MACD"].iloc[-1] > 0:
            bullish_count += 1
        elif df["DIF"].iloc[-1] < df["DEA"].iloc[-1] and df["MACD"].iloc[-1] < 0:
            bearish_count += 1

    # ── 3. RSI14 ─────────────────────────────────────────────────────────
    if "RSI14" in df.columns:
        total += 1
        if df["RSI14"].iloc[-1] > 50:
            bullish_count += 1
        elif df["RSI14"].iloc[-1] < 50:
            bearish_count += 1

    # ── 4. BOLL 位置 ────────────────────────────────────────────────────
    if "BOLL_MID" in df.columns:
        total += 1
        if c.iloc[-1] > df["BOLL_MID"].iloc[-1]:
            bullish_count += 1
        elif c.iloc[-1] < df["BOLL_MID"].iloc[-1]:
            bearish_count += 1

    # ── 5. KDJ 金叉/死叉 ────────────────────────────────────────────────
    if "K" in df.columns and "D" in df.columns and "J" in df.columns:
        total += 1
        if df["K"].iloc[-1] > df["D"].iloc[-1] and df["J"].iloc[-1] > 80:
            bullish_count += 1
        elif df["K"].iloc[-1] < df["D"].iloc[-1] and df["J"].iloc[-1] < 20:
            bearish_count += 1

    # ── 6. OBV 趋势 ─────────────────────────────────────────────────────
    if "OBV" in df.columns and len(df) > 5:
        total += 1
        obv_slope = df["OBV"].diff().rolling(5).mean()
        if obv_slope.iloc[-1] > 0:
            bullish_count += 1
        elif obv_slope.iloc[-1] < 0:
            bearish_count += 1

    # ── 7. ADX14 趋势强度 ──────────────────────────────────────────────
    if "ADX14" in df.columns:
        total += 1
        if df["ADX14"].iloc[-1] > 25:
            bullish_count += 1
            bearish_count += 1  # ADX 只表示强度，不表示方向

    # ── 8. ATR14 扩张 ──────────────────────────────────────────────────
    if "ATR14" in df.columns and len(df) > 20:
        total += 1
        atr_mean = df["ATR14"].iloc[-20:].mean()
        if df["ATR14"].iloc[-1] > atr_mean * 1.2:
            bullish_count += 1  # 波动扩张，多空均可能

    # ── 9. 单K形态 ──────────────────────────────────────────────────────
    bullish_patterns = [
        "is_hammer", "is_morning_star", "is_three_white_soldiers",
        "is_engulfing_bullish", "is_harami_bullish", "is_piercing_line",
        "is_tweezer_bottom", "is_bullish_counterattack",
    ]
    bearish_patterns = [
        "is_hanging_man", "is_evening_star", "is_three_black_crows",
        "is_engulfing_bearish", "is_throwing_star",
        "is_tweezer_top", "is_bearish_counterattack",
    ]
    for col in bullish_patterns:
        if col in df.columns:
            total += 1
            if df[col].iloc[-1] == 1:
                bullish_count += 1
    for col in bearish_patterns:
        if col in df.columns:
            total += 1
            if df[col].iloc[-1] == 1:
                bearish_count += 1

    # ── 10. 波浪 ────────────────────────────────────────────────────────
    if "wave_label" in df.columns:
        total += 1
        wl = df["wave_label"].iloc[-1]
        if wl in ("3", "5"):
            bullish_count += 1
        elif wl in ("2", "4"):
            bearish_count += 1

    # ── 计算得分 ─────────────────────────────────────────────────────────
    if total == 0:
        df["confluence_score"] = 0.0
        df["confluence_direction"] = "neutral"
        return df

    score = max(bullish_count, bearish_count) / max(total, 1)
    df["confluence_score"] = score

    if bullish_count >= 3 and bullish_count > bearish_count:
        direction = "bullish"
    elif bearish_count >= 3 and bearish_count > bullish_count:
        direction = "bearish"
    else:
        direction = "neutral"
    df["confluence_direction"] = direction

    # warmup：数据量 < 100 → NaN
    if len(df) < 100:
        df["confluence_score"] = np.nan
        df["confluence_direction"] = np.nan

    return df
