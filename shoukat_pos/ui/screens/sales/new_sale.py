"""New Sale Screen - Main point of sale interface."""

import customtkinter as ctk
from typing import Optional, List, Dict
from datetime import datetime

from ui.theme import ThemeManager
from ui.components import DataTable
from ui.dialogs.confirmation_dialog import ConfirmationDialog


class NewSaleScreen(ctk.CTkFrame):
    """New Sale screen for processing sales."""
    
    def __init__(self, master, router, **kwargs):
        super().__init__(master, **kwargs)
        self.router = router
        self.theme = ThemeManager()
        self.cart: List[Dict] = []
        
        self._create_ui()
    
    def _create_ui(self):
        """Create the sale interface."""
        # Header
        header_frame = ctk.CTkFrame(self)
        header_frame.pack(fill="x", padx=20, pady=10)
        
        title = ctk.CTkLabel(
            header_frame, 
            text="New Sale",
            font=self.theme.get_font("heading")
        )
        title.pack(side="left")
        
        # Invoice preview
        invoice_num = f"INV-{datetime.now().strftime('%Y%m%d')}-XXXX"
        invoice_label = ctk.CTkLabel(
            header_frame,
            text=f"Invoice: {invoice_num}",
            font=self.theme.get_font("body")
        )
        invoice_label.pack(side="right")
        
        # Main content area
        content_frame = ctk.CTkFrame(self)
        content_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Left side - Product entry
        left_frame = ctk.CTkFrame(content_frame)
        left_frame.pack(side="left", fill="both", expand=True)
        
        # Barcode entry
        barcode_frame = ctk.CTkFrame(left_frame)
        barcode_frame.pack(fill="x", pady=10)
        
        barcode_label = ctk.CTkLabel(
            barcode_frame,
            text="Scan or Enter Barcode:"
        )
        barcode_label.pack(side="left", padx=5)
        
        self.barcode_entry = ctk.CTkEntry(barcode_frame, width=300)
        self.barcode_entry.pack(side="left", padx=5)
        self.barcode_entry.bind("<Return>", lambda e: self._add_to_cart())
        
        add_btn = ctk.CTkButton(
            barcode_frame,
            text="Add",
            command=self._add_to_cart
        )
        add_btn.pack(side="left", padx=5)
        
        # Cart table placeholder
        cart_placeholder = ctk.CTkLabel(
            left_frame,
            text="Cart Table (tksheet integration coming)",
            font=self.theme.get_font("body")
        )
        cart_placeholder.pack(expand=True)
        
        # Right side - Customer & Payment
        right_frame = ctk.CTkFrame(content_frame, width=300)
        right_frame.pack(side="right", fill="y", padx=10)
        right_frame.pack_propagate(False)
        
        # Customer section
        customer_section = ctk.CTkFrame(right_frame)
        customer_section.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            customer_section,
            text="Customer",
            font=self.theme.get_font("subheading")
        ).pack(anchor="w", padx=5, pady=5)
        
        self.customer_var = ctk.StringVar(value="Walk-in Customer")
        customer_dropdown = ctk.CTkOptionMenu(
            customer_section,
            variable=self.customer_var,
            values=["Walk-in Customer"]
        )
        customer_dropdown.pack(fill="x", padx=5, pady=5)
        
        # Totals section
        totals_section = ctk.CTkFrame(right_frame)
        totals_section.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            totals_section,
            text="Totals",
            font=self.theme.get_font("subheading")
        ).pack(anchor="w", padx=5, pady=5)
        
        self.subtotal_label = ctk.CTkLabel(
            totals_section,
            text="Subtotal: Rs. 0.00"
        )
        self.subtotal_label.pack(anchor="w", padx=5, pady=2)
        
        self.tax_label = ctk.CTkLabel(
            totals_section,
            text="Tax: Rs. 0.00"
        )
        self.tax_label.pack(anchor="w", padx=5, pady=2)
        
        self.total_label = ctk.CTkLabel(
            totals_section,
            text="Total: Rs. 0.00",
            font=self.theme.get_font("subheading")
        )
        self.total_label.pack(anchor="w", padx=5, pady=5)
        
        # Payment type
        payment_section = ctk.CTkFrame(right_frame)
        payment_section.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            payment_section,
            text="Payment Type",
            font=self.theme.get_font("subheading")
        ).pack(anchor="w", padx=5, pady=5)
        
        self.payment_type = ctk.StringVar(value="cash")
        payment_options = ["cash", "credit", "split"]
        for opt in payment_options:
            rb = ctk.CTkRadioButton(
                payment_section,
                text=opt.capitalize(),
                variable=self.payment_type,
                value=opt
            )
            rb.pack(anchor="w", padx=5, pady=2)
        
        # Action buttons
        action_frame = ctk.CTkFrame(right_frame)
        action_frame.pack(fill="x", pady=20)
        
        hold_btn = ctk.CTkButton(
            action_frame,
            text="Hold",
            fg_color=self.theme.get_color("warning"),
            command=self._hold_sale
        )
        hold_btn.pack(fill="x", padx=5, pady=5)
        
        cancel_btn = ctk.CTkButton(
            action_frame,
            text="Cancel",
            fg_color=self.theme.get_color("danger"),
            command=self._cancel_sale
        )
        cancel_btn.pack(fill="x", padx=5, pady=5)
        
        save_btn = ctk.CTkButton(
            action_frame,
            text="Save & Print",
            fg_color=self.theme.get_color("success"),
            height=50,
            command=self._save_and_print
        )
        save_btn.pack(fill="x", padx=5, pady=5)
    
    def _add_to_cart(self):
        """Add scanned/entered product to cart."""
        # TODO: Implement product lookup and cart addition
        pass
    
    def _hold_sale(self):
        """Hold current sale for later."""
        if not self.cart:
            return
        
        dialog = ConfirmationDialog(
            self,
            title="Hold Sale",
            message="Save this transaction for later?",
            confirm_text="Hold",
            cancel_text="Cancel"
        )
        if dialog.show():
            # TODO: Implement hold sale logic
            pass
    
    def _cancel_sale(self):
        """Cancel current sale."""
        if not self.cart:
            return
        
        dialog = ConfirmationDialog(
            self,
            title="Cancel Sale",
            message="Clear all items from cart?",
            confirm_text="Yes, Clear",
            cancel_text="Cancel"
        )
        if dialog.show():
            self.cart.clear()
            # Refresh UI
            pass
    
    def _save_and_print(self):
        """Process sale and print receipt."""
        if not self.cart:
            return
        
        # TODO: Implement sale processing via SaleEngine
        # TODO: Print receipt via ReceiptPrinter
        pass
