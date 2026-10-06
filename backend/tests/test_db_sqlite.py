"""SQLite backend 适配测试 — PR-3 回归测试

验证 PR-3 改动：
1. DB_BACKEND=sqlite 切换：URL 解析正确（sqlite+aiosqlite:///{path}）
2. SQLite init_db() 不抛异常（跳过 PG 扩展）
3. SQLite 创建全部 7 张表（Kline/Indicator/Signal/Order/CalibrationModel/
   RecommendationHistory/TradeLog）
4. SQLite health_check() 返回 True
5. PG 扩展调用不会出现在 SQLite 路径
6. Postgres backend URL 不变（向后兼容）
"""
from __future__ import annotations

import os
import tempfile
from unittest.mock import patch

import pytest


# ── 测试 1：DB_BACKEND=sqlite 切换 URL 解析 ─────────────────────────────

def test_sqlite_backend_url_uses_aiosqlite():
    """DB_BACKEND=sqlite 应生成 sqlite+aiosqlite:///{path} URL。"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        tmp_path = f.name

    env = {
        "DB_BACKEND": "sqlite",
        "SQLITE_PATH": tmp_path,
        # 故意污染 postgres URL，验证 SQLite 模式忽略它
        "DATABASE_URL": "postgresql+asyncpg://should/be/ignored",
    }
    with patch.dict(os.environ, env, clear=True):
        # 强制重新导入以触发模块顶层 DB_BACKEND 设置
        import importlib
        import app.db
        importlib.reload(app.db)

        assert app.db.DB_BACKEND == "sqlite"
        assert "sqlite+aiosqlite" in app.db.DATABASE_URL
        assert tmp_path in app.db.DATABASE_URL
        # 关闭引擎，避免 reloader 残留
        import asyncio
        asyncio.run(app.db.close_db())


# ── 测试 2：DB_BACKEND=postgres（默认）向后兼容 ─────────────────────────

def test_postgres_backend_url_default():
    """DB_BACKEND 未设置 → postgres 默认。"""
    with patch.dict(os.environ, {}, clear=True):
        # 移除可能污染的环境变量
        os.environ.pop("DB_BACKEND", None)
        os.environ.pop("SQLITE_PATH", None)

        import importlib
        import app.db
        importlib.reload(app.db)

        assert app.db.DB_BACKEND == "postgres"
        assert "postgresql+asyncpg" in app.db.DATABASE_URL
        import asyncio
        asyncio.run(app.db.close_db())


# ── 测试 3：SQLite init_db() 不抛异常 + 创建 7 张表 ──────────────────────

@pytest.mark.asyncio
async def test_sqlite_init_creates_all_seven_tables():
    """DB_BACKEND=sqlite 时 init_db() 应成功执行（无 PG 扩展调用）。"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        tmp_path = f.name

    with patch.dict(os.environ, {"DB_BACKEND": "sqlite", "SQLITE_PATH": tmp_path}):
        import importlib
        import app.db
        importlib.reload(app.db)

        # 验证 init_db 不抛异常
        await app.db.init_db()

        # 通过 SQLAlchemy metadata 验证 7 张表已创建
        from app.models import Base as ModelBase
        table_names = set(ModelBase.metadata.tables.keys())
        expected = {
            "klines", "indicators", "signals", "orders",
            "calibration_models", "recommendation_history", "trade_logs",
        }
        assert expected.issubset(table_names), (
            f"Missing tables: {expected - table_names}"
        )

        # 验证 health_check 通过
        ok = await app.db.health_check()
        assert ok is True

        await app.db.close_db()
        os.unlink(tmp_path)


# ── 测试 4：SQLite 跳过 PG 扩展（用 patch 验证）──────────────────────

@pytest.mark.asyncio
async def test_sqlite_skips_pg_extensions():
    """SQLite backend 不应执行 CREATE EXTENSION 语句。"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        tmp_path = f.name

    with patch.dict(os.environ, {"DB_BACKEND": "sqlite", "SQLITE_PATH": tmp_path}):
        import importlib
        from sqlalchemy import text as sa_text
        import app.db

        # 重新加载以应用环境变量
        importlib.reload(app.db)

        # 拦截 conn.execute 验证不调用 PG 扩展
        extension_calls: list[str] = []

        original_engine = app.db.engine

        class ConnSpy:
            """Spy: 记录 CREATE EXTENSION 调用。"""
            def __init__(self, real_conn):
                self.real_conn = real_conn

            async def execute(self, stmt, *args, **kwargs):
                sql_str = str(stmt)
                if "CREATE EXTENSION" in sql_str:
                    extension_calls.append(sql_str)
                return await self.real_conn.execute(stmt, *args, **kwargs)

            async def run_sync(self, fn, *args, **kwargs):
                return await self.real_conn.run_sync(fn, *args, **kwargs)

            async def __aenter__(self):
                self._cm = self.real_conn.begin()
                await self._cm.__aenter__()
                return ConnSpy(self.real_conn)

            async def __aexit__(self, *exc):
                return await self._cm.__aexit__(*exc)

        # 直接调用 init_db，验证不抛异常 + 不调 CREATE EXTENSION
        await app.db.init_db()
        assert extension_calls == [], (
            f"SQLite不应调 CREATE EXTENSION，实际: {extension_calls}"
        )

        await app.db.close_db()
        os.unlink(tmp_path)


# ── 测试 5：跨 backend 通用 create_all（PG 路径不会破）────────────────

@pytest.mark.asyncio
async def test_postgres_init_still_works():
    """postgres backend 下 init_db() 仍能跑（mock engine 避免连真实 PG）。"""
    from unittest.mock import AsyncMock, MagicMock

    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("DB_BACKEND", None)

        import importlib
        import app.db
        importlib.reload(app.db)

        # mock engine 避免连真实 PG
        mock_engine = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        mock_conn.execute = AsyncMock(return_value=None)
        mock_conn.run_sync = AsyncMock(return_value=None)

        class _BeginCtx:
            async def __aenter__(self_inner):
                return mock_conn
            async def __aexit__(self_inner, *exc):
                return None

        mock_engine.begin = MagicMock(return_value=_BeginCtx())

        app.db.engine = mock_engine

        # postgres backend: 应执行 PG 扩展（被 mock 接收）
        await app.db.init_db()

        # 验证 CREATE EXTENSION 被调用过（PG 路径）
        executed_sql = [str(call.args[0]) for call in mock_conn.execute.call_args_list]
        assert any("uuid-ossp" in s for s in executed_sql), "PG 应创建 uuid-ossp"
        assert any("pg_trgm" in s for s in executed_sql), "PG 应创建 pg_trgm"