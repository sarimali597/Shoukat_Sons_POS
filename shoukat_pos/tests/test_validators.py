"""
Tests for validators module.

Verifies phone number, price, email, and serial number validation
following Pakistani business standards.
"""

import pytest

from utils.validators import (
    ValidationError,
    normalize_phone,
    validate_email,
    validate_phone,
    validate_price,
    validate_serial,
)


class TestPhoneNumberValidation:
    """Test Pakistani phone number validation."""

    def test_valid_local_format(self):
        """Test valid 03XXXXXXXXX format."""
        assert validate_phone("03001234567") is True
        assert validate_phone("03121234567") is True
        assert validate_phone("03331234567") is True

    def test_valid_international_format(self):
        """Test valid +923XXXXXXXXX format."""
        assert validate_phone("+923001234567") is True
        assert validate_phone("+923121234567") is True

    def test_valid_without_leading_zero(self):
        """Test valid 3XXXXXXXXX format."""
        assert validate_phone("3001234567") is True
        assert validate_phone("3121234567") is True

    def test_invalid_length(self):
        """Test invalid phone number lengths."""
        with pytest.raises(ValidationError):
            validate_phone("0300123456")  # Too short
        with pytest.raises(ValidationError):
            validate_phone("030012345678")  # Too long

    def test_invalid_prefix(self):
        """Test invalid phone number prefixes."""
        with pytest.raises(ValidationError):
            validate_phone("04001234567")  # Should start with 03
        with pytest.raises(ValidationError):
            validate_phone("05001234567")

    def test_invalid_characters(self):
        """Test phone numbers with invalid characters."""
        with pytest.raises(ValidationError):
            validate_phone("0300-123-456a")
        with pytest.raises(ValidationError):
            validate_phone("abc1234567")

    def test_non_string_raises(self):
        """Test that non-string input raises ValidationError."""
        with pytest.raises(ValidationError):
            validate_phone(1234567890)
        with pytest.raises(ValidationError):
            validate_phone(None)


class TestPriceValidation:
    """Test price validation (integer cents)."""

    def test_valid_positive_price(self):
        """Test valid positive prices."""
        assert validate_price(100) is True
        assert validate_price(100000) is True
        assert validate_price(1) is True

    def test_zero_not_allowed_by_default(self):
        """Test that zero is not allowed by default."""
        with pytest.raises(ValidationError):
            validate_price(0)

    def test_zero_allowed_with_flag(self):
        """Test that zero is allowed when explicitly permitted."""
        assert validate_price(0, allow_zero=True) is True

    def test_negative_price_raises(self):
        """Test that negative prices raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_price(-100)
        with pytest.raises(ValidationError):
            validate_price(-1, allow_zero=True)

    def test_float_raises(self):
        """Test that float prices raise TypeError."""
        with pytest.raises(ValidationError):
            validate_price(100.50)
        with pytest.raises(ValidationError):
            validate_price(0.0)

    def test_non_numeric_raises(self):
        """Test that non-numeric types raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_price("100")
        with pytest.raises(ValidationError):
            validate_price(None)


class TestEmailValidation:
    """Test email validation (optional field)."""

    def test_valid_email(self):
        """Test valid email formats."""
        assert validate_email("test@example.com") is True
        assert validate_email("user.name@domain.org") is True
        assert validate_email("user+tag@example.co.uk") is True

    def test_none_is_valid(self):
        """Test that None is valid (email is optional)."""
        assert validate_email(None) is True

    def test_empty_string_is_valid(self):
        """Test that empty string is valid (email is optional)."""
        assert validate_email("") is True
        assert validate_email("   ") is True

    def test_invalid_email_formats(self):
        """Test invalid email formats."""
        with pytest.raises(ValidationError):
            validate_email("invalid")
        with pytest.raises(ValidationError):
            validate_email("invalid@")
        with pytest.raises(ValidationError):
            validate_email("@example.com")
        with pytest.raises(ValidationError):
            validate_email("user@.com")

    def test_non_string_raises(self):
        """Test that non-string input raises AttributeError."""
        with pytest.raises(AttributeError):
            validate_email(123)


class TestSerialValidation:
    """Test serial number format validation (SSG-XXX-NNN)."""

    def test_valid_serial_format(self):
        """Test valid SSG-XXX-NNN format."""
        assert validate_serial("SSG-TSH-001") is True
        assert validate_serial("SSG-ABC-123") is True
        assert validate_serial("SSG-ZZZ-999") is True

    def test_case_insensitive(self):
        """Test that validation is case insensitive."""
        assert validate_serial("ssg-tsh-001") is True
        assert validate_serial("Ssg-Tsh-001") is True

    def test_invalid_prefix(self):
        """Test invalid prefix."""
        with pytest.raises(ValidationError):
            validate_serial("ABC-TSH-001")
        with pytest.raises(ValidationError):
            validate_serial("SS-TSH-001")

    def test_invalid_letters_section(self):
        """Test invalid letters section."""
        with pytest.raises(ValidationError):
            validate_serial("SSG-T-001")  # Only 1 letter
        with pytest.raises(ValidationError):
            validate_serial("SSG-TSHH-001")  # 4 letters
        with pytest.raises(ValidationError):
            validate_serial("SSG-123-001")  # Numbers instead of letters

    def test_invalid_numbers_section(self):
        """Test invalid numbers section."""
        with pytest.raises(ValidationError):
            validate_serial("SSG-TSH-1")  # Only 1 digit
        with pytest.raises(ValidationError):
            validate_serial("SSG-TSH-1234")  # 4 digits
        with pytest.raises(ValidationError):
            validate_serial("SSG-TSH-ABC")  # Letters instead of numbers

    def test_missing_hyphens(self):
        """Test missing hyphens."""
        with pytest.raises(ValidationError):
            validate_serial("SSGTSH001")
        with pytest.raises(ValidationError):
            validate_serial("SSG-TSH001")

    def test_non_string_raises(self):
        """Test that non-string input raises ValidationError."""
        with pytest.raises(ValidationError):
            validate_serial(123)
        with pytest.raises(ValidationError):
            validate_serial(None)


class TestPhoneNormalization:
    """Test phone number normalization."""

    def test_normalize_local_format(self):
        """Test normalizing local format."""
        assert normalize_phone("03001234567") == "03001234567"

    def test_normalize_international_format(self):
        """Test normalizing international format."""
        assert normalize_phone("+923001234567") == "03001234567"

    def test_normalize_without_leading_zero(self):
        """Test normalizing format without leading zero."""
        assert normalize_phone("3001234567") == "03001234567"

    def test_normalize_with_spaces(self):
        """Test normalizing with spaces."""
        assert normalize_phone("0300 123 4567") == "03001234567"
        assert normalize_phone("0300-123-4567") == "03001234567"

    def test_non_string_raises(self):
        """Test that non-string input raises ValidationError."""
        with pytest.raises(ValidationError):
            normalize_phone(1234567890)
