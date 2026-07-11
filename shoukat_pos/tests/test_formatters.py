"""
Tests for formatters module.

Verifies currency, date, and quantity formatting functions
following Pakistani business standards.
"""

import pytest

from utils.formatters import (
    format_currency,
    format_date,
    format_datetime,
    format_percentage,
    format_quantity,
)


class TestCurrencyFormatting:
    """Test currency formatting (cents to rupees)."""

    def test_basic_format(self):
        """Test basic currency formatting."""
        assert format_currency(125050) == "Rs. 1,250.50"
        assert format_currency(100000) == "Rs. 1,000.00"
        assert format_currency(50000) == "Rs. 500.00"

    def test_thousands_separator(self):
        """Test thousands separator formatting."""
        assert format_currency(1250000) == "Rs. 12,500.00"
        assert format_currency(12500000) == "Rs. 125,000.00"
        assert format_currency(125000000) == "Rs. 1,250,000.00"

    def test_zero_amount(self):
        """Test zero amount formatting."""
        assert format_currency(0) == "Rs. 0.00"

    def test_custom_currency_symbol(self):
        """Test custom currency symbol."""
        assert format_currency(100000, currency_symbol="$") == "$ 1,000.00"
        assert format_currency(100000, currency_symbol="€") == "€ 1,000.00"
        # Note: PKR with trailing space results in double space
        assert format_currency(100000, currency_symbol="PKR ") == "PKR  1,000.00"

    def test_non_integer_raises_typeerror(self):
        """Test that non-integer input raises TypeError."""
        with pytest.raises(TypeError):
            format_currency(100.50)
        with pytest.raises(TypeError):
            format_currency("10000")

    def test_negative_amount(self):
        """Test negative amount formatting."""
        # Negative amounts should still format correctly
        assert format_currency(-10000) == "Rs. -100.00"


class TestDateFormatting:
    """Test date formatting from ISO 8601."""

    def test_iso_date_to_ddmmyyyy(self):
        """Test ISO date to DD/MM/YYYY format."""
        assert format_date("2024-01-15") == "15/01/2024"
        assert format_date("2024-12-31") == "31/12/2024"

    def test_iso_datetime_to_ddmmyyyy(self):
        """Test ISO datetime to DD/MM/YYYY format."""
        assert format_date("2024-01-15T10:30:00") == "15/01/2024"
        assert format_date("2024-12-31T23:59:59") == "31/12/2024"

    def test_custom_output_format(self):
        """Test custom output format."""
        assert format_date("2024-01-15", "%Y-%m-%d") == "2024-01-15"
        assert format_date("2024-01-15", "%d-%m-%Y") == "15-01-2024"
        assert format_date("2024-01-15", "%B %d, %Y") == "January 15, 2024"

    def test_iso_with_timezone(self):
        """Test ISO date with timezone."""
        assert format_date("2024-01-15T10:30:00Z") == "15/01/2024"
        # Note: Timezone handling may vary based on implementation

    def test_invalid_date_raises_valueerror(self):
        """Test that invalid date raises ValueError."""
        with pytest.raises(ValueError):
            format_date("invalid-date")
        with pytest.raises(ValueError):
            format_date("2024-13-45")

    def test_non_string_raises_typeerror(self):
        """Test that non-string input raises TypeError."""
        with pytest.raises(TypeError):
            format_date(20240115)


class TestQuantityFormatting:
    """Test quantity formatting with optional units."""

    def test_basic_quantity(self):
        """Test basic quantity formatting."""
        assert format_quantity(10) == "10"
        assert format_quantity(1000) == "1,000"
        assert format_quantity(1000000) == "1,000,000"

    def test_quantity_with_unit(self):
        """Test quantity with unit suffix."""
        assert format_quantity(10, "pcs") == "10 pcs"
        assert format_quantity(1000, "kg") == "1,000 kg"
        assert format_quantity(500, "m") == "500 m"

    def test_zero_quantity(self):
        """Test zero quantity."""
        assert format_quantity(0) == "0"
        assert format_quantity(0, "pcs") == "0 pcs"

    def test_negative_quantity_raises(self):
        """Test that negative quantity raises ValueError."""
        with pytest.raises(ValueError):
            format_quantity(-10)
        with pytest.raises(ValueError):
            format_quantity(-10, "pcs")

    def test_non_integer_raises_typeerror(self):
        """Test that non-integer input raises TypeError."""
        with pytest.raises(TypeError):
            format_quantity(10.5)
        with pytest.raises(TypeError):
            format_quantity("10")


class TestPercentageFormatting:
    """Test percentage formatting."""

    def test_basic_percentage(self):
        """Test basic percentage formatting."""
        assert format_percentage(17.0) == "17.00%"
        assert format_percentage(0.0) == "0.00%"
        assert format_percentage(100.0) == "100.00%"

    def test_custom_decimals(self):
        """Test custom decimal places."""
        assert format_percentage(17.5, decimals=1) == "17.5%"
        assert format_percentage(17.5, decimals=0) == "18%"
        assert format_percentage(17.567, decimals=3) == "17.567%"

    def test_integer_input(self):
        """Test integer input."""
        assert format_percentage(17) == "17.00%"
        assert format_percentage(0) == "0.00%"

    def test_non_numeric_raises_typeerror(self):
        """Test that non-numeric input raises TypeError."""
        with pytest.raises(TypeError):
            format_percentage("17")


class TestDatetimeFormatting:
    """Test datetime formatting."""

    def test_basic_datetime(self):
        """Test basic datetime formatting."""
        result = format_datetime("2024-01-15T10:30:00")
        assert result == "15/01/2024 10:30"

    def test_custom_format(self):
        """Test custom datetime format."""
        result = format_datetime("2024-01-15T10:30:00", "%Y-%m-%d %H:%M:%S")
        assert result == "2024-01-15 10:30:00"

    def test_date_only(self):
        """Test date-only input."""
        result = format_datetime("2024-01-15")
        assert result == "15/01/2024 00:00"
