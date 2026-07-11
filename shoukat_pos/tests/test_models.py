"""
Tests for dataclass models.

Verifies model creation, validation, and row parsing.
"""

import sqlite3
from datetime import datetime, timezone

import pytest

from database.models import (
    Category,
    Vendor,
    User,
    Customer,
    Style,
    Variant,
    Batch,
    Sale,
    SaleItem,
    AuditLog,
)


class TestCategoryModel:
    """Test Category dataclass."""

    def test_create_category(self) -> None:
        """Test creating a Category instance."""
        category = Category(name="Shirt", code="SH", tax_rate=0.0)

        assert category.name == "Shirt"
        assert category.code == "SH"
        assert category.tax_rate == 0.0
        assert category.id is None

    def test_category_validate(self) -> None:
        """Test Category validation."""
        valid_category = Category(name="Shirt", code="SH")
        invalid_category = Category(name="", code="")

        assert valid_category.validate() is True
        assert invalid_category.validate() is False

    def test_category_from_row(self, db_connection: sqlite3.Connection) -> None:
        """Test creating Category from sqlite3.Row."""
        cursor = db_connection.cursor()
        cursor.execute("SELECT * FROM categories WHERE code = ?", ("SH",))
        row = cursor.fetchone()
        cursor.close()

        if row:
            category = Category.from_row(row)
            assert category.name == "Shirt"
            assert category.code == "SH"


class TestVendorModel:
    """Test Vendor dataclass."""

    def test_create_vendor(self) -> None:
        """Test creating a Vendor instance."""
        vendor = Vendor(name="Test Vendor", location="Karachi", phone="1234567890")

        assert vendor.name == "Test Vendor"
        assert vendor.location == "Karachi"
        assert vendor.phone == "1234567890"

    def test_vendor_validate(self) -> None:
        """Test Vendor validation."""
        valid_vendor = Vendor(name="Test Vendor")
        invalid_vendor = Vendor(name="")

        assert valid_vendor.validate() is True
        assert invalid_vendor.validate() is False


class TestUserModel:
    """Test User dataclass."""

    def test_create_user(self) -> None:
        """Test creating a User instance."""
        user = User(username="testuser", password_hash="hash123", role="cashier")

        assert user.username == "testuser"
        assert user.password_hash == "hash123"
        assert user.role == "cashier"
        assert user.is_active == 1

    def test_user_validate(self) -> None:
        """Test User validation."""
        valid_user = User(username="test", password_hash="hash", role="admin")
        invalid_user = User(username="", password_hash="", role="")

        assert valid_user.validate() is True
        assert invalid_user.validate() is False

    def test_user_is_admin(self) -> None:
        """Test User is_admin method."""
        admin_user = User(username="admin", password_hash="hash", role="admin")
        cashier_user = User(username="cashier", password_hash="hash", role="cashier")

        assert admin_user.is_admin() is True
        assert cashier_user.is_admin() is False

    def test_user_from_row(self, db_connection: sqlite3.Connection) -> None:
        """Test creating User from sqlite3.Row."""
        cursor = db_connection.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", ("admin",))
        row = cursor.fetchone()
        cursor.close()

        assert row is not None
        user = User.from_row(row)
        assert user.username == "admin"
        assert user.role == "admin"
        assert user.is_admin() is True


class TestCustomerModel:
    """Test Customer dataclass."""

    def test_create_customer(self) -> None:
        """Test creating a Customer instance."""
        customer = Customer(
            name="John Doe",
            phone="03001234567",
            address="Test Address",
            total_due=0,
            credit_limit=100000,
        )

        assert customer.name == "John Doe"
        assert customer.phone == "03001234567"
        assert customer.total_due == 0

    def test_customer_validate(self) -> None:
        """Test Customer validation."""
        valid_customer = Customer(name="John Doe")
        invalid_customer = Customer(name="")

        assert valid_customer.validate() is True
        assert invalid_customer.validate() is False


class TestStyleModel:
    """Test Style dataclass."""

    def test_create_style(self) -> None:
        """Test creating a Style instance."""
        style = Style(
            style_code="SSG-SH-001",
            name="Premium Shirt",
            category_id=1,
            base_sale_price=250000,
        )

        assert style.style_code == "SSG-SH-001"
        assert style.name == "Premium Shirt"
        assert style.base_sale_price == 250000

    def test_style_validate(self) -> None:
        """Test Style validation."""
        valid_style = Style(
            style_code="SSG-SH-001",
            name="Shirt",
            category_id=1,
            base_sale_price=100000,
        )
        invalid_style = Style(style_code="", name="", category_id=0, base_sale_price=0)

        assert valid_style.validate() is True
        assert invalid_style.validate() is False


class TestVariantModel:
    """Test Variant dataclass."""

    def test_create_variant(self) -> None:
        """Test creating a Variant instance."""
        variant = Variant(
            style_id=1,
            size="M",
            color="Blue",
            barcode="SSG001-M-BLU",
            quantity=10,
        )

        assert variant.style_id == 1
        assert variant.size == "M"
        assert variant.color == "Blue"
        assert variant.barcode == "SSG001-M-BLU"

    def test_variant_validate(self) -> None:
        """Test Variant validation."""
        valid_variant = Variant(
            style_id=1, size="M", color="Blue", barcode="TEST-001"
        )
        invalid_variant = Variant(style_id=0, size="", color="", barcode="")

        assert valid_variant.validate() is True
        assert invalid_variant.validate() is False


class TestBatchModel:
    """Test Batch dataclass."""

    def test_create_batch(self) -> None:
        """Test creating a Batch instance."""
        batch = Batch(
            variant_id=1,
            purchase_price=150000,
            secret_code="abc",
            quantity_received=20,
            quantity_remaining=20,
            date_received="2024-01-15T10:00:00",
        )

        assert batch.variant_id == 1
        assert batch.purchase_price == 150000
        assert batch.secret_code == "abc"

    def test_batch_validate(self) -> None:
        """Test Batch validation."""
        valid_batch = Batch(
            variant_id=1,
            purchase_price=100000,
            secret_code="abc",
            quantity_received=10,
            quantity_remaining=10,
            date_received="2024-01-15T10:00:00",
        )
        invalid_batch = Batch(
            variant_id=0,
            purchase_price=0,
            secret_code="",
            quantity_received=0,
            quantity_remaining=0,
            date_received="",
        )

        assert valid_batch.validate() is True
        assert invalid_batch.validate() is False


class TestSaleModel:
    """Test Sale dataclass."""

    def test_create_sale(self) -> None:
        """Test creating a Sale instance."""
        sale = Sale(
            invoice_number="INV-20240115-0001",
            user_id=1,
            subtotal=250000,
            total_amount=250000,
            payment_type="cash",
            sale_date="2024-01-15T12:00:00",
        )

        assert sale.invoice_number == "INV-20240115-0001"
        assert sale.user_id == 1
        assert sale.status == "completed"

    def test_sale_validate(self) -> None:
        """Test Sale validation."""
        valid_sale = Sale(
            invoice_number="INV-001",
            user_id=1,
            total_amount=100000,
            payment_type="cash",
            sale_date="2024-01-15T12:00:00",
        )
        invalid_sale = Sale(
            invoice_number="",
            user_id=0,
            total_amount=0,
            payment_type="",
            sale_date="",
        )

        assert valid_sale.validate() is True
        assert invalid_sale.validate() is False


class TestSaleItemModel:
    """Test SaleItem dataclass."""

    def test_create_sale_item(self) -> None:
        """Test creating a SaleItem instance."""
        item = SaleItem(
            sale_id=1,
            variant_id=1,
            quantity=2,
            unit_price=125000,
            total_price=250000,
        )

        assert item.sale_id == 1
        assert item.quantity == 2
        assert item.unit_price == 125000

    def test_sale_item_validate(self) -> None:
        """Test SaleItem validation."""
        valid_item = SaleItem(
            sale_id=1, variant_id=1, quantity=1, unit_price=100000, total_price=100000
        )
        invalid_item = SaleItem(
            sale_id=0, variant_id=0, quantity=0, unit_price=0, total_price=0
        )

        assert valid_item.validate() is True
        assert invalid_item.validate() is False


class TestAuditLogModel:
    """Test AuditLog dataclass."""

    def test_create_audit_log(self) -> None:
        """Test creating an AuditLog instance."""
        log = AuditLog(
            table_name="sales",
            record_id=1,
            action="INSERT",
            hmac_hash="abc123hash",
            timestamp="2024-01-15T12:00:00",
        )

        assert log.table_name == "sales"
        assert log.record_id == 1
        assert log.action == "INSERT"

    def test_audit_log_validate(self) -> None:
        """Test AuditLog validation."""
        valid_log = AuditLog(
            table_name="sales",
            record_id=1,
            action="INSERT",
            hmac_hash="hash123",
        )
        invalid_log = AuditLog(
            table_name="",
            record_id=0,
            action="",
            hmac_hash="",
        )

        assert valid_log.validate() is True
        assert invalid_log.validate() is False


class TestModelTimestamps:
    """Test that models have proper timestamp defaults."""

    def test_category_has_timestamp(self) -> None:
        """Test Category has created_at timestamp."""
        category = Category(name="Test", code="TE")
        assert category.created_at is not None
        # Verify it's a valid ISO 8601 format
        datetime.fromisoformat(category.created_at.replace("Z", "+00:00"))

    def test_style_has_timestamps(self) -> None:
        """Test Style has created_at and updated_at timestamps."""
        style = Style(style_code="TEST", name="Test", category_id=1, base_sale_price=100)
        assert style.created_at is not None
        assert style.updated_at is not None
