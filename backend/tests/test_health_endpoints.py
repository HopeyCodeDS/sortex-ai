"""Tests for health endpoints — mock dependency checks, verify 200/503 responses.

The health router imports `get_database` from `dependencies.py`, which eagerly
creates a Database(postgresql://...) at module scope — triggering psycopg2,
minio, paddleocr, etc. We sidestep the entire chain by stubbing
`src.api.dependencies` in sys.modules before importing the health router.
"""
import sys
from types import ModuleType
from unittest.mock import patch, MagicMock

import pytest

# ---- Stub the dependencies module that health.py imports from ----
_deps_stub = ModuleType("src.api.dependencies")
_deps_stub.get_database = MagicMock()  
sys.modules.setdefault("src.api.dependencies", _deps_stub)

# Now the import chain from health.py -> dependencies is satisfied
from src.api.routes.health import router  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestLivenessProbe:

    def test_health_always_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"


class TestReadinessProbe:

    @patch("src.api.routes.health._check_ollama", return_value={"status": "up", "latency_ms": 10})
    @patch("src.api.routes.health._check_minio", return_value={"status": "up", "latency_ms": 5})
    @patch("src.api.routes.health._check_redis", return_value={"status": "up", "latency_ms": 2})
    @patch("src.api.routes.health._check_postgres", return_value={"status": "up", "latency_ms": 3})
    def test_all_healthy_returns_200(self, mock_pg, mock_redis, mock_minio, mock_ollama, client):
        resp = client.get("/health/ready")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert body["dependencies"]["postgres"]["status"] == "up"
        assert body["dependencies"]["redis"]["status"] == "up"
        assert body["dependencies"]["minio"]["status"] == "up"
        assert body["dependencies"]["ollama"]["status"] == "up"

    @patch("src.api.routes.health._check_ollama", return_value={"status": "up"})
    @patch("src.api.routes.health._check_minio", return_value={"status": "up"})
    @patch("src.api.routes.health._check_redis", return_value={"status": "up"})
    @patch("src.api.routes.health._check_postgres", return_value={"status": "down", "error": "connection refused"})
    def test_postgres_down_returns_503(self, mock_pg, mock_redis, mock_minio, mock_ollama, client):
        resp = client.get("/health/ready")
        assert resp.status_code == 503
        assert resp.json()["status"] == "unhealthy"

    @patch("src.api.routes.health._check_ollama", return_value={"status": "up"})
    @patch("src.api.routes.health._check_minio", return_value={"status": "down", "error": "unreachable"})
    @patch("src.api.routes.health._check_redis", return_value={"status": "up"})
    @patch("src.api.routes.health._check_postgres", return_value={"status": "up"})
    def test_minio_down_returns_503(self, mock_pg, mock_redis, mock_minio, mock_ollama, client):
        resp = client.get("/health/ready")
        assert resp.status_code == 503

    @patch("src.api.routes.health._check_ollama", return_value={"status": "up"})
    @patch("src.api.routes.health._check_minio", return_value={"status": "up"})
    @patch("src.api.routes.health._check_redis", return_value={"status": "down", "error": "refused"})
    @patch("src.api.routes.health._check_postgres", return_value={"status": "up"})
    def test_redis_down_returns_503(self, mock_pg, mock_redis, mock_minio, mock_ollama, client):
        resp = client.get("/health/ready")
        assert resp.status_code == 503

    @patch("src.api.routes.health._check_ollama", return_value={"status": "down", "error": "unavailable"})
    @patch("src.api.routes.health._check_minio", return_value={"status": "up"})
    @patch("src.api.routes.health._check_redis", return_value={"status": "up"})
    @patch("src.api.routes.health._check_postgres", return_value={"status": "up"})
    def test_ollama_down_does_not_fail_readiness(self, mock_pg, mock_redis, mock_minio, mock_ollama, client):
        """Ollama is non-critical; readiness should still be 200."""
        resp = client.get("/health/ready")
        assert resp.status_code == 200
        assert resp.json()["dependencies"]["ollama"]["status"] == "down"
