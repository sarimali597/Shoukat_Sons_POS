"""
Confirmation dialog for destructive actions.

Reusable modal confirmation dialog with warning message.
Requires typing confirmation word for especially destructive actions.
"""

from typing import Callable, Optional, Tuple

import customtkinter as ctk

from ui.theme import get_theme_manager


class ConfirmationDialog(ctk.CTkToplevel):
    """
    Modal confirmation dialog for destructive actions.

    Returns (confirmed: bool) indicating user's choice.
    """

    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        title: str = "Confirm Action",
        message: str = "Are you sure?",
        warning: Optional[str] = None,
        confirm_word: Optional[str] = None,
        confirm_button_text: str = "Confirm",
        danger: bool = True,
    ) -> None:
        """
        Initialize the confirmation dialog.

        Args:
            parent: Parent window.
            title: Dialog title.
            message: Main confirmation message.
            warning: Additional warning text.
            confirm_word: Word that must be typed to confirm (e.g., "DELETE").
            confirm_button_text: Text for confirm button.
            danger: If True, use danger color scheme.
        """
        super().__init__(parent)
        assert parent is not None, "parent cannot be None"
        assert message is not None, "message cannot be None"

        self._theme = get_theme_manager()
        self.result: bool = False
        self.confirm_word = confirm_word

        # Configure dialog
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()  # Make modal

        # Calculate height based on content
        height = 200
        if warning:
            height += 40
        if confirm_word:
            height += 60

        self.geometry(f"450x{height}")
        self._center_on_parent(parent)

        # Create UI
        self._create_ui(message, warning, confirm_word, confirm_button_text, danger)

        # Bind escape key
        self.bind("<Escape>", lambda e: self._on_cancel())

    def _center_on_parent(self, parent: ctk.CTkBaseClass) -> None:
        """Center dialog on parent window."""
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()

        # Get current dialog dimensions
        self.update_idletasks()
        dialog_width = self.winfo_width()
        dialog_height = self.winfo_height()

        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2

        self.geometry(f"+{x}+{y}")

    def _create_ui(
        self,
        message: str,
        warning: Optional[str],
        confirm_word: Optional[str],
        confirm_button_text: str,
        danger: bool,
    ) -> None:
        """Create dialog UI elements."""
        # Message
        msg_label = ctk.CTkLabel(
            self,
            text=message,
            font=self._theme.get_font("subheading"),
            wraplength=400,
        )
        msg_label.pack(pady=(20, 10))

        # Warning
        if warning:
            warn_label = ctk.CTkLabel(
                self,
                text=warning,
                font=self._theme.get_font("small"),
                text_color=self._theme.get_color("danger" if danger else "warning"),
                wraplength=400,
            )
            warn_label.pack(pady=(0, 10))

        # Confirm word entry
        if confirm_word:
            entry_label = ctk.CTkLabel(
                self,
                text=f'Type "{confirm_word}" to confirm:',
                font=self._theme.get_font("body"),
            )
            entry_label.pack(pady=(10, 5))

            self.confirm_entry = ctk.CTkEntry(
                self,
                width=280,
                height=40,
                font=self._theme.get_font("body"),
            )
            self.confirm_entry.pack(pady=(0, 10))
            self.confirm_entry.focus()
        else:
            self.confirm_entry = None

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

        btn_color = "danger" if danger else "primary"
        self.confirm_btn = ctk.CTkButton(
            btn_frame,
            text=confirm_button_text,
            command=self._on_confirm,
            width=100,
            height=36,
            fg_color=self._theme.get_color(btn_color),
            font=self._theme.get_font("button"),
        )
        self.confirm_btn.pack(side="left", padx=10)

    def _on_confirm(self) -> None:
        """Handle confirm button."""
        if self.confirm_word and self.confirm_entry:
            entered = self.confirm_entry.get().strip()
            if entered != self.confirm_word:
                return  # Don't close, let user retry
        self.result = True
        self.destroy()

    def _on_cancel(self) -> None:
        """Handle cancel button."""
        self.result = False
        self.destroy()

    def get_result(self) -> bool:
        """
        Get the dialog result.

        Returns:
            True if confirmed, False otherwise.
        """
        return self.result


def ask_confirmation(
    parent: ctk.CTkBaseClass,
    title: str = "Confirm Action",
    message: str = "Are you sure?",
    warning: Optional[str] = None,
    confirm_word: Optional[str] = None,
    confirm_button_text: str = "Confirm",
    danger: bool = True,
) -> bool:
    """
    Show confirmation dialog and return result.

    Args:
        parent: Parent window.
        title: Dialog title.
        message: Main confirmation message.
        warning: Additional warning text.
        confirm_word: Word that must be typed to confirm.
        confirm_button_text: Text for confirm button.
        danger: If True, use danger color scheme.

    Returns:
        True if confirmed, False otherwise.
    """
    dialog = ConfirmationDialog(
        parent, title, message, warning, confirm_word, confirm_button_text, danger
    )
    dialog.wait_window()
    return dialog.get_result()
