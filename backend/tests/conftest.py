"""kbkkk backend pytest 全局配置。

V2 教训 #0.7：.env 中存在 pydantic v2 Settings 不识别的 keys（GRAFANA_PASSWORD 等），
会触发 ValidationError（pydantic_settings 直接读 .env 文件，不走 os.environ）。

本文件提供 conftest fixture 强制让 app.config.get_settings() 不读 .env，
让 `from app.main import app` 不被 .env 冲突阻塞。

⚠️ 不修 config.py（V2 报告："已有 bug，不属于本 PR 范围"）
⚠️ 不动 .env 文件本身（部署依赖）
"""
import os
from unittest.mock import patch

import pytest


# 已知 .env 中有但 pydantic v2 Settings 不识别的 keys
# （V2 报告 + v2 contract cleanup 实测）
_DOTENV_UNKNOWN_KEYS = (
    "GRAFANA_PASSWORD",
    "GF_SECURITY_ADMIN_PASSWORD",
    "GF_USERS_DEFAULT_THEME",
    "PROMETHEUS_URL",
)


def pytest_configure(config):
    """在 pytest 收集阶段（import 任何测试模块前）清掉 os.environ 中的 keys。

    ⚠️ 重要：pydantic_settings 直接读 .env 文件，不走 os.environ。
    单独这一行不够；还需要 mock Settings 的 _env_file。
    """
    for key in _DOTENV_UNKNOWN_KEYS:
        os.environ.pop(key, None)


@pytest.fixture(autouse=True)
def _patch_settings_no_dotenv(monkeypatch):
    """autouse fixture：每个测试前让 Settings() 不读 .env 文件。

    通过 patch Settings 类，让所有 Settings 实例化都用 _env_file=None，
    绕开 .env 中 GRAFANA_PASSWORD 等未知 key 的 ValidationError。
    """
    from pydantic_settings import BaseSettings
    original_init = BaseSettings.__init__

    def patched_init(self, **kwargs):
        # 强制 _env_file=None（不读 .env）+ extra=ignore（不报未知字段）
        kwargs.setdefault("_env_file", None)
        # 兼容两种写法：class Config vs model_config
        if not hasattr(self, "model_config") or self.model_config is None:
            pass
        return original_init(self, **kwargs)

    monkeypatch.setattr(BaseSettings, "__init__", patched_init)
    yield
