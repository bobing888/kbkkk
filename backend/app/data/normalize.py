"""Provider 输出规范化。

移植自 KB github-HKUDS-Vibe-Trading.md §3 "Boundary normalization" +
        KB github-openbq-org-OpenBB.md §2 "Output normalization adapters":
> Provider-specific interval maps and symbol parsers preserve distinctions
> and accept common aliases. Independent maps can drift across connectors.

目的：把 cn/us/crypto 三个 provider 的字段名统一为前端可消费的标准化 DataFrame。
"""
from __future__ import annotations

import pandas as pd

# 标准化列名（kbkk 与前端约定的最终格式）
STANDARD_COLUMNS = ["datetime", "open", "high", "low", "close", "volume", "amount"]

# 各 provider 的原始字段名 → 标准字段名映射
_FIELD_ALIASES = {
    "datetime": ["datetime", "date", "timestamp", "Date", "时间"],
    "open": ["open", "Open", "开盘"],
    "high": ["high", "High", "最高"],
    "low": ["low", "Low", "最低"],
    "close": ["close", "Close", "收盘"],
    "volume": ["volume", "Volume", "成交量"],
    "amount": ["amount", "Amount", "成交额", "成交金额", "turnover"],
}


def normalize_kline_df(df: pd.DataFrame, market: str) -> pd.DataFrame:
    """规范化 K 线 DataFrame：把 provider 字段名映射为标准列名。

    Args:
        df: 来自 cn/us/crypto 任一 provider 的原始 DataFrame
        market: 市场标识（用于日志）

    Returns:
        标准化列名的 DataFrame，缺失列以 NaN 填充。
        datetime 列转换为 pd.Timestamp 类型。
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=STANDARD_COLUMNS)

    # 构建 rename map
    rename_map = {}
    for std_col, aliases in _FIELD_ALIASES.items():
        for alias in aliases:
            if alias in df.columns and alias != std_col:
                rename_map[alias] = std_col
                break  # 命中第一个 alias 就用

    df = df.rename(columns=rename_map)

    # 确保所有标准列都存在
    for col in STANDARD_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA

    # datetime 转为 Timestamp
    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")

    # 按标准列顺序返回
    return df[STANDARD_COLUMNS].copy()


__all__ = ["normalize_kline_df", "STANDARD_COLUMNS"]