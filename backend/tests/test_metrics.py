"""Prometheus metrics endpoint tests — M4 SRE SLI 覆盖"""
import pytest


def test_prometheus_metrics_endpoint():
    """GET /metrics 应返回 200 + Prometheus 格式文本"""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    res = client.get("/metrics")
    assert res.status_code == 200
    assert res.headers.get("content-type", "").startswith("text/plain")
