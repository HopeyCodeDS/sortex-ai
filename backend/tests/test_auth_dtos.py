"""Tests for auth DTOs — password complexity, email validation."""
import pytest
from pydantic import ValidationError

from src.application.dtos.auth_dto import LoginRequest, RegisterRequest


class TestRegisterRequestPasswordComplexity:

    def test_valid_password(self):
        req = RegisterRequest(email="test@example.com", password="StrongPass1")
        assert req.password == "StrongPass1"

    def test_password_too_short(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(email="test@example.com", password="Short1A")
        assert "8 characters" in str(exc_info.value)

    def test_password_no_uppercase(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(email="test@example.com", password="nouppercase1")
        assert "uppercase" in str(exc_info.value)

    def test_password_no_lowercase(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(email="test@example.com", password="NOLOWERCASE1")
        assert "lowercase" in str(exc_info.value)

    def test_password_no_digit(self):
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(email="test@example.com", password="NoDigitHere")
        assert "digit" in str(exc_info.value)

    def test_password_exactly_8_chars_valid(self):
        req = RegisterRequest(email="test@example.com", password="Abcdefg1")
        assert req.password == "Abcdefg1"

    def test_password_with_special_characters(self):
        req = RegisterRequest(email="test@example.com", password="Str0ng!@#$")
        assert req.password == "Str0ng!@#$"


class TestLoginRequestEmailValidation:

    def test_valid_email(self):
        req = LoginRequest(email="user@example.com", password="anything")
        assert req.email == "user@example.com"

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="not-an-email", password="anything")

    def test_empty_email(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="", password="anything")


class TestRegisterRequestDefaults:

    def test_default_role_is_viewer(self):
        req = RegisterRequest(email="test@example.com", password="StrongPass1")
        assert req.role == "viewer"

    def test_custom_role(self):
        req = RegisterRequest(email="test@example.com", password="StrongPass1", role="admin")
        assert req.role == "admin"
