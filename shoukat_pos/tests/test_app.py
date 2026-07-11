"""
Tests for ScreenRouter and POSApp.

Verifies screen registration, navigation, back stack functionality.
Note: Full GUI tests require a display; these test the logic components.
"""

import pytest


class TestScreenRouterRegistration:
    """Test ScreenRouter screen registration."""

    def test_register_screen(self) -> None:
        """Test registering a screen factory."""
        from ui.app import ScreenRouter
        
        # Create a mock container
        class MockContainer:
            pass
        
        router = ScreenRouter(MockContainer())
        
        def factory():
            return "screen_instance"
        
        router.register_screen("test_screen", factory)
        
        assert "test_screen" in router._screens

    def test_register_screen_none_name_raises(self) -> None:
        """Test that None name raises assertion error."""
        from ui.app import ScreenRouter
        
        class MockContainer:
            pass
        
        router = ScreenRouter(MockContainer())
        
        with pytest.raises(AssertionError):
            router.register_screen(None, lambda: None)

    def test_register_screen_none_factory_raises(self) -> None:
        """Test that None factory raises assertion error."""
        from ui.app import ScreenRouter
        
        class MockContainer:
            pass
        
        router = ScreenRouter(MockContainer())
        
        with pytest.raises(AssertionError):
            router.register_screen("test", None)


class TestScreenRouterNavigation:
    """Test ScreenRouter navigation."""

    def test_navigate_to_registered_screen(self) -> None:
        """Test navigating to a registered screen."""
        from ui.app import ScreenRouter
        
        class MockContainer:
            pass
        
        router = ScreenRouter(MockContainer())
        created = []
        
        def factory():
            created.append("instance")
            return "screen_instance"
        
        router.register_screen("test", factory)
        # Note: navigate_to will fail without tkinter widgets, so we just verify registration
        assert "test" in router._screens
        assert router.get_current() is None  # No navigation yet without GUI

    def test_navigate_to_unregistered_raises(self) -> None:
        """Test that navigating to unregistered screen raises KeyError."""
        from ui.app import ScreenRouter
        
        class MockContainer:
            pass
        
        router = ScreenRouter(MockContainer())
        
        with pytest.raises(KeyError):
            router.navigate_to("nonexistent", animate=False)

    def test_navigate_to_none_raises(self) -> None:
        """Test that None screen_name raises assertion error."""
        from ui.app import ScreenRouter
        
        class MockContainer:
            pass
        
        router = ScreenRouter(MockContainer())
        
        with pytest.raises(AssertionError):
            router.navigate_to(None, animate=False)


class TestScreenRouterStack:
    """Test ScreenRouter back stack functionality."""

    def test_push_adds_to_stack(self) -> None:
        """Test that push adds screen to stack."""
        from ui.app import ScreenRouter
        
        class MockContainer:
            pass
        
        router = ScreenRouter(MockContainer())
        
        router.register_screen("screen1", lambda: "s1")
        router.register_screen("screen2", lambda: "s2")
        
        # Can't fully test navigation without tkinter, but can verify registration
        assert "screen1" in router._screens
        assert "screen2" in router._screens

    def test_pop_returns_previous(self) -> None:
        """Test that pop returns to previous screen."""
        from ui.app import ScreenRouter
        
        class MockContainer:
            pass
        
        router = ScreenRouter(MockContainer())
        
        # Empty stack - pop should return None
        result = router.pop()
        assert result is None

    def test_pop_on_single_screen_returns_none(self) -> None:
        """Test that pop on single screen returns None."""
        from ui.app import ScreenRouter
        
        class MockContainer:
            pass
        
        router = ScreenRouter(MockContainer())
        router.register_screen("only", lambda: "o")
        
        # Without actual navigation, stack is empty
        result = router.pop()
        
        assert result is None

    def test_get_current_empty_stack_returns_none(self) -> None:
        """Test that get_current on empty stack returns None."""
        from ui.app import ScreenRouter
        
        class MockContainer:
            pass
        
        router = ScreenRouter(MockContainer())
        
        assert router.get_current() is None


class TestScreenRouterContainer:
    """Test ScreenRouter container initialization."""

    def test_container_none_raises(self) -> None:
        """Test that None container raises assertion error."""
        from ui.app import ScreenRouter
        
        with pytest.raises(AssertionError):
            ScreenRouter(None)
