"""Tests for the input-sanitization utilities."""

import html

import pytest

from app.core.sanitization import (
    MAX_NAME_LENGTH,
    MAX_STRING_LENGTH,
    MAX_TEXT_LENGTH,
    sanitize_email,
    sanitize_name,
    sanitize_phone,
    sanitize_string,
    sanitize_text,
    validate_password_strength,
)


class TestSanitizeString:
    def test_strips_and_truncates(self) -> None:
        long = "x" * (MAX_STRING_LENGTH + 50)
        result = sanitize_string(f"  {long}  ")
        assert result is not None
        assert len(result) == MAX_STRING_LENGTH
        assert not result.startswith(" ")

    def test_html_encodes(self) -> None:
        result = sanitize_string("<script>alert(1)</script>")
        assert result is not None
        assert "<script>" not in result
        assert html.escape("<script>alert(1)</script>") in result

    def test_none_returns_none(self) -> None:
        assert sanitize_string(None) is None

    def test_custom_max_length(self) -> None:
        result = sanitize_string("abcdef", max_length=3)
        assert result == "abc"


class TestSanitizeText:
    def test_none_returns_none(self) -> None:
        assert sanitize_text(None) is None

    def test_strips_and_truncates(self) -> None:
        long = "a" * (MAX_TEXT_LENGTH + 100)
        result = sanitize_text(long)
        assert result is not None
        assert len(result) == MAX_TEXT_LENGTH

    def test_preserves_newlines_after_strip(self) -> None:
        result = sanitize_text("  line1\nline2  ")
        assert result is not None
        assert result == "line1\nline2"


class TestSanitizeName:
    def test_happy_path(self) -> None:
        assert sanitize_name("  Widget  ") == "Widget"

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            sanitize_name("")

    def test_whitespace_only_returns_empty(self) -> None:
        # sanitize_name checks emptiness before stripping, so whitespace-only
        # is treated as non-empty and returns an empty string after strip+escape.
        assert sanitize_name("   ") == ""

    def test_truncates_to_max_name_length(self) -> None:
        long_name = "x" * (MAX_NAME_LENGTH + 50)
        result = sanitize_name(long_name)
        assert len(result) == MAX_NAME_LENGTH

    def test_html_encodes(self) -> None:
        result = sanitize_name("<b>Bob</b>")
        assert result == html.escape("<b>Bob</b>")


class TestSanitizeEmail:
    def test_none_returns_none(self) -> None:
        assert sanitize_email(None) is None

    def test_empty_returns_none(self) -> None:
        assert sanitize_email("") is None

    def test_whitespace_only_raises_value_error(self) -> None:
        # sanitize_email checks truthiness before strip, so whitespace-only
        # passes the guard, strips to "" and then fails the email pattern.
        with pytest.raises(ValueError, match="Invalid email format"):
            sanitize_email("   ")

    def test_valid_email_lowercased_and_escaped(self) -> None:
        result = sanitize_email("  USER@Example.COM  ")
        assert result == "user@example.com"

    def test_invalid_email_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid email format"):
            sanitize_email("not-an-email")


class TestSanitizePhone:
    def test_none_returns_none(self) -> None:
        assert sanitize_phone(None) is None

    def test_empty_returns_none(self) -> None:
        assert sanitize_phone("") is None

    def test_valid_phone(self) -> None:
        assert sanitize_phone("+1 (555) 123-4567") == html.escape("+1 (555) 123-4567")

    def test_invalid_phone_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid phone number format"):
            sanitize_phone("abc")


class TestValidatePasswordStrength:
    def test_too_short(self) -> None:
        valid, msg = validate_password_strength("Ab1!")
        assert valid is False
        assert "8 characters" in msg

    def test_too_long(self) -> None:
        valid, msg = validate_password_strength("a1" * 80)  # 160 chars
        assert valid is False
        assert "128 characters" in msg

    def test_no_digit(self) -> None:
        valid, msg = validate_password_strength("OnlyLettersHere")
        assert valid is False

    def test_no_letter(self) -> None:
        valid, msg = validate_password_strength("12345678")
        assert valid is False

    def test_valid_passphrase_with_digit(self) -> None:
        valid, _msg = validate_password_strength("correct-horse-battery-staple-9")
        assert valid is True

    def test_valid_simple(self) -> None:
        valid, _msg = validate_password_strength("Password1")
        assert valid is True

    def test_empty_password(self) -> None:
        valid, msg = validate_password_strength("")
        assert valid is False
        assert "8 characters" in msg
