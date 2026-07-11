"""
Configuration constants, paths, and default settings for Shoukat Sons Garments POS.

All paths are defined using pathlib.Path for cross-platform compatibility.
The data directory is created with 0o700 permissions on first run.
"""

from pathlib import Path
from typing import Final

# =============================================================================
# Application Constants
# =============================================================================

APP_NAME: Final[str] = "Shoukat Sons Garments POS"
APP_VERSION: Final[str] = "1.0.0"
CURRENCY_SYMBOL: Final[str] = "Rs."
CURRENCY_CODE: Final[str] = "PKR"

# =============================================================================
# Size and Color Options for Garment Variants
# =============================================================================

SIZE_OPTIONS: Final[tuple[str, ...]] = ("S", "M", "L", "XL", "XXL", "XXXL")

COLOR_OPTIONS: Final[tuple[str, ...]] = (
    "Black",
    "White",
    "Blue",
    "Red",
    "Green",
    "Navy",
    "Grey",
    "Brown",
)

# =============================================================================
# Default Categories (seed data)
# =============================================================================

DEFAULT_CATEGORIES: Final[list[dict[str, str | float]]] = [
    {"name": "Shirt", "code": "SH", "tax_rate": 0.0},
    {"name": "Pant", "code": "PA", "tax_rate": 0.0},
    {"name": "Tie", "code": "TI", "tax_rate": 0.0},
    {"name": "Coat", "code": "CO", "tax_rate": 0.0},
    {"name": "Blazer", "code": "BL", "tax_rate": 0.0},
    {"name": "Waistcoat", "code": "WA", "tax_rate": 0.0},
    {"name": "Sherwani", "code": "SE", "tax_rate": 0.0},
    {"name": "Kurta", "code": "KU", "tax_rate": 0.0},
]

# =============================================================================
# Default Admin User (seed data)
# Password: admin123 (will be hashed with bcrypt on first run)
# =============================================================================

DEFAULT_ADMIN_USERNAME: Final[str] = "admin"
DEFAULT_ADMIN_PASSWORD: Final[str] = "admin123"
DEFAULT_ADMIN_ROLE: Final[str] = "admin"

# =============================================================================
# Secret Code Mapping (purchase price encoding)
# Single-character-per-digit encoding, visible only to owner/manager
# =============================================================================

SECRET_CODE_MAPPING: Final[dict[str, int]] = {
    "a": 0,
    "b": 1,
    "c": 2,
    "d": 3,
    "e": 4,
    "f": 5,
    "g": 6,
    "h": 7,
    "i": 8,
    "j": 9,
}

# Reverse mapping for decoding
SECRET_CODE_REVERSE: Final[dict[int, str]] = {v: k for k, v in SECRET_CODE_MAPPING.items()}

# =============================================================================
# Path Configuration
# =============================================================================

# Base directory (where main.py resides)
BASE_DIR: Final[Path] = Path(__file__).parent.resolve()

# Data directory (SQLite database, backups, logs)
DATA_DIR: Final[Path] = BASE_DIR / "data"
DATABASE_PATH: Final[Path] = DATA_DIR / "shoukat_pos.db"
BACKUP_DIR: Final[Path] = DATA_DIR / "backups"
LOG_DIR: Final[Path] = DATA_DIR / "logs"

# Assets directory
ASSETS_DIR: Final[Path] = BASE_DIR / "assets"
ICONS_DIR: Final[Path] = ASSETS_DIR / "icons"
FONTS_DIR: Final[Path] = ASSETS_DIR / "fonts"
BARCODE_TEMPLATES_DIR: Final[Path] = ASSETS_DIR / "barcode_templates"
LOGO_PATH: Final[Path] = ASSETS_DIR / "logo.png"

# Migrations directory
MIGRATIONS_DIR: Final[Path] = BASE_DIR / "migrations"

# =============================================================================
# Database Configuration
# =============================================================================

DB_WAL_MODE: Final[str] = "WAL"
DB_SYNCHRONOUS: Final[str] = "NORMAL"
DB_BUSY_TIMEOUT_MS: Final[int] = 10000  # 10 seconds
DB_CACHE_SIZE_KB: Final[int] = -64000  # 64 MB (negative means KB)
DB_MMAP_SIZE_BYTES: Final[int] = 268435456  # 256 MB
DB_FOREIGN_KEYS: Final[str] = "ON"
DB_TEMP_STORE: Final[str] = "MEMORY"
DB_SECURE_DELETE: Final[str] = "ON"
DB_WAL_AUTOCHECKPOINT: Final[int] = 1000

# =============================================================================
# Printer Configuration
# =============================================================================

# Label printer: BlackCopper BC-LP-1300, 203 DPI, TSPL command language
LABEL_PRINTER_NAME: Final[str] = "BlackCopper BC-LP-1300"
LABEL_PRINTER_DPI: Final[int] = 203
LABEL_WIDTH_MM: Final[int] = 100  # Standard label width
LABEL_HEIGHT_MM: Final[int] = 150  # Standard label height

# Receipt printer: generic 80mm thermal, ESC/POS protocol
RECEIPT_PRINTER_WIDTH: Final[int] = 80  # mm

# =============================================================================
# Barcode Configuration
# =============================================================================

BARCODE_FORMAT: Final[str] = "CODE128"
BARCODE_PREFIX: Final[str] = "SSG"  # Shoukat Sons Garments

# =============================================================================
# Invoice Numbering
# =============================================================================

INVOICE_PREFIX: Final[str] = "INV"
INVOICE_DATE_FORMAT: Final[str] = "%Y%m%d"

# =============================================================================
# Security Configuration
# =============================================================================

BCRYPT_ROUNDS: Final[int] = 12
AUDIT_HMAC_KEY: Final[bytes] = b"shoukat_sons_audit_key_change_in_production"  # TODO: Move to env var

# =============================================================================
# Backup Configuration
# =============================================================================

BACKUP_RETENTION_DAYS: Final[int] = 30
BACKUP_ENCRYPTION_ALGORITHM: Final[str] = "AES-256-GCM"

# =============================================================================
# First Run Wizard
# =============================================================================

FIRST_RUN_FLAG_FILE: Final[Path] = DATA_DIR / ".first_run_complete"


def ensure_data_directory() -> None:
    """
    Ensure the data directory exists with proper permissions (0o700).

    Creates the directory if it doesn't exist, and sets owner-only access.
    Also creates subdirectories for backups and logs.
    """
    for directory in [DATA_DIR, BACKUP_DIR, LOG_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
        # Set permissions to owner-only (read/write/execute)
        try:
            directory.chmod(0o700)
        except OSError:
            # On Windows, chmod may not work as expected; skip silently
            pass
