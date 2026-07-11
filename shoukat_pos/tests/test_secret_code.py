"""
Tests for secret code encoding/decoding.

Verifies price-to-code and code-to-price conversion with default
and custom mappings. Used to hide cost prices from cashiers.
"""

import pytest

from utils.secret_code import (
    SecretCodeError,
    decode_price,
    encode_price,
    get_reverse_mapping,
    validate_code,
)


class TestPriceEncoding:
    """Test price to secret code encoding."""

    def test_encode_basic_price(self):
        """Test encoding basic price values."""
        # 125050 -> RKMLML with default map (1->R, 2->K, 5->M, 0->L, 5->M, 0->L)
        assert encode_price(125050) == "RKMLML"
        # 100000 -> RLLLLL
        assert encode_price(100000) == "RLLLLL"
        # 50000 -> MLLLL
        assert encode_price(50000) == "MLLLL"

    def test_encode_zero(self):
        """Test encoding zero price."""
        assert encode_price(0) == "L"

    def test_encode_large_price(self):
        """Test encoding large price values."""
        # 999999 -> WWWWWW
        assert encode_price(999999) == "WWWWWW"
        # 1000000 -> RL... (7 digits)
        assert encode_price(1000000) == "RLLLLLL"

    def test_encode_negative_raises(self):
        """Test that negative price raises SecretCodeError."""
        with pytest.raises(SecretCodeError):
            encode_price(-100)

    def test_encode_non_integer_raises(self):
        """Test that non-integer price raises SecretCodeError."""
        with pytest.raises(SecretCodeError):
            encode_price(100.50)
        with pytest.raises(SecretCodeError):
            encode_price("100")

    def test_encode_with_custom_mapping(self):
        """Test encoding with custom digit mapping."""
        custom_map = {
            "0": "A",
            "1": "B",
            "2": "C",
            "3": "D",
            "4": "E",
            "5": "F",
            "6": "G",
            "7": "H",
            "8": "I",
            "9": "J",
        }
        # 125050 -> BCFABA with custom map (1->B, 2->C, 5->F, 0->A, 5->F, 0->A)
        assert encode_price(125050, mapping=custom_map) == "BCFAFA"


class TestPriceDecoding:
    """Test secret code to price decoding."""

    def test_decode_basic_code(self):
        """Test decoding basic codes."""
        # RKMLML -> 125050 with default map (R->1, K->2, M->5, L->0, M->5, L->0)
        assert decode_price("RKMLML") == 125050
        # RLLLLL -> 100000
        assert decode_price("RLLLLL") == 100000
        # MLLLL -> 50000
        assert decode_price("MLLLL") == 50000

    def test_decode_single_digit(self):
        """Test decoding single digit code."""
        assert decode_price("L") == 0
        assert decode_price("R") == 1

    def test_decode_case_insensitive(self):
        """Test that decoding is case insensitive."""
        assert decode_price("rkmlml") == 125050
        assert decode_price("RkMlMl") == 125050

    def test_decode_invalid_character_raises(self):
        """Test that invalid character raises SecretCodeError."""
        with pytest.raises(SecretCodeError):
            decode_price("XYZ")  # X not in default map
        with pytest.raises(SecretCodeError):
            decode_price("ABC")  # A, B, C not in default map

    def test_decode_empty_code_raises(self):
        """Test that empty code raises SecretCodeError."""
        with pytest.raises(SecretCodeError):
            decode_price("")

    def test_decode_non_string_raises(self):
        """Test that non-string code raises SecretCodeError."""
        with pytest.raises(SecretCodeError):
            decode_price(123)

    def test_decode_with_custom_mapping(self):
        """Test decoding with custom digit mapping."""
        custom_map = {
            "0": "A",
            "1": "B",
            "2": "C",
            "3": "D",
            "4": "E",
            "5": "F",
            "6": "G",
            "7": "H",
            "8": "I",
            "9": "J",
        }
        # BCFAFA -> 125050 with custom map (B->1, C->2, F->5, A->0, F->5, A->0)
        assert decode_price("BCFAFA", mapping=custom_map) == 125050


class TestEncodeDecodeRoundtrip:
    """Test encoding then decoding returns original value."""

    def test_roundtrip_basic(self):
        """Test basic roundtrip."""
        original = 125050
        encoded = encode_price(original)
        decoded = decode_price(encoded)
        assert decoded == original

    def test_roundtrip_various_values(self):
        """Test roundtrip with various values."""
        test_values = [0, 1, 100, 10000, 50000, 100000, 999999, 1000000]
        for value in test_values:
            encoded = encode_price(value)
            decoded = decode_price(encoded)
            assert decoded == value

    def test_roundtrip_custom_mapping(self):
        """Test roundtrip with custom mapping."""
        custom_map = {str(i): chr(ord("A") + i) for i in range(10)}
        original = 123456
        encoded = encode_price(original, mapping=custom_map)
        decoded = decode_price(encoded, mapping=custom_map)
        assert decoded == original


class TestCodeValidation:
    """Test code validation function."""

    def test_valid_code(self):
        """Test validating valid codes."""
        assert validate_code("RKMLMR") is True
        assert validate_code("RLLLLL") is True
        assert validate_code("MLLLL") is True

    def test_valid_code_case_insensitive(self):
        """Test that validation is case insensitive."""
        assert validate_code("rkmlmr") is True
        assert validate_code("RkMlMr") is True

    def test_invalid_code_raises(self):
        """Test that invalid code raises SecretCodeError."""
        with pytest.raises(SecretCodeError):
            validate_code("ABC")  # A, B, C not in default map
        with pytest.raises(SecretCodeError):
            validate_code("XZ")  # X not in default map

    def test_empty_code_raises(self):
        """Test that empty code raises SecretCodeError."""
        with pytest.raises(SecretCodeError):
            validate_code("")

    def test_non_string_raises(self):
        """Test that non-string code raises SecretCodeError."""
        with pytest.raises(SecretCodeError):
            validate_code(123)

    def test_validate_with_custom_mapping(self):
        """Test validation with custom mapping."""
        custom_map = {str(i): chr(ord("A") + i) for i in range(10)}
        assert validate_code("ABCDEF", mapping=custom_map) is True
        with pytest.raises(SecretCodeError):
            validate_code("RKMLMR", mapping=custom_map)  # Not valid in custom map


class TestReverseMapping:
    """Test reverse mapping utility."""

    def test_get_default_reverse_mapping(self):
        """Test getting default reverse mapping."""
        reverse = get_reverse_mapping()
        # L -> 0, R -> 1, etc.
        assert reverse["L"] == "0"
        assert reverse["R"] == "1"
        assert reverse["K"] == "2"
        assert reverse["W"] == "9"

    def test_get_custom_reverse_mapping(self):
        """Test getting custom reverse mapping."""
        custom_map = {str(i): chr(ord("A") + i) for i in range(10)}
        reverse = get_reverse_mapping(mapping=custom_map)
        assert reverse["A"] == "0"
        assert reverse["B"] == "1"
        assert reverse["J"] == "9"
