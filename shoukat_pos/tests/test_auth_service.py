"""Tests for authentication service."""

import pytest
import time
from datetime import datetime, timezone, timedelta

from services.auth_service import AuthService
from database.connection import ConnectionManager


class TestAuthService:
    """Test suite for AuthService."""

    @pytest.fixture
    def auth_service(self, connection_manager: ConnectionManager) -> AuthService:
        """Create AuthService instance with test database."""
        return AuthService(connection_manager)

    @pytest.fixture
    def test_user(self, auth_service: AuthService) -> tuple:
        """Create a test user and return credentials."""
        username = "testuser"
        password = "testpass123"
        role = "cashier"
        user_id = auth_service.create_user(username, password, role)
        return username, password, role, user_id

    def test_hash_password(self, auth_service: AuthService) -> None:
        """Test password hashing produces valid bcrypt hash."""
        password = "securepassword"
        hash1 = auth_service.hash_password(password)
        hash2 = auth_service.hash_password(password)
        
        # Hashes should be different (salt is random)
        assert hash1 != hash2
        # Both should be valid bcrypt hashes
        assert hash1.startswith("$2b$")
        assert hash2.startswith("$2b$")
        # Length should be consistent (bcrypt hash format)
        assert len(hash1) == 60
        assert len(hash2) == 60

    def test_verify_password_correct(self, auth_service: AuthService, test_user: tuple) -> None:
        """Test password verification with correct password."""
        username, password, role, user_id = test_user
        
        # Get the hash from database
        conn = auth_service.cm.get_read_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
        stored_hash = cursor.fetchone()[0]
        cursor.close()
        
        # Verify should return True
        assert auth_service.verify_password(password, stored_hash) is True

    def test_verify_password_incorrect(self, auth_service: AuthService, test_user: tuple) -> None:
        """Test password verification with incorrect password."""
        username, password, role, user_id = test_user
        
        # Get the hash from database
        conn = auth_service.cm.get_read_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
        stored_hash = cursor.fetchone()[0]
        cursor.close()
        
        # Wrong password should return False
        assert auth_service.verify_password("wrongpassword", stored_hash) is False

    def test_authenticate_success(self, auth_service: AuthService, test_user: tuple) -> None:
        """Test successful authentication."""
        username, password, role, user_id = test_user
        
        success, message = auth_service.authenticate(username, password)
        
        assert success is True
        assert message == "Login successful"
        assert auth_service.get_current_user() is not None
        assert auth_service.get_current_user().username == username

    def test_authenticate_invalid_username(self, auth_service: AuthService) -> None:
        """Test authentication with non-existent username."""
        success, message = auth_service.authenticate("nonexistent", "password")
        
        assert success is False
        assert message == "Invalid username or password"
        assert auth_service.get_current_user() is None

    def test_authenticate_invalid_password(self, auth_service: AuthService, test_user: tuple) -> None:
        """Test authentication with wrong password."""
        username, password, role, user_id = test_user
        
        success, message = auth_service.authenticate(username, "wrongpassword")
        
        assert success is False
        assert message == "Invalid username or password"
        assert auth_service.get_current_user() is None

    def test_account_lockout(self, auth_service: AuthService, test_user: tuple) -> None:
        """Test account lockout after 5 failed attempts."""
        username, password, role, user_id = test_user
        
        # Make 5 failed attempts
        for i in range(5):
            success, message = auth_service.authenticate(username, "wrongpassword")
            assert success is False
        
        # 6th attempt should be locked out
        success, message = auth_service.authenticate(username, password)
        assert success is False
        assert "Account locked" in message

    def test_create_user(self, auth_service: AuthService) -> None:
        """Test creating a new user."""
        username = "newuser"
        password = "newpass123"
        role = "cashier"
        
        user_id = auth_service.create_user(username, password, role)
        
        assert user_id is not None
        assert user_id > 0
        
        # Verify user exists in database
        conn = auth_service.cm.get_read_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT username, role FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        assert row is not None
        assert row[0] == username
        assert row[1] == role

    def test_create_duplicate_user(self, auth_service: AuthService, test_user: tuple) -> None:
        """Test creating user with duplicate username raises error."""
        username, password, role, user_id = test_user
        
        with pytest.raises(ValueError, match="already exists"):
            auth_service.create_user(username, "anotherpass", "cashier")

    def test_change_password_success(self, auth_service: AuthService, test_user: tuple) -> None:
        """Test changing password successfully."""
        username, old_password, role, user_id = test_user
        
        new_password = "newpassword123"
        result = auth_service.change_password(user_id, old_password, new_password)
        
        assert result is True
        
        # Verify new password works
        success, message = auth_service.authenticate(username, new_password)
        assert success is True

    def test_change_password_wrong_old(self, auth_service: AuthService, test_user: tuple) -> None:
        """Test changing password with wrong old password fails."""
        username, old_password, role, user_id = test_user
        
        result = auth_service.change_password(user_id, "wrongoldpass", "newpassword123")
        
        assert result is False
        
        # Old password should still work
        success, message = auth_service.authenticate(username, old_password)
        assert success is True

    def test_logout(self, auth_service: AuthService, test_user: tuple) -> None:
        """Test logout clears session."""
        username, password, role, user_id = test_user
        
        # Login first
        auth_service.authenticate(username, password)
        assert auth_service.get_current_user() is not None
        
        # Logout
        auth_service.logout()
        assert auth_service.get_current_user() is None

    def test_is_admin(self, auth_service: AuthService) -> None:
        """Test admin role checking."""
        # Not logged in - should return False
        assert auth_service.is_admin() is False
        
        # Create admin user
        admin_id = auth_service.create_user("adminuser", "adminpass123", "admin")
        auth_service.authenticate("adminuser", "adminpass123")
        assert auth_service.is_admin() is True
        
        # Create cashier user
        auth_service.logout()
        cashier_id = auth_service.create_user("cashieruser", "cashierpass123", "cashier")
        auth_service.authenticate("cashieruser", "cashierpass123")
        assert auth_service.is_admin() is False

    def test_session_timeout(self, auth_service: AuthService, test_user: tuple) -> None:
        """Test session timeout checking."""
        username, password, role, user_id = test_user
        
        # Login
        auth_service.authenticate(username, password)
        
        # Should not be timed out immediately
        assert auth_service.check_session_timeout(30) is True
        
        # Manually set session start to 31 minutes ago
        auth_service._session_start = (datetime.now(timezone.utc).timestamp() - (31 * 60))
        
        # Should now be timed out
        assert auth_service.check_session_timeout(30) is False

    def test_update_session_activity(self, auth_service: AuthService, test_user: tuple) -> None:
        """Test updating session activity extends session."""
        username, password, role, user_id = test_user
        
        # Login
        auth_service.authenticate(username, password)
        original_start = auth_service._session_start
        
        # Wait a bit then update activity
        time.sleep(0.1)
        auth_service.update_session_activity()
        
        # Session start should be updated (more recent)
        assert auth_service._session_start > original_start

    def test_reset_failed_attempts(self, auth_service: AuthService, test_user: tuple) -> None:
        """Test resetting failed attempts after successful login."""
        username, password, role, user_id = test_user
        
        # Make some failed attempts
        for i in range(3):
            auth_service.authenticate(username, "wrongpassword")
        
        # Verify attempts are recorded
        assert username in auth_service._failed_attempts
        assert len(auth_service._failed_attempts[username]) == 3
        
        # Successful login should reset attempts
        auth_service.authenticate(username, password)
        assert username not in auth_service._failed_attempts
