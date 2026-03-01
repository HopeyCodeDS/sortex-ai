"""
Redis-backed rate limiting middleware using sliding window algorithm.
Falls back to in-memory limiting if Redis is unavailable.
"""
import os
import time
from collections import defaultdict

import redis
from fastapi import Request, HTTPException

from ...infrastructure.monitoring.logging import get_logger

logger = get_logger("sortex.middleware.rate_limit")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")


class RateLimiter:
    """
    Sliding-window rate limiter backed by Redis.
    Automatically falls back to in-memory if Redis is unreachable.
    """

    def __init__(self, requests_per_minute: int = 5, prefix: str = "rl"):
        self.requests_per_minute = requests_per_minute
        self.prefix = prefix
        self._redis: redis.Redis | None = None
        self._init_redis()

        # In-memory fallback
        self._mem_requests: dict[str, list[float]] = defaultdict(list)

    def _init_redis(self) -> None:
        try:
            self._redis = redis.from_url(REDIS_URL, socket_connect_timeout=2)
            self._redis.ping()
        except Exception:
            logger.warning("Redis unavailable for rate limiting — using in-memory fallback")
            self._redis = None

    async def check(self, key: str) -> None:
        """
        Check if the request should be rate limited.

        Raises:
            HTTPException: 429 if rate limit exceeded.
        """
        full_key = f"{self.prefix}:{key}"

        if self._redis is not None:
            try:
                await self._check_redis(full_key)
                return
            except HTTPException:
                raise
            except Exception:
                # Redis went away mid-flight; fall back for this request
                pass

        self._check_memory(full_key)

    async def _check_redis(self, key: str) -> None:
        """Sliding window counter in Redis using a sorted set."""
        now = time.time()
        window_start = now - 60  # 1-minute window

        pipe = self._redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zcard(key)
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, 120)
        results = pipe.execute()

        current_count = results[1]
        if current_count >= self.requests_per_minute:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again later.",
            )

    def _check_memory(self, key: str) -> None:
        """In-memory fallback (single-instance only)."""
        now = time.time()
        window_start = now - 60

        self._mem_requests[key] = [t for t in self._mem_requests[key] if t > window_start]

        if len(self._mem_requests[key]) >= self.requests_per_minute:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again later.",
            )

        self._mem_requests[key].append(now)


# Global rate limiter instances
login_limiter = RateLimiter(requests_per_minute=5, prefix="rl:login")
refresh_limiter = RateLimiter(requests_per_minute=10, prefix="rl:refresh")
register_limiter = RateLimiter(requests_per_minute=3, prefix="rl:register")


async def rate_limit_login(request: Request) -> None:
    """FastAPI dependency — 5 requests/minute per IP on login."""
    client_ip = request.client.host if request.client else "unknown"
    await login_limiter.check(client_ip)


async def rate_limit_refresh(request: Request) -> None:
    """FastAPI dependency — 10 requests/minute per IP on token refresh."""
    client_ip = request.client.host if request.client else "unknown"
    await refresh_limiter.check(client_ip)


async def rate_limit_register(request: Request) -> None:
    """FastAPI dependency — 3 requests/minute per IP on registration."""
    client_ip = request.client.host if request.client else "unknown"
    await register_limiter.check(client_ip)
