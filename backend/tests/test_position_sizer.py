"""PositionSizer 单元测试 — F1（M3）

8 个测试覆盖：
1. 基础 long 仓位（confidence=0.8，基础 notional 超 cap → cap 优先）
2. 基础 short 仓位（confidence=0.7，基础 notional 超 cap → cap 优先）
3. confidence 加权（0.5 → 基础 notional 低于 cap → 不触发 cap）
4. confidence 加权（1.0 → 基础 notional 超 cap → cap 优先）
5. 上限保护：止损距离极小 → 强制 cap
6. risk_pct 永远不超过 max_risk_per_trade_pct
7. signal.direction == "neutral" 抛异常
8. equity <= 0 抛异常

注：cap（单仓位 ≤ 5%）在 confidence 加权之前触发——这是资金保护优先级的体现。
"""
from __future__ import annotations

import pytest

from app.analytics.signal_direction import Signal
from app.follow.position_sizer import PositionSizer, PositionSize


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def sizer() -> PositionSizer:
    """默认参数 PositionSizer。"""
    return PositionSizer(max_position_pct=0.05, max_risk_per_trade_pct=0.01)


@pytest.fixture
def long_signal() -> Signal:
    """标准 long Signal（confidence=0.8）。"""
    return Signal(
        name="test_long",
        direction="long",
        confidence=0.8,
        entry=100.0,
        stop_loss=98.0,   # 止损距离 = 2
        take_profit=108.0,
        sources=["confluence_bullish"],
    )


@pytest.fixture
def short_signal() -> Signal:
    """标准 short Signal（confidence=0.7）。"""
    return Signal(
        name="test_short",
        direction="short",
        confidence=0.7,
        entry=100.0,
        stop_loss=102.0,  # 止损距离 = 2
        take_profit=92.0,
        sources=["confluence_bearish"],
    )


# ── 测试 1 & 2：基础 long / short 仓位 ───────────────────────────────────

class TestBasicSizing:
    def test_long_basic_cap_before_confidence(
        self, sizer: PositionSizer, long_signal: Signal
    ) -> None:
        """long：基础 notional=5000 超 cap=500 → cap 触发，再 confidence 加权"""
        # 执行顺序：风险公式 → cap → confidence
        # base_quantity = (10000*0.01)/2 = 50
        # base_notional = 50*100 = 5000 > 500 → cap: quantity=5, notional=500
        # confidence_ratio=0.8 → final: quantity=5*0.8=4, notional=400
        result = sizer.size(long_signal, equity=10000.0, current_price=100.0)
        assert isinstance(result, PositionSize)
        assert result.quantity == pytest.approx(4.0, rel=1e-6)
        assert result.notional == pytest.approx(400.0, rel=1e-2)
        assert result.risk_amount == pytest.approx(8.0, rel=1e-2)
        assert result.risk_pct == pytest.approx(0.0008, rel=1e-2)
        # 上限确认
        assert result.notional <= 500.0  # ≤ 5% of 10000

    def test_short_basic_cap_before_confidence(
        self, sizer: PositionSizer, short_signal: Signal
    ) -> None:
        """short：基础 notional=5000 超 cap=500 → cap 触发，再 confidence 加权"""
        result = sizer.size(short_signal, equity=10000.0, current_price=100.0)
        assert result.quantity == pytest.approx(3.5, rel=1e-6)
        assert result.notional == pytest.approx(350.0, rel=1e-2)
        assert result.risk_amount == pytest.approx(7.0, rel=1e-2)


# ── 测试 3 & 4：confidence 加权（cap 不触发的场景）────────────────────────

class TestConfidenceWeighting:
    def test_confidence_05_no_cap(
        self, sizer: PositionSizer
    ) -> None:
        """confidence=0.5 → 基础 notional=2500 < cap=500 → 不触发 cap"""
        sig = Signal(
            name="low_conf",
            direction="long",
            confidence=0.5,
            entry=100.0,
            stop_loss=98.0,
            take_profit=108.0,
            sources=["pattern"],
        )
        # base_quantity = (10000*0.01)/2 = 50
        # base_notional = 50*100 = 5000 → cap to 5 (notional=500)
        # confidence_ratio=0.5 → final: quantity=5*0.5=2.5, notional=250
        result = sizer.size(sig, equity=10000.0, current_price=100.0)
        assert result.quantity == pytest.approx(2.5, rel=1e-6)
        assert result.notional == pytest.approx(250.0, rel=1e-2)

    def test_confidence_10_cap_kicks_in(
        self, sizer: PositionSizer
    ) -> None:
        """confidence=1.0 → 基础 notional=5000 超 cap=500 → cap 触发"""
        sig = Signal(
            name="high_conf",
            direction="long",
            confidence=1.0,
            entry=100.0,
            stop_loss=98.0,
            take_profit=108.0,
            sources=["confluence_bullish"],
        )
        # base notional = 5000 > 500 → cap: quantity=5, notional=500
        result = sizer.size(sig, equity=10000.0, current_price=100.0)
        assert result.quantity == pytest.approx(5.0, rel=1e-6)
        assert result.notional == pytest.approx(500.0, rel=1e-2)

    def test_confidence_below_min_uses_min(self, sizer: PositionSizer) -> None:
        """confidence < 0.5 时，按 0.5 处理"""
        sig = Signal(
            name="very_low_conf",
            direction="long",
            confidence=0.3,
            entry=100.0,
            stop_loss=98.0,
            take_profit=108.0,
            sources=["pattern"],
        )
        result = sizer.size(sig, equity=10000.0, current_price=100.0)
        # cap 先触发: quantity=5, notional=500
        # confidence_ratio = max(0.5, 0.3) = 0.5
        # final: quantity=5*0.5=2.5
        assert result.quantity == pytest.approx(2.5, rel=1e-6)


# ── 测试 5 & 6：上限保护 ─────────────────────────────────────────────────

class TestPositionLimits:
    def test_tight_stop_always_capped(self) -> None:
        """止损距离极小 → 基础 notional 远超 cap → 强制 cap"""
        sizer = PositionSizer(max_position_pct=0.05, max_risk_per_trade_pct=0.01)
        sig = Signal(
            name="tight_stop",
            direction="long",
            confidence=1.0,
            entry=100.0,
            stop_loss=99.99,  # 止损距离仅 0.01
            take_profit=104.0,
            sources=["confluence_bullish"],
        )
        # base: quantity = (10000*0.01)/0.01 = 10000
        # base_notional = 1,000,000 >> max_notional=500 → cap
        result = sizer.size(sig, equity=10000.0, current_price=100.0)
        assert result.notional <= 500.0
        assert result.risk_amount <= 100.0  # ≤ 1%

    def test_risk_never_exceeds_max_risk_pct(
        self, sizer: PositionSizer, long_signal: Signal
    ) -> None:
        """risk_pct 永远不超过 max_risk_per_trade_pct（1%）"""
        result = sizer.size(long_signal, equity=10000.0, current_price=100.0)
        assert result.risk_pct <= 0.01


# ── 测试 7 & 8：边界条件 ─────────────────────────────────────────────────

class TestBoundaryConditions:
    def test_neutral_signal_raises(self, sizer: PositionSizer) -> None:
        """neutral signal → ValueError"""
        sig = Signal(
            name="neutral",
            direction="neutral",
            confidence=0.5,
            entry=100.0,
            stop_loss=98.0,
            take_profit=108.0,
            sources=[],
        )
        with pytest.raises(ValueError, match="neutral"):
            sizer.size(sig, equity=10000.0, current_price=100.0)

    def test_zero_equity_raises(self, sizer: PositionSizer, long_signal: Signal) -> None:
        """equity <= 0 → ValueError"""
        with pytest.raises(ValueError, match="positive"):
            sizer.size(long_signal, equity=0.0, current_price=100.0)
        with pytest.raises(ValueError, match="positive"):
            sizer.size(long_signal, equity=-100.0, current_price=100.0)

    def test_zero_stop_distance_raises(self, sizer: PositionSizer) -> None:
        """entry == stop_loss → ValueError"""
        sig = Signal(
            name="flat",
            direction="long",
            confidence=0.8,
            entry=100.0,
            stop_loss=100.0,
            take_profit=108.0,
            sources=["confluence_bullish"],
        )
        with pytest.raises(ValueError, match="Invalid stop_loss"):
            sizer.size(sig, equity=10000.0, current_price=100.0)

    def test_constructor_invalid_params(self) -> None:
        """非法构造参数 → ValueError"""
        with pytest.raises(ValueError, match="max_position_pct"):
            PositionSizer(max_position_pct=0.0, max_risk_per_trade_pct=0.01)
        with pytest.raises(ValueError, match="max_position_pct"):
            PositionSizer(max_position_pct=1.5, max_risk_per_trade_pct=0.01)
        with pytest.raises(ValueError, match="max_risk_per_trade_pct"):
            PositionSizer(max_position_pct=0.05, max_risk_per_trade_pct=0.1)
