"""SPEC v2.0 落地契约测试。

来源：SPEC.md v2.0 §1（聚焦 BTC/ETH）、§M1.5（默认市场 crypto）。
目的：把"只做 BTC/ETH"从文档落到代码层。

注意：本文件**只**描述 SPEC v2.0 的契约，不测历史行为。
历史 cn/us 测试应在删除 cn/us 代码时同步删除。
"""
import pytest


class TestV2CryptoOnly:
    """SPEC v2 §1：只做 BTC/ETH。Provider 注册表只剩 crypto。"""

    def test_provider_registry_only_crypto(self):
        """DataFetcher._PROVIDERS 只剩 crypto 一项（cn/us 已砍）。"""
        from app.services.data_fetcher import DataFetcher
        keys = set(DataFetcher._PROVIDERS.keys())
        assert keys == {"crypto"}, f"SPEC v2 要求只做 crypto，实际: {keys}"

    def test_cn_provider_removed(self):
        """_get_cn_kline 不再存在。"""
        from app.services.data_fetcher import DataFetcher
        assert not hasattr(DataFetcher, "_get_cn_kline"), (
            "SPEC v2 §1 已删 A 股：_get_cn_kline 不应存在"
        )

    def test_us_provider_removed(self):
        """_get_us_kline 不再存在。"""
        from app.services.data_fetcher import DataFetcher
        assert not hasattr(DataFetcher, "_get_us_kline"), (
            "SPEC v2 §1 已删美股：_get_us_kline 不应存在"
        )


class TestV2DefaultMarket:
    """SPEC v2 §M1.5：默认 market 应是 crypto。"""

    def test_kline_router_default_market_is_crypto(self):
        from app.routers.kline import router
        # 找 get_kline 这个 endpoint（按 path 锁定）
        import inspect
        for route in router.routes:
            if getattr(route, "path", "").endswith("/kline/{symbol}"):
                sig = inspect.signature(route.endpoint)
                market_param = sig.parameters["market"]
                # FastAPI 把 Query(...) 包成 Annotated[..., Query(...)]，
                # default 是 Query(crypto)，实际值在 default.default
                default = market_param.default
                actual = getattr(default, "default", default)
                assert actual == "crypto", (
                    f"SPEC v2 §M1.5 默认市场应是 crypto，实际: {actual!r}"
                )
                return
        pytest.fail("未找到 /kline/{symbol} 路由")


class TestV2AppDescription:
    """main.py description 不再说"覆盖 A 股 / 美股 / 加密货币"。"""

    def test_app_description_mentions_only_btc_eth(self):
        from app.main import app
        desc = app.description or ""
        # 旧文案含 "A 股"
        assert "A 股" not in desc, f"SPEC v2 不再覆盖 A 股，但 description 含: {desc!r}"
        assert "美股" not in desc, f"SPEC v2 不再覆盖美股，但 description 含: {desc!r}"


class TestV2MarketAdapterSimplified:
    """market_adapter.py 只剩 CryptoMarketAdapter。"""

    def test_only_crypto_adapter_class_exists(self):
        from app import data  # noqa: F401
        import app.data.market_adapter as ma
        assert hasattr(ma, "CryptoMarketAdapter")
        assert not hasattr(ma, "CnMarketAdapter"), "CnMarketAdapter 应已被删除"
        assert not hasattr(ma, "UsMarketAdapter"), "UsMarketAdapter 应已被删除"

    def test_factory_only_crypto(self):
        from app.data.market_adapter import get_market_adapter
        adapter = get_market_adapter("crypto")
        # 跑通即 OK；如果误传非 crypto 应抛 ValueError
        with pytest.raises(ValueError):
            get_market_adapter("cn")
        with pytest.raises(ValueError):
            get_market_adapter("us")