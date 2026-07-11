"""
Update verification mechanism for Shoukat Sons Garments POS.

This module provides secure update checking with SHA-256 integrity verification.
The original design (check a JSON file for version, download new .exe, swap via
batch script) has no integrity verification. Anyone able to spoof that JSON
response could push an arbitrary executable onto the shop PC.

Minimum fix: SHA-256 checksum verification.

Future-proofing note: If Shoukat POS is ever distributed beyond your own shop
(second location, other retailers), replace the hand-rolled checksum approach
with `tufup` — a maintained, TUF-based (The Update Framework) update library
built specifically for standalone Python applications, with real cryptographic
signing rather than a hand-rolled checksum. The SHA-256 approach above is a
floor, not a destination.
"""

import hashlib
import json
import logging
import urllib.request
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class UpdateChecker:
    """Check for and verify application updates."""

    UPDATE_URL = "https://your-domain.com/shoukat-pos/updates.json"

    def __init__(self, current_version: str) -> None:
        """Initialize the update checker.

        Args:
            current_version: Current application version string (e.g., "1.0.0").
        """
        assert isinstance(current_version, str), "current_version must be a string"
        assert len(current_version) > 0, "current_version cannot be empty"
        self.current_version = current_version

    def check_for_update(self) -> Optional[dict]:
        """Check if a newer version is available.

        Returns:
            Update info dict with version, url, sha256, release_notes
            or None if no update available or check failed.
        """
        try:
            with urllib.request.urlopen(self.UPDATE_URL, timeout=10) as response:
                data = json.loads(response.read().decode())
                latest = data.get("latest_version")
                if self._is_newer(latest, self.current_version):
                    return data
                return None
        except Exception as e:
            logger.warning(f"Update check failed: {e}")
            return None

    def verify_update(self, file_path: Path, expected_sha256: str) -> bool:
        """Verify a downloaded update file against its SHA-256 hash.

        This is the minimum fix for a real gap: the original check-JSON-then-
        swap design has no integrity verification at all. Publish the SHA-256
        of each release alongside the version number, and refuse to install if
        it doesn't match.

        Args:
            file_path: Path to the downloaded update file.
            expected_sha256: Expected SHA-256 hash string (lowercase hex).

        Returns:
            True if the file's SHA-256 matches the expected value, False otherwise.
        """
        assert isinstance(file_path, Path), "file_path must be a Path object"
        assert isinstance(expected_sha256, str), "expected_sha256 must be a string"
        assert len(expected_sha256) == 64, "expected_sha256 must be 64 hex characters"
        assert file_path.exists(), f"File does not exist: {file_path}"

        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256_hash.update(chunk)
        computed_hash = sha256_hash.hexdigest()
        return computed_hash.lower() == expected_sha256.lower()

    def download_update(self, url: str, dest_path: Path) -> bool:
        """Download update file to temp location.

        Args:
            url: URL to download the update from.
            dest_path: Destination path for the downloaded file.

        Returns:
            True if download succeeded, False otherwise.
        """
        assert isinstance(url, str), "url must be a string"
        assert isinstance(dest_path, Path), "dest_path must be a Path object"
        assert len(url) > 0, "url cannot be empty"

        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                with open(dest_path, "wb") as out_file:
                    for chunk in iter(lambda: response.read(8192), b""):
                        out_file.write(chunk)
            return True
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return False

    def apply_update(self, update_file: Path) -> bool:
        """Apply update by replacing executable on next restart.

        Uses a Windows batch script to swap the executable after the current
        process exits.

        Args:
            update_file: Path to the verified update archive.

        Returns:
            True if update application was initiated successfully, False otherwise.
        """
        assert isinstance(update_file, Path), "update_file must be a Path object"
        assert update_file.exists(), f"Update file does not exist: {update_file}"

        # Implementation would create a batch script that:
        # 1. Waits for current process to exit
        # 2. Extracts the new version
        # 3. Replaces the old executable
        # 4. Restarts the application
        # This is a stub - full implementation depends on deployment structure
        logger.info(f"Update application initiated for: {update_file}")
        return True

    def _is_newer(self, latest: str, current: str) -> bool:
        """Compare version strings (semantic versioning).

        Args:
            latest: Latest version string from server.
            current: Current version string.

        Returns:
            True if latest is newer than current, False otherwise.
        """
        if not latest or not current:
            return False

        try:
            latest_parts = [int(x) for x in latest.split(".")]
            current_parts = [int(x) for x in current.split(".")]

            # Pad shorter version with zeros
            while len(latest_parts) < 3:
                latest_parts.append(0)
            while len(current_parts) < 3:
                current_parts.append(0)

            for l, c in zip(latest_parts[:3], current_parts[:3]):
                if l > c:
                    return True
                if l < c:
                    return False
            return False
        except ValueError:
            logger.warning(f"Invalid version format: latest={latest}, current={current}")
            return False
