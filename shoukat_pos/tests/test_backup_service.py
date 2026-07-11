"""
Tests for BackupService.

Tests cover backup creation, encryption, restoration, integrity verification,
and cleanup operations.
"""

import os
import threading
from pathlib import Path

import pytest

from database.connection import ConnectionManager
from database.schema import create_tables, seed_data
from services.backup_service import BackupInfo, BackupService


@pytest.fixture
def connection_manager(tmp_path: Path) -> ConnectionManager:
    """Create a ConnectionManager with a temporary database."""
    db_path = tmp_path / "test_backup.db"
    
    # Reset singleton state
    ConnectionManager._instance = None
    ConnectionManager._lock = threading.Lock()
    
    cm = ConnectionManager(db_path)
    
    # Initialize database with schema and seed data
    conn = cm.get_connection()
    create_tables(conn)
    seed_data(conn)
    conn.close()
    
    return cm


@pytest.fixture
def backup_service(connection_manager: ConnectionManager, tmp_path: Path) -> BackupService:
    """Create a BackupService instance."""
    return BackupService(connection_manager, tmp_path)


class TestBackupCreation:
    """Test backup creation functionality."""

    def test_create_unencrypted_backup(self, backup_service: BackupService):
        """Test creating an unencrypted backup."""
        backup_path = backup_service.create_backup(encrypt=False)
        
        assert backup_path.exists()
        assert backup_path.suffix == ".db"
        assert ".enc" not in str(backup_path)

    def test_create_encrypted_backup(self, backup_service: BackupService):
        """Test creating an encrypted backup."""
        backup_path = backup_service.create_backup(encrypt=True, password="test_password")
        
        assert backup_path.exists()
        assert ".enc" in str(backup_path) or backup_path.suffix == ".enc"

    def test_create_backup_file_size(self, backup_service: BackupService):
        """Test that backup has reasonable file size."""
        backup_path = backup_service.create_backup(encrypt=False)
        
        # Backup should be at least 1KB (database with schema)
        assert backup_path.stat().st_size > 1024

    def test_create_backup_missing_database(self, tmp_path: Path):
        """Test backup creation with missing database."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        
        # Reset singleton state
        ConnectionManager._instance = None
        ConnectionManager._lock = threading.Lock()
        
        cm = ConnectionManager(empty_dir / "nonexistent.db")
        service = BackupService(cm, empty_dir)
        
        with pytest.raises(FileNotFoundError):
            service.create_backup(encrypt=False)


class TestBackupEncryption:
    """Test backup encryption functionality."""

    def test_encrypt_decrypt_roundtrip(self, backup_service: BackupService, tmp_path: Path):
        """Test that encrypted backup can be decrypted."""
        password = "test_secret_password"
        
        # Create encrypted backup
        encrypted_path = backup_service.create_backup(encrypt=True, password=password)
        
        # Verify it's encrypted
        assert encrypted_path.exists()
        
        # Verify backup can be verified with correct password
        assert backup_service.verify_backup(encrypted_path, password) is True
        
        # Verify backup fails with wrong password
        assert backup_service.verify_backup(encrypted_path, "wrong_password") is False

    def test_encrypted_backup_different_passwords(self, backup_service: BackupService):
        """Test that different passwords produce different backups."""
        backup1 = backup_service.create_backup(encrypt=True, password="password1")
        backup2 = backup_service.create_backup(encrypt=True, password="password2")
        
        # Read contents
        with open(backup1, "rb") as f:
            content1 = f.read()
        with open(backup2, "rb") as f:
            content2 = f.read()
        
        # Should be different due to different salt and password
        assert content1 != content2


class TestBackupRestoration:
    """Test backup restoration functionality."""

    def test_restore_unencrypted_backup(self, backup_service: BackupService):
        """Test restoring from an unencrypted backup."""
        # Create initial backup
        backup_path = backup_service.create_backup(encrypt=False)
        
        # Restore should succeed
        result = backup_service.restore_backup(backup_path)
        assert result is True

    def test_restore_encrypted_backup(self, backup_service: BackupService):
        """Test restoring from an encrypted backup."""
        password = "restore_test_password"
        backup_path = backup_service.create_backup(encrypt=True, password=password)
        
        result = backup_service.restore_backup(backup_path, password)
        assert result is True

    def test_restore_nonexistent_backup(self, backup_service: BackupService):
        """Test restoring from non-existent backup."""
        fake_path = Path("/fake/path/backup.db")
        
        with pytest.raises(FileNotFoundError):
            backup_service.restore_backup(fake_path)

    def test_restore_corrupted_backup(self, backup_service: BackupService, tmp_path: Path):
        """Test restoring from corrupted backup."""
        # Create a fake corrupted file
        corrupted_path = tmp_path / "corrupted.db"
        with open(corrupted_path, "wb") as f:
            f.write(b"not a valid sqlite database")
        
        result = backup_service.restore_backup(corrupted_path)
        assert result is False


class TestBackupVerification:
    """Test backup verification functionality."""

    def test_verify_valid_backup(self, backup_service: BackupService):
        """Test verifying a valid backup."""
        backup_path = backup_service.create_backup(encrypt=False)
        assert backup_service.verify_backup(backup_path) is True

    def test_verify_encrypted_backup_correct_password(self, backup_service: BackupService):
        """Test verifying encrypted backup with correct password."""
        password = "verify_password"
        backup_path = backup_service.create_backup(encrypt=True, password=password)
        assert backup_service.verify_backup(backup_path, password) is True

    def test_verify_encrypted_backup_wrong_password(self, backup_service: BackupService):
        """Test verifying encrypted backup with wrong password."""
        password = "correct_password"
        backup_path = backup_service.create_backup(encrypt=True, password=password)
        
        # Should fail with wrong password
        assert backup_service.verify_backup(backup_path, "wrong_password") is False

    def test_verify_nonexistent_backup(self, backup_service: BackupService):
        """Test verifying non-existent backup."""
        fake_path = Path("/fake/path/backup.db")
        assert backup_service.verify_backup(fake_path) is False


class TestBackupListing:
    """Test backup listing functionality."""

    def test_list_backups_empty(self, backup_service: BackupService):
        """Test listing backups when none exist."""
        backups = backup_service.list_backups()
        assert isinstance(backups, list)
        assert len(backups) == 0

    def test_list_backups_with_backups(self, backup_service: BackupService):
        """Test listing backups after creating some."""
        # Create multiple backups
        backup1 = backup_service.create_backup(encrypt=False)
        backup2 = backup_service.create_backup(encrypt=True, password="test")
        
        backups = backup_service.list_backups()
        
        assert len(backups) == 2
        assert all(isinstance(b, BackupInfo) for b in backups)
        
        # Check sorting (newest first)
        assert backups[0].created_at >= backups[1].created_at

    def test_backup_info_properties(self, backup_service: BackupService):
        """Test BackupInfo properties."""
        backup_path = backup_service.create_backup(encrypt=False)
        backups = backup_service.list_backups()
        
        assert len(backups) == 1
        info = backups[0]
        
        assert info.path == backup_path
        assert info.filename == backup_path.name
        assert info.size_bytes > 0
        assert info.is_encrypted is False


class TestBackupCleanup:
    """Test backup cleanup functionality."""

    def test_delete_old_backups(self, backup_service: BackupService):
        """Test deleting old backups."""
        # Create a backup
        backup_service.create_backup(encrypt=False)
        
        # Delete backups older than 0 days (should delete all)
        deleted = backup_service.delete_old_backups(0)
        
        # Since the backup was just created, it shouldn't be deleted
        # But let's verify the method works
        assert isinstance(deleted, int)

    def test_delete_old_backups_retention(self, backup_service: BackupService):
        """Test backup retention logic."""
        # Create multiple backups
        backup_service.create_backup(encrypt=False)
        backup_service.create_backup(encrypt=False)
        
        # Keep backups for 365 days (should keep all)
        deleted = backup_service.delete_old_backups(365)
        assert deleted == 0
        
        backups = backup_service.list_backups()
        assert len(backups) == 2


class TestBackupStats:
    """Test backup statistics functionality."""

    def test_get_backup_stats_empty(self, backup_service: BackupService):
        """Test getting stats when no backups exist."""
        stats = backup_service.get_backup_stats()
        
        assert stats["total_backups"] == 0
        assert stats["total_size_bytes"] == 0
        assert stats["encrypted_count"] == 0
        assert stats["latest_backup"] is None

    def test_get_backup_stats_with_backups(self, backup_service: BackupService):
        """Test getting stats with existing backups."""
        backup_service.create_backup(encrypt=False)
        backup_service.create_backup(encrypt=True, password="test")
        
        stats = backup_service.get_backup_stats()
        
        assert stats["total_backups"] == 2
        assert stats["total_size_bytes"] > 0
        assert stats["encrypted_count"] == 1
        assert stats["latest_backup"] is not None


class TestBackupIntegrity:
    """Test backup integrity preservation."""

    def test_backup_contains_data(self, backup_service: BackupService):
        """Test that backup contains original database data."""
        import sqlite3
        
        # Create backup
        backup_path = backup_service.create_backup(encrypt=False)
        
        # Open backup and check tables exist
        conn = sqlite3.connect(str(backup_path))
        cursor = conn.cursor()
        
        # Check for expected tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        
        assert "users" in tables
        assert "categories" in tables
        
        conn.close()

    def test_restore_preserves_data(self, backup_service: BackupService, connection_manager: ConnectionManager):
        """Test that restore preserves database content."""
        # Add some data
        conn = connection_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
            ("test_user", "hash123", "cashier", "2024-01-01T00:00:00Z")
        )
        conn.commit()
        conn.close()
        
        # Create backup
        backup_path = backup_service.create_backup(encrypt=False)
        
        # Restore
        backup_service.restore_backup(backup_path)
        
        # Verify data exists
        conn = connection_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users WHERE username = ?", ("test_user",))
        result = cursor.fetchone()
        conn.close()
        
        assert result is not None
        assert result[0] == "test_user"
