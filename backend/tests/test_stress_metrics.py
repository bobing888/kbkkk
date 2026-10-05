"""test_stress_metrics — D2

TDD 红：7 压力指标 + 8 单元测试
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.backtest.stress_metrics import (
    cvar,
    sortino_ratio,
    calmar_ratio,
    recovery_factor,
    stability,
    tail_ratio,
    omega_ratio,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _flat(n: int = 100) -> pd.Series:
    """全是 0 的收益序列。"""
    return pd.Series([0.0] * n)


def _uniform(a: float, b: float, n: int = 100) -> pd.Series:
    """[a, b] 均匀分布。"""
    rng = np.random.default_rng(42)
    return pd.Series(rng.uniform(a, b, n))


# ── Test: cvar ───────────────────────────────────────────────────────────────

class TestCvar:
    def test_cvar_alpha_05(self):
        """CVaR(0.05) = 左尾 5% 的条件均值。"""
        returns = pd.Series([-0.10, -0.05, -0.02, 0.01, 0.03])
        result = cvar(returns, alpha=0.05)
        assert isinstance(result, float)
        # 最差的 5% = [-0.10] → 均值 = -0.10
        assert abs(result - (-0.10)) < 1e-6

    def test_cvar_edge_alpha(self):
        """alpha=1 → 所有收益。"""
        returns = pd.Series([0.01, 0.02, -0.01])
        result = cvar(returns, alpha=1.0)
        assert abs(result - returns.mean()) < 1e-6


# ── Test: sortino_ratio ───────────────────────────────────────────────────────

class TestSortinoRatio:
    def test_sortino_ratio_formula(self):
        """Sortino = mean / downside_std。"""
        returns = pd.Series([0.02, 0.03, -0.01, 0.01, -0.02])
        result = sortino_ratio(returns, risk_free=0.0)
        assert isinstance(result, float)

    def test_sortino_ratio_zero_downside(self):
        """无下行风险 → Sortino = 0（不除零）。"""
        returns = pd.Series([0.01, 0.02, 0.03])
        result = sortino_ratio(returns, risk_free=0.0)
        assert result == 0.0

    def test_sortino_ratio_with_risk_free(self):
        """sortino 支持 risk_free 参数。"""
        returns = pd.Series([0.03, 0.05, 0.02])
        result = sortino_ratio(returns, risk_free=0.01)
        assert isinstance(result, float)


# ── Test: calmar_ratio ───────────────────────────────────────────────────────

class TestCalmarRatio:
    def test_calmar_ratio_formula(self):
        """Calmar = mean_return / max_drawdown。"""
        returns = pd.Series([0.05, 0.10, 0.03, 0.02, 0.05])
        result = calmar_ratio(returns, max_dd=0.20)
        assert isinstance(result, float)
        assert result > 0  # total > 0, dd > 0

    def test_calmar_ratio_zero_dd(self):
        """max_dd=0 → Calmar = 0。"""
        returns = pd.Series([0.01, 0.02, 0.03])
        result = calmar_ratio(returns, max_dd=0.0)
        assert result == 0.0


# ── Test: recovery_factor ───────────────────────────────────────────────────

class TestRecoveryFactor:
    def test_recovery_factor_formula(self):
        """Recovery Factor = sum(returns) / max_drawdown。"""
        returns = pd.Series([0.05, 0.10, 0.03, 0.02, 0.05])
        result = recovery_factor(returns, max_dd=0.20)
        assert isinstance(result, float)
        assert result >= 0

    def test_recovery_factor_zero_dd(self):
        """max_dd=0 → Recovery Factor = 0。"""
        returns = pd.Series([0.01, 0.02, 0.03])
        result = recovery_factor(returns, max_dd=0.0)
        assert result == 0.0


# ── Test: stability ─────────────────────────────────────────────────────────

class TestStability:
    def test_stability_formula(self):
        """Stability = R² of equity vs time。"""
        # 线性上涨 → R² ≈ 1
        equity = pd.Series([100 + i for i in range(100)])
        result = stability(equity)
        assert 0.9 < result <= 1.0

    def test_stability_random(self):
        """随机 equity → R² 较低。"""
        rng = np.random.default_rng(123)
        equity = pd.Series(rng.normal(100, 10, 50))
        result = stability(equity)
        assert 0.0 <= result <= 1.0

    def test_stability_constant(self):
        """常数 equity → R² = 0（division by zero → 0）。"""
        equity = pd.Series([100.0] * 50)
        result = stability(equity)
        assert result == 0.0


# ── Test: tail_ratio ─────────────────────────────────────────────────────────

class TestTailRatio:
    def test_tail_ratio_formula(self):
        """Tail ratio = right_tail / left_tail。"""
        returns = pd.Series([-0.10, -0.05, 0.01, 0.02, 0.03])
        result = tail_ratio(returns)
        assert isinstance(result, float)
        assert result > 0

    def test_tail_ratio_no_right_tail(self):
        """全负收益 → 右尾为空 → math.nan。"""
        # 20 个全负样本：quantile(0.95, higher) = -0.02，无值 >= -0.02（都被截断覆盖）
        returns = pd.Series([-0.10, -0.10, -0.05] * 5 + [-0.02])
        result = tail_ratio(returns)
        assert result == 0.0  # 右尾空 → 0

    def test_tail_ratio_no_left_tail(self):
        """全正收益 → tail_ratio 应为正数（有定义）。"""
        returns = pd.Series([0.10, 0.10, 0.05] * 5 + [0.02])
        result = tail_ratio(returns)
        assert isinstance(result, float)
        assert result > 0


# ── Test: omega_ratio ────────────────────────────────────────────────────────

class TestOmegaRatio:
    def test_omega_ratio_formula(self):
        """Omega = sum(gains) / sum(losses)。"""
        returns = pd.Series([0.05, -0.03, 0.02, -0.01, 0.04])
        result = omega_ratio(returns, threshold=0.0)
        assert isinstance(result, float)
        assert result > 0

    def test_omega_ratio_zero_losses(self):
        """无亏损 → Omega = inf。"""
        returns = pd.Series([0.01, 0.02, 0.03, 0.04])
        result = omega_ratio(returns, threshold=0.0)
        assert result == float("inf")

    def test_omega_ratio_threshold(self):
        """Omega 支持 threshold 参数。"""
        returns = pd.Series([0.01, -0.005, 0.02, -0.01])
        result = omega_ratio(returns, threshold=0.01)
        assert isinstance(result, float)
