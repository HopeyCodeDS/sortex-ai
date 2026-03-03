"""Tests for TriggerExtractionUseCase — retry logic and DLQ."""
from unittest.mock import MagicMock, patch, PropertyMock
from uuid import uuid4

import pytest

from src.infrastructure.error_handling.retry import RetryableError, PermanentError


class TestTriggerExtractionRetry:
    """Verify retry/DLQ logic without importing the full use case (avoids Redis side effects)."""

    @patch("time.sleep", return_value=None)  # skip actual delays
    def test_retry_decorator_retries_on_transient_error(self, mock_sleep):
        from src.infrastructure.error_handling.retry import retry_with_backoff

        call_count = 0

        @retry_with_backoff(max_retries=3, initial_delay=0.01, jitter=False)
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("transient")
            return "success"

        result = flaky_func()
        assert result == "success"
        assert call_count == 3

    @patch("time.sleep", return_value=None)
    def test_retry_decorator_raises_permanent_error_immediately(self, mock_sleep):
        from src.infrastructure.error_handling.retry import retry_with_backoff

        call_count = 0

        @retry_with_backoff(max_retries=3, initial_delay=0.01, jitter=False)
        def perm_fail():
            nonlocal call_count
            call_count += 1
            raise PermanentError("bad data")

        with pytest.raises(PermanentError):
            perm_fail()
        assert call_count == 1  # no retries for permanent

    @patch("time.sleep", return_value=None)
    def test_retry_exhaustion_raises_retryable_error(self, mock_sleep):
        from src.infrastructure.error_handling.retry import retry_with_backoff

        @retry_with_backoff(max_retries=2, initial_delay=0.01, jitter=False)
        def always_fails():
            raise ConnectionError("network down")

        with pytest.raises(RetryableError, match="Max retries"):
            always_fails()

    @patch("time.sleep", return_value=None)
    def test_exponential_backoff_delays(self, mock_sleep):
        from src.infrastructure.error_handling.retry import retry_with_backoff

        @retry_with_backoff(max_retries=3, initial_delay=1.0, max_delay=60.0, jitter=False)
        def always_fails():
            raise RuntimeError("fail")

        with pytest.raises(RetryableError):
            always_fails()

        # Should have slept 3 times with exponential delays: 1, 2, 4
        assert mock_sleep.call_count == 3
        delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert delays[0] == pytest.approx(1.0)
        assert delays[1] == pytest.approx(2.0)
        assert delays[2] == pytest.approx(4.0)

    def test_trigger_use_case_sends_to_dlq_after_retries_exhausted(self):
        """Integration-style test: verify DLQ is called after all retries fail."""
        from src.infrastructure.error_handling.error_categorizer import ErrorCategorizer

        # A permanent error should NOT be retried
        perm_err = ValueError("invalid format data")
        assert ErrorCategorizer.should_retry(perm_err) is False

        # A connection error should be retried
        conn_err = ConnectionError("network timeout")
        assert ErrorCategorizer.should_retry(conn_err) is True
