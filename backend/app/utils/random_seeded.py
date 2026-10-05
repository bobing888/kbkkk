"""可复现的随机源工具。

移植自 KB github-HKUDS-AI-Trader.md §3 "Deterministic seeded randomization"：
> SHA-256-derived seeds make random grouping reproducible for experiments and reruns.

用途：
- 回测时 Monte Carlo / bootstrap 保证可复现
- 跟单时仓位随机化（同一信号源 + 同一标的 → 相同随机化结果，便于 debug）
- A/B 测试中实验组分配可复现

使用：
    rng = seeded_random("backtest_2024_btc", symbol="BTC/USDT", period="1d")
    sample = rng.sample(range(100), k=10)  # 同样输入 → 同样输出
"""
from __future__ import annotations

import hashlib
import random


def _seed_from(mission_key: str, features: tuple) -> int:
    """从 mission_key + features 派生稳定 32-bit 种子。"""
    raw = f"{mission_key}|" + "|".join(str(f) for f in features)
    # 取 SHA-256 前 8 位 hex → int（足够 random for 不同输入）
    return int(hashlib.sha256(raw.encode()).hexdigest()[:8], 16)


def seeded_random(mission_key: str, *features) -> random.Random:
    """返回可复现的 random.Random 实例。

    相同 (mission_key, features) → 相同随机序列。

    Args:
        mission_key: 任务/实验标识，如 "backtest_2024_btc"
        *features: 影响随机化的因子（symbol、period、实验 ID 等）

    Returns:
        已 seed 的 random.Random 实例
    """
    seed = _seed_from(mission_key, features)
    rng = random.Random()
    rng.seed(seed)
    return rng


__all__ = ["seeded_random", "_seed_from"]