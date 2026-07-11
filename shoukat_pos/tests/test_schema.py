"""
Tests for database schema.

Verifies table creation, foreign keys, constraints, and seed data.
"""

import sqlite3

import pytest

from database.schema import create_tables, seed_data, get_next_style_code


class TestSchemaCreation:
    """Test that all tables are created correctly."""

    def test_all_tables_created(self, db_connection: sqlite3.Connection) -> None:
        """Test that all required tables exist."""
        cursor = db_connection.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row[0] for row in cursor.fetchall()}
        cursor.close()

        expected_tables = {
            "categories",
            "vendors",
            "users",
            "customers",
            "styles",
            "variants",
            "batches",
            "sales",
            "sale_items",
            "held_sales",
            "credit_payments",
            "audit_log",
            "returns",
            "return_items",
            "exchanges",
            "sqlite_sequence",  # Auto-created for AUTOINCREMENT
        }

        assert tables == expected_tables

    def test_categories_table_structure(self, db_connection: sqlite3.Connection) -> None:
        """Test categories table has correct columns."""
        cursor = db_connection.cursor()
        cursor.execute("PRAGMA table_info(categories)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        cursor.close()

        assert columns["id"] == "INTEGER"
        assert columns["name"] == "TEXT"
        assert columns["code"] == "TEXT"
        assert columns["tax_rate"] == "REAL"
        assert columns["created_at"] == "TEXT"

    def test_styles_table_has_foreign_key_constraint(
        self, db_connection: sqlite3.Connection
    ) -> None:
        """Test styles table has named foreign key constraint."""
        cursor = db_connection.cursor()
        cursor.execute("PRAGMA foreign_key_list(styles)")
        fks = cursor.fetchall()
        cursor.close()

        # Check for fk_styles_category constraint
        fk_found = any(fk[2] == "categories" for fk in fks)
        assert fk_found

    def test_variants_table_has_unique_constraint(
        self, db_connection: sqlite3.Connection
    ) -> None:
        """Test variants table has unique constraint on (style_id, size, color)."""
        cursor = db_connection.cursor()
        cursor.execute("PRAGMA index_list(variants)")
        indexes = cursor.fetchall()

        # Look for the unique constraint index
        unique_found = False
        for idx in indexes:
            if idx[1].startswith("sqlite_autoindex") or "uq_variant" in idx[1]:
                cursor.execute(f"PRAGMA index_info({idx[1]})")
                cols = [row[2] for row in cursor.fetchall()]
                if set(cols) == {"style_id", "size", "color"}:
                    unique_found = True
                    break
        
        cursor.close()
        assert unique_found


class TestForeignKeys:
    """Test foreign key enforcement."""

    def test_foreign_keys_enforced(self, db_connection: sqlite3.Connection) -> None:
        """Test that foreign keys are enforced."""
        cursor = db_connection.cursor()
        cursor.execute("PRAGMA foreign_keys")
        result = cursor.fetchone()
        cursor.close()

        assert result[0] == 1

    def test_cascade_delete_on_variants(
        self, db_connection: sqlite3.Connection, sample_style_data: dict
    ) -> None:
        """Test that deleting a style cascades to variants."""
        cursor = db_connection.cursor()

        # Insert a style
        cursor.execute(
            """
            INSERT INTO styles (style_code, name, category_id, description,
            base_sale_price, tax_rate, season, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sample_style_data["style_code"],
                sample_style_data["name"],
                sample_style_data["category_id"],
                sample_style_data["description"],
                sample_style_data["base_sale_price"],
                sample_style_data["tax_rate"],
                sample_style_data["season"],
                "2024-01-15T10:00:00",
                "2024-01-15T10:00:00",
            ),
        )
        style_id = cursor.lastrowid

        # Insert a variant
        cursor.execute(
            """
            INSERT INTO variants (style_id, size, color, barcode, quantity,
            reorder_point, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (style_id, "M", "Blue", "TEST-001", 10, 5, "2024-01-15T10:00:00", "2024-01-15T10:00:00"),
        )

        # Delete the style
        cursor.execute("DELETE FROM styles WHERE id = ?", (style_id,))

        # Verify variant was deleted
        cursor.execute("SELECT COUNT(*) FROM variants WHERE style_id = ?", (style_id,))
        count = cursor.fetchone()[0]
        cursor.close()

        assert count == 0


class TestSeedData:
    """Test seed data insertion."""

    def test_default_categories_inserted(self, db_connection: sqlite3.Connection) -> None:
        """Test that default categories are inserted."""
        cursor = db_connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM categories")
        count = cursor.fetchone()[0]
        cursor.close()

        assert count >= 8  # At least 8 default categories

    def test_admin_user_inserted(self, db_connection: sqlite3.Connection) -> None:
        """Test that admin user is inserted."""
        cursor = db_connection.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", ("admin",))
        user = cursor.fetchone()
        cursor.close()

        assert user is not None
        assert user["role"] == "admin"

    def test_category_codes_are_unique(
        self, db_connection: sqlite3.Connection
    ) -> None:
        """Test that category codes are unique."""
        cursor = db_connection.cursor()
        cursor.execute("SELECT code, COUNT(*) as cnt FROM categories GROUP BY code HAVING cnt > 1")
        duplicates = cursor.fetchall()
        cursor.close()

        assert len(duplicates) == 0


class TestTriggers:
    """Test automatic timestamp triggers."""

    def test_update_styles_timestamp_trigger(
        self, db_connection: sqlite3.Connection, sample_style_data: dict
    ) -> None:
        """Test that updating a style updates the timestamp."""
        cursor = db_connection.cursor()

        # Insert a style
        cursor.execute(
            """
            INSERT INTO styles (style_code, name, category_id, description,
            base_sale_price, tax_rate, season, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sample_style_data["style_code"],
                sample_style_data["name"],
                sample_style_data["category_id"],
                sample_style_data["description"],
                sample_style_data["base_sale_price"],
                sample_style_data["tax_rate"],
                sample_style_data["season"],
                "2024-01-15T10:00:00",
                "2024-01-15T10:00:00",
            ),
        )
        style_id = cursor.lastrowid

        # Get initial updated_at
        cursor.execute("SELECT updated_at FROM styles WHERE id = ?", (style_id,))
        initial_updated_at = cursor.fetchone()[0]

        # Update the style
        cursor.execute(
            "UPDATE styles SET name = ? WHERE id = ?",
            ("Updated Name", style_id),
        )

        # Get new updated_at
        cursor.execute("SELECT updated_at FROM styles WHERE id = ?", (style_id,))
        new_updated_at = cursor.fetchone()[0]
        cursor.close()

        assert new_updated_at != initial_updated_at


class TestStyleCodeGeneration:
    """Test style code generation function."""

    def test_get_next_style_code_first_code(
        self, db_connection: sqlite3.Connection
    ) -> None:
        """Test generating first style code for a category."""
        code = get_next_style_code(db_connection, "SH")
        assert code == "SSG-SH-001"

    def test_get_next_style_code_incrementing(
        self, db_connection: sqlite3.Connection
    ) -> None:
        """Test that style codes increment correctly."""
        # First code
        code1 = get_next_style_code(db_connection, "PA")
        assert code1 == "SSG-PA-001"

        # Insert the style
        cursor = db_connection.cursor()
        cursor.execute(
            """
            INSERT INTO styles (style_code, name, category_id, base_sale_price, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (code1, "Test Pant", 2, 100000, "2024-01-15T10:00:00", "2024-01-15T10:00:00"),
        )
        cursor.close()

        # Second code
        code2 = get_next_style_code(db_connection, "PA")
        assert code2 == "SSG-PA-002"

    def test_get_next_style_code_case_insensitive(
        self, db_connection: sqlite3.Connection
    ) -> None:
        """Test that category code is case-insensitive."""
        code1 = get_next_style_code(db_connection, "sh")
        code2 = get_next_style_code(db_connection, "SH")

        # Both should generate codes with uppercase prefix
        assert code1.startswith("SSG-SH-")
        assert code2.startswith("SSG-SH-")
