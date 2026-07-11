"""
Pytest fixtures for Shoukat Sons Garments POS tests.

Provides in-memory SQLite database, sample data, and test utilities.
"""

import sqlite3
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, List, Dict, Any

import pytest

from database.connection import ConnectionManager
from database.schema import create_tables, seed_data


@pytest.fixture(scope="function")
def db_connection():
    """
    Create a fresh in-memory database for each test with all production pragmas.
    
    Yields:
        SQLite connection with schema and seed data initialized.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 10000")
    create_tables(conn)
    seed_data(conn)
    yield conn
    conn.close()


@pytest.fixture(scope="function")
def connection_manager(tmp_path: Path) -> Generator[ConnectionManager, None, None]:
    """
    Create a ConnectionManager pointing to a temp directory.
    
    Args:
        tmp_path: Pytest temporary path fixture.
        
    Yields:
        ConnectionManager instance with initialized database.
    """
    # Reset singleton state before creating new instance
    ConnectionManager._instance = None
    ConnectionManager._lock = threading.Lock()
    
    cm = ConnectionManager(database_path=tmp_path / "test.db")
    cm.initialize_database()
    
    yield cm
    
    # Clean up singleton state after test
    cm.close_all()


@pytest.fixture
def sample_category(db_connection: sqlite3.Connection) -> int:
    """
    Insert a sample category and return its ID.
    
    Args:
        db_connection: Database connection fixture.
        
    Returns:
        Category ID.
    """
    cursor = db_connection.cursor()
    cursor.execute(
        "INSERT INTO categories (name, code, tax_rate, created_at) VALUES (?, ?, ?, ?)",
        ("Test Shirt", "TS", 17.0, datetime.now(timezone.utc).isoformat()),
    )
    db_connection.commit()
    return cursor.lastrowid


@pytest.fixture
def sample_style(db_connection: sqlite3.Connection, sample_category: int) -> int:
    """
    Insert a sample style and return its ID.
    
    Args:
        db_connection: Database connection fixture.
        sample_category: Category ID fixture.
        
    Returns:
        Style ID.
    """
    cursor = db_connection.cursor()
    cursor.execute(
        "INSERT INTO styles (style_code, name, category_id, base_sale_price, tax_rate, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "SSG-TS-001",
            "Test Style Shirt",
            sample_category,
            250000,  # Rs. 2500 in cents
            17.0,
            datetime.now(timezone.utc).isoformat(),
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    db_connection.commit()
    return cursor.lastrowid


@pytest.fixture
def sample_variants(db_connection: sqlite3.Connection, sample_style: int) -> List[int]:
    """
    Insert sample variants for a style and return their IDs.
    
    Args:
        db_connection: Database connection fixture.
        sample_style: Style ID fixture.
        
    Returns:
        List of variant IDs.
    """
    cursor = db_connection.cursor()
    variant_ids = []
    
    sizes_colors = [
        ("M", "Blue"),
        ("L", "Blue"),
        ("XL", "Blue"),
        ("M", "Red"),
        ("L", "Red"),
    ]
    
    for size, color in sizes_colors:
        cursor.execute(
            "INSERT INTO variants (style_id, size, color, barcode, quantity, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                sample_style,
                size,
                color,
                f"SSG-{size}-{color[:3].upper()}",
                10,
                datetime.now(timezone.utc).isoformat(),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        variant_ids.append(cursor.lastrowid)
    
    db_connection.commit()
    return variant_ids


@pytest.fixture
def sample_customer(db_connection: sqlite3.Connection) -> int:
    """
    Insert a sample customer and return their ID.
    
    Args:
        db_connection: Database connection fixture.
        
    Returns:
        Customer ID.
    """
    cursor = db_connection.cursor()
    cursor.execute(
        "INSERT INTO customers (name, phone, address, total_due, credit_limit, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (
            "Test Customer",
            "03001234567",
            "Test Address, Lahore",
            0,
            1000000,  # Rs. 10,000 in cents
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    db_connection.commit()
    return cursor.lastrowid


@pytest.fixture
def sample_sale(db_connection: sqlite3.Connection, sample_variants: List[int], sample_customer: int) -> int:
    """
    Insert a sample completed sale and return its ID.
    
    Args:
        db_connection: Database connection fixture.
        sample_variants: Variant IDs fixture.
        sample_customer: Customer ID fixture.
        
    Returns:
        Sale ID.
    """
    cursor = db_connection.cursor()
    
    # Create sale
    cursor.execute(
        "INSERT INTO sales (invoice_number, customer_id, user_id, sale_date, subtotal, tax_amount, discount_amount, total_amount, paid_amount, due_amount, payment_type, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "INV-20240115-0001",
            sample_customer,
            1,
            datetime.now(timezone.utc).isoformat(),
            250000,
            42500,
            0,
            292500,
            292500,
            0,
            "cash",
            "completed",
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    sale_id = cursor.lastrowid
    
    # Create sale item
    cursor.execute(
        "INSERT INTO sale_items (sale_id, variant_id, quantity, unit_price, tax_rate, discount, total) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (sale_id, sample_variants[0], 1, 250000, 17.0, 0, 292500),
    )
    
    db_connection.commit()
    return sale_id


@pytest.fixture
def admin_user(db_connection: sqlite3.Connection) -> int:
    """
    Insert an admin user and return their ID.
    
    Args:
        db_connection: Database connection fixture.
        
    Returns:
        User ID.
    """
    cursor = db_connection.cursor()
    cursor.execute(
        "INSERT INTO users (username, password_hash, role, is_active, created_at) VALUES (?, ?, ?, 1, ?)",
        ("admin", "adminhash123", "admin", datetime.now(timezone.utc).isoformat()),
    )
    db_connection.commit()
    return cursor.lastrowid


@pytest.fixture
def cashier_user(db_connection: sqlite3.Connection) -> int:
    """
    Insert a cashier user and return their ID.
    
    Args:
        db_connection: Database connection fixture.
        
    Returns:
        User ID.
    """
    cursor = db_connection.cursor()
    cursor.execute(
        "INSERT INTO users (username, password_hash, role, is_active, created_at) VALUES (?, ?, ?, 1, ?)",
        ("cashier1", "cashierhash123", "cashier", datetime.now(timezone.utc).isoformat()),
    )
    db_connection.commit()
    return cursor.lastrowid


@pytest.fixture
def temp_db_path() -> Generator[Path, None, None]:
    """
    Create a temporary database file for testing.

    Yields:
        Path to temporary database file.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    db_path.unlink(missing_ok=True)
    # Clean up WAL files if they exist
    db_path.with_suffix(".db-wal").unlink(missing_ok=True)
    db_path.with_suffix(".db-shm").unlink(missing_ok=True)


@pytest.fixture
def temp_settings_file(temp_db_path: Path) -> Generator[Path, None, None]:
    """
    Create a temporary settings file for theme testing.

    Args:
        temp_db_path: Temporary database path fixture (used for base temp dir).

    Yields:
        Path to temporary settings file.
    """
    # Use the same temp directory as the database
    settings_path = temp_db_path.parent / "theme_settings.json"
    
    # Remove existing settings file if it exists
    if settings_path.exists():
        settings_path.unlink()
    
    yield settings_path
    
    # Clean up after test
    if settings_path.exists():
        settings_path.unlink()


@pytest.fixture
def sample_category_data() -> dict:
    """Sample category data for testing."""
    return {
        "name": "Test Shirt",
        "code": "TS",
        "tax_rate": 0.0,
    }


@pytest.fixture
def sample_vendor_data() -> dict:
    """Sample vendor data for testing."""
    return {
        "name": "Test Vendor",
        "location": "Test City",
        "phone": "1234567890",
    }


@pytest.fixture
def sample_user_data() -> dict:
    """Sample user data for testing."""
    return {
        "username": "testuser",
        "password_hash": "testhash",
        "role": "cashier",
        "is_active": 1,
    }


@pytest.fixture
def sample_customer_data() -> dict:
    """Sample customer data for testing."""
    return {
        "name": "Test Customer",
        "phone": "03001234567",
        "address": "Test Address",
        "total_due": 0,
        "credit_limit": 100000,  # Rs. 1000 in cents
    }


@pytest.fixture
def sample_style_data() -> dict:
    """Sample style data for testing."""
    return {
        "style_code": "SSG-TS-001",
        "name": "Test Style Shirt",
        "category_id": 1,
        "description": "A test style",
        "base_sale_price": 250000,  # Rs. 2500 in cents
        "tax_rate": 0.0,
        "season": "Summer",
    }


@pytest.fixture
def sample_variant_data() -> dict:
    """Sample variant data for testing."""
    return {
        "style_id": 1,
        "size": "M",
        "color": "Blue",
        "barcode": "SSG001-M-BLU",
        "quantity": 10,
        "reorder_point": 5,
    }


@pytest.fixture
def sample_batch_data() -> dict:
    """Sample batch data for testing."""
    return {
        "variant_id": 1,
        "purchase_price": 150000,  # Rs. 1500 in cents
        "secret_code": "abc",
        "quantity_received": 20,
        "quantity_remaining": 20,
        "vendor_id": 1,
        "bilty_no": "BILTY001",
        "bill_no": "BILL001",
        "date_received": "2024-01-15T10:00:00",
    }


@pytest.fixture
def sample_sale_data() -> dict:
    """Sample sale data for testing."""
    return {
        "invoice_number": "INV-20240115-0001",
        "customer_id": 1,
        "user_id": 1,
        "sale_date": "2024-01-15T12:00:00",
        "subtotal": 250000,
        "tax_amount": 0,
        "discount_amount": 0,
        "total_amount": 250000,
        "paid_amount": 250000,
        "due_amount": 0,
        "payment_type": "cash",
        "status": "completed",
    }
