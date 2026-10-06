"""数据获取层单元测试"""
import pytest
import pandas as pd
from datetime import datetime, timedelta
from app.services.data_fetcher import DataFetcher


class TestDataFetcher:
    """数据获取器测试"""

    def setup_method(self):
        self.fetcher = DataFetcher()

    def test_cn_data_cleaning(self):
        """A 股数据清洗测试"""
        # 模拟 akshare 返回的数据
        raw_data = pd.DataFrame({
            '日期': pd.date_range('2024-01-01', periods=5),
            '开盘': [10.0, 10.5, 10.3, 10.8, 11.0],
            '最高': [10.5, 10.8, 10.5, 11.0, 11.2],
            '最低': [9.8, 10.2, 10.0, 10.5, 10.8],
            '收盘': [10.3, 10.6, 10.4, 10.9, 11.1],
            '成交量': [1000000, 1100000, 950000, 1200000, 1050000],
            '涨跌幅': [3.0, 2.9, -1.9, 4.8, 1.8]
        })

        df = self.fetcher._clean_cn_data(raw_data)

        # 验证列名标准化
        assert 'datetime' in df.columns
        assert 'open' in df.columns
        assert 'close' in df.columns
        assert 'volume' in df.columns
        assert 'is_limit_up' in df.columns
        assert 'is_suspended' in df.columns

        # 验证数据完整性
        assert len(df) == 5
        assert df['close'].iloc[-1] == 11.1

    def test_limit_up_detection(self):
        """涨跌停检测测试"""
        raw_data = pd.DataFrame({
            '日期': pd.date_range('2024-01-01', periods=3),
            '开盘': [10.0, 10.0, 10.0],
            '最高': [10.5, 11.5, 10.5],
            '最低': [9.8, 10.5, 8.5],
            '收盘': [10.3, 11.0, 8.7],
            '成交量': [1000000, 1000000, 1000000],
            '涨跌幅': [3.0, 10.0, -10.0]
        })

        df = self.fetcher._clean_cn_data(raw_data)

        # 验证涨跌停标记
        assert df['is_limit_up'].iloc[1] == True
        assert df['is_limit_down'].iloc[2] == True

    def test_missing_data_handling(self):
        """缺失数据处理测试"""
        raw_data = pd.DataFrame({
            '日期': pd.date_range('2024-01-01', periods=5),
            '开盘': [10.0, None, 10.3, 10.8, 11.0],
            '最高': [10.5, 10.8, None, 11.0, 11.2],
            '最低': [9.8, 10.2, 10.0, 10.5, 10.8],
            '收盘': [10.3, 10.6, 10.4, 10.9, 11.1],
            '成交量': [1000000, 1100000, 950000, 1200000, 1050000]
        })

        df = self.fetcher._clean_cn_data(raw_data)

        # 验证缺失值已填充
        assert df['open'].isna().sum() == 0
        assert df['high'].isna().sum() == 0

    def test_unsupported_market(self):
        """不支持的市场测试"""
        with pytest.raises(ValueError):
            self.fetcher.get_kline('BTC', market='xxx')

    def test_us_data_cleaning(self):
        """美股数据清洗测试"""
        # 模拟 yfinance 返回的数据
        raw_data = pd.DataFrame({
            'Date': pd.date_range('2024-01-01', periods=3),
            'Open': [150.0, 152.0, 151.0],
            'High': [152.0, 153.0, 152.5],
            'Low': [149.5, 151.5, 150.5],
            'Close': [151.5, 152.5, 152.0],
            'Volume': [50000000, 55000000, 48000000]
        })

        df = self.fetcher._clean_us_data(raw_data)

        assert 'datetime' in df.columns
        assert len(df) == 3
        assert df['close'].iloc[-1] == 152.0


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


class TestProviderArgSignatures:
    """M5 部署修复：us/crypto 接受 adjust 参数"""

    def test_us_provider_accepts_adjust(self):
        """美股 provider 接受 adjust 参数（即使忽略）"""
        import inspect
        sig = inspect.signature(DataFetcher._get_us_kline)
        params = list(sig.parameters.keys())
        assert params == ['self', 'symbol', 'period', 'start', 'end', 'adjust']

    def test_crypto_provider_accepts_adjust(self):
        """加密 provider 接受 adjust 参数（即使忽略）"""
        import inspect
        sig = inspect.signature(DataFetcher._get_crypto_kline)
        params = list(sig.parameters.keys())
        assert params == ['self', 'symbol', 'period', 'start', 'end', 'adjust']

    def test_cn_provider_signature_unchanged(self):
        """A 股 provider 签名不动（含 adjust）"""
        import inspect
        sig = inspect.signature(DataFetcher._get_cn_kline)
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
