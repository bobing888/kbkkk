"""T1 — db-scoped cache key

移植自 KB github-HKUDS-AI-Trader.md §4 "Database-scoped cache keys"。
"""
import os
import hashlib
import random
from pathlib import Path

import pandas as pd

from app.cache import CacheKey
from app.utils.random_seeded import seeded_random
from app.utils.atomic_io import atomic_write_json, atomic_read_json
from app.data.normalize import normalize_kline_df, STANDARD_COLUMNS


# ─────────────────── T1: db-scoped cache key ───────────────────


def test_cache_key_has_prefix_and_scope():
    """CacheKey 必须以 PREFIX:SCOPE: 开头。"""
    key = CacheKey.kline("BTC/USDT", "1d", "20240101", "20241231")
    parts = key.split(":")
    assert len(parts) >= 3, f"key 必须至少三段，实际 {parts}"
    assert parts[0] == CacheKey.PREFIX
    assert parts[1] == CacheKey._scope()
    assert len(parts[1]) == 8  # md5 截 8 位


def test_cache_key_scope_changes_with_db_url(monkeypatch):
    """切换 KBKK_DB_URL 必须改变 SCOPE。"""
    monkeypatch.setenv("KBKK_DB_URL", "postgresql://prod:5432/db")
    expected = hashlib.md5(b"postgresql://prod:5432/db").hexdigest()[:8]
    assert CacheKey._scope() == expected


def test_cache_key_kline_full_path():
    key = CacheKey.kline("600519", "1d", "20240101", "20241231")
    assert key.endswith(":kline:600519:1d:20240101:20241231")


def test_cache_key_realtime_quote():
    key = CacheKey.realtime_quote("BTC/USDT")
    assert key.endswith(":quote:BTC/USDT")


def test_keys_are_unique_across_scopes(monkeypatch):
    """同一 symbol 在不同 SCOPE 下应产生不同 key。"""
    monkeypatch.setenv("KBKK_DB_URL", "db_a")
    key_a = CacheKey.kline("X", "1d", "s", "e")

    monkeypatch.setenv("KBKK_DB_URL", "db_b")
    key_b = CacheKey.kline("X", "1d", "s", "e")

    assert key_a != key_b


# ─────────────────── T7: deterministic seeded random ───────────────────


def test_seeded_random_reproducible():
    """相同 (mission_key, features) → 相同随机序列。"""
    rng1 = seeded_random("backtest_2024", "BTC/USDT", "1d")
    rng2 = seeded_random("backtest_2024", "BTC/USDT", "1d")
    assert rng1.random() == rng2.random()


def test_seeded_random_differs_with_features():
    """features 改变 → 序列改变。"""
    rng1 = seeded_random("backtest", "BTC/USDT")
    rng2 = seeded_random("backtest", "ETH/USDT")
    assert rng1.random() != rng2.random()


def test_seeded_random_differs_with_key():
    """mission_key 改变 → 序列改变。"""
    rng1 = seeded_random("a", "X")
    rng2 = seeded_random("b", "X")
    assert rng1.random() != rng2.random()


def test_seeded_random_returns_Random():
    """返回的对象是 random.Random 实例，有 sample/choice/shuffle 方法。"""
    rng = seeded_random("test", "feature")
    assert isinstance(rng, random.Random)
    sample = rng.sample(range(100), k=5)
    assert len(sample) == 5


# ─────────────────── T2: atomic JSON IO ───────────────────


def test_atomic_write_then_read(tmp_path: Path):
    """写后能读回相同内容。"""
    path = tmp_path / "sub" / "config.json"
    data = {"foo": "bar", "count": 42, "list": [1, 2, 3]}
    atomic_write_json(path, data)
    loaded = atomic_read_json(path)
    assert loaded == data


def test_atomic_write_creates_parent_dir(tmp_path: Path):
    """父目录不存在时应自动创建。"""
    path = tmp_path / "deep" / "nested" / "file.json"
    atomic_write_json(path, {"x": 1})
    assert path.exists()


def test_atomic_read_missing_returns_default(tmp_path: Path):
    """读不存在的文件应返回 default（不抛异常）。"""
    path = tmp_path / "nope.json"
    assert atomic_read_json(path, default={"empty": True}) == {"empty": True}
    assert atomic_read_json(path) is None


def test_atomic_write_no_tmp_leftover(tmp_path: Path):
    """成功后不应有 .tmp 残留。"""
    path = tmp_path / "clean.json"
    atomic_write_json(path, {"a": 1})
    leftovers = list(tmp_path.glob("*.tmp"))
    assert leftovers == []


def test_atomic_write_chinese_preserved(tmp_path: Path):
    """ensure_ascii=False 时中文不转义。"""
    path = tmp_path / "cn.json"
    atomic_write_json(path, {"name": "茅台", "code": "600519"})
    raw = path.read_text(encoding="utf-8")
    assert "茅台" in raw


# ─────────────────── T8: output normalization ───────────────────


def test_normalize_renames_cn_aliases():
    """akshare 的中文列名 → 标准列名。"""
    df = pd.DataFrame({
        "日期": ["2024-01-01", "2024-01-02"],
        "开盘": [100.0, 101.0],
        "最高": [105.0, 106.0],
        "最低": [99.0, 100.0],
        "收盘": [104.0, 105.0],
        "成交量": [1000, 1100],
        "成交额": [104000, 115500],
    })
    out = normalize_kline_df(df, market="cn")
    assert list(out.columns) == STANDARD_COLUMNS
    assert out["close"].iloc[0] == 104.0
    assert out["amount"].iloc[0] == 104000


def test_normalize_passes_through_us_already_standard():
    """yfinance 已经用小写列名，应无变更。"""
    df = pd.DataFrame({
        "datetime": pd.to_datetime(["2024-01-01", "2024-01-02"]),
        "open": [100.0, 101.0],
        "high": [105.0, 106.0],
        "low": [99.0, 100.0],
        "close": [104.0, 105.0],
        "volume": [1000, 1100],
    })
    out = normalize_kline_df(df, market="us")
    assert list(out.columns) == STANDARD_COLUMNS
    assert "amount" in out.columns  # 缺失列自动 NaN


def test_normalize_handles_empty():
    """空 DataFrame 应返回标准化空表。"""
    out = normalize_kline_df(pd.DataFrame(), market="crypto")
    assert list(out.columns) == STANDARD_COLUMNS
    assert len(out) == 0


def test_normalize_datetime_coerced():
    """datetime 列强制转 Timestamp。"""
    df = pd.DataFrame({
        "date": ["2024-01-01", "2024-01-02"],
        "open": [1.0, 2.0],
        "close": [1.0, 2.0],
    })
    out = normalize_kline_df(df, market="us")
    assert pd.api.types.is_datetime64_any_dtype(out["datetime"])