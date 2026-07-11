"""Login screen for Shoukat Sons Garments POS."""
import customtkinter as ctk
from typing import Callable
from ui.theme import ThemeManager
from ui.animations import fade_in_window
from services.auth_service import AuthService
from database.connection import ConnectionManager


class LoginScreen(ctk.CTkFrame):
    """Login screen with username/password authentication."""
    
    def __init__(self, master, on_login_success: Callable[[dict], None], **kwargs):
        super().__init__(master, **kwargs)
        self.theme = ThemeManager()
        self.cm = ConnectionManager()
        self.auth_service = AuthService(self.cm)
        self.on_login_success = on_login_success
        
        self._setup_ui()
        fade_in_window(self.master, duration_ms=200)
    
    def _setup_ui(self) -> None:
        """Configure login UI components."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)
        
        # Logo/Title
        title_label = ctk.CTkLabel(
            self,
            text="Shoukat Sons Garments",
            font=self.theme.get_font("heading")
        )
        title_label.grid(row=0, column=0, pady=(40, 10))
        
        subtitle = ctk.CTkLabel(
            self,
            text="POS System",
            font=self.theme.get_font("subheading"),
            text_color=self.theme.get_color("text_secondary")
        )
        subtitle.grid(row=1, column=0, pady=(0, 30))
        
        # Username field
        self.username_entry = ctk.CTkEntry(
            self,
            placeholder_text="Username",
            width=300,
            height=40,
            font=self.theme.get_font("body")
        )
        self.username_entry.grid(row=2, column=0, pady=10)
        self.username_entry.bind("<Return>", lambda e: self.password_entry.focus())
        
        # Password field
        self.password_entry = ctk.CTkEntry(
            self,
            placeholder_text="Password",
            width=300,
            height=40,
            font=self.theme.get_font("body"),
            show="•"
        )
        self.password_entry.grid(row=3, column=0, pady=10)
        self.password_entry.bind("<Return>", lambda e: self._attempt_login())
        
        # Login button
        login_btn = ctk.CTkButton(
            self,
            text="Login",
            command=self._attempt_login,
            width=300,
            height=45,
            font=self.theme.get_font("button")
        )
        login_btn.grid(row=4, column=0, pady=20)
        
        # Error label (hidden by default)
        self.error_label = ctk.CTkLabel(
            self,
            text="",
            text_color=self.theme.get_color("danger"),
            font=self.theme.get_font("small")
        )
        self.error_label.grid(row=5, column=0, pady=(0, 10))
        
        # Focus username on load
        self.after(100, lambda: self.username_entry.focus())
        
        # Apply theme
        self.theme.apply_to_widget(self, bg_key="bg")
    
    def _attempt_login(self) -> None:
        """Validate credentials and login."""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        
        if not username or not password:
            self.error_label.configure(text="Please enter username and password")
            return
        
        try:
            conn = self.cm.get_read_connection()
            user = self.auth_service.authenticate(conn, username, password)
            
            if user:
                self.on_login_success({
                    "user_id": user.id,
                    "username": user.username,
                    "role": user.role
                })
            else:
                self.error_label.configure(text="Invalid username or password")
                self.password_entry.delete(0, 'end')
        except Exception as e:
            self.error_label.configure(text=f"Login error: {str(e)}")
