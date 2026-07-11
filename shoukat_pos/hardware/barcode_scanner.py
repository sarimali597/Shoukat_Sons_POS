"""
Barcode scanner handler for Shoukat Sons Garments POS.

Distinguishes barcode scanner input from manual typing using inter-keystroke
timing analysis. Scanner bursts are typically <30ms between keystrokes,
while human typing is >100ms.
"""

import time
from typing import Callable, Optional

try:
    import customtkinter as ctk

    CTk_AVAILABLE = True
except ImportError:
    CTk_AVAILABLE = False


class ScannerAwareEntry:
    """
    Distinguishes a barcode-scanner burst from manual typing on the same
    Entry widget using inter-keystroke timing.

    Barcode scanners emulate keyboard input but send characters in rapid
    bursts (<30ms between keystrokes). Human typing is much slower (>100ms).
    This class buffers keystrokes and triggers a callback when a complete
    scan is detected (Enter key or timeout).
    """

    SCAN_THRESHOLD_MS = 30  # Max ms between keystrokes for scanner detection

    def __init__(
        self,
        entry_widget: "ctk.CTkEntry",
        on_scan_complete: Callable[[str], None],
    ) -> None:
        """
        Initialize scanner-aware entry wrapper.

        Args:
            entry_widget: CustomTkinter Entry widget to monitor.
            on_scan_complete: Callback function invoked when scan completes.
                Receives the scanned barcode string as argument.
        """
        assert entry_widget is not None
        assert callable(on_scan_complete)

        if not CTk_AVAILABLE:
            raise RuntimeError("customtkinter not available")

        self.entry = entry_widget
        self.on_scan_complete = on_scan_complete
        self._last_key_time = 0.0
        self._buffer = ""

        self.entry.bind("<Key>", self._on_key)

    def _on_key(self, event) -> None:
        """
        Handle key press events.

        Args:
            event: Tkinter key event.
        """
        now = time.monotonic() * 1000  # Convert to milliseconds
        gap = now - self._last_key_time
        self._last_key_time = now

        # Enter key signals end of scan
        if event.keysym == "Return":
            if self._buffer:
                self.on_scan_complete(self._buffer)
            self._buffer = ""
            return

        # Gap too long -- treat as fresh run of keys
        if gap > self.SCAN_THRESHOLD_MS:
            self._buffer = ""

        # Accumulate printable characters
        if event.char and event.char.isprintable():
            self._buffer += event.char

    def clear_buffer(self) -> None:
        """Clear the internal buffer without triggering callback."""
        self._buffer = ""

    def get_buffer(self) -> str:
        """
        Get current buffer content.

        Returns:
            Current buffered characters.
        """
        return self._buffer
