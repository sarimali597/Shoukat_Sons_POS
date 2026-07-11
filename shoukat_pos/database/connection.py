"""
ConnectionManager singleton for database connections.

Provides thread-safe access to SQLite with WAL mode, proper pragmas,
transaction management with retry logic, and integrity checking.
"""

import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from config import (
    DATABASE_PATH,
    DB_BUSY_TIMEOUT_MS,
    DB_CACHE_SIZE_KB,
    DB_FOREIGN_KEYS,
    DB_MMAP_SIZE_BYTES,
    DB_SECURE_DELETE,
    DB_SYNCHRONOUS,
    DB_TEMP_STORE,
    DB_WAL_AUTOCHECKPOINT,
    DB_WAL_MODE,
    ensure_data_directory,
)


class ConnectionManager:
    """
    Singleton connection manager for SQLite database.

    Manages database connections with proper pragmas, WAL mode,
    thread-safe write operations, and transaction support.

    Attributes:
        database_path: Path to the SQLite database file.
        _instance: Class-level singleton instance.
        _lock: Thread lock for singleton creation.
        _write_lock: Thread lock for serializing write operations.
    """

    _instance: Optional["ConnectionManager"] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls, database_path: Optional[Path] = None) -> "ConnectionManager":
        """
        Create or return the singleton ConnectionManager instance.

        Args:
            database_path: Optional path to database file. Defaults to config.DATABASE_PATH.

        Returns:
            The singleton ConnectionManager instance.
        """
        assert cls._lock is not None

        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
                cls._instance._database_path = database_path or DATABASE_PATH
                cls._instance._write_lock = threading.Lock()
                cls._instance._local = threading.local()
        return cls._instance

    def __init__(self, database_path: Optional[Path] = None) -> None:
        """
        Initialize the connection manager.

        Args:
            database_path: Optional path to database file. Only used on first init.
        """
        if self._initialized:
            return

        ensure_data_directory()
        self._apply_pragmas_on_connection: bool = True
        self._initialized = True

    def _apply_pragmas(self, conn: sqlite3.Connection) -> None:
        """
        Apply required PRAGMA settings to a connection.

        Args:
            conn: SQLite connection to configure.
        """
        assert conn is not None

        cursor = conn.cursor()
        cursor.execute(f"PRAGMA journal_mode={DB_WAL_MODE}")
        cursor.execute(f"PRAGMA synchronous={DB_SYNCHRONOUS}")
        cursor.execute(f"PRAGMA busy_timeout={DB_BUSY_TIMEOUT_MS}")
        cursor.execute(f"PRAGMA cache_size={DB_CACHE_SIZE_KB}")
        cursor.execute(f"PRAGMA mmap_size={DB_MMAP_SIZE_BYTES}")
        cursor.execute(f"PRAGMA foreign_keys={DB_FOREIGN_KEYS}")
        cursor.execute(f"PRAGMA temp_store={DB_TEMP_STORE}")
        cursor.execute(f"PRAGMA secure_delete={DB_SECURE_DELETE}")
        cursor.execute(f"PRAGMA wal_autocheckpoint={DB_WAL_AUTOCHECKPOINT}")
        conn.commit()
        cursor.close()

    def _create_connection(self) -> sqlite3.Connection:
        """
        Create a new SQLite connection with pragmas applied.

        Returns:
            Configured SQLite connection.
        """
        conn = sqlite3.connect(
            str(self._database_path),
            check_same_thread=False,
            isolation_level=None,  # Autocommit mode for manual transaction control
        )
        conn.row_factory = sqlite3.Row
        self._apply_pragmas(conn)
        return conn

    def get_read_connection(self) -> sqlite3.Connection:
        """
        Get a connection for read operations.

        Returns:
            SQLite connection configured for reading.
        """
        return self._create_connection()

    def get_connection(self) -> sqlite3.Connection:
        """
        Get a general purpose connection (alias for get_read_connection).

        This method exists for backward compatibility and testing.

        Returns:
            SQLite connection configured for general use.
        """
        return self.get_read_connection()

    def get_write_connection(self) -> sqlite3.Connection:
        """
        Get a connection for write operations.

        Acquires the write lock before returning the connection.
        Caller must release the lock after use.

        Returns:
            SQLite connection configured for writing.
        """
        self._write_lock.acquire()
        return self._create_connection()

    def release_write_connection(self) -> None:
        """
        Release the write lock after completing write operations.
        """
        try:
            self._write_lock.release()
        except RuntimeError:
            # Lock was not held; ignore
            pass

    @contextmanager
    def execute_transaction(
        self, max_retries: int = 3, base_delay: float = 0.1
    ) -> Generator[sqlite3.Connection, None, None]:
        """
        Context manager for executing database transactions with retry logic.

        Handles BEGIN IMMEDIATE, COMMIT, and ROLLBACK automatically.
        Retries on SQLITE_BUSY with exponential backoff.

        Args:
            max_retries: Maximum number of retry attempts.
            base_delay: Base delay in seconds for exponential backoff.

        Yields:
            SQLite connection within an active transaction.

        Raises:
            sqlite3.DatabaseError: If transaction fails after all retries.

        Example:
            with connection_manager.execute_transaction() as conn:
                conn.execute("INSERT INTO ...")
                # Commits automatically on exit
                # Rolls back on exception
        """
        assert max_retries > 0
        assert base_delay > 0

        last_exception: Optional[sqlite3.DatabaseError] = None

        for attempt in range(max_retries):
            conn = self.get_write_connection()
            try:
                conn.execute("BEGIN IMMEDIATE")
                yield conn
                conn.execute("COMMIT")
                return
            except sqlite3.DatabaseError as e:
                last_exception = e
                conn.execute("ROLLBACK")
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    time.sleep(delay)
                    continue
                raise
            finally:
                self.release_write_connection()
                if conn:
                    conn.close()

        raise sqlite3.DatabaseError(
            f"Transaction failed after {max_retries} retries"
        ) from last_exception

    def initialize_database(
        self, schema_module: Optional[object] = None
    ) -> None:
        """
        Initialize the database with schema and seed data.

        Args:
            schema_module: Optional schema module with create_tables and seed_data functions.
                          If None, uses database.schema module.
        """
        if schema_module is None:
            from database import schema as schema_module

        conn = self.get_read_connection()
        try:
            # Run schema creation
            if hasattr(schema_module, "create_tables"):
                schema_module.create_tables(conn)

            # Run seed data
            if hasattr(schema_module, "seed_data"):
                schema_module.seed_data(conn)

            # Run integrity check
            integrity_result = self.integrity_check(conn)
            if not integrity_result["is_valid"]:
                raise sqlite3.DatabaseError(
                    f"Database integrity check failed: {integrity_result['errors']}"
                )
        finally:
            conn.close()

    def integrity_check(
        self, conn: Optional[sqlite3.Connection] = None
    ) -> dict[str, bool | list[str]]:
        """
        Run SQLite integrity check and report violations.

        Args:
            conn: Optional existing connection. Creates one if not provided.

        Returns:
            Dictionary with 'is_valid' boolean and 'errors' list.
        """
        external_conn = conn is not None
        if conn is None:
            conn = self.get_read_connection()

        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            results = cursor.fetchall()
            cursor.close()

            errors = []
            for row in results:
                if row[0] != "ok":
                    errors.append(str(row[0]))

            return {"is_valid": len(errors) == 0, "errors": errors}
        finally:
            if not external_conn:
                conn.close()

    def close_all(self) -> None:
        """
        Close all active connections and reset the singleton.

        Used primarily for testing and application shutdown.
        """
        self._initialized = False
        ConnectionManager._instance = None
