"""Audit logger with HMAC chain for tamper detection.

Provides tamper-evident logging for critical database operations.
Each log entry includes an HMAC hash that chains to the previous entry,
making it possible to detect if any historical record has been modified.
"""

import hmac
import hashlib
import json
import sqlite3
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime, timezone

from config import AUDIT_HMAC_KEY


class AuditLogger:
    """Tamper-evident audit logger using HMAC chain."""

    # Genesis hash for the first record in the chain
    GENESIS_HASH = hashlib.sha256(b"GENESIS").hexdigest()

    def __init__(self, connection_manager, secret_key: bytes = None):
        """Initialize AuditLogger.

        Args:
            connection_manager: Database connection manager instance.
            secret_key: Secret key for HMAC. Uses default from config if None.
        """
        self.cm = connection_manager
        self.secret_key = secret_key or AUDIT_HMAC_KEY
        self._last_hash: Optional[str] = None

    def _compute_hash(
        self,
        table_name: str,
        record_id: int,
        action: str,
        old_values: Optional[str],
        new_values: Optional[str],
        user_id: Optional[int],
        timestamp: str,
        prev_hash: Optional[str],
    ) -> str:
        """Compute HMAC-SHA256 for an audit record.

        Args:
            table_name: Name of the table being audited.
            record_id: ID of the affected record.
            action: Action type (INSERT/UPDATE/DELETE).
            old_values: JSON string of old values (for UPDATE/DELETE).
            new_values: JSON string of new values (for INSERT/UPDATE).
            user_id: ID of user who performed the action.
            timestamp: ISO format timestamp of the action.
            prev_hash: Hash of the previous record in the chain.

        Returns:
            Hex-encoded HMAC-SHA256 hash.
        """
        # Build the message to hash
        message = "|".join([
            table_name or "",
            str(record_id),
            action,
            old_values or "",
            new_values or "",
            str(user_id) if user_id is not None else "",
            timestamp,
            prev_hash or self.GENESIS_HASH,
        ])
        
        return hmac.new(
            self.secret_key,
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def log(
        self,
        conn: sqlite3.Connection,
        table_name: str,
        record_id: int,
        action: str,
        old_values: Optional[Dict[str, Any]],
        new_values: Optional[Dict[str, Any]],
        user_id: Optional[int],
    ) -> None:
        """Log an audit entry with HMAC chain.

        The HMAC includes: table_name, record_id, action, old_values JSON,
        new_values JSON, user_id, timestamp, and the previous record's hash.

        Args:
            conn: SQLite connection (must be within a transaction).
            table_name: Name of the table being audited.
            record_id: ID of the affected record.
            action: Action type (INSERT/UPDATE/DELETE).
            old_values: Dictionary of old values (for UPDATE/DELETE).
            new_values: Dictionary of new values (for INSERT/UPDATE).
            user_id: ID of user who performed the action.
        """
        assert isinstance(table_name, str) and table_name
        assert isinstance(record_id, int) and record_id > 0
        assert action in ("INSERT", "UPDATE", "DELETE")
        
        cursor = conn.cursor()
        
        # Get the last hash from the chain
        if self._last_hash is None:
            cursor.execute(
                "SELECT hmac_hash FROM audit_log ORDER BY id DESC LIMIT 1"
            )
            row = cursor.fetchone()
            self._last_hash = row[0] if row else self.GENESIS_HASH
        
        # Prepare values
        timestamp = datetime.now(timezone.utc).isoformat()
        old_values_json = json.dumps(old_values) if old_values else None
        new_values_json = json.dumps(new_values) if new_values else None
        
        # Compute the HMAC hash
        hmac_hash = self._compute_hash(
            table_name=table_name,
            record_id=record_id,
            action=action,
            old_values=old_values_json,
            new_values=new_values_json,
            user_id=user_id,
            timestamp=timestamp,
            prev_hash=self._last_hash,
        )
        
        # Insert the audit record
        cursor.execute(
            """INSERT INTO audit_log 
               (table_name, record_id, action, old_values, new_values, user_id, timestamp, hmac_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (table_name, record_id, action, old_values_json, new_values_json, user_id, timestamp, hmac_hash),
        )
        
        # Update the last hash for the next record
        self._last_hash = hmac_hash
        
        cursor.close()

    def verify_chain(self, conn: sqlite3.Connection) -> Tuple[bool, Optional[int]]:
        """Verify the entire audit log chain.

        Walks the chain in order, recomputing each row's expected hash.
        Returns (is_valid, first_broken_row_id).
        If valid, first_broken_row_id is None.
        If invalid, first_broken_row_id is the ID of the first row that doesn't match.
        Everything before that row is provably intact; everything from that row forward is suspect.

        Args:
            conn: SQLite connection.

        Returns:
            Tuple of (is_valid: bool, first_broken_row_id: Optional[int]).
        """
        cursor = conn.cursor()
        cursor.execute(
            """SELECT id, table_name, record_id, action, old_values, new_values, 
                      user_id, timestamp, hmac_hash 
               FROM audit_log ORDER BY id ASC"""
        )
        
        rows = cursor.fetchall()
        cursor.close()
        
        if not rows:
            return True, None
        
        prev_hash = self.GENESIS_HASH
        
        for row in rows:
            (
                row_id,
                table_name,
                record_id,
                action,
                old_values,
                new_values,
                user_id,
                timestamp,
                stored_hash,
            ) = row
            
            # Recompute the expected hash
            expected_hash = self._compute_hash(
                table_name=table_name,
                record_id=record_id,
                action=action,
                old_values=old_values,
                new_values=new_values,
                user_id=user_id,
                timestamp=timestamp,
                prev_hash=prev_hash,
            )
            
            if expected_hash != stored_hash:
                return False, row_id
            
            prev_hash = stored_hash
        
        return True, None

    def reset_chain_cache(self) -> None:
        """Reset the cached last hash. Call this after manual database operations."""
        self._last_hash = None
