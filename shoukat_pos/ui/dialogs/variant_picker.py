"""
Variant picker dialog for size-color selection.

Size-color grid for quick variant selection during sales/exchanges.
Shows available stock per cell; out-of-stock cells disabled.
"""

from typing import Callable, Dict, List, Optional, Tuple

import customtkinter as ctk
from tksheet import Sheet

from ui.theme import get_theme_manager


class VariantPicker(ctk.CTkToplevel):
    """
    Modal variant picker with size-color matrix.

    Returns selected (size, color) tuple or None.
    """

    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        sizes: List[str],
        colors: List[str],
        stock: Dict[Tuple[str, str], int],
        title: str = "Select Variant",
    ) -> None:
        """
        Initialize the variant picker.

        Args:
            parent: Parent window.
            sizes: List of size options.
            colors: List of color options.
            stock: Dict mapping (size, color) to quantities.
            title: Dialog title.
        """
        super().__init__(parent)
        assert parent is not None, "parent cannot be None"
        assert sizes is not None, "sizes cannot be None"
        assert colors is not None, "colors cannot be None"
        assert stock is not None, "stock cannot be None"

        self._theme = get_theme_manager()
        self.result: Optional[Tuple[str, str]] = None
        self.sizes = sizes
        self.colors = colors
        self.stock = stock

        # Configure dialog
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()  # Make modal

        # Size: 600x500 for the matrix
        self.geometry("600x500")
        self._center_on_parent(parent)

        # Create UI
        self._create_ui()

        # Bind escape key
        self.bind("<Escape>", lambda e: self._on_cancel())

    def _center_on_parent(self, parent: ctk.CTkBaseClass) -> None:
        """Center dialog on parent window."""
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()

        self.update_idletasks()
        dialog_width = self.winfo_width()
        dialog_height = self.winfo_height()

        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2

        self.geometry(f"+{x}+{y}")

    def _create_ui(self) -> None:
        """Create dialog UI elements."""
        # Header
        header_label = ctk.CTkLabel(
            self,
            text="Select Size and Color:",
            font=self._theme.get_font("subheading"),
        )
        header_label.pack(pady=(15, 10))

        # Stock info
        stock_info = ctk.CTkLabel(
            self,
            text="Click a cell to select. Red = Out of stock, Orange = Low stock (<5)",
            font=self._theme.get_font("small"),
            text_color=self._theme.get_color("text_secondary"),
        )
        stock_info.pack(pady=(0, 10))

        # Matrix table
        self.sheet = Sheet(
            self,
            show_x_scrollbar=False,
            show_y_scrollbar=False,
            header_height=40,
            row_height=50,
        )
        self.sheet.pack(fill="both", expand=True, padx=20, pady=10)

        # Enable bindings
        self.sheet.enable_bindings("single_select")
        self.sheet.bind("<<SheetSelect>>", self._on_select)

        # Load matrix
        self._load_matrix()

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(10, 15))

        self.cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=self._on_cancel,
            width=100,
            height=36,
            font=self._theme.get_font("button"),
        )
        self.cancel_btn.pack(side="left", padx=10)

        self.select_btn = ctk.CTkButton(
            btn_frame,
            text="Select",
            command=self._on_select_confirmed,
            width=100,
            height=36,
            font=self._theme.get_font("button"),
        )
        self.select_btn.pack(side="left", padx=10)

        # Disable select button initially
        self.select_btn.configure(state="disabled")
        self._selected_row: Optional[int] = None
        self._selected_col: Optional[int] = None

    def _load_matrix(self) -> None:
        """Load the variant matrix with stock data."""
        # Build headers: ["Color \\ Size"] + sizes
        headers = ["Color \\ Size"] + self.sizes
        self.sheet.headers(headers)

        # Build rows
        rows: List[List[str]] = []
        for color in self.colors:
            row = [color] + [str(self.stock.get((size, color), 0)) for size in self.sizes]
            rows.append(row)

        self.sheet.set_sheet_data(rows)

        # Color-code cells based on stock
        for r, color in enumerate(self.colors):
            for c, size in enumerate(self.sizes, start=1):
                qty = self.stock.get((size, color), 0)
                if qty == 0:
                    bg = "#C62828"  # Red - out of stock
                    fg = "#FFFFFF"
                elif qty < 5:
                    bg = "#F57C00"  # Orange - low stock
                    fg = "#FFFFFF"
                else:
                    bg = "#FFFFFF"  # White - healthy stock
                    fg = "#000000"

                self.sheet.highlight_cells(row=r, column=c, bg=bg)
                self.sheet.highlight_cells(row=r, column=c, fg=fg)

    def _on_select(self, event: object) -> None:
        """Handle cell selection."""
        selected = self.sheet.currently_selected()
        if selected and selected[0] is not None and selected[1] is not None:
            row, col = selected[0], selected[1]
            # Check if valid cell (not header row/column)
            if row < len(self.colors) and col > 0 and col <= len(self.sizes):
                size = self.sizes[col - 1]
                color = self.colors[row]
                qty = self.stock.get((size, color), 0)

                # Only allow selection if in stock
                if qty > 0:
                    self._selected_row = row
                    self._selected_col = col
                    self.select_btn.configure(state="normal")
                else:
                    self._selected_row = None
                    self._selected_col = None
                    self.select_btn.configure(state="disabled")

    def _on_select_confirmed(self) -> None:
        """Handle select button."""
        if self._selected_row is not None and self._selected_col is not None:
            color = self.colors[self._selected_row]
            size = self.sizes[self._selected_col - 1]
            self.result = (size, color)
        self.destroy()

    def _on_cancel(self) -> None:
        """Handle cancel button."""
        self.result = None
        self.destroy()

    def get_result(self) -> Optional[Tuple[str, str]]:
        """
        Get the selected variant.

        Returns:
            Tuple of (size, color) or None if cancelled.
        """
        return self.result


def pick_variant(
    parent: ctk.CTkBaseClass,
    sizes: List[str],
    colors: List[str],
    stock: Dict[Tuple[str, str], int],
    title: str = "Select Variant",
) -> Optional[Tuple[str, str]]:
    """
    Show variant picker and return selected variant.

    Args:
        parent: Parent window.
        sizes: List of size options.
        colors: List of color options.
        stock: Dict mapping (size, color) to quantities.
        title: Dialog title.

    Returns:
        Tuple of (size, color) or None if cancelled.
    """
    dialog = VariantPicker(parent, sizes, colors, stock, title)
    dialog.wait_window()
    return dialog.get_result()
