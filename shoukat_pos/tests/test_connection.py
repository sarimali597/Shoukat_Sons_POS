"""
Tests for ConnectionManager.

Verifies pragmas, transaction rollback, integrity check, and singleton behavior.
"""

import sqlite3
from pathlib import Path

import pytest

from database.connection import ConnectionManager


class TestConnectionManagerSingleton:
    """Test ConnectionManager singleton behavior."""

    def test_singleton_returns_same_instance(self, temp_db_path: Path) -> None:
        """Test that ConnectionManager returns the same instance."""
        assert ConnectionManager._instance is None
        
        cm1 = ConnectionManager(database_path=temp_db_path)
        cm2 = ConnectionManager(database_path=temp_db_path)
        
        assert cm1 is cm2
        
        # Cleanup
        cm1.close_all()

    def test_singleton_reset_after_close_all(self, temp_db_path: Path) -> None:
        """Test that close_all resets the singleton."""
        ConnectionManager._instance = None
        
        cm = ConnectionManager(database_path=temp_db_path)
        assert ConnectionManager._instance is not None
        
        cm.close_all()
        assert ConnectionManager._instance is None


class TestConnectionManagerPragmas:
    """Test that ConnectionManager applies correct pragmas."""

    def test_wal_mode_applied(self, connection_manager: ConnectionManager) -> None:
        """Test that WAL mode is applied to connections."""
        conn = connection_manager.get_read_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        assert result[0] == "wal"

    def test_foreign_keys_enabled(self, connection_manager: ConnectionManager) -> None:
        """Test that foreign keys are enabled."""
        conn = connection_manager.get_read_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        assert result[0] == 1

    def test_busy_timeout_set(self, connection_manager: ConnectionManager) -> None:
        """Test that busy timeout is set to 10 seconds."""
        conn = connection_manager.get_read_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA busy_timeout")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        assert result[0] == 10000

    def test_synchronous_normal(self, connection_manager: ConnectionManager) -> None:
        """Test that synchronous mode is NORMAL."""
        conn = connection_manager.get_read_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA synchronous")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        assert result[0] == 1  # NORMAL = 1

    def test_row_factory_set(self, connection_manager: ConnectionManager) -> None:
        """Test that row_factory is set to sqlite3.Row."""
        conn = connection_manager.get_read_connection()
        assert conn.row_factory == sqlite3.Row
        conn.close()


class TestConnectionManagerTransaction:
    """Test transaction management with rollback."""

    def test_transaction_commits_on_success(
        self, connection_manager: ConnectionManager, db_connection: sqlite3.Connection
    ) -> None:
        """Test that transaction commits successfully."""
        with connection_manager.execute_transaction() as conn:
            conn.execute(
                "INSERT INTO vendors (name, location, phone, created_at) VALUES (?, ?, ?, ?)",
                ("Test Vendor", "Test City", "1234567890", "2024-01-15T10:00:00"),
            )
        
        # Verify insert was committed
        conn = connection_manager.get_read_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM vendors WHERE name = ?", ("Test Vendor",))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        assert result[0] == 1

    def test_transaction_rollback_on_error(
        self, connection_manager: ConnectionManager
    ) -> None:
        """Test that transaction rolls back on error."""
        # First create tables
        from database.schema import create_tables
        create_tables(connection_manager.get_read_connection())
        
        try:
            with connection_manager.execute_transaction() as conn:
                conn.execute(
                    "INSERT INTO vendors (name, location, phone, created_at) VALUES (?, ?, ?, ?)",
                    ("Test Vendor", "Test City", "1234567890", "2024-01-15T10:00:00"),
                )
                # Force an error - insert into non-existent table
                conn.execute("INSERT INTO nonexistent_table VALUES (1)")
        except sqlite3.DatabaseError:
            pass  # Expected
        
        # Verify no insert was committed
        conn = connection_manager.get_read_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM vendors")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        assert result[0] == 0


class TestConnectionManagerIntegrityCheck:
    """Test integrity check functionality."""

    def test_integrity_check_valid_database(
        self, connection_manager: ConnectionManager, db_connection: sqlite3.Connection
    ) -> None:
        """Test integrity check on valid database."""
        result = connection_manager.integrity_check(db_connection)
        
        assert result["is_valid"] is True
        assert len(result["errors"]) == 0

    def test_integrity_check_creates_connection_if_needed(
        self, connection_manager: ConnectionManager
    ) -> None:
        """Test integrity check creates its own connection if none provided."""
        # Create tables first
        from database.schema import create_tables, seed_data
        conn = connection_manager.get_read_connection()
        create_tables(conn)
        seed_data(conn)
        conn.close()
        
        # Now run integrity check without providing connection
        result = connection_manager.integrity_check()
        
        assert result["is_valid"] is True


class TestConnectionManagerWriteLock:
    """Test write lock serialization."""

    def test_write_lock_acquire_release(self, connection_manager: ConnectionManager) -> None:
        """Test that write lock can be acquired and released."""
        conn = connection_manager.get_write_connection()
        assert conn is not None
        
        connection_manager.release_write_connection()
        # Should not raise

    def test_release_without_acquire_does_not_raise(
        self, connection_manager: ConnectionManager
    ) -> None:
        """Test that releasing without acquiring doesn't raise."""
        # Should not raise
        connection_manager.release_write_connection()
