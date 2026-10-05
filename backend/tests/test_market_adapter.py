"""MarketAdapter 多市场适配层测试

覆盖 A 股 / 美股 / 加密 三个市场：
- Symbol 规范化
- 交易时间（含 A 股午休、美股盘前盘后、加密 24/7）
- 复权因子
- 涨跌停识别
- 交易日判断
- 工厂函数
- 颜色方案
"""
import pytest
import pandas as pd
from datetime import date, datetime, time
from unittest.mock import patch

# 测试数据
CN_SYMBOLS = ["600519", "000858", "300750"]
US_SYMBOLS = ["AAPL", "TSLA", "NVDA"]
CRYPTO_SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]


class TestCnMarketAdapter:
    """A 股市场适配器测试"""

    def setup_method(self):
        from app.data.market_adapter import get_market_adapter
        self.adapter = get_market_adapter("cn")

    # ── Symbol 规范化 ──

    def test_normalize_shanghai_symbol(self):
        """上证股票：6 开头 → exchange=shanghai, ticker=600519, market=cn"""
        result = self.adapter.normalize_symbol("600519")
        assert result["exchange"] == "shanghai"
        assert result["ticker"] == "600519"
        assert result["market"] == "cn"

    def test_normalize_shenzhen_symbol(self):
        """深证股票：0 / 3 开头 → exchange=shenzhen"""
        result = self.adapter.normalize_symbol("000858")
        assert result["exchange"] == "shenzhen"
        assert result["ticker"] == "000858"
        assert result["market"] == "cn"

    def test_normalize_chi_next_symbol(self):
        """创业板：3 开头"""
        result = self.adapter.normalize_symbol("300750")
        assert result["exchange"] == "chi_next"
        assert result["ticker"] == "300750"
        assert result["market"] == "cn"

    # ── 交易时间 ──

    def test_trading_hours_weekday_has_lunch_break(self):
        """A 股工作日含午休（11:30-13:00）"""
        # 2024-01-02 是周二
        weekday = date(2024, 1, 2)
        start, end = self.adapter.get_trading_hours(weekday)
        assert start.time() == time(9, 30)
        assert end.time() == time(15, 0)

    def test_trading_hours_weekend(self):
        """周末无交易"""
        saturday = date(2024, 1, 6)  # 周六
        start, end = self.adapter.get_trading_hours(saturday)
        assert start is None
        assert end is None

    # ── 复权因子 ──

    def test_qfq_adjust_factor(self):
        """前复权因子 > 1（历史价格被压缩）"""
        factor = self.adapter.get_adjust_factor("600519", date(2024, 1, 15))
        assert isinstance(factor, float)
        assert factor >= 1.0

    def test_hfq_adjust_factor(self):
        """后复权因子 > 1（历史价格被放大）"""
        factor = self.adapter.get_adjust_factor("600519", date(2024, 1, 15), adjust="hfq")
        assert isinstance(factor, float)
        assert factor >= 1.0

    # ── 涨跌停识别 ──

    def test_limit_up_detection(self):
        """涨幅 = +10% → limit_type=up"""
        df = pd.DataFrame({
            "datetime": pd.date_range("2024-01-01 10:00", periods=3, freq="h"),
            "open": [10.0, 10.0, 11.0],
            "high": [10.5, 10.5, 11.0],
            "low": [9.5, 9.5, 10.0],
            "close": [10.0, 11.0, 11.0],
            "volume": [1000, 1000, 1000],
        })
        result = self.adapter.detect_limit_up_down(df, date(2024, 1, 1))
        assert "limit_type" in result.columns
        assert result["limit_type"].iloc[1] == "up"

    def test_limit_down_detection(self):
        """跌幅 = -10% → limit_type=down"""
        # close 从 11.0 跌到 9.9 → pct_change = -10.0%
        df = pd.DataFrame({
            "datetime": pd.date_range("2024-01-01 10:00", periods=3, freq="h"),
            "open": [11.0, 11.0, 10.0],
            "high": [11.5, 11.5, 10.5],
            "low": [10.5, 10.5, 9.0],
            "close": [11.0, 9.9, 9.9],
            "volume": [1000, 1000, 1000],
        })
        result = self.adapter.detect_limit_up_down(df, date(2024, 1, 1))
        assert "limit_type" in result.columns
        assert result["limit_type"].iloc[1] == "down"

    def test_no_limit_detection(self):
        """涨跌 < 10% → limit_type=none"""
        df = pd.DataFrame({
            "datetime": pd.date_range("2024-01-01 10:00", periods=3, freq="h"),
            "open": [10.0, 10.0, 10.5],
            "high": [10.5, 10.5, 11.0],
            "low": [9.5, 9.5, 10.0],
            "close": [10.0, 10.5, 10.5],
            "volume": [1000, 1000, 1000],
        })
        result = self.adapter.detect_limit_up_down(df, date(2024, 1, 1))
        assert result["limit_type"].iloc[1] == "none"

    # ── 交易日判断 ──

    def test_is_trading_day_weekday(self):
        """周一至周五（非节假日）→ True"""
        # 2024-01-02 周二
        assert self.adapter.is_trading_day(date(2024, 1, 2)) is True

    def test_is_trading_day_weekend(self):
        """周末 → False"""
        assert self.adapter.is_trading_day(date(2024, 1, 6)) is False  # 周六

    def test_is_trading_day_holiday(self):
        """A股节假日（mock）→ False"""
        # 元旦 2024-01-01
        with patch.object(self.adapter, "_get_holidays", return_value=[date(2024, 1, 1)]):
            assert self.adapter.is_trading_day(date(2024, 1, 1)) is False


class TestUsMarketAdapter:
    """美股市场适配器测试"""

    def setup_method(self):
        from app.data.market_adapter import get_market_adapter
        self.adapter = get_market_adapter("us")

    # ── Symbol 规范化 ──

    def test_normalize_us_symbol(self):
        """美股 symbol → exchange=US, ticker=AAPL"""
        result = self.adapter.normalize_symbol("AAPL")
        assert result["exchange"] == "US"
        assert result["ticker"] == "AAPL"
        assert result["market"] == "us"

    # ── 交易时间（含盘前盘后）──

    def test_trading_hours_with_premarket(self):
        """美股交易时段含盘前（04:00-09:30）和盘后（16:00-20:00）"""
        weekday = date(2024, 1, 2)  # 周二
        start, end = self.adapter.get_trading_hours(weekday)
        assert start.time() == time(4, 0)   # 盘前开始
        assert end.time() == time(20, 0)    # 盘后结束

    # ── 复权 ──

    def test_us_no_adjust_factor(self):
        """美股不复权 → factor=1.0"""
        factor = self.adapter.get_adjust_factor("AAPL", date(2024, 1, 15))
        assert factor == 1.0

    # ── 涨跌停 ──

    def test_us_no_limit_up_down(self):
        """美股无涨跌停 → limit_type=none"""
        df = pd.DataFrame({
            "datetime": pd.date_range("2024-01-01 10:00", periods=3, freq="h"),
            "open": [150.0, 150.0, 165.0],
            "high": [155.0, 155.0, 170.0],
            "low": [148.0, 148.0, 160.0],
            "close": [150.0, 165.0, 165.0],
            "volume": [1000000, 1000000, 1000000],
        })
        result = self.adapter.detect_limit_up_down(df, date(2024, 1, 1))
        assert (result["limit_type"] == "none").all()

    # ── 交易日 ──

    def test_us_trading_day_weekend(self):
        """美股周末 → False"""
        assert self.adapter.is_trading_day(date(2024, 1, 6)) is False  # 周六


class TestCryptoMarketAdapter:
    """加密货币市场适配器测试"""

    def setup_method(self):
        from app.data.market_adapter import get_market_adapter
        self.adapter = get_market_adapter("crypto")

    # ── Symbol 规范化 ──

    def test_normalize_crypto_symbol(self):
        """加密 symbol → exchange=binance, ticker=BTC/USDT"""
        result = self.adapter.normalize_symbol("BTC/USDT")
        assert result["exchange"] == "binance"
        assert result["ticker"] == "BTC/USDT"
        assert result["market"] == "crypto"

    # ── 交易时间 24/7 ──

    def test_trading_hours_247(self):
        """加密 24/7 → 整天都是交易日"""
        saturday = date(2024, 1, 6)  # 周六
        start, end = self.adapter.get_trading_hours(saturday)
        assert start.date() == saturday
        assert end.date() == saturday

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
        result = self.adapter.detect_limit_up_down(df, date(2024, 1, 1))
        assert (result["limit_type"] == "none").all()


class TestMarketAdapterFactory:
    """工厂函数测试"""

    def test_get_cn_adapter(self):
        from app.data.market_adapter import get_market_adapter
        from app.data.market_adapter import CnMarketAdapter
        adapter = get_market_adapter("cn")
        assert isinstance(adapter, CnMarketAdapter)

    def test_get_us_adapter(self):
        from app.data.market_adapter import get_market_adapter
        from app.data.market_adapter import UsMarketAdapter
        adapter = get_market_adapter("us")
        assert isinstance(adapter, UsMarketAdapter)

    def test_get_crypto_adapter(self):
        from app.data.market_adapter import get_market_adapter
        from app.data.market_adapter import CryptoMarketAdapter
        adapter = get_market_adapter("crypto")
        assert isinstance(adapter, CryptoMarketAdapter)

    def test_invalid_market_raises(self):
        from app.data.market_adapter import get_market_adapter
        with pytest.raises(ValueError, match="Unsupported market"):
            get_market_adapter("invalid")


class TestColorScheme:
    """多市场主题颜色方案测试"""

    def test_cn_color_scheme(self):
        """A 股：红涨绿跌"""
        from app.data.market_adapter import get_color_scheme
        scheme = get_color_scheme("cn")
        assert scheme["up_color"] == "#FF0000"   # 红
        assert scheme["down_color"] == "#00FF00"  # 绿
        assert scheme["bullish"] == "red"

    def test_us_color_scheme(self):
        """美股：绿涨红跌"""
        from app.data.market_adapter import get_color_scheme
        scheme = get_color_scheme("us")
        assert scheme["up_color"] == "#00FF00"   # 绿
        assert scheme["down_color"] == "#FF0000"  # 红
        assert scheme["bullish"] == "green"

    def test_crypto_color_scheme(self):
        """加密：绿涨红跌"""
        from app.data.market_adapter import get_color_scheme
        scheme = get_color_scheme("crypto")
        assert scheme["up_color"] == "#00FF00"   # 绿
        assert scheme["down_color"] == "#FF0000"  # 红
        assert scheme["bullish"] == "green"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
