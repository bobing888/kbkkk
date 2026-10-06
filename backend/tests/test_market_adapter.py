"""MarketAdapter 多市场适配层测试（crypto-only）

SPEC v2 §1：kbkkk 仅覆盖 BTC/ETH 加密市场。
- A 股（涨跌停 / 复权 / 调休）已删除
- 美股（盘前盘后 / split）已删除
- 仅保留加密 24/7 + symbol 规范化 + 环境变量回滚测试
"""
import pytest
import pandas as pd
from datetime import date, time


CRYPTO_SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]


class TestCryptoMarketAdapter:
    """加密货币市场适配器测试"""

    def setup_method(self):
        from app.data.market_adapter import get_market_adapter
        self.adapter = get_market_adapter("crypto")

    # ── Symbol 规范化 ──

    def test_normalize_crypto_symbol(self):
        """加密 symbol → 默认 exchange=okx, ticker=BTC/USDT"""
        result = self.adapter.normalize_symbol("BTC/USDT")
        assert result["exchange"] == "okx"
        assert result["ticker"] == "BTC/USDT"
        assert result["market"] == "crypto"

    def test_normalize_crypto_symbol_explicit_okx(self):
        """加密 symbol 显式带 OKX 前缀 → exchange=okx"""
        result = self.adapter.normalize_symbol("OKX:BTC/USDT")
        assert result["exchange"] == "okx"

    def test_normalize_crypto_symbol_explicit_binance(self):
        """加密 symbol 显式带 BINANCE 前缀 → exchange=binance"""
        result = self.adapter.normalize_symbol("BINANCE:BTC/USDT")
        assert result["exchange"] == "binance"

    def test_normalize_crypto_no_slash_default_okx(self):
        """加密无斜杠 symbol（BTC）→ 默认交易所 okx"""
        result = self.adapter.normalize_symbol("BTC")
        assert result["exchange"] == "okx"
        assert result["ticker"] == "BTC/USDT"

    def test_normalize_crypto_env_override_binance(self, monkeypatch):
        """KBKKK_CRYPTO_EXCHANGE=binance → 默认改回 binance（回滚用）"""
        monkeypatch.setenv("KBKKK_CRYPTO_EXCHANGE", "binance")
        from app.data.market_adapter import CryptoMarketAdapter
        adapter = CryptoMarketAdapter()
        result = adapter.normalize_symbol("BTC")
        assert result["exchange"] == "binance"

    # ── 交易时间 24/7 ──

    def test_trading_hours_247(self):
        """加密 24/7 → 整天都是交易日（list[tuple]，保持与历史契约）"""
        saturday = date(2024, 1, 6)  # 周六
        sessions = self.adapter.get_trading_hours(saturday)
        assert isinstance(sessions, list)
        assert len(sessions) == 1
        assert sessions[0][0].date() == saturday
        assert sessions[0][1].date() == saturday

    # ── 复权 ──

    def test_crypto_no_adjust_factor(self):
        """加密不复权 → factor=1.0"""
        factor = self.adapter.get_adjust_factor("BTC/USDT", date(2024, 1, 15))
        assert factor == 1.0

    # ── 涨跌停 ──

    def test_crypto_no_limit(self):
        """加密无涨跌停 → limit_type=none"""
        df = pd.DataFrame({
            "datetime": pd.date_range("2024-01-01 10:00", periods=3, freq="h"),
            "open": [50000.0, 50000.0, 60000.0],
            "high": [52000.0, 52000.0, 65000.0],
            "low": [49000.0, 49000.0, 58000.0],
            "close": [50000.0, 60000.0, 60000.0],
            "volume": [1000, 1000, 1000],
        })
        result = self.adapter.detect_limit_up_down(df, date(2024, 1, 1), symbol="BTC/USDT")
        assert (result["limit_type"] == "none").all()

    # ── 交易日 ──

    def test_crypto_is_trading_day_anywhere(self):
        """加密 24/7 → 任意一天都是交易日（含周末）"""
        assert self.adapter.is_trading_day(date(2024, 1, 6)) is True  # 周六
        assert self.adapter.is_trading_day(date(2024, 1, 1)) is True  # 元旦


class TestMarketAdapterFactory:
    """工厂函数测试（v2：仅 crypto）"""

    def test_get_crypto_adapter(self):
        from app.data.market_adapter import get_market_adapter
        from app.data.market_adapter import CryptoMarketAdapter
        adapter = get_market_adapter("crypto")
        assert isinstance(adapter, CryptoMarketAdapter)

    def test_invalid_market_raises(self):
        from app.data.market_adapter import get_market_adapter
        # SPEC v2 §1：cn/us 已删，传非 crypto 抛 ValueError
        with pytest.raises(ValueError, match="only supports BTC/ETH"):
            get_market_adapter("cn")
        with pytest.raises(ValueError, match="only supports BTC/ETH"):
            get_market_adapter("us")
        with pytest.raises(ValueError, match="only supports BTC/ETH"):
            get_market_adapter("invalid")


class TestColorScheme:
    """加密配色方案（v2：仅 crypto 1 套）"""

    def test_crypto_color_scheme(self):
        """加密：绿涨红跌"""
        from app.data.market_adapter import get_color_scheme
        scheme = get_color_scheme("crypto")
        assert scheme["up_color"] == "#00FF00"   # 绿
        assert scheme["down_color"] == "#FF0000"  # 红
        assert scheme["bullish"] == "green"

    def test_non_crypto_color_raises(self):
        """cn/us 配色方案已删（SPEC v2）"""
        from app.data.market_adapter import get_color_scheme
        with pytest.raises(ValueError, match="only supports BTC/ETH"):
            get_color_scheme("cn")
        with pytest.raises(ValueError, match="only supports BTC/ETH"):
            get_color_scheme("us")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])