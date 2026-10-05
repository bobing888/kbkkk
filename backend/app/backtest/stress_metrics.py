"""压力测试指标 — D2

7 个风险调整收益指标：
  cvar          CVaR (Conditional Value at Risk)
  sortino_ratio Sortino 比率
  calmar_ratio  Calmar 比率
  recovery_factor 恢复因子
  stability    R² of equity curve vs time
  tail_ratio   右尾/左尾比
  omega_ratio  收益/亏损概率密度比
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np
import pandas as pd


# ── CVaR ──────────────────────────────────────────────────────────────────────

def cvar(returns: pd.Series, alpha: float = 0.05) -> float:
    """CVaR (Conditional Value at Risk)，条件风险价值。

    定义：左尾 alpha 分位点以下收益的条件均值（期望损失）。

    Args:
        returns: 收益率序列
        alpha: 左尾分位点，默认 5%（95% 置信）

    Returns:
        CVaR（负值表示损失）

    Example:
        >>> cvar(pd.Series([-0.10, -0.05, -0.02, 0.01, 0.03]), alpha=0.05)
        -0.10  # 左尾 5% 为 -0.10
    """
    if returns.empty:
        return 0.0

    # VaR 分位点
    var_threshold = returns.quantile(alpha, interpolation="lower")
    # 左尾部分
    tail = returns[returns <= var_threshold]

    if tail.empty:
        return 0.0

    return float(tail.mean())


# ── Sortino Ratio ─────────────────────────────────────────────────────────────

def sortino_ratio(
    returns: pd.Series,
    risk_free: float = 0.0,
) -> float:
    """Sortino 比率。

    公式：Sortino = (mean(returns) - risk_free) / downside_std
    只考虑下行风险（负收益），比 Sharpe 更关注亏损。

    Args:
        returns: 收益率序列
        risk_free: 无风险收益率（年化）

    Returns:
        Sortino 比率
    """
    if returns.empty:
        return 0.0

    excess = returns - risk_free
    downside = excess[excess < 0]

    if downside.empty:
        return 0.0

    downside_std = float(downside.std(ddof=1))
    if downside_std == 0:
        return 0.0

    return float(excess.mean() / downside_std)


# ── Calmar Ratio ──────────────────────────────────────────────────────────────

def calmar_ratio(
    returns: pd.Series,
    max_dd: float,
) -> float:
    """Calmar 比率。

    公式：Calmar = total_return / max_drawdown
    衡量每单位最大回撤的收益。

    Args:
        returns: 收益率序列
        max_dd: 最大回撤（小数，如 0.20 表示 20%）

    Returns:
        Calmar 比率
    """
    if max_dd <= 0:
        return 0.0

    total_return = float(returns.sum())
    return total_return / max_dd


# ── Recovery Factor ───────────────────────────────────────────────────────────

def recovery_factor(
    returns: pd.Series,
    max_dd: float,
) -> float:
    """恢复因子。

    公式：Recovery Factor = sum(returns) / max_drawdown
    衡量从最大回撤中恢复的能力。

    Args:
        returns: 收益率序列
        max_dd: 最大回撤（小数）

    Returns:
        恢复因子
    """
    if max_dd <= 0:
        return 0.0

    net_return = float(returns.sum())
    return net_return / max_dd


# ── Stability ─────────────────────────────────────────────────────────────────

def stability(equity: pd.Series) -> float:
    """Equity 曲线稳定性（R²）。

    公式：R² of equity curve vs time (linear regression)
    衡量 equity 随时间增长的稳定性（0-1，1=完美线性增长）。

    Args:
        equity: 资金曲线

    Returns:
        R²（0-1）

    Example:
        >>> stability(pd.Series([100 + i for i in range(100)]))  # 线性 → ~1.0
    """
    if equity.empty or len(equity) < 2:
        return 0.0

    # 检查方差是否为 0（常数序列）
    if equity.std(ddof=1) == 0:
        return 0.0

    # 时间序列（x = 0, 1, 2, ...）
    x = np.arange(len(equity))
    y = equity.values.astype(float)

    # 线性回归：y = a*x + b
    x_mean = x.mean()
    y_mean = y.mean()

    num = np.sum((x - x_mean) * (y - y_mean))
    den = np.sum((x - x_mean) ** 2)

    if den == 0:
        return 0.0

    slope = num / den
    intercept = y_mean - slope * x_mean

    # 预测值
    y_pred = slope * x + intercept

    # R² = 1 - SS_res / SS_tot
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - y_mean) ** 2)

    if ss_tot == 0:
        return 0.0

    r_squared = 1 - ss_res / ss_tot
    return float(max(0.0, min(1.0, r_squared)))


# ── Tail Ratio ────────────────────────────────────────────────────────────────

def tail_ratio(returns: pd.Series) -> float:
    """尾部比率。

    公式：tail_ratio = right_tail_95 / |left_tail_95|
    右尾 95% 均值 / 左尾 5% 均值绝对值。
    > 1 表示右尾更肥（收益潜力更大）。

    Args:
        returns: 收益率序列

    Returns:
        尾部比率（无右尾 → 0，无左尾 → inf）
    """
    if returns.empty:
        return 0.0

    # 用 interpolation="lower"/"higher" 确保左右尾不重叠
    left_thresh = returns.quantile(0.05, interpolation="lower")
    right_thresh = returns.quantile(0.95, interpolation="higher")
    left_tail = returns[returns <= left_thresh]
    right_tail = returns[returns >= right_thresh]

    if right_tail.empty:
        return 0.0
    if left_tail.empty:
        return float("inf")

    right_mean = float(right_tail.mean())
    left_mean = abs(float(left_tail.mean()))

    if left_mean == 0:
        return float("inf")
    # 右尾均值必须为正（否则无实质收益）
    if right_mean <= 0:
        return 0.0

    return right_mean / left_mean


# ── Omega Ratio ───────────────────────────────────────────────────────────────

def omega_ratio(
    returns: pd.Series,
    threshold: float = 0.0,
) -> float:
    """Omega 比率。

    公式：Omega = sum(gains below threshold) / sum(losses below threshold)
    = P(gain > threshold) / P(loss < threshold) 的概率加权比。
    threshold=0 时等价于盈亏总额比。

    Args:
        returns: 收益率序列
        threshold: 收益阈值（默认 0）

    Returns:
        Omega 比率（无亏损 → inf）
    """
    if returns.empty:
        return 0.0

    excess = returns - threshold

    gains = excess[excess > 0]
    losses = excess[excess < 0]

    if losses.empty:
        return float("inf")

    total_gains = float(gains.sum())
    total_losses = abs(float(losses.sum()))

    if total_losses == 0:
        return float("inf")

    return total_gains / total_losses
