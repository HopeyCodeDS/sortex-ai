"""Health check endpoints with deep dependency probing."""
import os
import time

import httpx
import redis
from fastapi import APIRouter
from sqlalchemy import text

from ...api.dependencies import get_database
from ...infrastructure.monitoring.logging import get_logger

router = APIRouter()
logger = get_logger("sortex.api.health")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")


def _check_postgres() -> dict:
    """Probe PostgreSQL with a lightweight query."""
    start = time.monotonic()
    try:
        session = get_database().get_session()
        try:
            session.execute(text("SELECT 1"))
            latency_ms = round((time.monotonic() - start) * 1000, 1)
            return {"status": "up", "latency_ms": latency_ms}
        finally:
            session.close()
    except Exception as e:
        return {"status": "down", "error": str(e)}


def _check_redis() -> dict:
    """Probe Redis with PING."""
    start = time.monotonic()
    try:
        client = redis.from_url(REDIS_URL, socket_connect_timeout=3)
        client.ping()
        latency_ms = round((time.monotonic() - start) * 1000, 1)
        client.close()
        return {"status": "up", "latency_ms": latency_ms}
    except Exception as e:
        return {"status": "down", "error": str(e)}


def _check_minio() -> dict:
    """Probe MinIO health endpoint."""
    start = time.monotonic()
    try:
        url = f"http://{MINIO_ENDPOINT}/minio/health/live"
        resp = httpx.get(url, timeout=5)
        latency_ms = round((time.monotonic() - start) * 1000, 1)
        if resp.status_code == 200:
            return {"status": "up", "latency_ms": latency_ms}
        return {"status": "degraded", "http_status": resp.status_code}
    except Exception as e:
        return {"status": "down", "error": str(e)}


def _check_ollama() -> dict:
    """Probe Ollama API availability."""
    start = time.monotonic()
    try:
        resp = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        latency_ms = round((time.monotonic() - start) * 1000, 1)
        if resp.status_code == 200:
            return {"status": "up", "latency_ms": latency_ms}
        return {"status": "degraded", "http_status": resp.status_code}
    except Exception as e:
        return {"status": "down", "error": str(e)}


@router.get("/health")
async def health_simple():
    """Lightweight liveness probe — always returns 200 if the process is up."""
    return {"status": "healthy"}


@router.get("/health/ready")
async def health_ready():
    """
    Readiness probe — checks all critical dependencies.
    Returns 200 only when the service can handle requests end-to-end.
    Returns 503 if any critical dependency (postgres, redis, minio) is down.
    """
    checks = {
        "postgres": _check_postgres(),
        "redis": _check_redis(),
        "minio": _check_minio(),
        "ollama": _check_ollama(),
    }

    critical = ["postgres", "redis", "minio"]
    any_critical_down = any(checks[svc]["status"] == "down" for svc in critical)

    overall = "unhealthy" if any_critical_down else "healthy"

    if any_critical_down:
        logger.warning("Readiness check failed", checks=checks)

    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=503 if any_critical_down else 200,
        content={"status": overall, "dependencies": checks},
    )
