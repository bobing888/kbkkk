"""信号方向判定 — B6

来源：kline-system M2-B signal 层
基于 confluence_direction + 形态 + ADX14
输出 Signal dataclass list

判定规则：
  - confluence_direction == 'bullish' AND ADX14 > 25  → long, confidence 0.6
  - confluence_direction == 'bearish' AND ADX14 > 25 → short, confidence 0.6
  - bullish 形态（hammer/morning_star/three_white_soldiers 等） → long, 0.4
  - bearish 形态（暮星/三乌鸦 等）→ short, 0.4
  - 共振 + 形态同向 → confidence +0.2（最高 0.8）
  - 中性：不输出信号

仓位计算：
  - entry = 当前 close
  - stop_loss = entry ± 2 * ATR14
  - take_profit = entry ± 4 * ATR14（2:1 风险回报）
"""
from __future__ import annotations

import pandas as pd
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Signal:
    """交易信号。"""
    name: str                                        # 信号名
    direction: Literal["long", "short", "neutral"]  # 方向
    confidence: float                                # 0-1
    entry: float                                     # 入场价
    stop_loss: float                                 # 止损价
    take_profit: float                               # 止盈价
    sources: list[str] = field(default_factory=list)  # 来源列表
    datetime: pd.Timestamp | None = None             # K 线时间


_BULLISH_PATTERNS = [
    "is_hammer",
    "is_morning_star",
    "is_three_white_soldiers",
    "is_engulfing_bullish",
    "is_harami_bullish",
    "is_piercing_line",
    "is_tweezer_bottom",
    "is_bullish_counterattack",
]

_BEARISH_PATTERNS = [
    "is_hanging_man",
    "is_evening_star",
    "is_three_black_crows",
    "is_engulfing_bearish",
    "is_throwing_star",
    "is_tweezer_top",
    "is_bearish_counterattack",
]

# 形态列名 → Signal name 映射
_PATTERN_NAME_MAP = {
    "is_hammer": "hammer_bullish",
    "is_morning_star": "morning_star_bullish",
    "is_three_white_soldiers": "three_white_soldiers_bullish",
    "is_engulfing_bullish": "engulfing_bullish",
    "is_harami_bullish": "harami_bullish",
    "is_piercing_line": "piercing_line_bullish",
    "is_tweezer_bottom": "tweezer_bottom_bullish",
    "is_bullish_counterattack": "bullish_counterattack_bullish",
    "is_hanging_man": "hanging_man_bearish",
    "is_evening_star": "evening_star_bearish",
    "is_three_black_crows": "three_black_crows_bearish",
    "is_engulfing_bearish": "engulfing_bearish",
    "is_throwing_star": "throwing_star_bearish",
    "is_tweezer_top": "tweezer_top_bearish",
    "is_bearish_counterattack": "bearish_counterattack_bearish",
}


def _detect_bullish_patterns(row: pd.Series, df_cols: list[str]) -> list[str]:
    """返回命中的 bullish 形态的 Signal name 列表。"""
    return [
        _PATTERN_NAME_MAP[col]
        for col in _BULLISH_PATTERNS
        if col in df_cols
        and isinstance(row.get(col), (int, float))
        and not pd.isna(row.get(col))
        and row.get(col) == 1
    ]


def _detect_bearish_patterns(row: pd.Series, df_cols: list[str]) -> list[str]:
    """返回命中的 bearish 形态的 Signal name 列表。"""
    return [
        _PATTERN_NAME_MAP[col]
        for col in _BEARISH_PATTERNS
        if col in df_cols
        and isinstance(row.get(col), (int, float))
        and not pd.isna(row.get(col))
        and row.get(col) == 1
    ]


def generate_signal(df: pd.DataFrame) -> list[Signal]:
    """从指标 + 形态 + 共振数据生成交易信号。

    前提：df 已通过：
      1. AnalyticsEngine.calculate_all（17 个指标列，含 ADX14/ATR14）
      2. detect_single_candle / detect_multi_candle（形态列）
      3. detect_confluence（confluence_direction）

    判定规则：
      confluence_direction == 'bullish' AND ADX14 > 25  → long, confidence 0.6
      confluence_direction == 'bearish' AND ADX14 > 25 → short, confidence 0.6
      bullish 形态（锤子/晨星/红三兵 等）  → long, confidence 0.4
      bearish 形态（暮星/三乌鸦 等）       → short, confidence 0.4
      共振 + 形态同向                    → confidence +0.2（最高 0.8）
      中性                              → 不出信号

    Args:
        df: 含 confluence_direction + ADX14 + ATR14 + close + 形态列

    Returns:
        list[Signal]，仅当有信号时返回（非 neutral）
    """
    signals: list[Signal] = []

    if "confluence_direction" not in df.columns:
        return signals
    if "ADX14" not in df.columns:
        return signals
    if "ATR14" not in df.columns:
        return signals

    df_cols: list[str] = list(df.columns)
    rsi_col = "RSI14" if "RSI14" in df_cols else None

    for i in range(len(df)):
        row = df.iloc[i]
        confluence_dir = row.get("confluence_direction")
        if isinstance(confluence_dir, float) and pd.isna(confluence_dir):
            continue

        adx = float(row.get("ADX14", 0))
        atr = float(row.get("ATR14", 0))
        # 处理 ATR14 为 0 或 NaN 的情况
        if atr <= 0 or (isinstance(atr, float) and pd.isna(atr)):
            atr = float(row.get("close", 0)) * 0.02
        entry = float(row.get("close", 0))
        dt_val = row.get("datetime")
        dt: pd.Timestamp | None = dt_val if isinstance(dt_val, pd.Timestamp) else None

        # ── 收集 bullish / bearish 形态 ────────────────────────────────
        bullish_sources = _detect_bullish_patterns(row, df_cols)
        bearish_sources = _detect_bearish_patterns(row, df_cols)

        # ── 基础方向判定 ─────────────────────────────────────────────
        direction: Literal["long", "short", "neutral"] = "neutral"
        confidence = 0.0
        sources: list[str] = []

        # 共振方向驱动
        if confluence_dir == "bullish" and adx > 25:
            direction = "long"
            confidence = 0.6
            sources.append("confluence_bullish")
        elif confluence_dir == "bearish" and adx > 25:
            direction = "short"
            confidence = 0.6
            sources.append("confluence_bearish")

        # 形态驱动（无共振时）
        if direction == "neutral":
            if bullish_sources:
                direction = "long"
                confidence = 0.4
                sources.extend(bullish_sources)
            elif bearish_sources:
                direction = "short"
                confidence = 0.4
                sources.extend(bearish_sources)

        if direction == "neutral":
            continue

        # ── 补充同向形态（不在 sources 中则加入）──────────────────────
        if direction == "long":
            for s in bullish_sources:
                if s not in sources:
                    sources.append(s)
        elif direction == "short":
            for s in bearish_sources:
                if s not in sources:
                    sources.append(s)

        # ── 共振 + 形态同向 → confidence +0.2 ─────────────────────────
        has_confluence = any(src.startswith("confluence") for src in sources)
        has_pattern = any(not src.startswith("confluence") for src in sources)
        if has_confluence and has_pattern:
            confidence = min(1.0, confidence + 0.2)

        # ── RSI 过滤 ────────────────────────────────────────────────
        if rsi_col and rsi_col in df_cols:
            rsi = row.get(rsi_col)
            if isinstance(rsi, float) and not pd.isna(rsi):
                if direction == "long" and rsi >= 70:
                    continue  # 超买过滤
                if direction == "short" and rsi <= 30:
                    continue  # 超卖过滤

        # ── 仓位计算 ───────────────────────────────────────────────
        if direction == "long":
            stop_loss = entry - 2 * atr
            take_profit = entry + 4 * atr
        elif direction == "short":
            stop_loss = entry + 2 * atr
            take_profit = entry - 4 * atr
        else:
            continue

        # ── Signal name ────────────────────────────────────────────
        name = "_".join(sorted(sources[:3])) if sources else f"signal_{direction}"

        signals.append(Signal(
            name=name,
            direction=direction,
            confidence=round(confidence, 2),
            entry=round(entry, 2),
            stop_loss=round(stop_loss, 2),
            take_profit=round(take_profit, 2),
            sources=sources,
            datetime=dt,
        ))

    return signals
