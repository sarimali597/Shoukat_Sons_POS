"""Authentication service for Shoukat Sons Garments POS.

Handles user authentication, password hashing, session management,
and account lockout after failed attempts.
"""

import bcrypt
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Dict, List
import sqlite3

from database.connection import ConnectionManager
from database.models import User


class AuthService:
    """Service for user authentication and session management."""

    def __init__(self, connection_manager: ConnectionManager):
        """Initialize AuthService.

        Args:
            connection_manager: Database connection manager instance.
        """
        self.cm = connection_manager
        self._current_user: Optional[User] = None
        self._session_start: Optional[float] = None
        self._failed_attempts: Dict[str, List[float]] = {}
        self._lockout_until: Dict[str, float] = {}

    def hash_password(self, password: str) -> str:
        """Hash password with bcrypt, rounds=12.

        Args:
            password: Plain text password to hash.

        Returns:
            Bcrypt hash string.
        """
        assert isinstance(password, str) and len(password) >= 1
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash.

        Args:
            password: Plain text password to verify.
            password_hash: Bcrypt hash to compare against.

        Returns:
            True if password matches, False otherwise.
        """
        assert isinstance(password, str) and isinstance(password_hash, str)
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                password_hash.encode('utf-8')
            )
        except (ValueError, TypeError):
            return False

    def authenticate(self, username: str, password: str) -> Tuple[bool, str]:
        """Authenticate a user. Returns (success, message).

        Lock account for 15 minutes after 5 failed attempts within 15 minutes.

        Args:
            username: Username to authenticate.
            password: Password to verify.

        Returns:
            Tuple of (success: bool, message: str).
        """
        assert isinstance(username, str) and isinstance(password, str)
        
        now = datetime.now(timezone.utc).timestamp()
        
        # Check if account is locked
        if username in self._lockout_until:
            if now < self._lockout_until[username]:
                remaining = int(self._lockout_until[username] - now)
                return False, f"Account locked. Try again in {remaining // 60} minutes."
            else:
                # Lockout expired, clear it
                del self._lockout_until[username]
                self._failed_attempts.pop(username, None)

        # Get user from database
        conn = self.cm.get_read_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE username = ? AND is_active = 1",
            (username,)
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row:
            # Record failed attempt
            self._record_failed_attempt(username, now)
            return False, "Invalid username or password"

        user = User.from_row(row)

        # Verify password
        if not self.verify_password(password, user.password_hash):
            self._record_failed_attempt(username, now)
            return False, "Invalid username or password"

        # Authentication successful
        self.reset_failed_attempts(username)
        self._current_user = user
        self._session_start = now
        
        # Update last_login
        self._update_last_login(user.id)
        
        return True, "Login successful"

    def _record_failed_attempt(self, username: str, timestamp: float) -> None:
        """Record a failed login attempt.

        Args:
            username: Username that failed authentication.
            timestamp: Unix timestamp of attempt.
        """
        if username not in self._failed_attempts:
            self._failed_attempts[username] = []
        
        # Keep only attempts within last 15 minutes
        cutoff = timestamp - (15 * 60)
        self._failed_attempts[username] = [
            t for t in self._failed_attempts[username] if t > cutoff
        ]
        self._failed_attempts[username].append(timestamp)
        
        # Lock out if 5 or more attempts
        if len(self._failed_attempts[username]) >= 5:
            self._lockout_until[username] = timestamp + (15 * 60)

    def reset_failed_attempts(self, username: str) -> None:
        """Reset failed attempts for a username.

        Args:
            username: Username to reset.
        """
        self._failed_attempts.pop(username, None)
        self._lockout_until.pop(username, None)

    def _update_last_login(self, user_id: int) -> None:
        """Update last_login timestamp for user.

        Args:
            user_id: ID of user to update.
        """
        with self.cm.execute_transaction() as conn:
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "UPDATE users SET last_login = ? WHERE id = ?",
                (now, user_id)
            )

    def create_user(self, username: str, password: str, role: str) -> int:
        """Create a new user. Returns user_id.

        Args:
            username: Unique username.
            password: Password to hash and store.
            role: User role (admin/cashier).

        Returns:
            New user's ID.

        Raises:
            ValueError: If username already exists.
        """
        assert isinstance(username, str) and isinstance(password, str)
        assert role in ("admin", "cashier")
        
        password_hash = self.hash_password(password)
        now = datetime.now(timezone.utc).isoformat()
        
        with self.cm.execute_transaction() as conn:
            try:
                conn.execute(
                    """INSERT INTO users (username, password_hash, role, is_active, created_at)
                       VALUES (?, ?, ?, 1, ?)""",
                    (username, password_hash, role, now)
                )
                user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                return user_id
            except sqlite3.IntegrityError:
                raise ValueError(f"Username '{username}' already exists")

    def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """Change user password.

        Args:
            user_id: ID of user.
            old_password: Current password for verification.
            new_password: New password to set.

        Returns:
            True if successful, False otherwise.
        """
        assert isinstance(user_id, int) and isinstance(old_password, str)
        assert isinstance(new_password, str) and len(new_password) >= 8
        
        conn = self.cm.get_read_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT password_hash FROM users WHERE id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not row or not self.verify_password(old_password, row[0]):
            return False
        
        new_hash = self.hash_password(new_password)
        
        with self.cm.execute_transaction() as update_conn:
            update_conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (new_hash, user_id)
            )
        
        return True

    def logout(self) -> None:
        """Clear current user session."""
        self._current_user = None
        self._session_start = None

    def get_current_user(self) -> Optional[User]:
        """Get current logged-in user.

        Returns:
            Current User object or None if not logged in.
        """
        return self._current_user

    def is_admin(self) -> bool:
        """Check if current user has admin role.

        Returns:
            True if current user is admin, False otherwise.
        """
        if self._current_user is None:
            return False
        return self._current_user.is_admin()

    def check_session_timeout(self, timeout_minutes: int = 30) -> bool:
        """Check if session has exceeded timeout.

        Args:
            timeout_minutes: Session timeout in minutes.

        Returns:
            True if session is still valid, False if timed out.
        """
        if self._session_start is None:
            return False
        
        now = datetime.now(timezone.utc).timestamp()
        elapsed = now - self._session_start
        return elapsed < (timeout_minutes * 60)

    def update_session_activity(self) -> None:
        """Update session activity timestamp to prevent timeout."""
        if self._session_start is not None:
            self._session_start = datetime.now(timezone.utc).timestamp()
