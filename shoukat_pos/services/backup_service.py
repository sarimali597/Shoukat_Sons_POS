"""
Backup Service for Shoukat Sons Garments POS.

Handles database backup creation, restoration, encryption,
and integrity verification. Supports automatic scheduled backups.
"""

import hashlib
import os
import shutil
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from database.connection import ConnectionManager


class BackupInfo:
    """Information about a backup file."""

    def __init__(
        self,
        path: Path,
        created_at: datetime,
        size_bytes: int,
        is_encrypted: bool,
    ):
        """
        Initialize BackupInfo.

        Args:
            path: Path to backup file.
            created_at: Creation timestamp.
            size_bytes: File size in bytes.
            is_encrypted: Whether backup is encrypted.
        """
        self.path = path
        self.created_at = created_at
        self.size_bytes = size_bytes
        self.is_encrypted = is_encrypted

    @property
    def filename(self) -> str:
        """Get filename without directory."""
        return self.path.name


class BackupService:
    """Service for managing database backups."""

    def __init__(self, connection_manager: ConnectionManager, data_dir: Path):
        """
        Initialize BackupService.

        Args:
            connection_manager: Database connection manager.
            data_dir: Application data directory.
        """
        self.cm = connection_manager
        self.data_dir = Path(data_dir)
        self.backup_dir = self.data_dir / "backups"
        self._ensure_backup_dir()

    def _ensure_backup_dir(self) -> None:
        """Create backup directory if it doesn't exist."""
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def _get_db_path(self) -> Path:
        """Get path to the main database file."""
        # The database path is typically in data_dir
        db_path = self.data_dir / "pos.db"
        if not db_path.exists():
            # Try alternative locations
            for pattern in ["*.db"]:
                matches = list(self.data_dir.glob(pattern))
                if matches:
                    return matches[0]
        return db_path

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """
        Derive encryption key from password using PBKDF2.

        Args:
            password: User password.
            salt: Random salt for key derivation.

        Returns:
            32-byte derived key.
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100_000,
        )
        return kdf.derive(password.encode("utf-8"))

    def create_backup(self, encrypt: bool = True, password: Optional[str] = None) -> Path:
        """
        Create a backup of the database.

        Args:
            encrypt: Whether to encrypt the backup.
            password: Password for encryption (required if encrypt=True).

        Returns:
            Path to the created backup file.

        Raises:
            ValueError: If encrypt=True but no password provided.
        """
        db_path = self._get_db_path()
        if not db_path.exists():
            raise FileNotFoundError(f"Database not found at {db_path}")

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        base_filename = f"backup_{timestamp}.db"

        # Create plain backup first using SQLite backup API
        temp_backup = self.backup_dir / base_filename

        conn = self.cm.get_read_connection()
        try:
            backup_conn = sqlite3.connect(str(temp_backup))

            with backup_conn:
                conn.backup(backup_conn)

            backup_conn.close()
        finally:
            conn.close()

        if encrypt:
            if not password:
                # Use a default password based on edit_password setting
                from services.settings_service import SettingsService

                settings = SettingsService(self.cm)
                password = settings.get_setting("edit_password", "shoukat_pos_backup")
                if not password:
                    password = "shoukat_pos_backup"

            encrypted_path = self._encrypt_file(temp_backup, password)
            temp_backup.unlink()  # Remove plain backup
            return encrypted_path

        return temp_backup

    def _encrypt_file(self, source_path: Path, password: str) -> Path:
        """
        Encrypt a file using Fernet encryption.

        Args:
            source_path: Path to file to encrypt.
            password: Password for encryption.

        Returns:
            Path to encrypted file.
        """
        # Generate random salt
        salt = os.urandom(16)

        # Derive key from password
        key = self._derive_key(password, salt)

        # Read source file
        with open(source_path, "rb") as f:
            data = f.read()

        # Encrypt with Fernet
        fernet = Fernet(key)
        encrypted_data = fernet.encrypt(data)

        # Write encrypted file with salt prepended
        encrypted_path = source_path.with_suffix(".db.enc")
        with open(encrypted_path, "wb") as f:
            f.write(salt)
            f.write(encrypted_data)

        return encrypted_path

    def restore_backup(
        self, backup_path: Path, password: Optional[str] = None
    ) -> bool:
        """
        Restore from a backup file.

        Args:
            backup_path: Path to backup file.
            password: Password for encrypted backup.

        Returns:
            True if restore successful, False otherwise.

        Raises:
            FileNotFoundError: If backup file doesn't exist.
            ValueError: If password required but not provided.
        """
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        # Verify backup integrity first
        if not self.verify_backup(backup_path, password):
            return False

        db_path = self._get_db_path()

        # Handle encrypted backup
        if backup_path.suffix == ".enc" or str(backup_path).endswith(".db.enc"):
            if not password:
                from services.settings_service import SettingsService

                settings = SettingsService(self.cm)
                password = settings.get_setting("edit_password", "")
                if not password:
                    raise ValueError("Password required for encrypted backup")

            # Decrypt to temp file
            temp_db = self._decrypt_file(backup_path, password)
            source_path = temp_db
        else:
            source_path = backup_path

        try:
            # Close any existing connections
            self.cm.close_all()

            # Replace database file
            if db_path.exists():
                db_path.unlink()

            shutil.copy2(str(source_path), str(db_path))

            # Re-open connection to verify
            test_conn = sqlite3.connect(str(db_path))
            cursor = test_conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            test_conn.close()

            return result[0] == "ok"

        finally:
            # Clean up temp file
            if backup_path.suffix == ".enc" and "temp_db" in locals():
                temp_db.unlink(missing_ok=True)

    def _decrypt_file(self, encrypted_path: Path, password: str) -> Path:
        """
        Decrypt an encrypted backup file.

        Args:
            encrypted_path: Path to encrypted file.
            password: Password for decryption.

        Returns:
            Path to decrypted temp file.
        """
        # Read encrypted file
        with open(encrypted_path, "rb") as f:
            salt = f.read(16)
            encrypted_data = f.read()

        # Derive key from password
        key = self._derive_key(password, salt)

        # Decrypt with Fernet
        fernet = Fernet(key)
        decrypted_data = fernet.decrypt(encrypted_data)

        # Write to temp file
        temp_fd, temp_path = tempfile.mkstemp(suffix=".db")
        with os.fdopen(temp_fd, "wb") as f:
            f.write(decrypted_data)

        return Path(temp_path)

    def list_backups(self) -> List[BackupInfo]:
        """
        List available backups.

        Returns:
            List of BackupInfo objects sorted by date (newest first).
        """
        backups = []

        for pattern in ["*.db", "*.db.enc"]:
            for backup_path in self.backup_dir.glob(pattern):
                stat = backup_path.stat()
                is_encrypted = backup_path.suffix == ".enc" or str(
                    backup_path
                ).endswith(".db.enc")

                info = BackupInfo(
                    path=backup_path,
                    created_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                    size_bytes=stat.st_size,
                    is_encrypted=is_encrypted,
                )
                backups.append(info)

        # Sort by creation time, newest first
        backups.sort(key=lambda x: x.created_at, reverse=True)
        return backups

    def delete_old_backups(self, retention_days: int) -> int:
        """
        Delete backups older than retention_days.

        Args:
            retention_days: Number of days to keep backups.

        Returns:
            Count of deleted backups.
        """
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        deleted_count = 0

        for backup_info in self.list_backups():
            if backup_info.created_at < cutoff:
                backup_info.path.unlink()
                deleted_count += 1

        return deleted_count

    def verify_backup(
        self, backup_path: Path, password: Optional[str] = None
    ) -> bool:
        """
        Run integrity check on a backup file.

        Args:
            backup_path: Path to backup file.
            password: Password for encrypted backup.

        Returns:
            True if integrity check passes, False otherwise.
        """
        if not backup_path.exists():
            return False

        # Handle encrypted backup
        if backup_path.suffix == ".enc" or str(backup_path).endswith(".db.enc"):
            if not password:
                from services.settings_service import SettingsService

                settings = SettingsService(self.cm)
                password = settings.get_setting("edit_password", "")
                if not password:
                    return False

            temp_db = self._decrypt_file(backup_path, password)
            source_path = temp_db
        else:
            source_path = backup_path
            temp_db = None

        try:
            conn = sqlite3.connect(str(source_path))
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            conn.close()

            return result[0] == "ok"

        except Exception:
            return False

        finally:
            if temp_db:
                temp_db.unlink(missing_ok=True)

    def get_backup_stats(self) -> Dict[str, Any]:
        """
        Get backup statistics.

        Returns:
            Dictionary with backup stats.
        """
        backups = self.list_backups()
        total_size = sum(b.size_bytes for b in backups)
        encrypted_count = sum(1 for b in backups if b.is_encrypted)

        return {
            "total_backups": len(backups),
            "total_size_bytes": total_size,
            "encrypted_count": encrypted_count,
            "latest_backup": backups[0] if backups else None,
        }
