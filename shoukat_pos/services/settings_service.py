"""
Settings Service for Shoukat Sons Garments POS.

Manages application settings including shop info, printer settings,
secret code mapping, and user preferences. All settings are stored
in SQLite with proper validation and transaction handling.
"""

import json
from typing import Any, Dict, Optional

import bcrypt

from database.connection import ConnectionManager


class SettingsService:
    """Service for managing application settings."""

    DEFAULT_SECRET_CODE_MAP = {
        "0": "L",
        "1": "R",
        "2": "K",
        "3": "B",
        "4": "S",
        "5": "M",
        "6": "N",
        "7": "T",
        "8": "H",
        "9": "W",
    }

    DEFAULT_SETTINGS = {
        "shop_name": "Shoukat Sons Garments",
        "shop_address": "",
        "shop_phone": "",
        "shop_gstin": "",
        "currency_symbol": "Rs.",
        "tax_rate_default": 0.0,
        "theme_mode": "light",
        "secret_code_map": json.dumps(DEFAULT_SECRET_CODE_MAP),
        "label_printer_name": "",
        "label_sticker_size": "28x19",
        "label_gap_mm": 2,
        "label_density": "normal",
        "label_speed": "medium",
        "receipt_printer_name": "",
        "receipt_width_mm": 80,
        "receipt_header": "",
        "receipt_footer": "",
        "auto_backup_enabled": True,
        "auto_backup_frequency": "daily",
        "auto_backup_time": "23:00",
        "auto_backup_retention": 30,
        "auto_backup_encrypt": True,
        "session_timeout_minutes": 30,
        "edit_password": "",
    }

    def __init__(self, connection_manager: ConnectionManager):
        """
        Initialize SettingsService.

        Args:
            connection_manager: Database connection manager instance.
        """
        self.cm = connection_manager
        self._ensure_settings_table()

    def _ensure_settings_table(self) -> None:
        """Create settings table if it doesn't exist and seed defaults."""
        conn = self.cm.get_read_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.commit()
            cursor.close()
        finally:
            conn.close()
        self._seed_default_settings()

    def _seed_default_settings(self) -> None:
        """Insert default settings if they don't exist."""
        conn = self.cm.get_read_connection()
        try:
            cursor = conn.cursor()
            now = self._get_current_timestamp()

            for key, default_value in self.DEFAULT_SETTINGS.items():
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO settings (key, value, updated_at)
                    VALUES (?, ?, ?)
                    """,
                    (key, str(default_value), now),
                )
            conn.commit()
            cursor.close()
        finally:
            conn.close()

    def _get_current_timestamp(self) -> str:
        """Get current UTC timestamp in ISO format."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()

    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Get a setting value by key.

        Args:
            key: Setting key name.
            default: Default value if key doesn't exist.

        Returns:
            Setting value as appropriate type (str, int, float, bool, dict).
        """
        assert isinstance(key, str) and len(key) > 0

        conn = self.cm.get_read_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT value FROM settings WHERE key = ?",
                (key,),
            )
            result = cursor.fetchone()
            cursor.close()
        finally:
            conn.close()

        if result is None:
            return default

        value = result[0]
        return self._parse_value(value, default)

    def _parse_value(self, value: str, default: Any = None) -> Any:
        """
        Parse string value to appropriate type.

        Args:
            value: String value from database.
            default: Default value to infer type.

        Returns:
            Parsed value as int, float, bool, dict, or str.
        """
        if default is not None:
            if isinstance(default, bool):
                return value.lower() in ("true", "1", "yes")
            if isinstance(default, int):
                try:
                    return int(value)
                except ValueError:
                    return default
            if isinstance(default, float):
                try:
                    return float(value)
                except ValueError:
                    return default
            if isinstance(default, dict):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return default

        # Try to parse as JSON first
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass

        # Try int
        try:
            return int(value)
        except ValueError:
            pass

        # Try float
        try:
            return float(value)
        except ValueError:
            pass

        return value

    def set_setting(self, key: str, value: Any) -> None:
        """
        Set a setting value.

        Args:
            key: Setting key name.
            value: Value to store (will be converted to string).

        Raises:
            ValueError: If key is empty.
        """
        assert isinstance(key, str) and len(key) > 0

        if isinstance(value, (dict, list)):
            str_value = json.dumps(value)
        elif isinstance(value, bool):
            str_value = "true" if value else "false"
        else:
            str_value = str(value)

        with self.cm.execute_transaction() as conn:
            cursor = conn.cursor()
            now = self._get_current_timestamp()
            cursor.execute(
                """
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
                """,
                (key, str_value, now),
            )
            cursor.close()

    def get_all_settings(self) -> Dict[str, Any]:
        """
        Get all settings as a dictionary.

        Returns:
            Dictionary of all key-value pairs with parsed values.
        """
        conn = self.cm.get_read_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM settings")
            rows = cursor.fetchall()
            cursor.close()
        finally:
            conn.close()

        result = {}
        for key, value in rows:
            result[key] = self._parse_value(value, self.DEFAULT_SETTINGS.get(key))

        return result

    def get_secret_code_map(self) -> Dict[str, str]:
        """
        Get the digit-to-character mapping for secret codes.

        Returns:
            Dictionary mapping digit characters to code characters.
        """
        map_value = self.get_setting("secret_code_map", self.DEFAULT_SECRET_CODE_MAP)
        if isinstance(map_value, dict):
            return {str(k): v for k, v in map_value.items()}
        return self.DEFAULT_SECRET_CODE_MAP.copy()

    def set_secret_code_map(self, mapping: Dict[str, str]) -> None:
        """
        Update the secret code mapping.

        Validates that all 10 digits are mapped with unique characters.

        Args:
            mapping: Dictionary mapping digit strings to code characters.

        Raises:
            ValueError: If mapping is invalid (not 10 unique mappings).
        """
        assert isinstance(mapping, dict)

        # Validate: must have exactly 10 entries for digits 0-9
        if len(mapping) != 10:
            raise ValueError("Secret code map must have exactly 10 entries")

        # Validate: all keys must be digit strings
        for key in mapping.keys():
            if str(key) not in "0123456789":
                raise ValueError(f"Invalid digit key: {key}")

        # Validate: all values must be unique
        values = list(mapping.values())
        if len(values) != len(set(values)):
            raise ValueError("All code characters must be unique")

        # Convert keys to strings
        str_mapping = {str(k): v for k, v in mapping.items()}
        self.set_setting("secret_code_map", str_mapping)

    def get_shop_info(self) -> Dict[str, str]:
        """
        Get shop information.

        Returns:
            Dictionary with shop_name, shop_address, shop_phone, shop_gstin.
        """
        return {
            "shop_name": self.get_setting("shop_name", ""),
            "shop_address": self.get_setting("shop_address", ""),
            "shop_phone": self.get_setting("shop_phone", ""),
            "shop_gstin": self.get_setting("shop_gstin", ""),
        }

    def set_shop_info(self, info: Dict[str, str]) -> None:
        """
        Set shop information.

        Args:
            info: Dictionary with optional keys: shop_name, shop_address,
                  shop_phone, shop_gstin.
        """
        assert isinstance(info, dict)

        valid_keys = {"shop_name", "shop_address", "shop_phone", "shop_gstin"}
        for key, value in info.items():
            if key in valid_keys:
                self.set_setting(key, str(value))

    def get_printer_settings(self) -> Dict[str, Any]:
        """
        Get all printer-related settings.

        Returns:
            Dictionary with label and receipt printer settings.
        """
        return {
            "label_printer_name": self.get_setting("label_printer_name", ""),
            "label_sticker_size": self.get_setting("label_sticker_size", "28x19"),
            "label_gap_mm": self.get_setting("label_gap_mm", 2),
            "label_density": self.get_setting("label_density", "normal"),
            "label_speed": self.get_setting("label_speed", "medium"),
            "receipt_printer_name": self.get_setting("receipt_printer_name", ""),
            "receipt_width_mm": self.get_setting("receipt_width_mm", 80),
            "receipt_header": self.get_setting("receipt_header", ""),
            "receipt_footer": self.get_setting("receipt_footer", ""),
        }

    def set_printer_settings(self, settings: Dict[str, Any]) -> None:
        """
        Set printer-related settings.

        Args:
            settings: Dictionary with optional printer setting keys.
        """
        assert isinstance(settings, dict)

        valid_keys = {
            "label_printer_name",
            "label_sticker_size",
            "label_gap_mm",
            "label_density",
            "label_speed",
            "receipt_printer_name",
            "receipt_width_mm",
            "receipt_header",
            "receipt_footer",
        }
        for key, value in settings.items():
            if key in valid_keys:
                self.set_setting(key, value)

    def set_edit_password(self, password: str) -> None:
        """
        Set the edit password (for protecting sensitive operations).

        Args:
            password: Plain text password to hash and store.
        """
        assert isinstance(password, str) and len(password) >= 4

        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12))
        self.set_setting("edit_password", hashed.decode("utf-8"))

    def verify_edit_password(self, password: str) -> bool:
        """
        Verify the edit password.

        Args:
            password: Plain text password to verify.

        Returns:
            True if password matches, False otherwise.
        """
        stored_hash = self.get_setting("edit_password", "")
        if not stored_hash:
            return False

        try:
            return bcrypt.checkpw(
                password.encode("utf-8"), stored_hash.encode("utf-8")
            )
        except Exception:
            return False

    def get_theme_mode(self) -> str:
        """
        Get the current theme mode.

        Returns:
            'light' or 'dark'.
        """
        return self.get_setting("theme_mode", "light")

    def set_theme_mode(self, mode: str) -> None:
        """
        Set the theme mode.

        Args:
            mode: 'light' or 'dark'.
        """
        assert mode in ("light", "dark")
        self.set_setting("theme_mode", mode)

    def get_auto_backup_settings(self) -> Dict[str, Any]:
        """
        Get auto-backup configuration.

        Returns:
            Dictionary with backup settings.
        """
        return {
            "enabled": self.get_setting("auto_backup_enabled", True),
            "frequency": self.get_setting("auto_backup_frequency", "daily"),
            "time": self.get_setting("auto_backup_time", "23:00"),
            "retention": self.get_setting("auto_backup_retention", 30),
            "encrypt": self.get_setting("auto_backup_encrypt", True),
        }

    def set_auto_backup_settings(self, settings: Dict[str, Any]) -> None:
        """
        Set auto-backup configuration.

        Args:
            settings: Dictionary with optional backup setting keys.
        """
        assert isinstance(settings, dict)

        valid_keys = {
            "auto_backup_enabled",
            "auto_backup_frequency",
            "auto_backup_time",
            "auto_backup_retention",
            "auto_backup_encrypt",
        }
        for key, value in settings.items():
            if key in valid_keys:
                self.set_setting(key, value)
