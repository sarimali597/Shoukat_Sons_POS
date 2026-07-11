"""
Main application class and screen router for Shoukat Sons Garments POS.

Provides ScreenRouter for navigation between screens and POSApp as the main window.
Includes sidebar navigation, responsive layout, and light/dark mode toggle.
"""

import tkinter as tk
from typing import Any, Callable, Dict, List, Optional, Tuple

import customtkinter as ctk

from ui.animations import fade_in_window
from ui.theme import ThemeManager, get_theme_manager


class ScreenRouter:
    """
    Screen navigation router with frame caching and transitions.

    Maintains a dictionary of instantiated screen frames and handles
    navigation with optional animations.

    Attributes:
        _screens: Dictionary of registered screen factories.
        _instances: Dictionary of instantiated screen frames.
        _stack: Navigation stack for back functionality.
    """

    def __init__(self, container: ctk.CTkBaseClass) -> None:
        """
        Initialize the ScreenRouter.

        Args:
            container: Parent container for all screens.
        """
        assert container is not None, "container cannot be None"

        self.container = container
        self._screens: Dict[str, Callable] = {}
        self._instances: Dict[str, ctk.CTkFrame] = {}
        self._stack: List[str] = []

    def register_screen(self, name: str, factory: Callable[[], ctk.CTkFrame]) -> None:
        """
        Register a screen with lazy instantiation.

        Args:
            name: Unique screen name.
            factory: Callable that creates the screen frame.
        """
        assert name is not None, "name cannot be None"
        assert factory is not None, "factory cannot be None"

        self._screens[name] = factory

    def navigate_to(self, screen_name: str, animate: bool = True, **kwargs: Any) -> None:
        """
        Navigate to a screen, creating it if needed.

        Args:
            screen_name: Name of the screen to navigate to.
            animate: Whether to animate the transition.
            **kwargs: Arguments passed to the screen factory.
        """
        assert screen_name is not None, "screen_name cannot be None"

        # Create screen if not already instantiated
        if screen_name not in self._instances:
            if screen_name not in self._screens:
                raise KeyError(f"Screen '{screen_name}' not registered")
            self._instances[screen_name] = self._screens[screen_name]()

        # Hide all screens
        for instance in self._instances.values():
            instance.pack_forget()

        # Show target screen
        screen = self._instances[screen_name]
        screen.pack(fill="both", expand=True)

        # Animate if requested
        if animate and hasattr(screen, "winfo_toplevel"):
            fade_in_window(screen.winfo_toplevel(), duration_ms=150)

        # Push to stack (only if different from current)
        if not self._stack or self._stack[-1] != screen_name:
            self._stack.append(screen_name)

    def push(self, screen_name: str, **kwargs: Any) -> None:
        """
        Push a screen onto the navigation stack.

        Args:
            screen_name: Name of the screen to push.
            **kwargs: Arguments passed to the screen factory.
        """
        self.navigate_to(screen_name, **kwargs)

    def pop(self) -> Optional[str]:
        """
        Pop the current screen and return to the previous one.

        Returns:
            Name of the previous screen, or None if stack is empty.
        """
        if len(self._stack) <= 1:
            return None

        self._stack.pop()
        previous = self._stack[-1]
        self.navigate_to(previous, animate=False)
        return previous

    def get_current(self) -> Optional[str]:
        """
        Get the current screen name.

        Returns:
            Current screen name or None.
        """
        return self._stack[-1] if self._stack else None


class POSApp(ctk.CTk):
    """
    Main application window for Shoukat Sons Garments POS.

    Includes sidebar navigation, main content area, and responsive layout.
    """

    def __init__(self) -> None:
        """Initialize the main application window."""
        super().__init__()

        self._theme = get_theme_manager()
        self._current_breakpoint = "standard"

        # Configure window
        self.title("Shoukat Sons Garments POS")
        self.geometry("1366x768")
        self.minsize(1024, 768)

        # Apply initial theme
        self._apply_theme()

        # Create layout
        self._create_sidebar()
        self._create_main_area()

        # Setup screen router
        self.router = ScreenRouter(self.main_area)

        # Bind resize event for responsive layout
        self.bind("<Configure>", self._on_resize)
        self._resize_job: Optional[int] = None

        # Register default screens (stubs for now)
        self._register_default_screens()

        # Navigate to dashboard
        self.router.navigate_to("dashboard", animate=False)

    def _apply_theme(self) -> None:
        """Apply current theme to the application."""
        bg_color = self._theme.get_color("bg")
        self.configure(fg_color=bg_color)

    def _create_sidebar(self) -> None:
        """Create the sidebar navigation panel."""
        sidebar_width = 200

        self.sidebar = ctk.CTkFrame(self, width=sidebar_width, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")

        # Logo/Title
        self.logo_label = ctk.CTkLabel(
            self.sidebar,
            text="Shoukat Sons\nGarments",
            font=self._theme.get_font("heading"),
            text_color=self._theme.get_color("primary"),
        )
        self.logo_label.pack(pady=20)

        # Navigation items
        nav_items = [
            ("Dashboard", "dashboard"),
            ("Products", "products"),
            ("Sales", "sales"),
            ("Customers", "customers"),
            ("Reports", "reports"),
            ("Settings", "settings"),
        ]

        for label_text, screen_name in nav_items:
            btn = ctk.CTkButton(
                self.sidebar,
                text=label_text,
                command=lambda name=screen_name: self.router.navigate_to(name),
                anchor="w",
                height=40,
                font=self._theme.get_font("button"),
            )
            btn.pack(fill="x", padx=10, pady=5)

        # Theme toggle at bottom
        self.theme_btn = ctk.CTkButton(
            self.sidebar,
            text="🌙 Dark Mode",
            command=self._toggle_theme,
            height=40,
            font=self._theme.get_font("button"),
        )
        self.theme_btn.pack(side="bottom", fill="x", padx=10, pady=20)

        self._update_theme_button_text()

    def _create_main_area(self) -> None:
        """Create the main content area."""
        self.main_area = ctk.CTkFrame(self, corner_radius=0)
        self.main_area.pack(side="right", fill="both", expand=True)

    def _register_default_screens(self) -> None:
        """Register default screen implementations."""
        # Dashboard
        def dashboard_factory() -> ctk.CTkFrame:
            from ui.screens.dashboard_screen import DashboardScreen
            user_info = {"username": "Admin", "user_id": 1, "role": "admin"}
            return DashboardScreen(self.main_area, user_info, self.router)
        
        self.router.register_screen("dashboard", dashboard_factory)
        
        # Product screens
        def product_list_factory() -> ctk.CTkFrame:
            from ui.screens.products.product_list import ProductListScreen
            return ProductListScreen(self.main_area, self.router, {"username": "Admin", "user_id": 1, "role": "admin"})
        
        self.router.register_screen("products", product_list_factory)
        
        def quick_restock_factory() -> ctk.CTkFrame:
            from ui.screens.products.quick_restock import QuickRestockScreen
            return QuickRestockScreen(self.main_area, self.router, {"username": "Admin", "user_id": 1, "role": "admin"})
        
        self.router.register_screen("quick_restock", quick_restock_factory)
        
        def print_labels_factory() -> ctk.CTkFrame:
            from ui.screens.products.print_labels import PrintLabelsScreen
            return PrintLabelsScreen(self.main_area, self.router, {"username": "Admin", "user_id": 1, "role": "admin"})
        
        self.router.register_screen("print_labels", print_labels_factory)
        
        # Placeholder screens for now (to be implemented in subsequent stages)
        def make_placeholder(title: str) -> Callable[[], ctk.CTkFrame]:
            def factory() -> ctk.CTkFrame:
                frame = ctk.CTkFrame(self.main_area)
                label = ctk.CTkLabel(
                    frame,
                    text=f"{title} Screen - Coming Soon",
                    font=self._theme.get_font("heading"),
                )
                label.pack(expand=True)
                return frame
            
            return factory
        
        screens = ["sales", "customers", "reports", "settings", "add_product"]
        for screen in screens:
            self.router.register_screen(screen, make_placeholder(screen.replace("_", " ").title()))

    def _toggle_theme(self) -> None:
        """Toggle between light and dark modes."""
        self._theme.toggle_mode()
        self._apply_theme()
        self._update_theme_button_text()

    def _update_theme_button_text(self) -> None:
        """Update theme toggle button text based on current mode."""
        mode = self._theme.current_mode
        if mode == "light":
            self.theme_btn.configure(text="🌙 Dark Mode")
        else:
            self.theme_btn.configure(text="☀️ Light Mode")

    def _on_resize(self, event: tk.Event) -> None:
        """Handle window resize with debouncing."""
        if self._resize_job:
            self.after_cancel(self._resize_job)

        self._resize_job = self.after(200, lambda: self._handle_resize(event.width))

    def _handle_resize(self, width: int) -> None:
        """Handle responsive layout changes."""
        breakpoint = self._theme.get_breakpoint(width)

        if breakpoint != self._current_breakpoint:
            self._current_breakpoint = breakpoint
            self._apply_responsive_layout()

    def _apply_responsive_layout(self) -> None:
        """Apply responsive layout based on current breakpoint."""
        if self._current_breakpoint == "compact":
            # Collapse sidebar to icons only
            self.sidebar.configure(width=60)
            for widget in self.sidebar.winfo_children():
                if isinstance(widget, ctk.CTkButton):
                    # Could show icon-only here
                    pass
        elif self._current_breakpoint == "standard":
            self.sidebar.configure(width=200)
        else:  # wide
            self.sidebar.configure(width=250)


def run_app() -> None:
    """Run the POS application."""
    app = POSApp()
    app.mainloop()


if __name__ == "__main__":
    run_app()
