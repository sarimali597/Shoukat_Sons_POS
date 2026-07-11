"""
Database schema definitions for Shoukat Sons Garments POS.

Contains CREATE TABLE statements with named constraints, triggers,
and seed data initialization. All monetary values are INTEGER cents.
"""

import sqlite3
from datetime import datetime, timezone

from config import (
    DEFAULT_ADMIN_PASSWORD,
    DEFAULT_ADMIN_ROLE,
    DEFAULT_ADMIN_USERNAME,
    DEFAULT_CATEGORIES,
)


def create_tables(conn: sqlite3.Connection) -> None:
    """
    Create all database tables with named constraints and triggers.

    Args:
        conn: SQLite connection to execute schema creation.
    """
    cursor = conn.cursor()

    # Enable foreign keys for this session
    cursor.execute("PRAGMA foreign_keys=ON")

    # Categories table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            code TEXT NOT NULL UNIQUE,
            tax_rate REAL DEFAULT 0.0,
            created_at TEXT NOT NULL
        )
    """)

    # Vendors table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            location TEXT,
            phone TEXT,
            created_at TEXT NOT NULL
        )
    """)

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            last_login TEXT,
            created_at TEXT NOT NULL
        )
    """)

    # Customers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT UNIQUE,
            address TEXT,
            total_due INTEGER DEFAULT 0,
            credit_limit INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    # Styles table (parent product definition)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS styles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            style_code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            category_id INTEGER NOT NULL,
            description TEXT,
            base_sale_price INTEGER NOT NULL,
            tax_rate REAL DEFAULT 0.0,
            season TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            CONSTRAINT fk_styles_category FOREIGN KEY (category_id) 
                REFERENCES categories(id) ON DELETE RESTRICT
        )
    """)

    # Variants table (size-color combinations)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS variants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            style_id INTEGER NOT NULL,
            size TEXT NOT NULL,
            color TEXT NOT NULL,
            barcode TEXT NOT NULL UNIQUE,
            quantity INTEGER DEFAULT 0,
            reorder_point INTEGER DEFAULT 5,
            sync_status TEXT DEFAULT 'local',
            modified_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            CONSTRAINT fk_variants_style FOREIGN KEY (style_id) 
                REFERENCES styles(id) ON DELETE CASCADE,
            CONSTRAINT uq_variant_size_color UNIQUE (style_id, size, color)
        )
    """)

    # Batches table (purchase batches with cost tracking)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            variant_id INTEGER NOT NULL,
            purchase_price INTEGER NOT NULL,
            secret_code TEXT NOT NULL,
            quantity_received INTEGER NOT NULL,
            quantity_remaining INTEGER NOT NULL,
            vendor_id INTEGER,
            bilty_no TEXT,
            bill_no TEXT,
            date_received TEXT NOT NULL,
            created_at TEXT NOT NULL,
            CONSTRAINT fk_batches_variant FOREIGN KEY (variant_id) 
                REFERENCES variants(id) ON DELETE CASCADE,
            CONSTRAINT fk_batches_vendor FOREIGN KEY (vendor_id) 
                REFERENCES vendors(id) ON DELETE SET NULL
        )
    """)

    # Sales table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT NOT NULL UNIQUE,
            customer_id INTEGER,
            user_id INTEGER NOT NULL,
            sale_date TEXT NOT NULL,
            subtotal INTEGER NOT NULL,
            tax_amount INTEGER DEFAULT 0,
            discount_amount INTEGER DEFAULT 0,
            total_amount INTEGER NOT NULL,
            paid_amount INTEGER DEFAULT 0,
            due_amount INTEGER DEFAULT 0,
            payment_type TEXT NOT NULL,
            status TEXT DEFAULT 'completed',
            created_at TEXT NOT NULL,
            CONSTRAINT fk_sales_customer FOREIGN KEY (customer_id) 
                REFERENCES customers(id) ON DELETE SET NULL,
            CONSTRAINT fk_sales_user FOREIGN KEY (user_id) 
                REFERENCES users(id) ON DELETE RESTRICT
        )
    """)

    # Sale items table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            variant_id INTEGER NOT NULL,
            batch_id INTEGER,
            quantity INTEGER NOT NULL,
            unit_price INTEGER NOT NULL,
            tax_amount INTEGER DEFAULT 0,
            total_price INTEGER NOT NULL,
            is_returned INTEGER DEFAULT 0,
            CONSTRAINT fk_sale_items_sale FOREIGN KEY (sale_id) 
                REFERENCES sales(id) ON DELETE CASCADE,
            CONSTRAINT fk_sale_items_variant FOREIGN KEY (variant_id) 
                REFERENCES variants(id) ON DELETE RESTRICT,
            CONSTRAINT fk_sale_items_batch FOREIGN KEY (batch_id) 
                REFERENCES batches(id) ON DELETE SET NULL
        )
    """)

    # Audit log table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT NOT NULL,
            record_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            old_values TEXT,
            new_values TEXT,
            user_id INTEGER,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            hmac_hash TEXT NOT NULL,
            CONSTRAINT fk_audit_log_user FOREIGN KEY (user_id) 
                REFERENCES users(id) ON DELETE SET NULL
        )
    """)

    # Create updated_at triggers for automatic timestamp maintenance
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS update_styles_timestamp 
        AFTER UPDATE ON styles
        BEGIN
            UPDATE styles SET updated_at = CURRENT_TIMESTAMP 
            WHERE id = NEW.id;
        END
    """)

    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS update_variants_timestamp 
        AFTER UPDATE ON variants
        BEGIN
            UPDATE variants SET updated_at = CURRENT_TIMESTAMP 
            WHERE id = NEW.id;
        END
    """)

    conn.commit()
    cursor.close()


def seed_data(conn: sqlite3.Connection) -> None:
    """
    Insert default seed data into the database.

    Inserts default categories and admin user if they don't exist.

    Args:
        conn: SQLite connection to insert seed data.
    """
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()

    # Insert default categories
    for category in DEFAULT_CATEGORIES:
        cursor.execute(
            """
            INSERT OR IGNORE INTO categories (name, code, tax_rate, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (category["name"], category["code"], category["tax_rate"], now),
        )

    # Insert default admin user (password should be hashed by caller)
    cursor.execute(
        """
        INSERT OR IGNORE INTO users (username, password_hash, role, is_active, created_at)
        VALUES (?, ?, ?, 1, ?)
        """,
        (DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_ROLE, now),
    )

    conn.commit()
    cursor.close()


def get_next_style_code(conn: sqlite3.Connection, category_code: str) -> str:
    """
    Generate the next style code for a given category.

    Format: SSG-[category_code]-[NNN] where NNN is zero-padded sequence.

    Args:
        conn: SQLite connection.
        category_code: Category code (e.g., 'SH' for Shirt).

    Returns:
        Generated style code string.
    """
    assert len(category_code) <= 4

    cursor = conn.cursor()
    prefix = f"SSG-{category_code.upper()}-"

    cursor.execute(
        """
        SELECT MAX(CAST(SUBSTR(style_code, LENGTH(?) + 1) AS INTEGER)) as max_seq
        FROM styles
        WHERE style_code LIKE ? || '%'
        """,
        (prefix, prefix),
    )
    result = cursor.fetchone()
    cursor.close()

    max_seq = result[0] if result and result[0] else 0
    return f"{prefix}{max_seq + 1:03d}"
