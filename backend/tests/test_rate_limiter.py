"""Tests for RateLimiter — Redis path and in-memory fallback."""
import time
from unittest.mock import patch, MagicMock

import pytest
from fastapi import HTTPException


class TestInMemoryRateLimiter:
    """Test the in-memory fallback path (no Redis needed)."""

    def _make_limiter(self, rpm=3):
        """Create a RateLimiter with Redis disabled."""
        with patch("src.api.middleware.rate_limit.redis") as mock_redis_mod:
            mock_redis_mod.from_url.side_effect = ConnectionError("no redis")
            from src.api.middleware.rate_limit import RateLimiter
            limiter = RateLimiter(requests_per_minute=rpm, prefix="test")
        assert limiter._redis is None  # confirm in-memory mode
        return limiter

    def test_allows_requests_under_limit(self):
        limiter = self._make_limiter(rpm=5)
        # Should not raise for 5 requests
        for _ in range(5):
            limiter._check_memory("test:ip1")

    def test_blocks_request_over_limit(self):
        limiter = self._make_limiter(rpm=3)
        for _ in range(3):
            limiter._check_memory("test:ip2")
        with pytest.raises(HTTPException) as exc_info:
            limiter._check_memory("test:ip2")
        assert exc_info.value.status_code == 429

    def test_different_keys_have_separate_limits(self):
        limiter = self._make_limiter(rpm=2)
        for _ in range(2):
            limiter._check_memory("test:ip_a")
        # ip_b should still be allowed
        limiter._check_memory("test:ip_b")  # should not raise

    def test_window_expires_old_requests(self):
        limiter = self._make_limiter(rpm=2)
        # Add requests "in the past" manually
        key = "test:ip_old"
        old_time = time.time() - 120  # 2 minutes ago
        limiter._mem_requests[key] = [old_time, old_time]
        # Despite 2 old entries, new request should be allowed
        limiter._check_memory(key)  # should not raise

    @pytest.mark.asyncio
    async def test_async_check_falls_back_to_memory(self):
        limiter = self._make_limiter(rpm=5)
        # check() is async and should work with in-memory backend
        await limiter.check("test:async_ip")  # should not raise

    @pytest.mark.asyncio
    async def test_async_check_raises_429(self):
        limiter = self._make_limiter(rpm=1)
        await limiter.check("test:limit_ip")
        with pytest.raises(HTTPException) as exc_info:
            await limiter.check("test:limit_ip")
        assert exc_info.value.status_code == 429
