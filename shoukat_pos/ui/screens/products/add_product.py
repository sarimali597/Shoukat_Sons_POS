"""
Add Product Screen - 4-step wizard for creating styles and variants.

Step 1: Style Information (name, category, base price, tax rate, season)
Step 2: Variant Matrix Builder (size/color selection with live preview)
Step 3: Batch Entry (bilty no, bill no, vendor, date received)
Step 4: Review & Save (summary table with save all option)
"""

import customtkinter as ctk
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from ui.theme import ThemeManager
from ui.components import DataTable, EmptyState
from ui.dialogs.confirmation_dialog import ConfirmationDialog


class AddProductScreen(ctk.CTkFrame):
    """Four-step wizard for adding new products with variants."""

    SIZES = ["XS", "S", "M", "L", "XL", "XXL", "XXXL"]
    COLORS = [
        "Black", "White", "Blue", "Red", "Green", 
        "Navy", "Grey", "Brown"
    ]

    def __init__(self, master, router, user_context: Optional[Dict] = None):
        """Initialize add product screen.
        
        Args:
            master: Parent widget
            router: ScreenRouter instance
            user_context: Current user information (role, username, etc.)
        """
        super().__init__(master)
        self.router = router
        self.user_context = user_context or {}
        self.theme = ThemeManager()
        
        # Wizard state
        self.current_step = 0
        self.style_data = {}
        self.selected_sizes = []
        self.selected_colors = []
        self.variant_data = {}
        self.batch_data = {}
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)  # Content area
        
        # Header
        self._create_header()
        
        # Content area
        self.content_frame = ctk.CTkFrame(self)
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)
        
        # Show first step
        self._show_step_1()
        
        # Footer with navigation
        self._create_footer()

    def _create_header(self) -> None:
        """Create header with title and progress indicator."""
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        title = ctk.CTkLabel(
            header,
            text="Add New Product",
            font=self.theme.get_font("heading")
        )
        title.pack(side="left")
        
        # Progress indicator
        self.progress_label = ctk.CTkLabel(
            header,
            text="Step 1 of 4: Style Information",
            font=self.theme.get_font("body")
        )
        self.progress_label.pack(side="right")

    def _create_footer(self) -> None:
        """Create footer with navigation buttons."""
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="e", padx=20, pady=(0, 20))
        
        self.back_btn = ctk.CTkButton(
            footer,
            text="Back",
            command=self._previous_step,
            state="disabled",
            width=100
        )
        self.back_btn.pack(side="left", padx=(0, 10))
        
        self.next_btn = ctk.CTkButton(
            footer,
            text="Next",
            command=self._next_step,
            width=100
        )
        self.next_btn.pack(side="left")

    def _show_step_1(self) -> None:
        """Show Step 1: Style Information form."""
        # Clear content
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Form frame
        form = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        form.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        form.grid_columnconfigure(1, weight=1)
        
        # Style name
        ctk.CTkLabel(form, text="Style Name *").grid(row=0, column=0, sticky="w", pady=5)
        self.style_name_entry = ctk.CTkEntry(form, width=400)
        self.style_name_entry.grid(row=0, column=1, sticky="ew", pady=5, padx=(10, 0))
        
        # Category
        ctk.CTkLabel(form, text="Category *").grid(row=1, column=0, sticky="w", pady=5)
        self.category_var = ctk.StringVar(value="Shirt")
        self.category_combo = ctk.CTkComboBox(
            form, 
            values=["Shirt", "Pant", "Tie", "Coat", "Blazer", "Jeans", "Shorts"],
            variable=self.category_var,
            width=400
        )
        self.category_combo.grid(row=1, column=1, sticky="ew", pady=5, padx=(10, 0))
        
        # Base sale price
        ctk.CTkLabel(form, text="Base Sale Price (Rs.) *").grid(row=2, column=0, sticky="w", pady=5)
        self.base_price_entry = ctk.CTkEntry(form, width=400, placeholder_text="e.g., 2500")
        self.base_price_entry.grid(row=2, column=1, sticky="ew", pady=5, padx=(10, 0))
        
        # Tax rate
        ctk.CTkLabel(form, text="Tax Rate (%)").grid(row=3, column=0, sticky="w", pady=5)
        self.tax_rate_entry = ctk.CTkEntry(form, width=400, placeholder_text="e.g., 17")
        self.tax_rate_entry.insert(0, "0")
        self.tax_rate_entry.grid(row=3, column=1, sticky="ew", pady=5, padx=(10, 0))
        
        # Season
        ctk.CTkLabel(form, text="Season").grid(row=4, column=0, sticky="w", pady=5)
        self.season_var = ctk.StringVar(value="All Season")
        self.season_combo = ctk.CTkComboBox(
            form,
            values=["All Season", "Summer", "Winter", "Festive"],
            variable=self.season_var,
            width=400
        )
        self.season_combo.grid(row=4, column=1, sticky="ew", pady=5, padx=(10, 0))
        
        # Description
        ctk.CTkLabel(form, text="Description").grid(row=5, column=0, sticky="nw", pady=5)
        self.desc_text = ctk.CTkTextbox(form, width=400, height=100)
        self.desc_text.grid(row=5, column=1, sticky="ew", pady=5, padx=(10, 0))

    def _show_step_2(self) -> None:
        """Show Step 2: Variant Matrix Builder."""
        # Clear content
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        info_label = ctk.CTkLabel(
            self.content_frame,
            text="Select sizes and colors to generate variant matrix",
            font=self.theme.get_font("subheading")
        )
        info_label.grid(row=0, column=0, pady=20, padx=20)
        
        # Size selector
        size_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        size_frame.grid(row=1, column=0, sticky="w", padx=20, pady=10)
        
        ctk.CTkLabel(size_frame, text="Select Sizes:", font=self.theme.get_font("body")).pack(anchor="w")
        
        self.size_vars = {}
        size_container = ctk.CTkFrame(size_frame, fg_color="transparent")
        size_container.pack(anchor="w", fill="x")
        
        for i, size in enumerate(self.SIZES):
            var = ctk.BooleanVar(value=False)
            self.size_vars[size] = var
            chk = ctk.CTkCheckBox(
                size_container,
                text=size,
                variable=var,
                command=self._update_matrix_preview
            )
            chk.grid(row=0, column=i, padx=5, pady=5, sticky="w")
        
        # Color selector
        color_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        color_frame.grid(row=2, column=0, sticky="w", padx=20, pady=10)
        
        ctk.CTkLabel(color_frame, text="Select Colors:", font=self.theme.get_font("body")).pack(anchor="w")
        
        self.color_vars = {}
        color_container = ctk.CTkFrame(color_frame, fg_color="transparent")
        color_container.pack(anchor="w", fill="x")
        
        for i, color in enumerate(self.COLORS):
            var = ctk.BooleanVar(value=False)
            self.color_vars[color] = var
            chk = ctk.CTkCheckBox(
                color_container,
                text=color,
                variable=var,
                command=self._update_matrix_preview
            )
            chk.grid(row=0, column=i, padx=5, pady=5, sticky="w")
        
        # Matrix preview placeholder
        preview_frame = ctk.CTkFrame(self.content_frame)
        preview_frame.grid(row=3, column=0, sticky="nsew", padx=20, pady=10)
        preview_frame.grid_columnconfigure(0, weight=1)
        preview_frame.grid_rowconfigure(0, weight=1)
        
        self.matrix_label = ctk.CTkLabel(
            preview_frame,
            text="Matrix preview will appear here\n(Select at least one size and one color)",
            font=self.theme.get_font("body")
        )
        self.matrix_label.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    def _update_matrix_preview(self) -> None:
        """Update matrix preview when sizes/colors selected."""
        self.selected_sizes = [s for s, v in self.size_vars.items() if v.get()]
        self.selected_colors = [c for c, v in self.color_vars.items() if v.get()]
        
        if self.selected_sizes and self.selected_colors:
            count = len(self.selected_sizes) * len(self.selected_colors)
            self.matrix_label.configure(
                text=f"Will generate {count} variants:\n"
                     f"{len(self.selected_sizes)} sizes × {len(self.selected_colors)} colors"
            )
        else:
            self.matrix_label.configure(
                text="Matrix preview will appear here\n(Select at least one size and one color)"
            )

    def _show_step_3(self) -> None:
        """Show Step 3: Batch Entry."""
        # Clear content
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Form frame
        form = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        form.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        form.grid_columnconfigure(1, weight=1)
        
        # Bilty number
        ctk.CTkLabel(form, text="Bilty Number *").grid(row=0, column=0, sticky="w", pady=5)
        self.bilty_entry = ctk.CTkEntry(form, width=400)
        self.bilty_entry.grid(row=0, column=1, sticky="ew", pady=5, padx=(10, 0))
        
        # Bill number
        ctk.CTkLabel(form, text="Bill Number *").grid(row=1, column=0, sticky="w", pady=5)
        self.bill_entry = ctk.CTkEntry(form, width=400)
        self.bill_entry.grid(row=1, column=1, sticky="ew", pady=5, padx=(10, 0))
        
        # Vendor
        ctk.CTkLabel(form, text="Vendor *").grid(row=2, column=0, sticky="w", pady=5)
        self.vendor_var = ctk.StringVar()
        self.vendor_combo = ctk.CTkComboBox(
            form,
            values=["Vendor A", "Vendor B", "Vendor C"],  # Would be populated from DB
            variable=self.vendor_var,
            width=400
        )
        self.vendor_combo.grid(row=2, column=1, sticky="ew", pady=5, padx=(10, 0))
        
        # Date received
        ctk.CTkLabel(form, text="Date Received *").grid(row=3, column=0, sticky="w", pady=5)
        today = datetime.now().strftime("%Y-%m-%d")
        self.date_entry = ctk.CTkEntry(form, width=400)
        self.date_entry.insert(0, today)
        self.date_entry.grid(row=3, column=1, sticky="ew", pady=5, padx=(10, 0))
        
        # Quantity per variant
        ctk.CTkLabel(form, text="Quantity per Variant *").grid(row=4, column=0, sticky="w", pady=5)
        self.qty_entry = ctk.CTkEntry(form, width=400, placeholder_text="e.g., 10")
        self.qty_entry.insert(0, "1")
        self.qty_entry.grid(row=4, column=1, sticky="ew", pady=5, padx=(10, 0))
        
        # Purchase price
        ctk.CTkLabel(form, text="Purchase Price per Unit (Rs.) *").grid(row=5, column=0, sticky="w", pady=5)
        self.purchase_price_entry = ctk.CTkEntry(form, width=400, placeholder_text="e.g., 1250")
        self.purchase_price_entry.grid(row=5, column=1, sticky="ew", pady=5, padx=(10, 0))

    def _show_step_4(self) -> None:
        """Show Step 4: Review & Save."""
        # Clear content
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Summary label
        summary_label = ctk.CTkLabel(
            self.content_frame,
            text="Review before saving",
            font=self.theme.get_font("subheading")
        )
        summary_label.grid(row=0, column=0, pady=20, padx=20)
        
        # Placeholder for summary table
        # In full implementation, this would show a DataTable with all variants
        summary_frame = ctk.CTkFrame(self.content_frame)
        summary_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        summary_frame.grid_columnconfigure(0, weight=1)
        summary_frame.grid_rowconfigure(0, weight=1)
        
        sizes_count = len(self.selected_sizes) if self.selected_sizes else 0
        colors_count = len(self.selected_colors) if self.selected_colors else 0
        total_variants = sizes_count * colors_count
        
        summary_text = ctk.CTkLabel(
            summary_frame,
            text=f"Style: {self.style_name_entry.get() if hasattr(self, 'style_name_entry') else 'N/A'}\n"
                 f"Category: {self.category_var.get() if hasattr(self, 'category_var') else 'N/A'}\n"
                 f"Variants to create: {total_variants}\n"
                 f"Sizes: {', '.join(self.selected_sizes) if self.selected_sizes else 'None'}\n"
                 f"Colors: {', '.join(self.selected_colors) if self.selected_colors else 'None'}",
            font=self.theme.get_font("body"),
            justify="left"
        )
        summary_text.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    def _next_step(self) -> None:
        """Proceed to next step or save."""
        if self.current_step == 0:
            # Validate step 1
            if not self.style_name_entry.get().strip():
                # Show error
                return
            self.style_data['name'] = self.style_name_entry.get()
            self.style_data['category'] = self.category_var.get()
            self.style_data['base_price'] = self.base_price_entry.get()
            self.style_data['tax_rate'] = self.tax_rate_entry.get()
            self.style_data['season'] = self.season_var.get()
            self.style_data['description'] = self.desc_text.get("1.0", "end-1c")
            
            self._show_step_2()
            self.current_step = 1
            
        elif self.current_step == 1:
            # Validate step 2
            if not self.selected_sizes or not self.selected_colors:
                # Show error
                return
            
            self._show_step_3()
            self.current_step = 2
            
        elif self.current_step == 2:
            # Validate step 3
            if not self.bilty_entry.get().strip():
                return
            
            self.batch_data['bilty'] = self.bilty_entry.get()
            self.batch_data['bill'] = self.bill_entry.get()
            self.batch_data['vendor'] = self.vendor_var.get()
            self.batch_data['date'] = self.date_entry.get()
            self.batch_data['qty'] = self.qty_entry.get()
            self.batch_data['purchase_price'] = self.purchase_price_entry.get()
            
            self._show_step_4()
            self.current_step = 3
            
        elif self.current_step == 3:
            # Save all data
            self._save_product()

        self._update_footer()

    def _previous_step(self) -> None:
        """Go back to previous step."""
        if self.current_step > 0:
            self.current_step -= 1
            
            if self.current_step == 0:
                self._show_step_1()
            elif self.current_step == 1:
                self._show_step_2()
            elif self.current_step == 2:
                self._show_step_3()
                
            self._update_footer()

    def _update_footer(self) -> None:
        """Update footer buttons based on current step."""
        steps = ["Style Information", "Variant Matrix", "Batch Entry", "Review & Save"]
        self.progress_label.configure(text=f"Step {self.current_step + 1} of 4: {steps[self.current_step]}")
        
        # Back button
        if self.current_step == 0:
            self.back_btn.configure(state="disabled")
        else:
            self.back_btn.configure(state="normal")
        
        # Next button
        if self.current_step == 3:
            self.next_btn.configure(text="Save Product")
        else:
            self.next_btn.configure(text="Next")

    def _save_product(self) -> None:
        """Save the product with all variants and batch data."""
        # In full implementation, this would call ProductService
        # to create style, variants, and batch records atomically
        
        # Show success message
        dialog = ctk.CTkToplevel(self)
        dialog.title("Success")
        dialog.geometry("400x200")
        
        msg = ctk.CTkLabel(
            dialog,
            text="Product created successfully!\n\nWould you like to print labels now?",
            font=self.theme.get_font("body")
        )
        msg.pack(pady=20, padx=20)
        
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=10)
        
        def on_yes():
            dialog.destroy()
            self.router.navigate_to("print_labels")
        
        def on_no():
            dialog.destroy()
            self.router.navigate_to("product_list")
        
        ctk.CTkButton(btn_frame, text="Yes, Print Labels", command=on_yes).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="No, Go to List", command=on_no).pack(side="left", padx=5)
