"""Credit Sale Screen - Extension of New Sale for credit transactions."""

import customtkinter as ctk
from typing import Optional, Dict
from datetime import datetime

from ui.theme import ThemeManager
from ui.dialogs.confirmation_dialog import ConfirmationDialog


class CreditSaleScreen(ctk.CTkFrame):
    """Credit Sale screen with mandatory customer selection and credit limit validation."""
    
    def __init__(self, master, router, **kwargs):
        super().__init__(master, **kwargs)
        self.router = router
        self.theme = ThemeManager()
        
        self._create_ui()
    
    def _create_ui(self):
        """Create credit sale interface."""
        # Header
        header_frame = ctk.CTkFrame(self)
        header_frame.pack(fill="x", padx=20, pady=10)
        
        title = ctk.CTkLabel(
            header_frame,
            text="Credit Sale",
            font=self.theme.get_font("heading"),
            text_color=self.theme.get_color("warning")
        )
        title.pack(side="left")
        
        # Main content
        content_frame = ctk.CTkFrame(self)
        content_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Customer selection (mandatory)
        customer_section = ctk.CTkFrame(content_frame)
        customer_section.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            customer_section,
            text="Customer (Required for Credit Sale)",
            font=self.theme.get_font("subheading")
        ).pack(anchor="w", padx=5, pady=5)
        
        self.customer_var = ctk.StringVar(value="")
        customer_dropdown = ctk.CTkOptionMenu(
            customer_section,
            variable=self.customer_var,
            values=["Select Customer..."]  # Will be populated from DB
        )
        customer_dropdown.pack(fill="x", padx=5, pady=5)
        
        # Credit info display
        credit_info = ctk.CTkFrame(content_frame)
        credit_info.pack(fill="x", pady=10)
        
        self.credit_limit_label = ctk.CTkLabel(
            credit_info,
            text="Credit Limit: Rs. 0.00"
        )
        self.credit_limit_label.pack(anchor="w", padx=5, pady=2)
        
        self.current_due_label = ctk.CTkLabel(
            credit_info,
            text="Current Due: Rs. 0.00"
        )
        self.current_due_label.pack(anchor="w", padx=5, pady=2)
        
        self.available_credit_label = ctk.CTkLabel(
            credit_info,
            text="Available Credit: Rs. 0.00",
            text_color=self.theme.get_color("success")
        )
        self.available_credit_label.pack(anchor="w", padx=5, pady=2)
        
        # Due amount display
        due_section = ctk.CTkFrame(content_frame)
        due_section.pack(fill="x", pady=20)
        
        ctk.CTkLabel(
            due_section,
            text="Amount Due After This Sale:",
            font=self.theme.get_font("subheading")
        ).pack(anchor="w", padx=5, pady=5)
        
        self.due_amount_label = ctk.CTkLabel(
            due_section,
            text="Rs. 0.00",
            font=("Segoe UI", 24, "bold"),
            text_color=self.theme.get_color("danger")
        )
        self.due_amount_label.pack(anchor="w", padx=5, pady=10)
        
        # Action buttons
        action_frame = ctk.CTkFrame(content_frame)
        action_frame.pack(fill="x", pady=20)
        
        cancel_btn = ctk.CTkButton(
            action_frame,
            text="Cancel",
            fg_color=self.theme.get_color("danger"),
            command=lambda: self.router.navigate_to("new_sale")
        )
        cancel_btn.pack(side="left", padx=5)
        
        save_btn = ctk.CTkButton(
            action_frame,
            text="Process Credit Sale",
            fg_color=self.theme.get_color("primary"),
            height=50,
            command=self._process_credit_sale
        )
        save_btn.pack(side="right", padx=5)
    
    def _process_credit_sale(self):
        """Process credit sale with validation."""
        # TODO: Implement credit sale logic
        pass
