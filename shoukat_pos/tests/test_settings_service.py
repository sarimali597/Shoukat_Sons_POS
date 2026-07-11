"""
Tests for SettingsService.

Tests cover setting CRUD operations, secret code mapping validation,
shop info management, and password handling.
"""

import json
from pathlib import Path

import pytest

from database.connection import ConnectionManager
from services.settings_service import SettingsService


@pytest.fixture
def connection_manager(tmp_path: Path) -> ConnectionManager:
    """Create a ConnectionManager with a temporary database."""
    db_path = tmp_path / "test_settings.db"
    return ConnectionManager(str(db_path))


@pytest.fixture
def settings_service(connection_manager: ConnectionManager) -> SettingsService:
    """Create a SettingsService instance."""
    return SettingsService(connection_manager)


class TestSettingsServiceBasic:
    """Test basic settings operations."""

    def test_get_setting_default(self, settings_service: SettingsService):
        """Test getting a default setting value."""
        shop_name = settings_service.get_setting("shop_name")
        assert shop_name == "Shoukat Sons Garments"

    def test_get_setting_nonexistent(self, settings_service: SettingsService):
        """Test getting a non-existent setting."""
        value = settings_service.get_setting("nonexistent_key", "default_value")
        assert value == "default_value"

    def test_set_setting(self, settings_service: SettingsService):
        """Test setting a custom value."""
        settings_service.set_setting("custom_key", "custom_value")
        value = settings_service.get_setting("custom_key")
        assert value == "custom_value"

    def test_set_setting_integer(self, settings_service: SettingsService):
        """Test setting an integer value."""
        settings_service.set_setting("int_key", 42)
        value = settings_service.get_setting("int_key")
        assert value == 42
        assert isinstance(value, int)

    def test_set_setting_bool(self, settings_service: SettingsService):
        """Test setting boolean values."""
        settings_service.set_setting("bool_true", True)
        settings_service.set_setting("bool_false", False)

        assert settings_service.get_setting("bool_true") is True
        assert settings_service.get_setting("bool_false") is False

    def test_get_all_settings(self, settings_service: SettingsService):
        """Test getting all settings."""
        all_settings = settings_service.get_all_settings()
        assert isinstance(all_settings, dict)
        assert "shop_name" in all_settings
        assert "theme_mode" in all_settings


class TestSecretCodeMapping:
    """Test secret code mapping functionality."""

    def test_get_default_secret_code_map(self, settings_service: SettingsService):
        """Test getting the default secret code mapping."""
        mapping = settings_service.get_secret_code_map()
        assert isinstance(mapping, dict)
        assert len(mapping) == 10
        assert mapping["0"] == "L"
        assert mapping["1"] == "R"

    def test_set_valid_secret_code_map(self, settings_service: SettingsService):
        """Test setting a valid custom mapping."""
        custom_map = {
            "0": "A",
            "1": "B",
            "2": "C",
            "3": "D",
            "4": "E",
            "5": "F",
            "6": "G",
            "7": "H",
            "8": "I",
            "9": "J",
        }
        settings_service.set_secret_code_map(custom_map)
        retrieved = settings_service.get_secret_code_map()
        assert retrieved == custom_map

    def test_set_invalid_mapping_wrong_count(self, settings_service: SettingsService):
        """Test that mapping with wrong count raises error."""
        invalid_map = {"0": "A", "1": "B"}  # Only 2 entries
        with pytest.raises(ValueError, match="exactly 10 entries"):
            settings_service.set_secret_code_map(invalid_map)

    def test_set_invalid_mapping_duplicates(self, settings_service: SettingsService):
        """Test that mapping with duplicate values raises error."""
        invalid_map = {
            "0": "A",
            "1": "A",  # Duplicate
            "2": "C",
            "3": "D",
            "4": "E",
            "5": "F",
            "6": "G",
            "7": "H",
            "8": "I",
            "9": "J",
        }
        with pytest.raises(ValueError, match="unique"):
            settings_service.set_secret_code_map(invalid_map)

    def test_set_invalid_mapping_invalid_keys(self, settings_service: SettingsService):
        """Test that mapping with invalid keys raises error."""
        invalid_map = {
            "a": "A",  # Invalid key
            "1": "B",
            "2": "C",
            "3": "D",
            "4": "E",
            "5": "F",
            "6": "G",
            "7": "H",
            "8": "I",
            "9": "J",
        }
        with pytest.raises(ValueError, match="Invalid digit key"):
            settings_service.set_secret_code_map(invalid_map)


class TestShopInfo:
    """Test shop information management."""

    def test_get_shop_info_defaults(self, settings_service: SettingsService):
        """Test getting default shop info."""
        info = settings_service.get_shop_info()
        assert isinstance(info, dict)
        assert "shop_name" in info
        assert info["shop_name"] == "Shoukat Sons Garments"

    def test_set_shop_info(self, settings_service: SettingsService):
        """Test setting shop information."""
        new_info = {
            "shop_name": "New Shop Name",
            "shop_address": "123 Main St",
            "shop_phone": "+92-300-1234567",
            "shop_gstin": "GST123456",
        }
        settings_service.set_shop_info(new_info)
        retrieved = settings_service.get_shop_info()
        assert retrieved["shop_name"] == "New Shop Name"
        assert retrieved["shop_address"] == "123 Main St"

    def test_set_partial_shop_info(self, settings_service: SettingsService):
        """Test setting partial shop information."""
        settings_service.set_shop_info({"shop_name": "Updated Name"})
        info = settings_service.get_shop_info()
        assert info["shop_name"] == "Updated Name"
        # Other fields should remain at defaults
        assert info["shop_address"] == ""


class TestPrinterSettings:
    """Test printer settings management."""

    def test_get_printer_settings_defaults(self, settings_service: SettingsService):
        """Test getting default printer settings."""
        settings = settings_service.get_printer_settings()
        assert isinstance(settings, dict)
        assert "label_sticker_size" in settings
        assert settings["label_sticker_size"] == "28x19"
        assert settings["receipt_width_mm"] == 80

    def test_set_printer_settings(self, settings_service: SettingsService):
        """Test setting printer settings."""
        new_settings = {
            "label_sticker_size": "32x25",
            "label_gap_mm": 3,
            "receipt_width_mm": 58,
        }
        settings_service.set_printer_settings(new_settings)
        retrieved = settings_service.get_printer_settings()
        assert retrieved["label_sticker_size"] == "32x25"
        assert retrieved["label_gap_mm"] == 3
        assert retrieved["receipt_width_mm"] == 58


class TestEditPassword:
    """Test edit password functionality."""

    def test_set_and_verify_password(self, settings_service: SettingsService):
        """Test setting and verifying edit password."""
        password = "secure_password_123"
        settings_service.set_edit_password(password)
        assert settings_service.verify_edit_password(password) is True

    def test_verify_wrong_password(self, settings_service: SettingsService):
        """Test verifying wrong password."""
        settings_service.set_edit_password("correct_password")
        assert settings_service.verify_edit_password("wrong_password") is False

    def test_verify_no_password(self, settings_service: SettingsService):
        """Test verifying when no password is set."""
        assert settings_service.verify_edit_password("any_password") is False

    def test_password_minimum_length(self, settings_service: SettingsService):
        """Test password minimum length requirement."""
        with pytest.raises(AssertionError):
            settings_service.set_edit_password("abc")  # Too short


class TestThemeMode:
    """Test theme mode settings."""

    def test_get_default_theme(self, settings_service: SettingsService):
        """Test getting default theme mode."""
        mode = settings_service.get_theme_mode()
        assert mode == "light"

    def test_set_theme_mode(self, settings_service: SettingsService):
        """Test setting theme mode."""
        settings_service.set_theme_mode("dark")
        assert settings_service.get_theme_mode() == "dark"

    def test_set_invalid_theme_mode(self, settings_service: SettingsService):
        """Test setting invalid theme mode."""
        with pytest.raises(AssertionError):
            settings_service.set_theme_mode("invalid_mode")


class TestAutoBackupSettings:
    """Test auto-backup settings."""

    def test_get_default_backup_settings(self, settings_service: SettingsService):
        """Test getting default backup settings."""
        settings = settings_service.get_auto_backup_settings()
        assert isinstance(settings, dict)
        assert settings["enabled"] is True
        assert settings["frequency"] == "daily"
        assert settings["retention"] == 30

    def test_set_backup_settings(self, settings_service: SettingsService):
        """Test setting backup settings."""
        new_settings = {
            "auto_backup_enabled": False,
            "auto_backup_frequency": "weekly",
            "auto_backup_retention": 60,
        }
        settings_service.set_auto_backup_settings(new_settings)
        retrieved = settings_service.get_auto_backup_settings()
        assert retrieved["enabled"] is False
        assert retrieved["frequency"] == "weekly"
        assert retrieved["retention"] == 60
