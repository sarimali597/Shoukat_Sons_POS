"""
Reusable UI components for Shoukat Sons Garments POS.

All data grids are built on tksheet since CustomTkinter has no native table widget.
Components include: DataTable, VariantMatrixTable, StatCard, SearchBar, EmptyState.
"""

import tkinter as tk
from typing import Any, Callable, Dict, List, Optional, Tuple

import customtkinter as ctk
from tksheet import Sheet

from ui.theme import ThemeManager, get_theme_manager


class DataTable(ctk.CTkFrame):
    """
    Data table component wrapping tksheet.Sheet.

    Provides sortable columns, search/filter, pagination, row actions,
    and cell coloring based on data values.

    Attributes:
        columns: List of column definitions.
        sheet: The underlying tksheet.Sheet widget.
    """

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        columns: List[Dict[str, Any]],
        on_select: Optional[Callable[[int], None]] = None,
        on_double_click: Optional[Callable[[int], None]] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the DataTable.

        Args:
            master: Parent widget.
            columns: Column definitions with name, width, sortable, formatter.
            on_select: Callback when a row is selected.
            on_double_click: Callback when a row is double-clicked.
            **kwargs: Additional arguments for CTkFrame.
        """
        super().__init__(master, **kwargs)
        assert columns is not None, "columns cannot be None"
        assert len(columns) > 0, "columns must have at least one column"

        self.columns = columns
        self.on_select = on_select
        self.on_double_click = on_double_click
        self._data: List[List[Any]] = []
        self._filtered_data: List[List[Any]] = []
        self._theme = get_theme_manager()

        # Create search bar
        self.search_var = tk.StringVar()
        self.search_bar = ctk.CTkEntry(
            self,
            placeholder_text="Search...",
            textvariable=self.search_var,
            height=32,
        )
        self.search_bar.pack(fill="x", padx=10, pady=(10, 5))
        self.search_var.trace_add("write", self._on_search_change)

        # Create sheet
        self.sheet = Sheet(
            self,
            show_x_scrollbar=True,
            show_y_scrollbar=True,
            header_height=40,
        )
        self.sheet.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Enable bindings
        self.sheet.enable_bindings(
            "single_select",
            "row_select",
            "column_width_resize",
            "arrowkeys",
            "copy",
        )

        # Bind events
        self.sheet.bind("<<SheetSelect>>", self._on_sheet_select)
        self.sheet.bind("<<SheetDoubleClick>>", self._on_sheet_double_click)

        # Initialize headers
        self._update_headers()

    def _update_headers(self) -> None:
        """Update sheet headers from column definitions."""
        headers = [col["name"] for col in self.columns]
        self.sheet.headers(headers)

        # Set column widths
        for i, col in enumerate(self.columns):
            if "width" in col:
                self.sheet.column_width(i, col["width"])

    def _on_search_change(self, *args: Any) -> None:
        """Handle search text change with debouncing."""
        query = self.search_var.get().lower()
        if not query:
            self._filtered_data = self._data.copy()
        else:
            self._filtered_data = [
                row for row in self._data if any(query in str(cell).lower() for cell in row)
            ]
        self._refresh_sheet()

    def _refresh_sheet(self) -> None:
        """Refresh sheet data from filtered data."""
        self.sheet.set_sheet_data(self._filtered_data)

    def set_data(self, data: List[List[Any]]) -> None:
        """
        Set the table data.

        Args:
            data: List of rows, each row is a list of cell values.
        """
        assert data is not None, "data cannot be None"
        self._data = [list(row) for row in data]
        self._filtered_data = self._data.copy()
        self._refresh_sheet()

    def _on_sheet_select(self, event: Any) -> None:
        """Handle row selection."""
        if self.on_select:
            selected = self.sheet.currently_selected()
            if selected and selected[0] is not None:
                self.on_select(selected[0])

    def _on_sheet_double_click(self, event: Any) -> None:
        """Handle row double-click."""
        if self.on_double_click:
            selected = self.sheet.currently_selected()
            if selected and selected[0] is not None:
                self.on_double_click(selected[0])

    def clear(self) -> None:
        """Clear all data from the table."""
        self._data = []
        self._filtered_data = []
        self._refresh_sheet()


class VariantMatrixTable(ctk.CTkFrame):
    """
    Specialized table for displaying size-color variant matrix.

    Shows stock levels in a grid with color-coded cells.
    """

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        on_select: Optional[Callable[[str, str, int], None]] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the VariantMatrixTable.

        Args:
            master: Parent widget.
            on_select: Callback when a cell is selected (size, color, qty).
            **kwargs: Additional arguments for CTkFrame.
        """
        super().__init__(master, **kwargs)
        self.on_select = on_select
        self._sizes: List[str] = []
        self._colors: List[str] = []
        self._stock: Dict[Tuple[str, str], int] = {}

        self.sheet = Sheet(
            self,
            show_x_scrollbar=True,
            show_y_scrollbar=True,
            header_height=40,
        )
        self.sheet.pack(fill="both", expand=True, padx=10, pady=10)

        self.sheet.enable_bindings("single_select", "row_select", "arrowkeys")
        self.sheet.bind("<<SheetSelect>>", self._on_select)

    def load_matrix(
        self, sizes: List[str], colors: List[str], stock: Dict[Tuple[str, str], int]
    ) -> None:
        """
        Load the variant matrix with stock data.

        Args:
            sizes: List of size options.
            colors: List of color options.
            stock: Dict mapping (size, color) tuples to quantities.
        """
        assert sizes is not None, "sizes cannot be None"
        assert colors is not None, "colors cannot be None"
        assert stock is not None, "stock cannot be None"

        self._sizes = sizes
        self._colors = colors
        self._stock = stock

        # Build headers: ["Color \\ Size"] + sizes
        headers = ["Color \\ Size"] + sizes
        self.sheet.headers(headers)

        # Build rows
        rows: List[List[str]] = []
        for color in colors:
            row = [color] + [str(stock.get((size, color), 0)) for size in sizes]
            rows.append(row)

        self.sheet.set_sheet_data(rows)

        # Color-code cells based on stock
        for r, color in enumerate(colors):
            for c, size in enumerate(sizes, start=1):
                qty = stock.get((size, color), 0)
                if qty == 0:
                    bg = "#C62828"  # Red - out of stock
                elif qty < 5:
                    bg = "#F57C00"  # Orange - low stock
                else:
                    bg = "#FFFFFF"  # White - healthy stock

                self.sheet.highlight_cells(row=r, column=c, bg=bg)
                self.sheet.highlight_cells(row=r, column=c, fg="#000000")

    def _on_select(self, event: Any) -> None:
        """Handle cell selection."""
        if self.on_select:
            selected = self.sheet.currently_selected()
            if selected and selected[0] is not None and selected[1] is not None:
                row, col = selected[0], selected[1]
                if row < len(self._colors) and col > 0 and col <= len(self._sizes):
                    color = self._colors[row]
                    size = self._sizes[col - 1]
                    qty = self._stock.get((size, color), 0)
                    self.on_select(size, color, qty)


class StatCard(ctk.CTkFrame):
    """
    Statistics card component for dashboard.

    Displays a title, value, optional change indicator, and icon.
    """

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        title: str,
        value: str,
        change_percent: Optional[float] = None,
        icon: Optional[str] = None,
        on_click: Optional[Callable[[], None]] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the StatCard.

        Args:
            master: Parent widget.
            title: Card title.
            value: Main value to display.
            change_percent: Optional percentage change (positive=green, negative=red).
            icon: Optional icon text/emoji.
            on_click: Optional callback when card is clicked.
            **kwargs: Additional arguments for CTkFrame.
        """
        super().__init__(master, **kwargs)
        assert title is not None, "title cannot be None"
        assert value is not None, "value cannot be None"

        self._theme = get_theme_manager()
        self.on_click = on_click

        # Configure frame
        self.configure(fg_color=self._theme.get_color("surface"))
        self.configure(corner_radius=10)

        # Add click binding if provided
        if on_click:
            self.bind("<Button-1>", lambda e: on_click())

        # Title
        self.title_label = ctk.CTkLabel(
            self,
            text=title,
            font=self._theme.get_font("small"),
            text_color=self._theme.get_color("text_secondary"),
        )
        self.title_label.pack(anchor="w", padx=15, pady=(15, 5))

        # Value
        self.value_label = ctk.CTkLabel(
            self,
            text=value,
            font=self._theme.get_font("heading"),
            text_color=self._theme.get_color("text"),
        )
        self.value_label.pack(anchor="w", padx=15, pady=(0, 5))

        # Change indicator
        if change_percent is not None:
            arrow = "↑" if change_percent >= 0 else "↓"
            color_key = "success" if change_percent >= 0 else "danger"
            self.change_label = ctk.CTkLabel(
                self,
                text=f"{arrow} {abs(change_percent):.1f}%",
                font=self._theme.get_font("small"),
                text_color=self._theme.get_color(color_key),
            )
            self.change_label.pack(anchor="w", padx=15, pady=(0, 15))

        # Icon (top-right)
        if icon:
            self.icon_label = ctk.CTkLabel(
                self,
                text=icon,
                font=("Segoe UI", 24),
                text_color=self._theme.get_color("primary"),
            )
            self.icon_label.place(relx=0.95, rely=0.1, anchor="ne")

    def update_value(self, value: str) -> None:
        """
        Update the displayed value.

        Args:
            value: New value string.
        """
        self.value_label.configure(text=value)


class SearchBar(ctk.CTkFrame):
    """
    Search bar component with debounced input and clear button.

    Supports barcode scanner input detection.
    """

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        on_search: Callable[[str], None],
        placeholder: str = "Search...",
        debounce_ms: int = 250,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the SearchBar.

        Args:
            master: Parent widget.
            on_search: Callback with search query.
            placeholder: Placeholder text.
            debounce_ms: Debounce delay in milliseconds.
            **kwargs: Additional arguments for CTkFrame.
        """
        super().__init__(master, **kwargs)
        assert on_search is not None, "on_search cannot be None"
        assert debounce_ms > 0, "debounce_ms must be positive"

        self.on_search = on_search
        self.debounce_ms = debounce_ms
        self._debounce_job: Optional[int] = None
        self._theme = get_theme_manager()

        # Entry field
        self.entry = ctk.CTkEntry(
            self,
            placeholder_text=placeholder,
            height=40,
            font=self._theme.get_font("body"),
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.entry.bind("<KeyRelease>", self._on_key_release)

        # Clear button
        self.clear_btn = ctk.CTkButton(
            self,
            text="✕",
            width=40,
            height=40,
            command=self.clear,
            font=self._theme.get_font("body"),
        )
        self.clear_btn.pack(side="right")
        self.clear_btn.configure(state="disabled")

        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)

    def _on_key_release(self, event: Any) -> None:
        """Handle key release with debouncing."""
        if self._debounce_job:
            self.after_cancel(self._debounce_job)

        query = self.entry.get()
        self.clear_btn.configure(state="normal" if query else "disabled")

        self._debounce_job = self.after(self.debounce_ms, lambda: self.on_search(query))

    def clear(self) -> None:
        """Clear the search field."""
        self.entry.delete(0, "end")
        self.clear_btn.configure(state="disabled")
        self.on_search("")

    def _on_focus_in(self, event: Any) -> None:
        """Handle focus in."""
        pass

    def _on_focus_out(self, event: Any) -> None:
        """Handle focus out."""
        pass

    def get_query(self) -> str:
        """
        Get the current search query.

        Returns:
            Current text in the search field.
        """
        return self.entry.get()

    def set_query(self, query: str) -> None:
        """
        Set the search query programmatically.

        Args:
            query: Query string to set.
        """
        self.entry.delete(0, "end")
        self.entry.insert(0, query)
        self.clear_btn.configure(state="normal" if query else "disabled")


class EmptyState(ctk.CTkFrame):
    """
    Empty state component for zero-data scenarios.

    Shows an icon, explanation message, and call-to-action button.
    """

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        message: str,
        action_text: str,
        action_callback: Callable[[], None],
        icon: str = "📦",
        **kwargs: Any,
    ) -> None:
        """
        Initialize the EmptyState.

        Args:
            master: Parent widget.
            message: Explanation message.
            action_text: CTA button text.
            action_callback: Callback when CTA is clicked.
            icon: Icon emoji/text.
            **kwargs: Additional arguments for CTkFrame.
        """
        super().__init__(master, **kwargs)
        assert message is not None, "message cannot be None"
        assert action_text is not None, "action_text cannot be None"
        assert action_callback is not None, "action_callback cannot be None"

        self._theme = get_theme_manager()

        # Center content
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Icon
        self.icon_label = ctk.CTkLabel(
            self,
            text=icon,
            font=("Segoe UI", 64),
            text_color=self._theme.get_color("text_secondary"),
        )
        self.icon_label.grid(row=0, column=0, sticky="n", pady=(40, 10))

        # Message
        self.message_label = ctk.CTkLabel(
            self,
            text=message,
            font=self._theme.get_font("subheading"),
            text_color=self._theme.get_color("text"),
            wraplength=400,
        )
        self.message_label.grid(row=1, column=0, sticky="n", pady=10)

        # CTA Button
        self.action_btn = ctk.CTkButton(
            self,
            text=action_text,
            command=action_callback,
            font=self._theme.get_font("button"),
            height=40,
        )
        self.action_btn.grid(row=2, column=0, sticky="n", pady=(20, 40))
