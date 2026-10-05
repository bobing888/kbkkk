"""PAVA Isotonic Calibration Library — C1

基于 Probability Aters + PAVA (Pool Adjacent Violators) 算法
将原始置信度校准为实际胜率。

核心公式：
  Brier Score = (1/N) * Σ (confidence_i - outcome_i)^2
  验收阈值：Brier Score < 0.25

PAVA 步骤：
  1. 按 confidence 排序样本
  2. 从左到右扫描，对每个违反单调性的 block 合并（平均）
  3. 重复直到所有 block 单调递增
  4. 输出断点表 [{confidence, observed_freq, sample_size}, ...]
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Protocol

# ── 最低样本量（参照 calibration.py trainer 的 MIN_TRAIN_SAMPLES）──────────────
MIN_TRAIN_SAMPLES = 100


# ── Types ────────────────────────────────────────────────────────────────────

Confidence = float
PnLPct = float
BinaryOutcome = int  # 1 = win, 0 = loss
Sample = tuple[Confidence, PnLPct]
BinarySample = tuple[Confidence, BinaryOutcome]


# ── CalibrationModel ──────────────────────────────────────────────────────────

@dataclass
class CalibrationModel:
    """校准后模型，含断点表。

    断点表格式：
        breakpoints = [
            {confidence: 0.3, observed_freq: 0.25, sample_size: 50},
            {confidence: 0.6, observed_freq: 0.55, sample_size: 100},
            ...
        ]
    """
    timeframe: str
    breakpoints: list[dict] = field(default_factory=list)
    brier_score: float = 0.0

    def apply(self, raw_confidence: float) -> float:
        """将原始置信度映射到校准后置信度。

        规则：
          - 命中断点 → 直接返回 observed_freq
          - 区间内 → 线性插值
          - 外插（< 最小 / > 最大）→ 用最近断点的 observed_freq
        """
        if not self.breakpoints:
            return raw_confidence  # 无模型时返回原值

        # 按 confidence 升序
        sorted_bp = sorted(self.breakpoints, key=lambda b: b["confidence"])

        # 边界外插
        if raw_confidence <= sorted_bp[0]["confidence"]:
            return sorted_bp[0]["observed_freq"]
        if raw_confidence >= sorted_bp[-1]["confidence"]:
            return sorted_bp[-1]["observed_freq"]

        # 线性插值
        for i in range(len(sorted_bp) - 1):
            lo, hi = sorted_bp[i], sorted_bp[i + 1]
            if lo["confidence"] <= raw_confidence <= hi["confidence"]:
                if hi["confidence"] == lo["confidence"]:
                    return lo["observed_freq"]
                t = (raw_confidence - lo["confidence"]) / (hi["confidence"] - lo["confidence"])
                return lo["observed_freq"] + t * (hi["observed_freq"] - lo["observed_freq"])

        # fallback（理论上不会到这）
        return raw_confidence


# ── PAVA (Pool Adjacent Violators) ───────────────────────────────────────────

def _pava(x: list[float], y: list[float]) -> list[float]:
    """PAVA: Pool Adjacent Violators 算法。

    Args:
        x: 排序后的置信度（升序）
        y: 对应的观测频率

    Returns:
        单调不减的 y 值列表（与 x 等长）
    """
    if len(x) != len(y):
        raise ValueError("x 和 y 长度必须相同")
    if len(x) == 0:
        return []
    if len(x) == 1:
        return [float(y[0])]

    n = len(x)
    # blocks: list of (start_idx, end_idx, value)
    blocks: list[tuple[int, int, float]] = [(i, i + 1, float(y[i])) for i in range(n)]

    def _merge(blocks: list[tuple[int, int, float]]) -> list[tuple[int, int, float]]:
        i = 0
        while i < len(blocks) - 1:
            curr = blocks[i]
            nxt = blocks[i + 1]
            # 检查单调性：curr.value > nxt.value → 违反
            if curr[2] > nxt[2]:
                # 合并两个块
                merged_start = curr[0]
                merged_end = nxt[1]
                merged_val = (
                    (curr[2] * (curr[1] - curr[0]) + nxt[2] * (nxt[1] - nxt[0]))
                    / (merged_end - merged_start)
                )
                merged = (merged_start, merged_end, merged_val)
                blocks = blocks[:i] + [merged] + blocks[i + 2:]
                # 合并后可能产生新的 violator，退回前一位置重检
                if i > 0:
                    i -= 1
                else:
                    i = 0
            else:
                i += 1
        return blocks

    blocks = _merge(blocks)

    # 展开 blocks 到每个样本
    result = []
    for start, end, val in blocks:
        result.extend([val] * (end - start))
    return result


# ── Brier Score ──────────────────────────────────────────────────────────────

def _compute_brier_score(binary_samples: list[BinarySample]) -> float:
    """计算 Brier Score。

    Brier Score = (1/N) * Σ (confidence - outcome)^2
    范围 [0, 1]，越接近 0 校准越好。
    """
    if not binary_samples:
        return 0.0
    total = sum((conf - outcome) ** 2 for conf, outcome in binary_samples)
    return total / len(binary_samples)


def _pnl_to_binary(samples: list[Sample]) -> list[BinarySample]:
    """PnL → 二值 outcome（win=1, loss=0）"""
    return [(conf, 1 if pnl > 0 else 0) for conf, pnl in samples]


# ── Main API ─────────────────────────────────────────────────────────────────

def train_calibrator(timeframe: str, samples: list[Sample]) -> CalibrationModel:
    """训练 PAVA Isotonic 校准模型。

    Args:
        timeframe: 时间周期，如 "1h"、"5m"
        samples: (raw_confidence, pnl_pct) 样本列表

    Returns:
        CalibrationModel，含断点表 + Brier score

    Raises:
        ValueError: 样本数 < MIN_TRAIN_SAMPLES
    """
    if len(samples) < MIN_TRAIN_SAMPLES:
        raise ValueError(
            f"样本不足：需要 ≥ {MIN_TRAIN_SAMPLES}，当前 {len(samples)}"
        )

    # 1. 转二进制 outcome
    binary_samples = _pnl_to_binary(samples)

    # 2. 按 confidence 升序排序
    sorted_samples = sorted(binary_samples, key=lambda s: s[0])
    x = [s[0] for s in sorted_samples]
    y = [float(s[1]) for s in sorted_samples]

    # 3. PAVA 拟合
    calibrated = _pava(x, y)

    # 4. 构造断点表（合并相邻同值块）
    breakpoints: list[dict] = []
    i = 0
    while i < len(x):
        conf = x[i]
        val = calibrated[i]
        # 统计该块内样本数
        j = i
        while j < len(x) and abs(calibrated[j] - val) < 1e-9:
            j += 1
        sample_size = j - i
        breakpoints.append({
            "confidence": round(conf, 4),
            "observed_freq": round(val, 4),
            "sample_size": sample_size,
        })
        i = j

    # 5. 计算 Brier Score
    brier = _compute_brier_score(binary_samples)

    return CalibrationModel(
        timeframe=timeframe,
        breakpoints=breakpoints,
        brier_score=round(brier, 4),
    )
