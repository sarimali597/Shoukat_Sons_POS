"""
Tests for animation utilities.

Verifies color interpolation, window fade, and toast functionality.
Note: Full GUI tests require a display; these test the pure logic functions.
"""

import pytest

from ui.animations import _interpolate_hex


class TestColorInterpolation:
    """Test hex color interpolation."""

    def test_interpolate_same_color(self) -> None:
        """Test interpolating same color returns that color."""
        result = _interpolate_hex("#FF0000", "#FF0000", 0.5)
        assert result == "#ff0000"

    def test_interpolate_start(self) -> None:
        """Test t=0 returns start color."""
        result = _interpolate_hex("#FF0000", "#00FF00", 0.0)
        assert result == "#ff0000"

    def test_interpolate_end(self) -> None:
        """Test t=1 returns end color."""
        result = _interpolate_hex("#FF0000", "#00FF00", 1.0)
        assert result == "#00ff00"

    def test_interpolate_midpoint(self) -> None:
        """Test t=0.5 returns midpoint color."""
        # Red (255,0,0) to Green (0,255,0) at t=0.5 should be (127,127,0)
        result = _interpolate_hex("#FF0000", "#00FF00", 0.5)
        assert result == "#7f7f00"

    def test_interpolate_black_to_white(self) -> None:
        """Test black to white interpolation."""
        # Black (0,0,0) to White (255,255,255) at t=0.5
        result = _interpolate_hex("#000000", "#FFFFFF", 0.5)
        assert result == "#7f7f7f"

    def test_interpolate_invalid_t_low_raises(self) -> None:
        """Test t < 0 raises assertion error."""
        with pytest.raises(AssertionError):
            _interpolate_hex("#FF0000", "#00FF00", -0.1)

    def test_interpolate_invalid_t_high_raises(self) -> None:
        """Test t > 1 raises assertion error."""
        with pytest.raises(AssertionError):
            _interpolate_hex("#FF0000", "#00FF00", 1.1)

    def test_interpolate_invalid_hex_format_raises(self) -> None:
        """Test invalid hex format raises assertion error."""
        with pytest.raises(AssertionError):
            _interpolate_hex("FF0000", "#00FF00", 0.5)  # Missing #

    def test_interpolate_short_hex_raises(self) -> None:
        """Test short hex format raises assertion error."""
        with pytest.raises(AssertionError):
            _interpolate_hex("#F00", "#00FF00", 0.5)  # Short form not supported
