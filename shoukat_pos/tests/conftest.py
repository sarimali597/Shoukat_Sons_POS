"""
Pytest fixtures for Shoukat Sons Garments POS tests.

Provides in-memory SQLite database, sample data, and test utilities.
"""

import sqlite3
import tempfile
from pathlib import Path
from typing import Generator

import pytest

from database.connection import ConnectionManager
from database.schema import create_tables, seed_data


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
def connection_manager(temp_db_path: Path) -> Generator[ConnectionManager, None, None]:
    """
    Create a ConnectionManager instance with a temporary database.

    Args:
        temp_db_path: Temporary database path fixture.

    Yields:
        ConnectionManager instance configured for testing.
    """
    # Reset singleton state before creating new instance
    ConnectionManager._instance = None
    ConnectionManager._lock = type(ConnectionManager)._lock.__class__()
    
    cm = ConnectionManager(database_path=temp_db_path)
    yield cm
    
    # Clean up singleton state after test
    cm.close_all()


@pytest.fixture
def db_connection(connection_manager: ConnectionManager) -> Generator[sqlite3.Connection, None, None]:
    """
    Create a database connection with schema and seed data.

    Args:
        connection_manager: ConnectionManager fixture.

    Yields:
        SQLite connection ready for testing.
    """
    conn = connection_manager.get_read_connection()
    create_tables(conn)
    seed_data(conn)
    yield conn
    conn.close()


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
