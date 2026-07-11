"""
Theme configuration for Shoukat Sons Garments POS.

Provides centralized color palette, font definitions, responsive breakpoints,
and a ThemeManager class for applying themes throughout the application.
Supports light/dark mode switching with persistence.
"""

import json
from pathlib import Path
from typing import Optional, Tuple

import customtkinter as ctk

from config import DATA_DIR

# =============================================================================
# Color Palette
# =============================================================================

COLORS = {
    "light": {
        "bg": "#F5F5F5",
        "surface": "#FFFFFF",
        "primary": "#1E3A5F",
        "success": "#2E7D32",
        "warning": "#F57C00",
        "danger": "#C62828",
        "text": "#212121",
        "text_secondary": "#757575",
        "border": "#E0E0E0",
    },
    "dark": {
        "bg": "#1A1A1A",
        "surface": "#2D2D2D",
        "primary": "#4A7BA6",
        "success": "#66BB6A",
        "warning": "#FFA726",
        "danger": "#EF5350",
        "text": "#E0E0E0",
        "text_secondary": "#B0B0B0",
        "border": "#424242",
    },
}

# =============================================================================
# Font Definitions
# =============================================================================

FONTS = {
    "heading": ("Segoe UI", 20, "bold"),
    "subheading": ("Segoe UI", 14, "bold"),
    "body": ("Segoe UI", 12),
    "small": ("Segoe UI", 10),
    "mono": ("Consolas", 12),
    "button": ("Segoe UI", 12, "bold"),
}

# =============================================================================
# Responsive Breakpoints
# =============================================================================

BREAKPOINTS = {
    "compact": 1024,
    "standard": 1366,
    "wide": 1920,
}

# =============================================================================
# Settings File Path
# =============================================================================

SETTINGS_FILE = DATA_DIR / "theme_settings.json"


class ThemeManager:
    """
    Centralized theme management for the POS application.

    Manages light/dark mode, color retrieval, font access, breakpoint detection,
    and widget theming. Persists user preferences to disk.

    Attributes:
        _instance: Class-level singleton instance.
        _current_mode: Current theme mode ('light' or 'dark').
    """

    _instance: Optional["ThemeManager"] = None

    def __new__(cls) -> "ThemeManager":
        """Return the singleton ThemeManager instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize the ThemeManager with persisted settings."""
        if self._initialized:
            return

        self._current_mode = self._load_settings()
        self._initialized = True

    def _load_settings(self) -> str:
        """
        Load theme settings from disk.

        Returns:
            Theme mode string ('light' or 'dark'). Defaults to 'light'.
        """
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)
                    return data.get("mode", "light")
            except (json.JSONDecodeError, IOError):
                return "light"
        return "light"

    def _save_settings(self) -> None:
        """Save current theme settings to disk."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w") as f:
            json.dump({"mode": self._current_mode}, f)

    @property
    def current_mode(self) -> str:
        """
        Get the current theme mode.

        Returns:
            Current mode: 'light' or 'dark'.
        """
        return self._current_mode

    def toggle_mode(self) -> str:
        """
        Toggle between light and dark modes.

        Returns:
            New theme mode after toggling.
        """
        self._current_mode = "dark" if self._current_mode == "light" else "light"
        self._save_settings()
        return self._current_mode

    def set_mode(self, mode: str) -> None:
        """
        Set the theme mode explicitly.

        Args:
            mode: Theme mode ('light' or 'dark').

        Raises:
            ValueError: If mode is not 'light' or 'dark'.
        """
        assert mode in ("light", "dark"), f"Invalid mode: {mode}"
        self._current_mode = mode
        self._save_settings()

    def get_color(self, key: str, mode: Optional[str] = None) -> str:
        """
        Get a color value by key for the current or specified mode.

        Args:
            key: Color key (e.g., 'bg', 'primary', 'success').
            mode: Optional mode override. Uses current_mode if None.

        Returns:
            Hex color string.

        Raises:
            KeyError: If color key doesn't exist.
        """
        assert isinstance(key, str), f"key must be str, got {type(key)}"
        mode = mode or self._current_mode
        if mode not in COLORS:
            raise ValueError(f"Invalid mode: {mode}")
        if key not in COLORS[mode]:
            raise KeyError(f"Color key '{key}' not found")
        return COLORS[mode][key]

    def get_font(self, key: str) -> Tuple[str, int, str]:
        """
        Get a font tuple by key.

        Args:
            key: Font key (e.g., 'heading', 'body', 'button').

        Returns:
            Font tuple: (family, size, weight).

        Raises:
            KeyError: If font key doesn't exist.
        """
        assert isinstance(key, str), f"key must be str, got {type(key)}"
        if key not in FONTS:
            raise KeyError(f"Font key '{key}' not found")
        return FONTS[key]

    def get_breakpoint(self, width: int) -> str:
        """
        Determine the responsive breakpoint for a given width.

        Args:
            width: Window width in pixels.

        Returns:
            Breakpoint name: 'compact', 'standard', or 'wide'.
        """
        assert isinstance(width, int) and width > 0, f"Invalid width: {width}"
        if width < BREAKPOINTS["compact"]:
            return "compact"
        elif width < BREAKPOINTS["wide"]:
            return "standard"
        else:
            return "wide"

    def apply_to_widget(
        self,
        widget: ctk.CTkBaseClass,
        bg_key: Optional[str] = None,
        fg_key: Optional[str] = None,
        font_key: Optional[str] = None,
    ) -> None:
        """
        Apply theme colors and fonts to a CustomTkinter widget.

        Args:
            widget: The CTk widget to theme.
            bg_key: Background color key (e.g., 'bg', 'surface').
            fg_key: Foreground/text color key (e.g., 'text', 'primary').
            font_key: Font key (e.g., 'body', 'button').
        """
        assert widget is not None, "widget cannot be None"

        if bg_key:
            bg_color = self.get_color(bg_key)
            widget.configure(fg_color=bg_color)

        if fg_key:
            fg_color = self.get_color(fg_key)
            # CTk widgets use text_color for foreground
            if hasattr(widget, "configure") and "text_color" in widget.configure():
                widget.configure(text_color=fg_color)

        if font_key:
            font = self.get_font(font_key)
            if hasattr(widget, "configure") and "font" in widget.configure():
                widget.configure(font=font)


def get_theme_manager() -> ThemeManager:
    """
    Get the global ThemeManager instance.

    Returns:
        Singleton ThemeManager instance.
    """
    return ThemeManager()
