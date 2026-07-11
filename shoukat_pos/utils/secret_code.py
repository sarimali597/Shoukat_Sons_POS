"""
Secret code encoding/decoding for Shoukat Sons Garments POS.

Provides functions to encode purchase prices into secret codes
and decode them back. Used to hide cost prices from cashiers.
"""

from typing import Dict, Optional


class SecretCodeError(Exception):
    """Raised when secret code encoding/decoding fails."""

    pass


DEFAULT_CODE_MAP: Dict[str, str] = {
    "0": "L",
    "1": "R",
    "2": "K",
    "3": "B",
    "4": "S",
    "5": "M",
    "6": "N",
    "7": "T",
    "8": "H",
    "9": "W",
}


def encode_price(price_cents: int, mapping: Optional[Dict[str, str]] = None) -> str:
    """
    Encode a price in cents to a secret code string.

    Each digit is replaced with its mapped character.

    Args:
        price_cents: Price value in cents (integer).
        mapping: Optional custom digit-to-character mapping.
                 Uses DEFAULT_CODE_MAP if not provided.

    Returns:
        Encoded secret code string.

    Raises:
        SecretCodeError: If price is invalid or encoding fails.

    Example:
        >>> encode_price(125050)  # With default map
        'RKMLMR'
    """
    if not isinstance(price_cents, int):
        raise SecretCodeError(f"Price must be an integer, got {type(price_cents).__name__}")

    if price_cents < 0:
        raise SecretCodeError(f"Price cannot be negative: {price_cents}")

    code_map = mapping if mapping is not None else DEFAULT_CODE_MAP

    price_str = str(price_cents)
    encoded_chars = []

    for digit in price_str:
        if digit not in code_map:
            raise SecretCodeError(f"No mapping for digit: {digit}")
        encoded_chars.append(code_map[digit])

    return "".join(encoded_chars)


def decode_price(code: str, mapping: Optional[Dict[str, str]] = None) -> int:
    """
    Decode a secret code string back to price in cents.

    Args:
        code: Secret code string to decode.
        mapping: Optional custom digit-to-character mapping.
                 Uses DEFAULT_CODE_MAP if not provided.

    Returns:
        Decoded price in cents.

    Raises:
        SecretCodeError: If code is invalid or decoding fails.

    Example:
        >>> decode_price("RKMLMR")  # With default map
        125050
    """
    if not isinstance(code, str):
        raise SecretCodeError(f"Code must be a string, got {type(code).__name__}")

    if not code:
        raise SecretCodeError("Code cannot be empty")

    code_map = mapping if mapping is not None else DEFAULT_CODE_MAP

    # Build reverse mapping: character -> digit
    reverse_map = {v: k for k, v in code_map.items()}

    decoded_digits = []
    for char in code.upper():
        if char not in reverse_map:
            raise SecretCodeError(f"Invalid character in code: {char}")
        decoded_digits.append(reverse_map[char])

    decoded_str = "".join(decoded_digits)

    try:
        return int(decoded_str)
    except ValueError:
        raise SecretCodeError(f"Failed to decode code: {code}")


def validate_code(code: str, mapping: Optional[Dict[str, str]] = None) -> bool:
    """
    Validate that a code string can be decoded.

    Args:
        code: Code string to validate.
        mapping: Optional custom mapping to validate against.

    Returns:
        True if code is valid.

    Raises:
        SecretCodeError: If code is invalid.
    """
    if not isinstance(code, str):
        raise SecretCodeError(f"Code must be a string, got {type(code).__name__}")

    if not code:
        raise SecretCodeError("Code cannot be empty")

    code_map = mapping if mapping is not None else DEFAULT_CODE_MAP
    reverse_map = {v: k for k, v in code_map.items()}

    for char in code.upper():
        if char not in reverse_map:
            raise SecretCodeError(f"Invalid character '{char}' - not in mapping")

    return True


def get_reverse_mapping(mapping: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Get the reverse mapping (character -> digit) for a given mapping.

    Args:
        mapping: Optional custom digit-to-character mapping.

    Returns:
        Reverse mapping dictionary.
    """
    code_map = mapping if mapping is not None else DEFAULT_CODE_MAP
    return {v: k for k, v in code_map.items()}
