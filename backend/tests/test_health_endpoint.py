"""Health endpoint tests — M4 SRE SLI 覆盖"""
import pytest


def test_health_returns_200():
    """GET /api/v1/health 应返回 200（不论依赖状态）"""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    res = client.get("/api/v1/health")
    # 健康检查永不掉线：200 是 SLI 核心，status 字段反映真实状态
    assert res.status_code == 200
    data = res.json()
    # 依赖全 up → "ok"，任一下 → "degraded"
    assert data["status"] in ("ok", "degraded")


def test_health_includes_dependency_keys():
    """健康检查应包含依赖项 key（database=postgres, redis）"""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    res = client.get("/api/v1/health")
    data = res.json()
    # 返回 "database"（即 postgres）和 "redis" 状态
    assert "database" in data
    assert "redis" in data
    # 状态值只能是 ok/down（无 null/undefined 歧义）
    assert data["database"] in ("ok", "down")
    assert data["redis"] in ("ok", "down")
