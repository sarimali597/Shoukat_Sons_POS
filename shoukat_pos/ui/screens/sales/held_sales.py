"""Held Sales Screen - Manage suspended transactions."""

import customtkinter as ctk
from typing import List, Dict

from ui.theme import ThemeManager
from ui.components import DataTable
from ui.dialogs.confirmation_dialog import ConfirmationDialog


class HeldSalesScreen(ctk.CTkFrame):
    """Held Sales management screen."""
    
    def __init__(self, master, router, **kwargs):
        super().__init__(master, **kwargs)
        self.router = router
        self.theme = ThemeManager()
        
        self._create_ui()
    
    def _create_ui(self):
        """Create held sales interface."""
        # Header
        header_frame = ctk.CTkFrame(self)
        header_frame.pack(fill="x", padx=20, pady=10)
        
        title = ctk.CTkLabel(
            header_frame,
            text="Held Sales",
            font=self.theme.get_font("heading")
        )
        title.pack(side="left")
        
        # Content area
        content_frame = ctk.CTkFrame(self)
        content_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Info label
        info_label = ctk.CTkLabel(
            content_frame,
            text="Select a held sale to resume or discard",
            font=self.theme.get_font("body")
        )
        info_label.pack(pady=10)
        
        # Placeholder for held sales list
        placeholder = ctk.CTkLabel(
            content_frame,
            text="Held Sales Table (tksheet integration coming)",
            font=self.theme.get_font("body")
        )
        placeholder.pack(expand=True)
        
        # Action buttons at bottom
        action_frame = ctk.CTkFrame(self)
        action_frame.pack(fill="x", padx=20, pady=10)
        
        resume_btn = ctk.CTkButton(
            action_frame,
            text="Resume Selected",
            fg_color=self.theme.get_color("primary"),
            command=self._resume_sale
        )
        resume_btn.pack(side="left", padx=5)
        
        discard_btn = ctk.CTkButton(
            action_frame,
            text="Discard Selected",
            fg_color=self.theme.get_color("danger"),
            command=self._discard_sale
        )
        discard_btn.pack(side="left", padx=5)
        
        back_btn = ctk.CTkButton(
            action_frame,
            text="Back to New Sale",
            fg_color=self.theme.get_color("surface"),
            border_width=1,
            border_color=self.theme.get_color("border"),
            command=lambda: self.router.navigate_to("new_sale")
        )
        back_btn.pack(side="right", padx=5)
    
    def _resume_sale(self):
        """Resume selected held sale."""
        # TODO: Implement resume logic
        pass
    
    def _discard_sale(self):
        """Discard selected held sale."""
        dialog = ConfirmationDialog(
            self,
            title="Discard Held Sale",
            message="This action cannot be undone. Discard this held sale?",
            confirm_text="Discard",
            cancel_text="Cancel"
        )
        if dialog.show():
            # TODO: Implement discard logic
            pass
