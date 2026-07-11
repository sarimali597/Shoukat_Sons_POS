"""Customer Manager Screen - Manage customer accounts and credit."""

import customtkinter as ctk
from typing import List, Dict, Optional

from ui.theme import ThemeManager
from ui.components import DataTable


class CustomerManagerScreen(ctk.CTkFrame):
    """Customer management screen with ledger and payment recording."""
    
    def __init__(self, master, router, **kwargs):
        super().__init__(master, **kwargs)
        self.router = router
        self.theme = ThemeManager()
        
        self._create_ui()
    
    def _create_ui(self):
        """Create customer manager interface."""
        # Header
        header_frame = ctk.CTkFrame(self)
        header_frame.pack(fill="x", padx=20, pady=10)
        
        title = ctk.CTkLabel(
            header_frame,
            text="Customer Management",
            font=self.theme.get_font("heading")
        )
        title.pack(side="left")
        
        new_customer_btn = ctk.CTkButton(
            header_frame,
            text="+ New Customer",
            fg_color=self.theme.get_color("success"),
            command=self._add_customer
        )
        new_customer_btn.pack(side="right")
        
        # Search bar
        search_frame = ctk.CTkFrame(self)
        search_frame.pack(fill="x", padx=20, pady=10)
        
        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="Search by name or phone...", width=300)
        self.search_entry.pack(side="left", padx=5)
        
        search_btn = ctk.CTkButton(
            search_frame,
            text="Search",
            command=self._search_customers
        )
        search_btn.pack(side="left")
        
        # Customer list placeholder
        content_frame = ctk.CTkFrame(self)
        content_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        placeholder = ctk.CTkLabel(
            content_frame,
            text="Customer List (DataTable integration coming)",
            font=self.theme.get_font("body")
        )
        placeholder.pack(expand=True)
    
    def _add_customer(self):
        """Add new customer."""
        # TODO: Implement add customer dialog
        pass
    
    def _search_customers(self):
        """Search customers by name or phone."""
        # TODO: Implement search logic
        pass
