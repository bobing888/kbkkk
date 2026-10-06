"""阶段 2 - 分析 API 路由（指标 / 形态 / 信号 / 聚合）

业务逻辑在 services/indicators.py、analytics/patterns.py、analytics/signal_direction.py。
本路由只做：参数解析 → 调业务 → 序列化为 JSON。
"""
from typing import Literal

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from app.services.data_fetcher import data_fetcher
from app.services.indicators import IndicatorEngine
from app.analytics.patterns import detect_single_candle, detect_multi_candle
from app.analytics.signal_direction import generate_signal, Signal

router = APIRouter(prefix="/api/v1", tags=["analysis"])


# ─── 工具 ────────────────────────────────────────────────────────────────


def _df_to_records(df: pd.DataFrame, datetime_as_iso: bool = True) -> list[dict]:
    """DataFrame → JSON records。处理 NaN/datetime。"""
    out = df.to_dict(orient="records")
    for row in out:
        if "datetime" in row:
            v = row["datetime"]
            if datetime_as_iso and hasattr(v, "isoformat"):
                row["datetime"] = v.isoformat()
            elif pd.isna(v):
                row["datetime"] = None
    return out


def _signal_to_dict(s: Signal) -> dict:
    """Signal dataclass → JSON 字典。"""
    return {
        "name": s.name,
        "direction": s.direction,
        "confidence": round(s.confidence, 3),
        "entry": round(s.entry, 4) if s.entry is not None else None,
        "stop_loss": round(s.stop_loss, 4) if s.stop_loss is not None else None,
        "take_profit": round(s.take_profit, 4) if s.take_profit is not None else None,
        "sources": s.sources,
        "datetime": s.datetime.isoformat() if s.datetime is not None else None,
    }


# ─── 共享 K 线获取 ────────────────────────────────────────────────────────


async def _get_df(
    symbol: str,
    period: str,
    market: str,
    adjust: str,
) -> pd.DataFrame:
    """统一 K 线获取，错误包成 HTTPException(500)。"""
    try:
        df = data_fetcher.get_kline(symbol, period, None, None, market, adjust)
        # 兼容测试 mock 返回 coroutine
        if hasattr(df, "__await__"):
            df = await df
        return df
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_kline failed: {symbol}/{period}/{market}: {e}")
        raise HTTPException(status_code=500, detail=f"数据获取失败: {str(e)}")


# ─── /api/v1/indicators/{symbol} ─────────────────────────────────────────


@router.get("/indicators/{symbol}")
async def get_indicators(
    symbol: str,
    period: Literal['1m', '5m', '15m', '30m', '60m', '1d', '1w', '1M'] = Query("1d"),
    market: Literal['cn', 'us', 'crypto'] = Query("cn"),
    adjust: Literal['qfq', 'hfq', 'none'] = Query("qfq"),
):
    """计算 6 大指标族（MA/MACD/RSI/BOLL/KDJ/OBV）。返回最后 N 行。"""
    df = await _get_df(symbol, period, market, adjust)
    df_ind = IndicatorEngine.calculate_all(df)

    # 提取最近 1 行 + 全部指标列
    last_row = df_ind.iloc[-1].to_dict() if len(df_ind) else {}
    # 处理 datetime
    if "datetime" in last_row and hasattr(last_row["datetime"], "isoformat"):
        last_row["datetime"] = last_row["datetime"].isoformat()
    # 移除 NaN（JSON 不支持）
    last_row = {k: (None if (isinstance(v, float) and pd.isna(v)) else v)
                for k, v in last_row.items()}

    # 6 大指标族 → 子字典
    indicators = {
        "MA": {k: last_row.get(k) for k in ["MA5", "MA10", "MA20", "MA60", "MA120", "MA250"]},
        "MACD": {k: last_row.get(k) for k in ["DIF", "DEA", "MACD"]},
        "RSI": last_row.get("RSI"),
        "BOLL": {k: last_row.get(k) for k in ["BOLL_MID", "BOLL_UPPER", "BOLL_LOWER"]},
        "KDJ": {k: last_row.get(k) for k in ["K", "D", "J"]},
        "OBV": last_row.get("OBV"),
    }

    return {
        "symbol": symbol,
        "period": period,
        "market": market,
        "datetime": last_row.get("datetime"),
        "indicators": indicators,
    }


# ─── /api/v1/patterns/{symbol} ───────────────────────────────────────────


@router.get("/patterns/{symbol}")
async def get_patterns(
    symbol: str,
    period: Literal['1m', '5m', '15m', '30m', '60m', '1d', '1w', '1M'] = Query("1d"),
    market: Literal['cn', 'us', 'crypto'] = Query("cn"),
    adjust: Literal['qfq', 'hfq', 'none'] = Query("qfq"),
    limit: int = Query(10, ge=1, le=100, description="返回最近 N 根 K 线"),
):
    """检测单 K / 多 K 形态，返回最近 N 根 K 线命中的形态列表。"""
    df = await _get_df(symbol, period, market, adjust)
    df = detect_single_candle(df)
    df = detect_multi_candle(df)

    # 形态列名（is_*）
    pattern_cols = [c for c in df.columns if c.startswith("is_")]

    # 取最近 N 行
    recent = df.tail(limit)
    patterns_found = []
    for _, row in recent.iterrows():
        for col in pattern_cols:
            val = row.get(col)
            if isinstance(val, (int, float)) and not pd.isna(val) and val == 1:
                patterns_found.append({
                    "datetime": row["datetime"].isoformat() if hasattr(row["datetime"], "isoformat") else row["datetime"],
                    "name": col,
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                })

    return {
        "symbol": symbol,
        "period": period,
        "market": market,
        "count": len(patterns_found),
        "patterns": patterns_found,
    }


# ─── /api/v1/signals/{symbol} ────────────────────────────────────────────


@router.get("/signals/{symbol}")
async def get_signals(
    symbol: str,
    period: Literal['1m', '5m', '15m', '30m', '60m', '1d', '1w', '1M'] = Query("1d"),
    market: Literal['cn', 'us', 'crypto'] = Query("cn"),
    adjust: Literal['qfq', 'hfq', 'none'] = Query("qfq"),
):
    """基于指标 + 形态 + 共振判定交易信号。"""
    df = await _get_df(symbol, period, market, adjust)

    # 1. 算指标
    df = IndicatorEngine.calculate_all(df)
    # 2. 算形态
    df = detect_single_candle(df)
    df = detect_multi_candle(df)
    # 3. 生成信号
    signals = generate_signal(df)

    return {
        "symbol": symbol,
        "period": period,
        "market": market,
        "count": len(signals),
        "signals": [_signal_to_dict(s) for s in signals],
    }


# ─── /api/v1/analysis/{symbol} 聚合 ──────────────────────────────────────


@router.get("/analysis/{symbol}")
async def get_analysis(
    symbol: str,
    period: Literal['1m', '5m', '15m', '30m', '60m', '1d', '1w', '1M'] = Query("1d"),
    market: Literal['cn', 'us', 'crypto'] = Query("cn"),
    adjust: Literal['qfq', 'hfq', 'none'] = Query("qfq"),
    limit: int = Query(10, ge=1, le=100, description="形态返回最近 N 根 K 线"),
):
    """一次返回 指标 + 形态 + 信号（前端省 RTT）。"""
    df = await _get_df(symbol, period, market, adjust)

    # 指标
    df_ind = IndicatorEngine.calculate_all(df)
    last_row = df_ind.iloc[-1].to_dict() if len(df_ind) else {}
    if "datetime" in last_row and hasattr(last_row["datetime"], "isoformat"):
        last_row["datetime"] = last_row["datetime"].isoformat()
    last_row = {k: (None if (isinstance(v, float) and pd.isna(v)) else v)
                for k, v in last_row.items()}
    indicators = {
        "MA": {k: last_row.get(k) for k in ["MA5", "MA10", "MA20", "MA60", "MA120", "MA250"]},
        "MACD": {k: last_row.get(k) for k in ["DIF", "DEA", "MACD"]},
        "RSI": last_row.get("RSI"),
        "BOLL": {k: last_row.get(k) for k in ["BOLL_MID", "BOLL_UPPER", "BOLL_LOWER"]},
        "KDJ": {k: last_row.get(k) for k in ["K", "D", "J"]},
        "OBV": last_row.get("OBV"),
    }

    # 形态
    df_pat = detect_single_candle(df_ind)
    df_pat = detect_multi_candle(df_pat)
    pattern_cols = [c for c in df_pat.columns if c.startswith("is_")]
    recent = df_pat.tail(limit)
    patterns_found = []
    for _, row in recent.iterrows():
        for col in pattern_cols:
            val = row.get(col)
            if isinstance(val, (int, float)) and not pd.isna(val) and val == 1:
                patterns_found.append({
                    "datetime": row["datetime"].isoformat() if hasattr(row["datetime"], "isoformat") else row["datetime"],
                    "name": col,
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                })

    # 信号
    signals = generate_signal(df_pat)

    return {
        "symbol": symbol,
        "period": period,
        "market": market,
        "datetime": last_row.get("datetime"),
        "indicators": indicators,
        "patterns": patterns_found,
        "signals": [_signal_to_dict(s) for s in signals],
    }
