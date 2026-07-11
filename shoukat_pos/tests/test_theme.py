"""
Tests for ThemeManager and theme functionality.

Verifies mode switching, color retrieval, font access, breakpoint detection,
and settings persistence.
"""

import json
import os
from pathlib import Path

import pytest

from ui.theme import (
    BREAKPOINTS,
    COLORS,
    FONTS,
    SETTINGS_FILE,
    ThemeManager,
    get_theme_manager,
)


class TestThemeManagerSingleton:
    """Test ThemeManager singleton behavior."""

    def test_singleton_returns_same_instance(self) -> None:
        """Test that ThemeManager returns the same instance."""
        # Reset singleton state
        ThemeManager._instance = None
        
        tm1 = ThemeManager()
        tm2 = ThemeManager()
        
        assert tm1 is tm2

    def test_get_theme_manager_helper(self) -> None:
        """Test the get_theme_manager helper function."""
        ThemeManager._instance = None
        
        tm = get_theme_manager()
        assert isinstance(tm, ThemeManager)
        assert tm is get_theme_manager()


class TestThemeManagerMode:
    """Test theme mode switching."""

    def test_default_mode_is_light(self, temp_settings_file: Path) -> None:
        """Test that default mode is light when no settings exist."""
        ThemeManager._instance = None
        
        tm = ThemeManager()
        assert tm.current_mode == "light"

    def test_toggle_mode_switches(self, temp_settings_file: Path) -> None:
        """Test that toggle_mode switches between light and dark."""
        ThemeManager._instance = None
        
        tm = ThemeManager()
        assert tm.current_mode == "light"
        
        new_mode = tm.toggle_mode()
        assert new_mode == "dark"
        assert tm.current_mode == "dark"
        
        new_mode = tm.toggle_mode()
        assert new_mode == "light"
        assert tm.current_mode == "light"

    def test_set_mode_explicitly(self, temp_settings_file: Path) -> None:
        """Test setting mode explicitly."""
        ThemeManager._instance = None
        
        tm = ThemeManager()
        tm.set_mode("dark")
        assert tm.current_mode == "dark"
        
        tm.set_mode("light")
        assert tm.current_mode == "light"

    def test_set_mode_invalid_raises(self, temp_settings_file: Path) -> None:
        """Test that invalid mode raises assertion error."""
        ThemeManager._instance = None
        
        tm = ThemeManager()
        with pytest.raises(AssertionError):
            tm.set_mode("invalid")


class TestThemeManagerColors:
    """Test color retrieval."""

    def test_get_color_light_mode(self, temp_settings_file: Path) -> None:
        """Test getting colors in light mode."""
        ThemeManager._instance = None
        
        tm = ThemeManager()
        assert tm.get_color("bg") == COLORS["light"]["bg"]
        assert tm.get_color("primary") == COLORS["light"]["primary"]

    def test_get_color_dark_mode(self, temp_settings_file: Path) -> None:
        """Test getting colors in dark mode."""
        ThemeManager._instance = None
        
        tm = ThemeManager()
        tm.set_mode("dark")
        assert tm.get_color("bg") == COLORS["dark"]["bg"]
        assert tm.get_color("primary") == COLORS["dark"]["primary"]

    def test_get_color_with_mode_override(self, temp_settings_file: Path) -> None:
        """Test getting color with explicit mode override."""
        ThemeManager._instance = None
        
        tm = ThemeManager()
        # In light mode, but request dark color
        assert tm.get_color("bg", mode="dark") == COLORS["dark"]["bg"]

    def test_get_color_invalid_key_raises(self, temp_settings_file: Path) -> None:
        """Test that invalid color key raises KeyError."""
        ThemeManager._instance = None
        
        tm = ThemeManager()
        with pytest.raises(KeyError):
            tm.get_color("nonexistent")

    def test_get_color_invalid_mode_raises(self, temp_settings_file: Path) -> None:
        """Test that invalid mode raises ValueError."""
        ThemeManager._instance = None
        
        tm = ThemeManager()
        with pytest.raises(ValueError):
            tm.get_color("bg", mode="invalid")


class TestThemeManagerFonts:
    """Test font retrieval."""

    def test_get_font_heading(self, temp_settings_file: Path) -> None:
        """Test getting heading font."""
        ThemeManager._instance = None
        
        tm = ThemeManager()
        font = tm.get_font("heading")
        assert font == FONTS["heading"]
        assert len(font) == 3  # (family, size, weight)

    def test_get_font_body(self, temp_settings_file: Path) -> None:
        """Test getting body font."""
        ThemeManager._instance = None
        
        tm = ThemeManager()
        font = tm.get_font("body")
        assert font == FONTS["body"]

    def test_get_font_invalid_key_raises(self, temp_settings_file: Path) -> None:
        """Test that invalid font key raises KeyError."""
        ThemeManager._instance = None
        
        tm = ThemeManager()
        with pytest.raises(KeyError):
            tm.get_font("nonexistent")


class TestThemeManagerBreakpoints:
    """Test breakpoint detection."""

    def test_breakpoint_compact(self, temp_settings_file: Path) -> None:
        """Test compact breakpoint detection."""
        ThemeManager._instance = None
        
        tm = ThemeManager()
        assert tm.get_breakpoint(800) == "compact"
        assert tm.get_breakpoint(1023) == "compact"

    def test_breakpoint_standard(self, temp_settings_file: Path) -> None:
        """Test standard breakpoint detection."""
        ThemeManager._instance = None
        
        tm = ThemeManager()
        assert tm.get_breakpoint(1024) == "standard"
        assert tm.get_breakpoint(1366) == "standard"
        assert tm.get_breakpoint(1919) == "standard"

    def test_breakpoint_wide(self, temp_settings_file: Path) -> None:
        """Test wide breakpoint detection."""
        ThemeManager._instance = None
        
        tm = ThemeManager()
        assert tm.get_breakpoint(1920) == "wide"
        assert tm.get_breakpoint(2560) == "wide"

    def test_breakpoint_invalid_width_raises(self, temp_settings_file: Path) -> None:
        """Test that invalid width raises assertion error."""
        ThemeManager._instance = None
        
        tm = ThemeManager()
        with pytest.raises(AssertionError):
            tm.get_breakpoint(0)
        with pytest.raises(AssertionError):
            tm.get_breakpoint(-100)


class TestThemeManagerPersistence:
    """Test settings persistence."""

    def test_settings_persisted_to_file(self, temp_settings_file: Path) -> None:
        """Test that mode changes are persisted to file."""
        ThemeManager._instance = None
        
        # Import theme module to modify SETTINGS_FILE
        from ui import theme
        
        # Set temp settings file
        temp_file = temp_settings_file.parent / "theme_test_settings.json"
        original = theme.SETTINGS_FILE
        theme.SETTINGS_FILE = temp_file
        
        try:
            tm = ThemeManager()
            tm.set_mode("dark")
            
            # Verify file was created
            assert temp_file.exists()
            
            # Verify content
            with open(temp_file, "r") as f:
                data = json.load(f)
            assert data["mode"] == "dark"
        finally:
            # Restore original
            theme.SETTINGS_FILE = original
            if temp_file.exists():
                temp_file.unlink()

    def test_settings_loaded_on_init(self, temp_settings_file: Path) -> None:
        """Test that settings are loaded on initialization."""
        from ui import theme
        
        # Create settings file with dark mode
        temp_file = temp_settings_file.parent / "theme_test_settings2.json"
        with open(temp_file, "w") as f:
            json.dump({"mode": "dark"}, f)
        
        original = theme.SETTINGS_FILE
        theme.SETTINGS_FILE = temp_file
        
        try:
            ThemeManager._instance = None
            
            tm = ThemeManager()
            assert tm.current_mode == "dark"
        finally:
            # Restore original
            theme.SETTINGS_FILE = original
            if temp_file.exists():
                temp_file.unlink()
