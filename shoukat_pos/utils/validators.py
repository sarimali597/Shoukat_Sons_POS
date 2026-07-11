"""
Validators for Shoukat Sons Garments POS.

Provides validation functions for phone numbers, prices, emails, and serial numbers
used throughout the application. All validations follow Pakistani business standards.
"""

import re
from typing import Optional


class ValidationError(Exception):
    """Raised when validation fails."""

    pass


def validate_phone(phone: str) -> bool:
    """
    Validate Pakistani phone number format.

    Accepts formats:
    - 03XXXXXXXXX (11 digits starting with 03)
    - +923XXXXXXXXX (international format)
    - 3XXXXXXXXX (without leading zero)

    Args:
        phone: Phone number string to validate.

    Returns:
        True if phone number is valid Pakistani format.

    Raises:
        ValidationError: If phone number format is invalid.
    """
    if not isinstance(phone, str):
        raise ValidationError("Phone must be a string")

    phone = phone.strip()

    # Remove spaces and dashes
    phone = re.sub(r"[\s\-]", "", phone)

    # Pakistani mobile patterns
    patterns = [
        r"^03[0-9]{9}$",  # 03XXXXXXXXX
        r"^\+923[0-9]{9}$",  # +923XXXXXXXXX
        r"^3[0-9]{9}$",  # 3XXXXXXXXX
    ]

    for pattern in patterns:
        if re.match(pattern, phone):
            return True

    raise ValidationError(
        f"Invalid Pakistani phone number: {phone}. "
        "Expected format: 03XXXXXXXXX or +923XXXXXXXXX"
    )


def validate_price(price: int, allow_zero: bool = False) -> bool:
    """
    Validate price as positive integer (cents).

    All monetary values are stored as INTEGER cents, never FLOAT.

    Args:
        price: Price value in cents to validate.
        allow_zero: Whether zero price is acceptable.

    Returns:
        True if price is valid.

    Raises:
        ValidationError: If price is not a positive integer.
    """
    if not isinstance(price, int):
        raise ValidationError(f"Price must be an integer (cents), got {type(price).__name__}")

    if allow_zero:
        if price < 0:
            raise ValidationError(f"Price cannot be negative: {price}")
    else:
        if price <= 0:
            raise ValidationError(f"Price must be positive, got {price}")

    return True


def validate_email(email: Optional[str]) -> bool:
    """
    Validate email address format (optional field).

    Args:
        email: Email address to validate, or None.

    Returns:
        True if email is valid or None.

    Raises:
        ValidationError: If email format is invalid.
    """
    if email is None or email.strip() == "":
        return True  # Email is optional

    if not isinstance(email, str):
        raise ValidationError("Email must be a string")

    email = email.strip()

    # Basic email pattern
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    if re.match(pattern, email):
        return True

    raise ValidationError(f"Invalid email format: {email}")


def validate_serial(serial: str) -> bool:
    """
    Validate serial number format (SSG-XXX-NNN).

    Format: SSG-[3 letters]-[3 digits]
    Example: SSG-TSH-001

    Args:
        serial: Serial number string to validate.

    Returns:
        True if serial number format is valid.

    Raises:
        ValidationError: If serial number format is invalid.
    """
    if not isinstance(serial, str):
        raise ValidationError("Serial number must be a string")

    serial = serial.strip().upper()

    # Pattern: SSG-XXX-NNN
    pattern = r"^SSG-[A-Z]{3}-\d{3}$"

    if re.match(pattern, serial):
        return True

    raise ValidationError(
        f"Invalid serial number format: {serial}. "
        "Expected format: SSG-XXX-NNN (e.g., SSG-TSH-001)"
    )


def normalize_phone(phone: str) -> str:
    """
    Normalize phone number to standard 03XXXXXXXXX format.

    Args:
        phone: Phone number in any valid Pakistani format.

    Returns:
        Normalized phone number as 03XXXXXXXXX.
    """
    if not isinstance(phone, str):
        raise ValidationError("Phone must be a string")

    phone = phone.strip()
    phone = re.sub(r"[\s\-]", "", phone)

    # Convert international to local format
    if phone.startswith("+92"):
        phone = "0" + phone[3:]

    # Add leading zero if missing
    if phone.startswith("3") and len(phone) == 10:
        phone = "0" + phone

    return phone
