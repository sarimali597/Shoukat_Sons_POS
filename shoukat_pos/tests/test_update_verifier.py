"""
Tests for the UpdateChecker class in utils/update_verifier.py.

These tests verify:
- Version comparison logic
- SHA-256 hash verification
- Update checking behavior (mocked)
- Download functionality (mocked)
"""

import hashlib
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from shoukat_pos.utils.update_verifier import UpdateChecker


class TestVersionComparison:
    """Test semantic version comparison."""

    def test_is_newer_major_version(self) -> None:
        """Test that major version increments are detected."""
        checker = UpdateChecker("1.0.0")
        assert checker._is_newer("2.0.0", "1.0.0") is True
        assert checker._is_newer("1.0.0", "2.0.0") is False

    def test_is_newer_minor_version(self) -> None:
        """Test that minor version increments are detected."""
        checker = UpdateChecker("1.0.0")
        assert checker._is_newer("1.1.0", "1.0.0") is True
        assert checker._is_newer("1.0.0", "1.1.0") is False

    def test_is_newer_patch_version(self) -> None:
        """Test that patch version increments are detected."""
        checker = UpdateChecker("1.0.0")
        assert checker._is_newer("1.0.1", "1.0.0") is True
        assert checker._is_newer("1.0.0", "1.0.1") is False

    def test_is_newer_same_version(self) -> None:
        """Test that same versions return False."""
        checker = UpdateChecker("1.0.0")
        assert checker._is_newer("1.0.0", "1.0.0") is False

    def test_is_newer_invalid_versions(self) -> None:
        """Test handling of invalid version strings."""
        checker = UpdateChecker("1.0.0")
        assert checker._is_newer("", "1.0.0") is False
        assert checker._is_newer(None, "1.0.0") is False  # type: ignore
        assert checker._is_newer("invalid", "1.0.0") is False

    def test_is_newer_partial_versions(self) -> None:
        """Test handling of partial version strings."""
        checker = UpdateChecker("1.0.0")
        # Should pad with zeros
        assert checker._is_newer("1.1", "1.0.0") is True
        assert checker._is_newer("2", "1.9.9") is True


class TestSHA256Verification:
    """Test SHA-256 hash verification for update integrity."""

    def test_verify_update_correct_hash(self) -> None:
        """Test verification with correct SHA-256 hash."""
        checker = UpdateChecker("1.0.0")
        
        # Create a test file
        content = b"Test update content for verification"
        expected_hash = hashlib.sha256(content).hexdigest()
        
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)
        
        try:
            assert checker.verify_update(temp_path, expected_hash) is True
        finally:
            temp_path.unlink()

    def test_verify_update_incorrect_hash(self) -> None:
        """Test verification fails with incorrect SHA-256 hash."""
        checker = UpdateChecker("1.0.0")
        
        # Create a test file
        content = b"Test update content for verification"
        wrong_hash = "a" * 64  # Invalid hash
        
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)
        
        try:
            assert checker.verify_update(temp_path, wrong_hash) is False
        finally:
            temp_path.unlink()

    def test_verify_update_case_insensitive(self) -> None:
        """Test that hash comparison is case-insensitive."""
        checker = UpdateChecker("1.0.0")
        
        content = b"Test update content"
        hash_lower = hashlib.sha256(content).hexdigest()
        hash_upper = hash_lower.upper()
        
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)
        
        try:
            # Both lower and upper case should work
            assert checker.verify_update(temp_path, hash_lower) is True
            assert checker.verify_update(temp_path, hash_upper) is True
        finally:
            temp_path.unlink()

    def test_verify_update_nonexistent_file(self) -> None:
        """Test verification fails for non-existent file."""
        checker = UpdateChecker("1.0.0")
        fake_hash = "a" * 64
        fake_path = Path("/nonexistent/file.txt")
        
        with pytest.raises(AssertionError):
            checker.verify_update(fake_path, fake_hash)

    def test_verify_update_invalid_hash_length(self) -> None:
        """Test verification fails with invalid hash length."""
        checker = UpdateChecker("1.0.0")
        
        content = b"Test"
        short_hash = "abc123"  # Too short
        
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(AssertionError):
                checker.verify_update(temp_path, short_hash)
        finally:
            temp_path.unlink()


class TestUpdateChecking:
    """Test update checking functionality (with mocked network)."""

    @patch('shoukat_pos.utils.update_verifier.urllib.request.urlopen')
    def test_check_for_update_available(self, mock_urlopen: MagicMock) -> None:
        """Test that available updates are detected."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "latest_version": "2.0.0",
            "download_url": "https://example.com/update.zip",
            "sha256": "a" * 64,
            "release_notes": "Bug fixes"
        }).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = lambda s, *args: None
        mock_urlopen.return_value = mock_response
        
        checker = UpdateChecker("1.0.0")
        result = checker.check_for_update()
        
        assert result is not None
        assert result["latest_version"] == "2.0.0"

    @patch('shoukat_pos.utils.update_verifier.urllib.request.urlopen')
    def test_check_for_no_update(self, mock_urlopen: MagicMock) -> None:
        """Test that no update is returned when current version is latest."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "latest_version": "1.0.0",
            "download_url": "https://example.com/update.zip",
            "sha256": "a" * 64,
            "release_notes": "Current version"
        }).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = lambda s, *args: None
        mock_urlopen.return_value = mock_response
        
        checker = UpdateChecker("1.0.0")
        result = checker.check_for_update()
        
        assert result is None

    @patch('shoukat_pos.utils.update_verifier.urllib.request.urlopen')
    def test_check_for_update_network_error(self, mock_urlopen: MagicMock) -> None:
        """Test that network errors are handled gracefully."""
        mock_urlopen.side_effect = Exception("Network error")
        
        checker = UpdateChecker("1.0.0")
        result = checker.check_for_update()
        
        assert result is None


class TestDownloadUpdate:
    """Test download functionality (with mocked network)."""

    @patch('shoukat_pos.utils.update_verifier.urllib.request.urlopen')
    def test_download_update_success(self, mock_urlopen: MagicMock) -> None:
        """Test successful download."""
        mock_response = MagicMock()
        mock_response.read.side_effect = [b"chunk1", b"chunk2", b""]
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = lambda s, *args: None
        mock_urlopen.return_value = mock_response
        
        checker = UpdateChecker("1.0.0")
        
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            result = checker.download_update("https://example.com/update.zip", temp_path)
            assert result is True
            # Verify file was written
            assert temp_path.stat().st_size > 0
        finally:
            if temp_path.exists():
                temp_path.unlink()

    @patch('shoukat_pos.utils.update_verifier.urllib.request.urlopen')
    def test_download_update_network_error(self, mock_urlopen: MagicMock) -> None:
        """Test download handles network errors."""
        mock_urlopen.side_effect = Exception("Download failed")
        
        checker = UpdateChecker("1.0.0")
        
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            result = checker.download_update("https://example.com/update.zip", temp_path)
            assert result is False
        finally:
            if temp_path.exists():
                temp_path.unlink()


class TestApplyUpdate:
    """Test update application logic."""

    def test_apply_update_with_valid_file(self) -> None:
        """Test applying update with valid file path."""
        checker = UpdateChecker("1.0.0")
        
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"update content")
            temp_path = Path(f.name)
        
        try:
            # This is a stub implementation, just verifies it doesn't crash
            result = checker.apply_update(temp_path)
            assert result is True
        finally:
            temp_path.unlink()

    def test_apply_update_with_nonexistent_file(self) -> None:
        """Test applying update fails with non-existent file."""
        checker = UpdateChecker("1.0.0")
        fake_path = Path("/nonexistent/update.zip")
        
        with pytest.raises(AssertionError):
            checker.apply_update(fake_path)


class TestUpdateCheckerInitialization:
    """Test UpdateChecker initialization and validation."""

    def test_init_valid_version(self) -> None:
        """Test initialization with valid version string."""
        checker = UpdateChecker("1.0.0")
        assert checker.current_version == "1.0.0"

    def test_init_empty_version(self) -> None:
        """Test initialization fails with empty version."""
        with pytest.raises(AssertionError):
            UpdateChecker("")

    def test_init_invalid_type(self) -> None:
        """Test initialization fails with non-string version."""
        with pytest.raises(AssertionError):
            UpdateChecker(123)  # type: ignore
