"""General Settings Screen - Configure shop info, users, and preferences."""

import customtkinter as ctk
from typing import Dict

from ui.theme import ThemeManager
from ui.dialogs.password_dialog import PasswordDialog


class GeneralSettingsScreen(ctk.CTkFrame):
    """General settings configuration screen."""
    
    def __init__(self, master, router, **kwargs):
        super().__init__(master, **kwargs)
        self.router = router
        self.theme = ThemeManager()
        
        self._create_ui()
    
    def _create_ui(self):
        """Create general settings interface."""
        # Header
        header_frame = ctk.CTkFrame(self)
        header_frame.pack(fill="x", padx=20, pady=10)
        
        title = ctk.CTkLabel(
            header_frame,
            text="General Settings",
            font=self.theme.get_font("heading")
        )
        title.pack(side="left")
        
        save_btn = ctk.CTkButton(
            header_frame,
            text="Save Changes",
            fg_color=self.theme.get_color("success"),
            command=self._save_settings
        )
        save_btn.pack(side="right")
        
        # Scrollable content
        scroll_frame = ctk.CTkScrollableFrame(self)
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Shop Information Section
        shop_section = ctk.CTkFrame(scroll_frame)
        shop_section.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            shop_section,
            text="Shop Information",
            font=self.theme.get_font("subheading")
        ).pack(anchor="w", padx=5, pady=5)
        
        self.shop_name = ctk.CTkEntry(shop_section, placeholder_text="Shop Name", width=400)
        self.shop_name.insert(0, "Shoukat Sons Garments")
        self.shop_name.pack(anchor="w", padx=5, pady=5)
        
        self.shop_address = ctk.CTkEntry(shop_section, placeholder_text="Address", width=400)
        self.shop_address.pack(anchor="w", padx=5, pady=5)
        
        self.shop_phone = ctk.CTkEntry(shop_section, placeholder_text="Phone", width=400)
        self.shop_phone.pack(anchor="w", padx=5, pady=5)
        
        self.shop_gstin = ctk.CTkEntry(shop_section, placeholder_text="GSTIN (Optional)", width=400)
        self.shop_gstin.pack(anchor="w", padx=5, pady=5)
        
        # Preferences Section
        pref_section = ctk.CTkFrame(scroll_frame)
        pref_section.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            pref_section,
            text="Preferences",
            font=self.theme.get_font("subheading")
        ).pack(anchor="w", padx=5, pady=5)
        
        # Theme toggle
        theme_frame = ctk.CTkFrame(pref_section)
        theme_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(theme_frame, text="Theme:").pack(side="left", padx=5)
        
        self.theme_var = ctk.StringVar(value=self.theme.current_mode)
        theme_toggle = ctk.CTkSegmentedButton(
            theme_frame,
            values=["light", "dark"],
            variable=self.theme_var,
            command=self._toggle_theme
        )
        theme_toggle.pack(side="left", padx=5)
        
        # Session timeout
        timeout_frame = ctk.CTkFrame(pref_section)
        timeout_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(timeout_frame, text="Session Timeout (minutes):").pack(side="left", padx=5)
        
        self.timeout_entry = ctk.CTkEntry(timeout_frame, width=100)
        self.timeout_entry.insert(0, "30")
        self.timeout_entry.pack(side="left", padx=5)
        
        # Edit Password Section
        password_section = ctk.CTkFrame(scroll_frame)
        password_section.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            password_section,
            text="Edit Protection Password",
            font=self.theme.get_font("subheading")
        ).pack(anchor="w", padx=5, pady=5)
        
        ctk.CTkLabel(
            password_section,
            text="This password protects sensitive operations like editing products and viewing profit reports.",
            font=self.theme.get_font("small"),
            text_color=self.theme.get_color("text_secondary")
        ).pack(anchor="w", padx=5, pady=5)
        
        change_pwd_btn = ctk.CTkButton(
            password_section,
            text="Change Edit Password",
            command=self._change_edit_password
        )
        change_pwd_btn.pack(anchor="w", padx=5, pady=5)
    
    def _toggle_theme(self, value):
        """Toggle between light and dark theme."""
        self.theme.toggle_mode()
    
    def _change_edit_password(self):
        """Change edit protection password."""
        dialog = PasswordDialog(
            self,
            title="Set Edit Password",
            message="Enter new edit protection password:"
        )
        result = dialog.show()
        if result[0]:  # confirmed
            # TODO: Save password hash via SettingsService
            pass
    
    def _save_settings(self):
        """Save all settings."""
        # TODO: Save settings via SettingsService
        pass
