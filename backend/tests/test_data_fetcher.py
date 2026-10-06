"""数据获取层单元测试

SPEC v2 §1：只做 BTC/ETH（crypto）。cn/us 测试已删除。
"""
import pytest
import pandas as pd
from datetime import datetime, timedelta
from app.services.data_fetcher import DataFetcher


class TestDataFetcher:
    """数据获取器测试（crypto-only）"""

    def setup_method(self):
        self.fetcher = DataFetcher()

    def test_unsupported_market(self):
        """不支持的市场测试（SPEC v2：cn/us 已删，传 'xxx' 抛 ValueError）"""
        with pytest.raises(ValueError):
            self.fetcher.get_kline('BTC', market='xxx')


class TestIndicators:
    """指标计算测试（基础）"""

    def test_ma_calculation(self):
        """MA 计算测试"""
        from app.services.indicators import IndicatorEngine
        df = pd.DataFrame({
            'close': [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
        })
        result = IndicatorEngine._calc_ma(df, periods=(5,))
        assert 'MA5' in result.columns
        # MA5 应该是 (16+17+18+19+20)/5 = 18
        assert abs(result['MA5'].iloc[-1] - 18.0) < 0.01


class TestCryptoProviderContract:
    """SPEC v2 §1：crypto provider 必须保留 adjust 参数签名。"""

    def test_crypto_provider_accepts_adjust(self):
        """加密 provider 接受 adjust 参数（即使忽略）"""
        import inspect
        sig = inspect.signature(DataFetcher._get_crypto_kline)
        params = list(sig.parameters.keys())
        assert params == ['self', 'symbol', 'period', 'start', 'end', 'adjust']


class TestCryptoExchangeEnv:
    """M5 部署修复：crypto provider 用 KBKKK_CRYPTO_EXCHANGE 选 ccxt 交易所"""

    def test_crypto_does_not_hardcode_binance(self):
        """crypto kline 不再硬编码 ccxt.binance()（Binance 在国内被地区限制）"""
        import inspect
        source = inspect.getsource(DataFetcher._get_crypto_kline)
        assert "ccxt.binance()" not in source

    def test_crypto_reads_env_var(self):
        """crypto kline 读 KBKKK_CRYPTO_EXCHANGE 环境变量"""
        import inspect
        source = inspect.getsource(DataFetcher._get_crypto_kline)
        assert 'os.getenv("KBKKK_CRYPTO_EXCHANGE"' in source

    def test_crypto_normalizes_symbol_with_quote(self):
        """BTC 自动补 /USDT（Binance 用 BTCUSDT，OKX 用 BTC/USDT，kbkkk API 默认 BTC）"""
        import inspect
        source = inspect.getsource(DataFetcher._get_crypto_kline)
        # 验证 ccxt_symbol 逻辑存在
        assert "ccxt_symbol" in source
        assert '"/USDT"' in source or 'f"{symbol}/USDT"' in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
