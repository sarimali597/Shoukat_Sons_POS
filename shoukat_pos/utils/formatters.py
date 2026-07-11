"""
Formatters for Shoukat Sons Garments POS.

Provides formatting functions for currency, dates, and quantities
used throughout the application. All formatting follows Pakistani business standards.
"""

from datetime import datetime
from typing import Optional


def format_currency(amount_cents: int, currency_symbol: str = "Rs.") -> str:
    """
    Format amount in cents to human-readable currency string.

    Converts integer cents to rupees with proper formatting.
    Example: 125050 -> "Rs. 1,250.50"

    Args:
        amount_cents: Amount in cents (integer).
        currency_symbol: Currency symbol prefix (default "Rs.").

    Returns:
        Formatted currency string with thousands separators.
    """
    if not isinstance(amount_cents, int):
        raise TypeError(f"Amount must be an integer (cents), got {type(amount_cents).__name__}")

    # Convert cents to rupees
    rupees = amount_cents / 100

    # Format with thousands separators and 2 decimal places
    formatted = f"{rupees:,.2f}"

    return f"{currency_symbol} {formatted}"


def format_date(date_value: str, output_format: str = "%d/%m/%Y") -> str:
    """
    Format date from ISO 8601 to display format.

    Args:
        date_value: Date string in ISO 8601 format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS).
        output_format: Desired output format (default "%d/%m/%Y").

    Returns:
        Formatted date string.

    Raises:
        ValueError: If date cannot be parsed.
    """
    if not isinstance(date_value, str):
        raise TypeError("Date must be a string")

    # Try parsing ISO 8601 formats
    formats_to_try = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
    ]

    parsed_date = None
    for fmt in formats_to_try:
        try:
            parsed_date = datetime.strptime(date_value[:26], fmt)  # Trim microseconds/timezone
            break
        except ValueError:
            continue

    if parsed_date is None:
        # Try with fromisoformat as fallback
        try:
            # Handle timezone suffix
            clean_date = date_value.replace("Z", "+00:00")
            if "+" in clean_date[10:] or "-" in clean_date[10:]:
                # Has timezone info
                parsed_date = datetime.fromisoformat(clean_date)
            else:
                parsed_date = datetime.fromisoformat(clean_date)
        except ValueError:
            raise ValueError(f"Unable to parse date: {date_value}")

    return parsed_date.strftime(output_format)


def format_quantity(quantity: int, unit: Optional[str] = None) -> str:
    """
    Format quantity with optional unit.

    Args:
        quantity: Quantity value (integer).
        unit: Optional unit suffix (e.g., "pcs", "kg", "m").

    Returns:
        Formatted quantity string.
    """
    if not isinstance(quantity, int):
        raise TypeError(f"Quantity must be an integer, got {type(quantity).__name__}")

    if quantity < 0:
        raise ValueError(f"Quantity cannot be negative: {quantity}")

    if unit:
        return f"{quantity:,} {unit}"
    return f"{quantity:,}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """
    Format percentage value.

    Args:
        value: Percentage value (e.g., 17.5 for 17.5%).
        decimals: Number of decimal places.

    Returns:
        Formatted percentage string.
    """
    if not isinstance(value, (int, float)):
        raise TypeError(f"Value must be a number, got {type(value).__name__}")

    return f"{value:.{decimals}f}%"


def format_datetime(datetime_value: str, output_format: str = "%d/%m/%Y %H:%M") -> str:
    """
    Format datetime from ISO 8601 to display format.

    Args:
        datetime_value: Datetime string in ISO 8601 format.
        output_format: Desired output format.

    Returns:
        Formatted datetime string.
    """
    return format_date(datetime_value, output_format)
