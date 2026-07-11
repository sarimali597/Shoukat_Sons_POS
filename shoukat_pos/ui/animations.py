"""
Animation utilities for Shoukat Sons Garments POS.

Provides window fade transitions, per-widget color interpolation, slide animations,
pulse effects, and a toast notification system. Note: Tkinter alpha transparency
only works at the toplevel window level, not on individual widgets.
"""

import tkinter as tk
from typing import Callable, List, Optional, Tuple

import customtkinter as ctk


def _interpolate_hex(start_hex: str, end_hex: str, t: float) -> str:
    """
    Interpolate between two hex colors.

    Args:
        start_hex: Starting hex color (e.g., '#FF0000').
        end_hex: Ending hex color (e.g., '#00FF00').
        t: Interpolation factor (0.0 to 1.0).

    Returns:
        Interpolated hex color string.
    """
    assert 0.0 <= t <= 1.0, f"t must be between 0 and 1, got {t}"
    assert len(start_hex) == 7 and start_hex.startswith("#")
    assert len(end_hex) == 7 and end_hex.startswith("#")

    s = tuple(int(start_hex[i : i + 2], 16) for i in (1, 3, 5))
    e = tuple(int(end_hex[i : i + 2], 16) for i in (1, 3, 5))
    mixed = tuple(int(s[i] + (e[i] - s[i]) * t) for i in range(3))
    return "#%02x%02x%02x" % mixed


def fade_in_window(window: tk.Tk, duration_ms: int = 150, steps: int = 15) -> None:
    """
    Fade in a top-level window using alpha transparency.

    Only works on toplevel windows, not individual widgets.

    Args:
        window: The Tk/Toplevel window to fade in.
        duration_ms: Total animation duration in milliseconds.
        steps: Number of animation steps.
    """
    assert window is not None, "window cannot be None"
    assert duration_ms > 0, "duration_ms must be positive"
    assert steps > 0, "steps must be positive"

    window.attributes("-alpha", 0.0)
    delay = max(1, duration_ms // steps)

    def _step(i: int = 0) -> None:
        window.attributes("-alpha", min(1.0, i / steps))
        if i < steps:
            window.after(delay, _step, i + 1)

    _step()


def fade_out_window(
    window: tk.Tk, duration_ms: int = 150, steps: int = 15, callback: Optional[Callable] = None
) -> None:
    """
    Fade out a top-level window using alpha transparency.

    Args:
        window: The Tk/Toplevel window to fade out.
        duration_ms: Total animation duration in milliseconds.
        steps: Number of animation steps.
        callback: Optional function to call after fade completes.
    """
    assert window is not None, "window cannot be None"
    assert duration_ms > 0, "duration_ms must be positive"
    assert steps > 0, "steps must be positive"

    delay = max(1, duration_ms // steps)

    def _step(i: int = 0) -> None:
        window.attributes("-alpha", 1.0 - (i / steps))
        if i < steps:
            window.after(delay, _step, i + 1)
        elif callback:
            callback()

    _step()


def color_fade_in(
    widget: ctk.CTkBaseClass,
    from_color: str,
    to_color: str,
    duration_ms: int = 150,
    steps: int = 15,
) -> None:
    """
    Fade a widget's background color from one color to another.

    Uses RGB interpolation since CTk widgets don't have alpha channels.

    Args:
        widget: The CustomTkinter widget to animate.
        from_color: Starting hex color.
        to_color: Ending hex color.
        duration_ms: Total animation duration in milliseconds.
        steps: Number of animation steps.
    """
    assert widget is not None, "widget cannot be None"
    assert duration_ms > 0, "duration_ms must be positive"
    assert steps > 0, "steps must be positive"

    delay = max(1, duration_ms // steps)

    def _step(i: int = 0) -> None:
        t = i / steps
        color = _interpolate_hex(from_color, to_color, t)
        widget.configure(fg_color=color)
        if i < steps:
            window = widget.winfo_toplevel()
            window.after(delay, _step, i + 1)

    _step()


def slide_in(
    widget: ctk.CTkBaseClass,
    from_x: int,
    to_x: int,
    duration_ms: int = 200,
    steps: int = 20,
) -> None:
    """
    Slide a widget horizontally with ease-out cubic easing.

    Args:
        widget: The widget to animate.
        from_x: Starting x position.
        to_x: Ending x position.
        duration_ms: Total animation duration in milliseconds.
        steps: Number of animation steps.
    """
    assert widget is not None, "widget cannot be None"
    assert duration_ms > 0, "duration_ms must be positive"
    assert steps > 0, "steps must be positive"

    delay = max(1, duration_ms // steps)

    def _step(i: int = 0) -> None:
        t = i / steps
        t = 1 - (1 - t) ** 3  # ease-out cubic
        x = int(from_x + (to_x - from_x) * t)
        widget.place(x=x)
        if i < steps:
            window = widget.winfo_toplevel()
            window.after(delay, _step, i + 1)

    _step()


def pulse_animation(
    widget: ctk.CTkBaseClass,
    color1: str,
    color2: str,
    cycles: int = 3,
    duration_per_cycle_ms: int = 300,
    steps: int = 15,
) -> None:
    """
    Pulse a widget's background color between two colors.

    Args:
        widget: The widget to animate.
        color1: First hex color.
        color2: Second hex color.
        cycles: Number of pulse cycles.
        duration_per_cycle_ms: Duration of one complete cycle.
        steps: Number of steps per half-cycle.
    """
    assert widget is not None, "widget cannot be None"
    assert cycles > 0, "cycles must be positive"
    assert duration_per_cycle_ms > 0, "duration_per_cycle_ms must be positive"

    delay = max(1, (duration_per_cycle_ms // 2) // steps)

    def _pulse_cycle(cycle: int = 0, going_forward: bool = True, step: int = 0) -> None:
        if cycle >= cycles:
            return

        t = step / steps
        if going_forward:
            color = _interpolate_hex(color1, color2, t)
        else:
            color = _interpolate_hex(color2, color1, t)

        widget.configure(fg_color=color)

        if step < steps:
            window = widget.winfo_toplevel()
            window.after(delay, _pulse_cycle, cycle, going_forward, step + 1)
        elif going_forward:
            window = widget.winfo_toplevel()
            window.after(delay, _pulse_cycle, cycle, False, 0)
        else:
            window = widget.winfo_toplevel()
            window.after(delay, _pulse_cycle, cycle + 1, True, 0)

    _pulse_cycle()


class Toast:
    """
    Non-blocking toast notification system.

    Displays temporary notifications that slide in from top-right,
    auto-dismiss after a duration, and stack vertically.

    Class Attributes:
        _toasts: List of active toast windows.
    """

    _toasts: List["Toast"] = []

    def __init__(
        self,
        parent: tk.Tk,
        message: str,
        toast_type: str = "info",
        duration_ms: int = 3000,
    ) -> None:
        """
        Create a toast notification.

        Args:
            parent: Parent window.
            message: Message text to display.
            toast_type: Type of toast ('success', 'warning', 'error', 'info').
            duration_ms: Auto-dismiss duration in milliseconds.
        """
        assert parent is not None, "parent cannot be None"
        assert isinstance(message, str), "message must be string"
        assert toast_type in ("success", "warning", "error", "info"), f"Invalid type: {toast_type}"
        assert duration_ms > 0, "duration_ms must be positive"

        self.parent = parent
        self.message = message
        self.toast_type = toast_type
        self.duration_ms = duration_ms
        self.window: Optional[ctk.CTkToplevel] = None
        self.label: Optional[ctk.CTkLabel] = None

        self._colors = {
            "success": ("#2E7D32", "#FFFFFF"),
            "warning": ("#F57C00", "#FFFFFF"),
            "error": ("#C62828", "#FFFFFF"),
            "info": ("#1E3A5F", "#FFFFFF"),
        }

    def show(self) -> None:
        """Display the toast notification."""
        bg_color, fg_color = self._colors[self.toast_type]

        # Create transparent toplevel
        self.window = ctk.CTkToplevel(self.parent)
        self.window.withdraw()  # Hide initially
        self.window.overrideredirect(True)  # No window decorations

        # Calculate position (top-right, stacked)
        toast_index = len(Toast._toasts)
        padding = 20
        toast_height = 60
        toast_width = 300

        # Get parent window geometry
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()

        x = parent_x + parent_width - toast_width - padding
        y = parent_y + padding + (toast_index * (toast_height + 10))

        self.window.geometry(f"{toast_width}x{toast_height}+{x}+{y}")
        self.window.attributes("-alpha", 0.0)
        self.window.configure(fg_color=bg_color)

        # Add label
        self.label = ctk.CTkLabel(
            self.window,
            text=self.message,
            font=("Segoe UI", 12),
            text_color=fg_color,
            wraplength=toast_width - 40,
        )
        self.label.pack(expand=True, fill="both", padx=20, pady=10)

        # Show window
        self.window.deiconify()
        fade_in_window(self.window, duration_ms=150)

        # Schedule auto-dismiss
        self.window.after(self.duration_ms, self.dismiss)

        # Track this toast
        Toast._toasts.append(self)

    def dismiss(self) -> None:
        """Dismiss the toast notification."""
        if self.window is None:
            return

        # Fade out
        fade_out_window(
            self.window, duration_ms=150, callback=self._destroy_window
        )

    def _destroy_window(self) -> None:
        """Destroy the toast window and remove from tracking list."""
        if self.window:
            try:
                self.window.destroy()
            except Exception:
                pass
            self.window = None

        if self in Toast._toasts:
            Toast._toasts.remove(self)
            # Re-position remaining toasts
            self._reposition_toasts()

    def _reposition_toasts(self) -> None:
        """Re-position all active toasts after one is dismissed."""
        padding = 20
        toast_height = 60
        toast_width = 300

        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()

        for i, toast in enumerate(Toast._toasts):
            if toast.window:
                x = parent_x + parent_width - toast_width - padding
                y = parent_y + padding + (i * (toast_height + 10))
                toast.window.geometry(f"+{x}+{y}")

    @classmethod
    def show(cls, parent: tk.Tk, message: str, toast_type: str = "success", duration_ms: int = 3000) -> "Toast":
        """
        Static method to create and show a toast notification.

        Args:
            parent: Parent window.
            message: Message text to display.
            toast_type: Type of toast ('success', 'warning', 'error', 'info').
            duration_ms: Auto-dismiss duration in milliseconds.

        Returns:
            The created Toast instance.
        """
        toast = cls(parent, message, toast_type, duration_ms)
        toast.show()
        return toast
