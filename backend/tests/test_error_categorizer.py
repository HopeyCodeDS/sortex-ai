"""Tests for ErrorCategorizer — retryable vs permanent classification."""
import pytest

from src.infrastructure.error_handling.error_categorizer import ErrorCategorizer
from src.infrastructure.error_handling.retry import RetryableError, PermanentError


class TestRetryableErrors:

    def test_connection_error_by_type_name(self):
        is_retryable, category = ErrorCategorizer.categorize(ConnectionError("refused"))
        assert is_retryable is True
        assert category == "network_error"

    def test_timeout_error_by_type_name(self):
        is_retryable, category = ErrorCategorizer.categorize(TimeoutError("timed out"))
        assert is_retryable is True
        assert category == "network_error"

    def test_network_keyword_in_message(self):
        is_retryable, category = ErrorCategorizer.categorize(RuntimeError("network unreachable"))
        assert is_retryable is True
        assert category == "network_error"

    def test_temporary_keyword_in_message(self):
        is_retryable, category = ErrorCategorizer.categorize(RuntimeError("temporary failure"))
        assert is_retryable is True
        assert category == "network_error"

    def test_rate_limit_keyword(self):
        is_retryable, category = ErrorCategorizer.categorize(RuntimeError("rate limit exceeded"))
        assert is_retryable is True
        assert category == "rate_limit"

    def test_429_in_message(self):
        is_retryable, category = ErrorCategorizer.categorize(RuntimeError("HTTP 429 too many requests"))
        assert is_retryable is True
        assert category == "rate_limit"

    def test_expired_auth_token_retryable(self):
        # Custom exception class with 'Auth' in name
        class AuthError(Exception):
            pass
        is_retryable, category = ErrorCategorizer.categorize(AuthError("token expired"))
        assert is_retryable is True
        assert category == "auth_token_expired"

    def test_unknown_error_defaults_to_retryable(self):
        is_retryable, category = ErrorCategorizer.categorize(RuntimeError("something weird"))
        assert is_retryable is True
        assert category == "unknown_error"


class TestPermanentErrors:

    def test_auth_error_without_expiry(self):
        class AuthError(Exception):
            pass
        is_retryable, category = ErrorCategorizer.categorize(AuthError("invalid credentials"))
        assert is_retryable is False
        assert category == "authentication_error"

    def test_validation_error_by_type_name(self):
        class ValidationError(Exception):
            pass
        is_retryable, category = ErrorCategorizer.categorize(ValidationError("bad data"))
        assert is_retryable is False
        assert category == "validation_error"

    def test_value_error(self):
        is_retryable, category = ErrorCategorizer.categorize(ValueError("invalid"))
        assert is_retryable is False
        assert category == "validation_error"

    def test_file_format_error(self):
        is_retryable, category = ErrorCategorizer.categorize(RuntimeError("unsupported file format"))
        assert is_retryable is False
        assert category == "file_format_error"

    def test_invalid_file_keyword(self):
        is_retryable, category = ErrorCategorizer.categorize(RuntimeError("invalid file uploaded"))
        assert is_retryable is False
        assert category == "file_format_error"


class TestShouldRetry:

    def test_returns_true_for_retryable(self):
        assert ErrorCategorizer.should_retry(ConnectionError("down")) is True

    def test_returns_false_for_permanent(self):
        assert ErrorCategorizer.should_retry(ValueError("bad")) is False


class TestRaiseAppropriateError:

    def test_raises_retryable_error(self):
        with pytest.raises(RetryableError):
            ErrorCategorizer.raise_appropriate_error(ConnectionError("down"))

    def test_raises_permanent_error(self):
        with pytest.raises(PermanentError):
            ErrorCategorizer.raise_appropriate_error(ValueError("bad"))
