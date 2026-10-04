"""SQLAlchemy ORM 模型 — K线 / 指标 / 信号 / 订单 4 张表

设计原则（来自 kline-system SPEC.md M1）：
1. K线：高频写入，分区友好（按 symbol + period + date 分区）
2. 指标：1:N 关联 K线，单独存便于回放
3. 信号：M:N 关联 K线 + 指标，记录置信度 + outcome
4. 订单：跟单业务，复用 ai-trader follow 设计但简化

来源参考：
- ai-trader: app/db/models.py (MIT/Apache-2.0) 谨慎复用概念
- ai-trader UserFollow 表设计有借鉴价值，但 kline-system 简化

⚠️ 修改后必须更新 SPEC.md 数据架构部分
"""

from datetime import UTC, datetime, timezone
from typing import Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """ORM 基类"""
    pass


# ═══════════════════════════════════════════════════════════════
# 1. K线表（核心数据，最高频写入）
# ═══════════════════════════════════════════════════════════════

class Kline(Base):
    """K线数据（OHLCV + 多市场标记）

    数据来源：
    - cn: akshare（A 股，前复权默认）
    - us: yfinance
    - crypto: ccxt (binance)
    """
    __tablename__ = "klines"

    # 主键：复合唯一索引（symbol + period + datetime 唯一）
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # 市场 + 标的
    market: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # cn/us/crypto
    symbol: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    period: Mapped[str] = mapped_column(String(10), nullable=False)  # 1m/5m/1d/...

    # 时间（精确到秒）
    datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # OHLCV
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float] = mapped_column(Float, nullable=False)
    amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 成交额（A 股特有）

    # 多市场特殊字段
    is_limit_up: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)   # 涨停
    is_limit_down: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)  # 跌停
    is_suspended: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)   # 停牌
    is_st: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)         # ST 股
    pct_change: Mapped[Optional[float]] = mapped_column(Float, nullable=True)            # 涨跌幅 %

    # 复权
    adjust_type: Mapped[str] = mapped_column(String(10), nullable=False, default="qfq")  # qfq/hfq/none

    # 元数据
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        # 唯一约束：同一标的同一周期同一时间只一根 K 线
        UniqueConstraint("market", "symbol", "period", "datetime", name="uq_kline"),
        # 查询优化：标的 + 周期 + 时间倒序
        Index("idx_kline_lookup", "market", "symbol", "period", "datetime"),
        Index("idx_kline_datetime", "datetime"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "market": self.market,
            "symbol": self.symbol,
            "period": self.period,
            "datetime": self.datetime.isoformat() if self.datetime else None,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "amount": self.amount,
            "is_limit_up": self.is_limit_up,
            "is_limit_down": self.is_limit_down,
            "is_suspended": self.is_suspended,
            "is_st": self.is_st,
            "pct_change": self.pct_change,
            "adjust_type": self.adjust_type,
        }


# ═══════════════════════════════════════════════════════════════
# 2. 指标表（每个 K 线对应一组指标值）
# ═══════════════════════════════════════════════════════════════

class Indicator(Base):
    """技术指标值（每个 K 线每周期每指标一条）

    简化策略：MA/MACD/RSI/布林带/KDJ/OBV/ADX/ATR/Hurst 全部存在这里
    通过 indicator_name 字段区分，indicator_value 是浮点值

    设计考量：
    - 单表宽列 vs 多表窄列
    - 选单表宽列：减少 JOIN，适合 OLAP 场景
    - 备选：JSON 字段存所有指标（更灵活但查询稍慢）
    """
    __tablename__ = "indicators"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # 关联 K 线
    kline_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("klines.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # 指标元数据
    indicator_name: Mapped[str] = mapped_column(String(40), nullable=False, index=True)  # MA20/MACD/RSI14/...
    indicator_value: Mapped[float] = mapped_column(Float, nullable=False)

    # 指标参数（JSON: {"period": 20}）
    params: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("idx_indicator_lookup", "kline_id", "indicator_name"),
        UniqueConstraint("kline_id", "indicator_name", name="uq_indicator"),
    )


# ═══════════════════════════════════════════════════════════════
# 3. 信号表（买卖点 + 置信度 + outcome）
# ═══════════════════════════════════════════════════════════════

class Signal(Base):
    """交易信号（买入/卖出/观望）

    关键字段：
    - direction: long/short/neutral
    - confidence: 0-1（ai-trader 教训 #2：必须 > 55% 命中率，否则不上线）
    - regime: bull/bear/choppy/crisis
    - outcome: 实际 N 根 K 线后盈亏（实盘前为空）

    ⚠️ ai-trader 教训 #2：信号命中率必须显著超过 50%
    """
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # 关联
    kline_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("klines.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # 信号内容
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # long/short/neutral
    confidence: Mapped[float] = mapped_column(Float, nullable=False)  # 0-1
    regime: Mapped[str] = mapped_column(String(20), nullable=False)   # bull/bear/choppy/crisis
    regime_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # 价位（做多：entry < stop_loss < take_profit；做空反之）
    entry_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    stop_loss: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    take_profit: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 入场/离场时间窗口（分钟）
    entry_window_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    exit_window_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 信号源 + 推理链
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="rule_based")
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Outcome tracking（实盘后回填，ai-trader 教训 #2 配套）
    outcome_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    outcome_pnl_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    outcome_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)  # 命中?

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("idx_signal_lookup", "kline_id", "direction", "confidence"),
        Index("idx_signal_confidence", "confidence"),
        Index("idx_signal_outcome", "outcome_correct"),
    )


# ═══════════════════════════════════════════════════════════════
# 4. 订单表（跟单业务）
# ═══════════════════════════════════════════════════════════════

class Order(Base):
    """跟单订单

    简化版（参考 ai-trader UserFollow 但简化）：
    - ai-trader 有 status: open/closed/cancelled
    - kline-system 简化：只跟 open/closed

    ⚠️ ai-trader UserFollow 有 100+ 字段，kline-system 简化到核心 15 个
    """
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # 关联（可选：手动下单可不关联信号）
    signal_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("signals.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # 订单内容
    market: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # long/short

    # 价位
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    stop_loss: Mapped[float] = mapped_column(Float, nullable=False)
    take_profit: Mapped[float] = mapped_column(Float, nullable=False)

    # 仓位（USDT）
    stake_amount: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    leverage: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # 状态机：open → closed（出场）
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open", index=True)

    # 出场信息
    exit_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    exit_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    pnl_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pnl_usdt: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("idx_order_status_time", "status", "created_at"),
        Index("idx_order_symbol", "symbol", "status"),
    )


# ═══════════════════════════════════════════════════════════════
# 5. 校准表（ai-trader 复用 PAVA Isotonic）
# ═══════════════════════════════════════════════════════════════

class CalibrationModel(Base):
    """置信度校准模型（PAVA Isotonic regression）

    ai-trader 教训 #2 配套：必须校准置信度
    每 24h 重训一次（参考 ai-trader calibration_trainer.py）
    """
    __tablename__ = "calibration_models"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # 校准范围
    market: Mapped[str] = mapped_column(String(10), nullable=False)
    period: Mapped[str] = mapped_column(String(10), nullable=False)

    # 校准模型（JSON: PAVA 断点表 [{confidence: 0.3, observed: 0.25}, ...]）
    breakpoints: Mapped[list] = mapped_column(JSON, nullable=False)

    # 评估指标
    brier_score: Mapped[float] = mapped_column(Float, nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)

    # 是否生效
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("idx_calibration_lookup", "market", "period", "is_active"),
    )