"""
Password dialog for secure actions.

Reusable modal password prompt with show/hide toggle.
Used for edit product protection, settings access, void sale confirmation.
"""

import tkinter as tk
from typing import Optional, Tuple

import customtkinter as ctk

from ui.theme import get_theme_manager


class PasswordDialog(ctk.CTkToplevel):
    """
    Modal password prompt dialog.

    Returns (confirmed: bool, password: str) tuple.
    """

    def __init__(self, parent: ctk.CTkBaseClass, title: str = "Enter Password") -> None:
        """
        Initialize the password dialog.

        Args:
            parent: Parent window.
            title: Dialog title.
        """
        super().__init__(parent)
        assert parent is not None, "parent cannot be None"

        self._theme = get_theme_manager()
        self.result: Tuple[bool, str] = (False, "")

        # Configure dialog
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()  # Make modal

        # Center on parent
        self.geometry("350x180")
        self._center_on_parent(parent)

        # Create UI
        self._create_ui()

        # Bind enter key
        self.bind("<Return>", lambda e: self._on_confirm())
        self.bind("<Escape>", lambda e: self._on_cancel())

    def _center_on_parent(self, parent: ctk.CTkBaseClass) -> None:
        """Center dialog on parent window."""
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()

        x = parent_x + (parent_width - 350) // 2
        y = parent_y + (parent_height - 180) // 2

        self.geometry(f"+{x}+{y}")

    def _create_ui(self) -> None:
        """Create dialog UI elements."""
        # Label
        label = ctk.CTkLabel(
            self,
            text="Please enter your password:",
            font=self._theme.get_font("body"),
        )
        label.pack(pady=(20, 10))

        # Password entry
        self.password_entry = ctk.CTkEntry(
            self,
            show="•",
            width=280,
            height=40,
            font=self._theme.get_font("body"),
        )
        self.password_entry.pack(pady=10)

        # Show/hide toggle
        self.show_var = tk.BooleanVar(value=False)
        self.show_check = ctk.CTkCheckBox(
            self,
            text="Show password",
            variable=self.show_var,
            command=self._toggle_password_visibility,
            font=self._theme.get_font("small"),
        )
        self.show_check.pack(pady=(0, 20))

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack()

        self.cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=self._on_cancel,
            width=100,
            height=36,
            font=self._theme.get_font("button"),
        )
        self.cancel_btn.pack(side="left", padx=10)

        self.confirm_btn = ctk.CTkButton(
            btn_frame,
            text="Confirm",
            command=self._on_confirm,
            width=100,
            height=36,
            font=self._theme.get_font("button"),
        )
        self.confirm_btn.pack(side="left", padx=10)

        # Focus password entry
        self.password_entry.focus()

    def _toggle_password_visibility(self) -> None:
        """Toggle password visibility."""
        if self.show_var.get():
            self.password_entry.configure(show="")
        else:
            self.password_entry.configure(show="•")

    def _on_confirm(self) -> None:
        """Handle confirm button."""
        password = self.password_entry.get()
        self.result = (True, password)
        self.destroy()

    def _on_cancel(self) -> None:
        """Handle cancel button."""
        self.result = (False, "")
        self.destroy()

    def get_result(self) -> Tuple[bool, str]:
        """
        Get the dialog result.

        Returns:
            Tuple of (confirmed: bool, password: str).
        """
        return self.result


def ask_password(parent: ctk.CTkBaseClass, title: str = "Enter Password") -> Tuple[bool, str]:
    """
    Show password dialog and return result.

    Args:
        parent: Parent window.
        title: Dialog title.

    Returns:
        Tuple of (confirmed: bool, password: str).
    """
    dialog = PasswordDialog(parent, title)
    dialog.wait_window()
    return dialog.get_result()
