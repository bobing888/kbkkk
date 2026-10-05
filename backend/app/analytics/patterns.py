"""K 线形态识别 — 单K + 组合K + 缠论中枢 + 波浪驱动

来源：kline-system M2-B patterns 层
覆盖：B1 单K(11种) + B2 组合K(9种) + B3 缠论中枢 + B4 波浪驱动
实现：纯向量化（pandas/numpy），无循环
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _trend_by_price(df: "pd.DataFrame") -> "tuple[pd.Series, pd.Series]":
    """用价格位置 vs 近期低点/高点判断趋势，避免 RSI 被反弹扭曲。

    - 下跌趋势：当前 close < 过去 N 根最低 close（价格在近期低位）
    - 上涨趋势：当前 close > 过去 N 根最高 close（价格在近期高位）
    - 否则中性

    N=10 足够捕捉短期趋势，又不会太迟钝。
    """
    c = df["close"]
    lookback = 10
    # 足够数据才判断
    rolling_min = c.rolling(lookback, min_periods=lookback).min()
    rolling_max = c.rolling(lookback, min_periods=lookback).max()
    is_down = (c < rolling_min.shift(1)) & rolling_min.shift(1).notna()
    is_up   = (c > rolling_max.shift(1)) & rolling_max.shift(1).notna()
    return is_down, is_up


def detect_single_candle(df: "pd.DataFrame") -> "pd.DataFrame":
    """识别 11 种单 K 形态（向量化实现）。

    新增列（float 0/1）：is_hammer / is_doji / is_engulfing_bullish /
      is_engulfing_bearish / is_harami_bullish / is_hanging_man /
      is_inverted_hammer / is_three_white_soldiers / is_three_black_crows /
      is_morning_star / is_evening_star
    """
    df = df.copy()
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    body = (c - o).abs()
    body_range = h - l
    upper = h - pd.concat([o, c], axis=1).max(axis=1)
    lower = pd.concat([o, c], axis=1).min(axis=1) - l
    is_down, is_up = _trend_by_price(df)

    # 1. 锤子线：下影线>=2x实体，上影线<=实体，下降趋势
    is_hammer = (lower >= 2*body) & (upper <= body) & is_down

    # 2. 十字星：实体<10% range，上下影线存在
    is_doji = (body / (body_range + 1e-10) < 0.1) & (upper > 0) & (lower > 0)

    # 3. 看涨吞没：昨日阴，今日阳包阴
    is_engulfing_bullish = (
        (c.shift(1) < o.shift(1))
        & (c > o)
        & (o <= c.shift(1))
        & (c >= o.shift(1))
        & (body >= body.shift(1))
    )

    # 4. 看跌吞没：昨日阳，今日阴包阳
    is_engulfing_bearish = (
        (c.shift(1) > o.shift(1))
        & (c < o)
        & (o >= c.shift(1))
        & (c <= o.shift(1))
        & (body >= body.shift(1))
    )

    # 5. 看涨孕线：昨日大阴，今日小阳在昨日实体内
    is_harami_bullish = (
        (c.shift(1) < o.shift(1))
        & (c > o)
        & (body < body.shift(1) * 0.7)
        & (o > l.shift(1)) & (o < h.shift(1))
        & (c > l.shift(1)) & (c < h.shift(1))
    )

    # 6. 吊颈线：同锤子，上升趋势
    is_hanging_man = (lower >= 2*body) & (upper <= body) & is_up

    # 7. 倒锤：上影线长，下影线短
    is_inverted_hammer = (upper >= 2*body) & (lower <= body)

    # 8. 红三兵：连续3日阳，逐日新高
    is_three_white_soldiers = (
        (c.shift(2) > o.shift(2)) & (c.shift(1) > o.shift(1)) & (c > o)
        & (c.shift(2) < c.shift(1)) & (c.shift(1) < c)
    )

    # 9. 三乌鸦：连续3日阴，逐日新低
    is_three_black_crows = (
        (c.shift(2) < o.shift(2)) & (c.shift(1) < o.shift(1)) & (c < o)
        & (c.shift(2) > c.shift(1)) & (c.shift(1) > c)
    )

    # 10. 晨星：大跌->小星->阳突破
    big_drop = (c.shift(2) - o.shift(2)) / (o.shift(2) + 1e-10) < -0.02
    star_ratio = body.shift(1) / ((h.shift(1) - l.shift(1)) + 1e-10)
    is_small_star = star_ratio < 0.3
    # 收盘须超过前日开盘+收盘均值的一半（>= 而非 >，覆盖相等情况）
    mid = (o.shift(2) + c.shift(2)) / 2
    bullish_recovery = (c > o) & (c >= mid)
    is_morning_star = big_drop & is_small_star & bullish_recovery

    # 11. 暮星：大涨->小星->阴跌破
    big_rise = (c.shift(2) - o.shift(2)) / (o.shift(2) + 1e-10) > 0.02
    bearish_crash = (c < o) & (c <= mid)
    is_evening_star = big_rise & is_small_star & bearish_crash

    MIN = 10
    wm = df.index < MIN
    cols = ["is_hammer","is_doji","is_engulfing_bullish","is_engulfing_bearish",
            "is_harami_bullish","is_hanging_man","is_inverted_hammer",
            "is_three_white_soldiers","is_three_black_crows",
            "is_morning_star","is_evening_star"]
    vals = [is_hammer,is_doji,is_engulfing_bullish,is_engulfing_bearish,
            is_harami_bullish,is_hanging_man,is_inverted_hammer,
            is_three_white_soldiers,is_three_black_crows,
            is_morning_star,is_evening_star]
    for col, val in zip(cols, vals):
        df[col] = val.astype(float)
        df.loc[wm, col] = float("nan")
    return df


def detect_multi_candle(df: "pd.DataFrame") -> "pd.DataFrame":
    """识别 9 种组合 K 形态（向量化实现）。

    新增列（float 0/1）：is_tweezer_top / is_tweezer_bottom /
      is_rising_three / is_falling_three / is_bullish_counterattack /
      is_bearish_counterattack / is_matching_low / is_throwing_star / is_piercing_line
    """
    df = df.copy()
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    body = (c - o).abs()

    # 1. 顶平头
    is_tweezer_top = ((h - h.shift(1)).abs() / (h + 1e-10) < 0.001) & (c < c.shift(1))

    # 2. 底平头
    is_tweezer_bottom = ((l - l.shift(1)).abs() / (l + 1e-10) < 0.001) & (c > c.shift(1))

    # 3. 上升三法
    big_first = (c.shift(1) > o.shift(1)) & (body.shift(1) > body.shift(2) * 1.5)
    not_break_low = l > l.shift(1)
    final_up = (c > o) & (c > (o.shift(1) + c.shift(1)) / 2)
    is_rising_three = big_first & not_break_low & final_up

    # 4. 下降三法
    big_first_b = (c.shift(1) < o.shift(1)) & (body.shift(1) > body.shift(2) * 1.5)
    not_break_high = h < h.shift(1)
    final_down = (c < o) & (c < (o.shift(1) + c.shift(1)) / 2)
    is_falling_three = big_first_b & not_break_high & final_down

    # 5. 看涨反击线
    close_diff = (c - c.shift(1)).abs() / (c.shift(1) + 1e-10) < 0.005
    is_bullish_counterattack = (c.shift(1) < o.shift(1)) & (o > o.shift(1)) & close_diff

    # 6. 看跌反击线
    is_bearish_counterattack = (c.shift(1) > o.shift(1)) & (o < o.shift(1)) & close_diff

    # 7. 底部匹配
    same_low = (l - l.shift(1)).abs() / (l + 1e-10) < 0.001
    is_matching_low = same_low & (c > o)

    # 8. 射击之星
    ma20 = c.rolling(20).mean()
    is_uptrend = c > ma20
    upper = h - pd.concat([o, c], axis=1).max(axis=1)
    is_throwing_star = (upper >= 2*body) & is_uptrend

    # 9. 刺透线
    yesterday_big = (c.shift(1) < o.shift(1)) & (body.shift(1) > body.shift(2))
    today_lower = o < o.shift(1)
    mid = (o.shift(1) + c.shift(1)) / 2
    pierce = c > mid
    is_piercing_line = yesterday_big & today_lower & pierce

    MIN = 5
    wm = df.index < MIN
    cols = ["is_tweezer_top","is_tweezer_bottom","is_rising_three","is_falling_three",
            "is_bullish_counterattack","is_bearish_counterattack","is_matching_low",
            "is_throwing_star","is_piercing_line"]
    vals = [is_tweezer_top,is_tweezer_bottom,is_rising_three,is_falling_three,
            is_bullish_counterattack,is_bearish_counterattack,is_matching_low,
            is_throwing_star,is_piercing_line]
    for col, val in zip(cols, vals):
        df[col] = val.astype(float)
        df.loc[wm, col] = float("nan")
    return df


def detect_chan_pivot(df: "pd.DataFrame") -> "pd.DataFrame":
    """识别缠论简化版中枢。

    新增列：is_pivot_high / is_pivot_low / pivot_id / pivot_strength
    """
    df = df.copy()
    h, lo = df["high"], df["low"]
    W = 5
    rh = h.rolling(W, center=True).max()
    rl = lo.rolling(W, center=True).min()
    is_ph = (h == rh) & (h.shift(W//2) <= h) & (h.shift(-W//2) <= h)
    is_pl = (lo == rl) & (lo.shift(W//2) >= lo) & (lo.shift(-W//2) >= lo)
    is_ph = is_ph.astype(float)
    is_pl = is_pl.astype(float)
    is_ph.iloc[:W] = float("nan")
    is_ph.iloc[-W:] = float("nan")
    is_pl.iloc[:W] = float("nan")
    is_pl.iloc[-W:] = float("nan")
    pivot_id = pd.Series(0.0, index=df.index)
    pivot_strength = pd.Series(0.0, index=df.index)
    ph_idx = df.index[is_ph].tolist()
    pl_idx = df.index[is_pl].tolist()
    phs = {i: float(h.loc[i]) for i in ph_idx}
    pls = {i: float(lo.loc[i]) for i in pl_idx}
    all_pts = [(i, "H", phs[i]) for i in ph_idx] + [(i, "L", pls[i]) for i in pl_idx]
    all_pts.sort(key=lambda x: df.index.get_loc(x[0]))
    if len(all_pts) < 6:
        df["is_pivot_high"] = is_ph.astype(float)
        df["is_pivot_low"] = is_pl.astype(float)
        df["pivot_id"] = pivot_id
        df["pivot_strength"] = pivot_strength
        return df
    cid = 0
    for i in range(len(all_pts) - 2):
        s1, s2, s3 = all_pts[i], all_pts[i+1], all_pts[i+2]
        hs = [v for _, t, v in [s1,s2,s3] if t == "H"]
        ls = [v for _, t, v in [s1,s2,s3] if t == "L"]
        if not hs or not ls:
            continue
        rng2 = max(hs) - min(ls)
        pl2 = min(ls)
        if pl2 > 0 and rng2 / pl2 < 0.02:
            cid += 1
            for seg in [s1, s2, s3]:
                pivot_id.loc[seg[0]] = cid
                pivot_strength.loc[seg[0]] = 3
    df["is_pivot_high"] = is_ph.astype(float)
    df["is_pivot_low"] = is_pl.astype(float)
    df["pivot_id"] = pivot_id
    df["pivot_strength"] = pivot_strength
    wm = df.index < 11
    for col in ["is_pivot_high","is_pivot_low","pivot_id","pivot_strength"]:
        df.loc[wm, col] = float("nan")
    return df


def detect_elliott_wave(df: "pd.DataFrame") -> "pd.DataFrame":
    """识别波浪驱动（1+2+3+4+5 浪）。

    新增列：wave_label ('1'-'5') / wave_confidence (0-1)
    """
    df = df.copy()
    h, lo = df["high"], df["low"]
    wl = pd.Series(None, index=df.index, dtype=object)
    wc = pd.Series(0.0, index=df.index, dtype=float)
    if len(df) < 30:
        df["wave_label"] = wl
        df["wave_confidence"] = wc
        return df
    W = 5
    rh = h.rolling(W, center=True).max()
    rl = lo.rolling(W, center=True).min()
    is_ph = (h == rh) & (h.shift(W//2) <= h) & (h.shift(-W//2) <= h)
    is_pl = (lo == rl) & (lo.shift(W//2) >= lo) & (lo.shift(-W//2) >= lo)
    is_ph = is_ph.astype(float)
    is_pl = is_pl.astype(float)
    is_ph.iloc[:W] = float("nan")
    is_ph.iloc[-W:] = float("nan")
    is_pl.iloc[:W] = float("nan")
    is_pl.iloc[-W:] = float("nan")
    all_pts = []
    for idx in df.index[is_ph]:
        all_pts.append((idx, "H", float(h.loc[idx])))
    for idx in df.index[is_pl]:
        all_pts.append((idx, "L", float(lo.loc[idx])))
    all_pts.sort(key=lambda x: x[0])
    filtered = []
    prev = None
    for item in all_pts:
        if item[1] != prev:
            filtered.append(item)
            prev = item[1]
    all_pts = filtered
    if len(all_pts) < 5:
        df["wave_label"] = wl
        df["wave_confidence"] = wc
        return df
    wmap = {0:"1",1:"2",2:"3",3:"4",4:"5"}
    for si in range(len(all_pts)):
        if all_pts[si][1] != "L":
            continue
        seq = all_pts[si:si+5]
        if len(seq) < 5:
            continue
        pts = [(p[0], p[1], p[2]) for p in seq]
        rules = 0
        if pts[1][2] > pts[0][2]:
            rules += 1
        w1 = pts[1][2] - pts[0][2]
        w3 = pts[2][2] - pts[1][2]
        if w3 >= w1:
            rules += 1
        if pts[3][2] > pts[0][2]:
            rules += 1
        if pts[4][2] - pts[3][2] >= w1 * 0.5:
            rules += 1
        if pts[1][2] > pts[0][2]:
            rules += 1
        conf = min(1.0, rules / 5.0)
        for i, PT in enumerate(pts):
            wl.loc[PT[0]] = wmap[i]
            wc.loc[PT[0]] = conf
        break
    wm = df.index < 30
    wl[wm] = None
    wc[wm] = float("nan")
    df["wave_label"] = wl
    df["wave_confidence"] = wc.astype(float)
    return df
