"""RiskManager 单元测试 — F2（M3）

10 个测试（5 门控 × 2）：
G1: test_daily_loss_within_limit / test_daily_loss_at_limit_blocks
G2: test_position_count_within_limit / test_position_count_at_limit_blocks
G3: test_direction_exposure_within_limit / test_direction_exposure_at_limit_blocks
G4: test_confidence_above_threshold / test_confidence_below_threshold_blocks
G5: test_sources_valid / test_sources_invalid_blocks
"""
from __future__ import annotations

import pytest

from app.analytics.signal_direction import Signal
from app.follow.risk_manager import (
    AccountState,
    Position,
    RiskManager,
)


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def rm() -> RiskManager:
    """默认参数 RiskManager。"""
    return RiskManager(
        max_daily_loss_pct=0.02,
        max_concurrent_positions=3,
        max_correlation_exposure=0.10,
    )


@pytest.fixture
def base_state() -> AccountState:
    """基础账户状态。"""
    return AccountState(equity=10000.0, daily_pnl=0.0, daily_pnl_pct=0.0, positions=[])


@pytest.fixture
def base_signal() -> Signal:
    """基础 Signal。"""
    return Signal(
        name="test_signal",
        direction="long",
        confidence=0.7,
        entry=100.0,
        stop_loss=98.0,
        take_profit=108.0,
        sources=["confluence_bullish", "hammer_bullish"],
    )


# ── Gate 1: 单日亏损 ─────────────────────────────────────────────────────────

class TestDailyLossGate:
    def test_daily_loss_within_limit(self, rm: RiskManager, base_state: AccountState, base_signal: Signal) -> None:
        """当日亏损 1% < 2% → 通过"""
        state = AccountState(equity=10000.0, daily_pnl_pct=-0.01, positions=[])
        ok, reason = rm.can_open(base_signal, state)
        assert ok is True
        assert reason == ""

    def test_daily_loss_at_limit_blocks(self, rm: RiskManager, base_state: AccountState, base_signal: Signal) -> None:
        """当日亏损 = 2% → 拒绝"""
        state = AccountState(equity=10000.0, daily_pnl_pct=-0.02, positions=[])
        ok, reason = rm.can_open(base_signal, state)
        assert ok is False
        assert "daily_loss_limit" in reason


# ── Gate 2: 持仓数量 ────────────────────────────────────────────────────────

class TestPositionCountGate:
    def test_position_count_within_limit(self, rm: RiskManager, base_state: AccountState, base_signal: Signal) -> None:
        """持仓 2 < 3 → 通过"""
        positions = [
            Position(symbol="BTC/USDT", direction="long", notional=100.0, entry_price=100.0, stop_loss=98.0),
            Position(symbol="ETH/USDT", direction="long", notional=100.0, entry_price=100.0, stop_loss=98.0),
        ]
        state = AccountState(equity=10000.0, daily_pnl_pct=0.0, positions=positions)
        ok, reason = rm.can_open(base_signal, state)
        assert ok is True

    def test_position_count_at_limit_blocks(self, rm: RiskManager, base_state: AccountState, base_signal: Signal) -> None:
        """持仓 3 = 3 → 拒绝"""
        positions = [
            Position(symbol=f"BTC{i}/USDT", direction="long", notional=100.0, entry_price=100.0, stop_loss=98.0)
            for i in range(3)
        ]
        state = AccountState(equity=10000.0, daily_pnl_pct=0.0, positions=positions)
        ok, reason = rm.can_open(base_signal, state)
        assert ok is False
        assert "max_positions" in reason


# ── Gate 3: 同方向暴露 ──────────────────────────────────────────────────────

class TestDirectionExposureGate:
    def test_direction_exposure_within_limit(self, rm: RiskManager, base_signal: Signal) -> None:
        """同方向暴露 5% < 10% → 通过"""
        positions = [
            Position(symbol="BTC/USDT", direction="long", notional=500.0, entry_price=100.0, stop_loss=98.0),
        ]
        # equity=10000, same_dir=500 → 5%
        state = AccountState(equity=10000.0, daily_pnl_pct=0.0, positions=positions)
        ok, reason = rm.can_open(base_signal, state)
        assert ok is True

    def test_direction_exposure_at_limit_blocks(self, rm: RiskManager) -> None:
        """同方向暴露 10% = 10% → 拒绝"""
        sig = Signal(
            name="long_at_limit",
            direction="long",
            confidence=0.7,
            entry=100.0,
            stop_loss=98.0,
            take_profit=108.0,
            sources=["confluence_bullish", "hammer_bullish"],
        )
        positions = [
            Position(symbol="BTC/USDT", direction="long", notional=1000.0, entry_price=100.0, stop_loss=98.0),
        ]
        # equity=10000, same_dir=1000 → 10%
        state = AccountState(equity=10000.0, daily_pnl_pct=0.0, positions=positions)
        ok, reason = rm.can_open(sig, state)
        assert ok is False
        assert "direction_exposure" in reason

    def test_opposite_direction_not_counted(self, rm: RiskManager) -> None:
        """反方向持仓不算同方向暴露"""
        sig = Signal(
            name="long_with_short_positions",
            direction="long",
            confidence=0.7,
            entry=100.0,
            stop_loss=98.0,
            take_profit=108.0,
            sources=["confluence_bullish"],
        )
        # 反方向已有 10% 暴露，做多不应被拒
        positions = [
            Position(symbol="BTC/USDT", direction="short", notional=1000.0, entry_price=100.0, stop_loss=102.0),
        ]
        state = AccountState(equity=10000.0, daily_pnl_pct=0.0, positions=positions)
        ok, reason = rm.can_open(sig, state)
        assert ok is True


# ── Gate 4: confidence ─────────────────────────────────────────────────────

class TestConfidenceGate:
    def test_confidence_above_threshold(self, rm: RiskManager, base_state: AccountState) -> None:
        """confidence=0.5 >= 0.5 → 通过"""
        sig = Signal(
            name="edge_conf",
            direction="long",
            confidence=0.5,
            entry=100.0,
            stop_loss=98.0,
            take_profit=108.0,
            sources=["confluence_bullish"],
        )
        ok, reason = rm.can_open(sig, base_state)
        assert ok is True

    def test_confidence_below_threshold_blocks(self, rm: RiskManager, base_state: AccountState) -> None:
        """confidence=0.49 < 0.5 → 拒绝"""
        sig = Signal(
            name="low_conf",
            direction="long",
            confidence=0.49,
            entry=100.0,
            stop_loss=98.0,
            take_profit=108.0,
            sources=["confluence_bullish"],
        )
        ok, reason = rm.can_open(sig, base_state)
        assert ok is False
        assert "low_confidence" in reason


# ── Gate 5: sources ────────────────────────────────────────────────────────

class TestSourcesGate:
    def test_sources_valid_confluence(self, rm: RiskManager, base_state: AccountState) -> None:
        """confluence source → 通过"""
        sig = Signal(
            name="conf",
            direction="long",
            confidence=0.7,
            entry=100.0,
            stop_loss=98.0,
            take_profit=108.0,
            sources=["confluence_bullish"],
        )
        ok, reason = rm.can_open(sig, base_state)
        assert ok is True

    def test_sources_valid_pattern(self, rm: RiskManager, base_state: AccountState) -> None:
        """形态 source → 通过"""
        sig = Signal(
            name="pattern",
            direction="long",
            confidence=0.7,
            entry=100.0,
            stop_loss=98.0,
            take_profit=108.0,
            sources=["hammer_bullish", "engulfing_bullish"],
        )
        ok, reason = rm.can_open(sig, base_state)
        assert ok is True

    def test_sources_valid_mixed(self, rm: RiskManager, base_state: AccountState) -> None:
        """confluence + 形态 → 通过"""
        sig = Signal(
            name="mixed",
            direction="long",
            confidence=0.7,
            entry=100.0,
            stop_loss=98.0,
            take_profit=108.0,
            sources=["confluence_bullish", "hammer_bullish"],
        )
        ok, reason = rm.can_open(sig, base_state)
        assert ok is True

    def test_sources_empty_blocks(self, rm: RiskManager, base_state: AccountState) -> None:
        """空 sources → 拒绝"""
        sig = Signal(
            name="no_source",
            direction="long",
            confidence=0.7,
            entry=100.0,
            stop_loss=98.0,
            take_profit=108.0,
            sources=[],
        )
        ok, reason = rm.can_open(sig, base_state)
        assert ok is False
        assert "no_confluence_or_pattern" in reason

    def test_sources_invalid_blocks(self, rm: RiskManager, base_state: AccountState) -> None:
        """非 confluence/pattern source → 拒绝"""
        sig = Signal(
            name="invalid_source",
            direction="long",
            confidence=0.7,
            entry=100.0,
            stop_loss=98.0,
            take_profit=108.0,
            sources=["random_keyword", "unknown_signal"],
        )
        ok, reason = rm.can_open(sig, base_state)
        assert ok is False
        assert "no_confluence_or_pattern" in reason


# ── 综合测试 ────────────────────────────────────────────────────────────────

class TestIntegration:
    def test_all_gates_pass(self, rm: RiskManager, base_signal: Signal) -> None:
        """全部门控通过 → 返回 True"""
        state = AccountState(equity=10000.0, daily_pnl_pct=0.0, positions=[])
        ok, reason = rm.can_open(base_signal, state)
        assert ok is True
        assert reason == ""

    def test_first_failing_gate_stops(self, rm: RiskManager, base_signal: Signal) -> None:
        """多门控失败 → 返回第一个失败的原因"""
        # 同时亏损超限 + 持仓超限
        positions = [Position(symbol=f"BTC{i}/USDT", direction="long", notional=100.0, entry_price=100.0, stop_loss=98.0) for i in range(3)]
        state = AccountState(equity=10000.0, daily_pnl_pct=-0.03, positions=positions)
        ok, reason = rm.can_open(base_signal, state)
        assert ok is False
        # Gate 1 先检查，所以返回 daily_loss_limit
        assert "daily_loss_limit" in reason
