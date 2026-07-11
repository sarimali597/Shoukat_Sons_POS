"""
Tests for sale processing engine.

Verifies ACID transactions, invoice generation, held sales, voiding,
and credit limit validation.
"""

import sqlite3
from datetime import datetime, timezone

import pytest

from database.connection import ConnectionManager
from database.schema import create_tables, seed_data
from services.inventory_service import restock_variant
from services.sale_engine import (
    CartItem,
    CreditLimitExceededError,
    InsufficientStockError,
    SaleEngine,
    ValidationError,
)


class TestSaleEngineBasic:
    """Test basic sale processing functionality."""

    @pytest.fixture
    def setup_sale_engine(self, temp_db_path, connection_manager):
        """Set up database with sample data for sale testing."""
        conn = connection_manager.get_read_connection()
        create_tables(conn)
        seed_data(conn)

        # Create a category
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO categories (name, code, tax_rate, created_at) VALUES (?, ?, ?, ?)",
            ("Test", "TST", 17.0, datetime.now(timezone.utc).isoformat()),
        )
        category_id = cursor.lastrowid

        # Create a style
        cursor.execute(
            "INSERT INTO styles (style_code, name, category_id, base_sale_price, tax_rate, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "SSG-TST-001",
                "Test Shirt",
                category_id,
                250000,  # Rs. 2500 in cents
                17.0,
                datetime.now(timezone.utc).isoformat(),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        style_id = cursor.lastrowid

        # Create a variant
        cursor.execute(
            "INSERT INTO variants (style_id, size, color, barcode, quantity, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                style_id,
                "M",
                "Blue",
                "TEST001",
                10,
                datetime.now(timezone.utc).isoformat(),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        variant_id = cursor.lastrowid

        # Create a batch
        restock_variant(
            conn,
            variant_id,
            10,
            150000,  # Rs. 1500 in cents
            "abc",
            {
                "vendor_id": None,
                "bilty_no": None,
                "bill_no": None,
                "date_received": datetime.now(timezone.utc).isoformat(),
            },
        )

        # Create a user
        cursor.execute(
            "INSERT INTO users (username, password_hash, role, is_active, created_at) VALUES (?, ?, ?, 1, ?)",
            ("cashier1", "hash123", "cashier", datetime.now(timezone.utc).isoformat()),
        )
        user_id = cursor.lastrowid

        conn.commit()
        conn.close()

        return connection_manager, variant_id, user_id

    def test_process_cash_sale(self, setup_sale_engine):
        """Test processing a simple cash sale."""
        cm, variant_id, user_id = setup_sale_engine
        engine = SaleEngine(cm)

        cart = [
            CartItem(
                variant_id=variant_id,
                quantity=2,
                unit_price=250000,  # Rs. 2500
                tax_rate=17.0,
                discount=0,
            )
        ]

        result = engine.process_sale(
            cart=cart,
            customer_id=None,
            payment_type="cash",
            paid_amount=600000,  # Rs. 6000
            user_id=user_id,
        )

        assert result.sale_id > 0
        assert result.invoice_number.startswith("INV-")
        assert result.grand_total == 585000  # 500000 + 85000 tax
        assert result.change_due == 15000  # 600000 - 585000

    def test_process_sale_multiple_items(self, setup_sale_engine):
        """Test processing a sale with multiple items."""
        cm, variant_id, user_id = setup_sale_engine
        engine = SaleEngine(cm)

        # Add another variant to the same style (style_id=1)
        conn = cm.get_read_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO variants (style_id, size, color, barcode, quantity, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                1,
                "L",
                "Red",
                "TEST002",
                5,
                datetime.now(timezone.utc).isoformat(),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        variant2_id = cursor.lastrowid

        # Create batch for variant2
        restock_variant(
            conn,
            variant2_id,
            5,
            120000,
            "xyz",
            {"date_received": datetime.now(timezone.utc).isoformat()},
        )
        conn.commit()
        conn.close()

        cart = [
            CartItem(
                variant_id=variant_id,
                quantity=1,
                unit_price=250000,
                tax_rate=17.0,
                discount=0,
            ),
            CartItem(
                variant_id=variant2_id,
                quantity=2,
                unit_price=180000,
                tax_rate=17.0,
                discount=10000,  # Rs. 100 discount
            ),
        ]

        result = engine.process_sale(
            cart=cart,
            customer_id=None,
            payment_type="cash",
            paid_amount=800000,
            user_id=user_id,
        )

        assert result.sale_id > 0
        # Item 1: 250000 + 42500 tax = 292500
        # Item 2: 360000 + 61200 tax - 10000 discount = 411200
        # Total: 703700
        assert result.grand_total == 703700

    def test_empty_cart_raises_error(self, setup_sale_engine):
        """Test that empty cart raises ValidationError."""
        cm, variant_id, user_id = setup_sale_engine
        engine = SaleEngine(cm)

        with pytest.raises(ValidationError, match="Cart cannot be empty"):
            engine.process_sale(
                cart=[],
                customer_id=None,
                payment_type="cash",
                paid_amount=0,
                user_id=user_id,
            )

    def test_insufficient_stock_rolls_back(self, setup_sale_engine):
        """Test that insufficient stock causes rollback."""
        cm, variant_id, user_id = setup_sale_engine
        engine = SaleEngine(cm)

        # Try to sell more than available
        cart = [
            CartItem(
                variant_id=variant_id,
                quantity=100,  # Only 10 in stock
                unit_price=250000,
                tax_rate=17.0,
                discount=0,
            )
        ]

        with pytest.raises(InsufficientStockError):
            engine.process_sale(
                cart=cart,
                customer_id=None,
                payment_type="cash",
                paid_amount=30000000,
                user_id=user_id,
            )

        # Verify no sale was created
        conn = cm.get_read_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sales")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        assert count == 0  # No sales due to rollback

    def test_invoice_number_generation_sequential(self, setup_sale_engine):
        """Test that invoice numbers are sequential per day."""
        cm, variant_id, user_id = setup_sale_engine
        engine = SaleEngine(cm)

        cart = [
            CartItem(
                variant_id=variant_id,
                quantity=1,
                unit_price=100000,
                tax_rate=0.0,
                discount=0,
            )
        ]

        # Process three sales
        result1 = engine.process_sale(
            cart=cart, customer_id=None, payment_type="cash", paid_amount=100000, user_id=user_id
        )
        result2 = engine.process_sale(
            cart=cart, customer_id=None, payment_type="cash", paid_amount=100000, user_id=user_id
        )
        result3 = engine.process_sale(
            cart=cart, customer_id=None, payment_type="cash", paid_amount=100000, user_id=user_id
        )

        # Invoice numbers should be sequential
        assert result1.invoice_number.endswith("-0001")
        assert result2.invoice_number.endswith("-0002")
        assert result3.invoice_number.endswith("-0003")


class TestCreditSales:
    """Test credit sale processing."""

    @pytest.fixture
    def setup_credit_test(self, temp_db_path, connection_manager):
        """Set up database with customer for credit testing."""
        conn = connection_manager.get_read_connection()
        create_tables(conn)
        seed_data(conn)

        # Create category, style, variant, batch
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO categories (name, code, tax_rate, created_at) VALUES (?, ?, ?, ?)",
            ("Test", "TST", 0.0, datetime.now(timezone.utc).isoformat()),
        )
        cursor.execute(
            "INSERT INTO styles (style_code, name, category_id, base_sale_price, tax_rate, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("SSG-TST-001", "Test", 1, 100000, 0.0, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()),
        )
        cursor.execute(
            "INSERT INTO variants (style_id, size, color, barcode, quantity, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, "M", "Blue", "TEST001", 10, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()),
        )
        variant_id = cursor.lastrowid
        restock_variant(conn, variant_id, 10, 50000, "abc", {"date_received": datetime.now(timezone.utc).isoformat()})

        # Create customer with credit limit
        cursor.execute(
            "INSERT INTO customers (name, phone, address, total_due, credit_limit, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("Test Customer", "03001234567", "Test Addr", 0, 500000, datetime.now(timezone.utc).isoformat()),
        )
        customer_id = cursor.lastrowid

        # Create user
        cursor.execute(
            "INSERT INTO users (username, password_hash, role, is_active, created_at) VALUES (?, ?, ?, 1, ?)",
            ("cashier1", "hash", "cashier", datetime.now(timezone.utc).isoformat()),
        )
        user_id = cursor.lastrowid

        conn.commit()
        conn.close()

        return connection_manager, variant_id, customer_id, user_id

    def test_credit_sale_updates_customer_due(self, setup_credit_test):
        """Test that credit sale updates customer total_due."""
        cm, variant_id, customer_id, user_id = setup_credit_test
        engine = SaleEngine(cm)

        cart = [
            CartItem(
                variant_id=variant_id,
                quantity=2,
                unit_price=100000,
                tax_rate=0.0,
                discount=0,
            )
        ]

        result = engine.process_sale(
            cart=cart,
            customer_id=customer_id,
            payment_type="credit",
            paid_amount=0,
            user_id=user_id,
        )

        assert result.due_amount == 200000

        # Check customer total_due
        conn = cm.get_read_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT total_due FROM customers WHERE id = ?", (customer_id,))
        total_due = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        assert total_due == 200000

    def test_credit_limit_exceeded_raises_error(self, setup_credit_test):
        """Test that exceeding credit limit raises error."""
        cm, variant_id, customer_id, user_id = setup_credit_test
        engine = SaleEngine(cm)

        # First sale within limit
        cart1 = [
            CartItem(variant_id=variant_id, quantity=2, unit_price=100000, tax_rate=0.0)
        ]
        engine.process_sale(
            cart=cart1, customer_id=customer_id, payment_type="credit", paid_amount=0, user_id=user_id
        )

        # Second sale would exceed limit (500000 limit, 200000 already due)
        cart2 = [
            CartItem(variant_id=variant_id, quantity=4, unit_price=100000, tax_rate=0.0)
        ]

        with pytest.raises(CreditLimitExceededError):
            engine.process_sale(
                cart=cart2, customer_id=customer_id, payment_type="credit", paid_amount=0, user_id=user_id
            )


class TestHeldSales:
    """Test held sale functionality."""

    @pytest.fixture
    def setup_held_test(self, temp_db_path, connection_manager):
        """Set up for held sale testing."""
        conn = connection_manager.get_read_connection()
        create_tables(conn)
        seed_data(conn)

        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO categories (name, code, tax_rate, created_at) VALUES (?, ?, ?, ?)",
            ("Test", "TST", 0.0, datetime.now(timezone.utc).isoformat()),
        )
        cursor.execute(
            "INSERT INTO styles (style_code, name, category_id, base_sale_price, tax_rate, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("SSG-TST-001", "Test", 1, 100000, 0.0, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()),
        )
        cursor.execute(
            "INSERT INTO variants (style_id, size, color, barcode, quantity, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, "M", "Blue", "TEST001", 10, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()),
        )
        variant_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO users (username, password_hash, role, is_active, created_at) VALUES (?, ?, ?, 1, ?)",
            ("cashier1", "hash", "cashier", datetime.now(timezone.utc).isoformat()),
        )
        user_id = cursor.lastrowid

        conn.commit()
        conn.close()

        return connection_manager, variant_id, user_id

    def test_hold_and_resume_sale(self, setup_held_test):
        """Test holding a sale and resuming it."""
        cm, variant_id, user_id = setup_held_test
        engine = SaleEngine(cm)

        cart = [
            CartItem(variant_id=variant_id, quantity=2, unit_price=100000, tax_rate=0.0)
        ]

        # Hold the sale
        held_id = engine.hold_sale(cart=cart, customer_id=None, user_id=user_id)

        assert held_id > 0

        # Resume the sale
        held_sale = engine.resume_sale(held_id)

        assert held_sale.id == held_id
        assert len(held_sale.items) == 1
        assert held_sale.items[0].variant_id == variant_id
        assert held_sale.items[0].quantity == 2


class TestVoidSale:
    """Test sale voiding functionality."""

    @pytest.fixture
    def setup_void_test(self, temp_db_path, connection_manager):
        """Set up for void sale testing."""
        cm = connection_manager
        conn = cm.get_read_connection()
        create_tables(conn)
        seed_data(conn)

        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO categories (name, code, tax_rate, created_at) VALUES (?, ?, ?, ?)",
            ("Test", "TST", 0.0, datetime.now(timezone.utc).isoformat()),
        )
        cursor.execute(
            "INSERT INTO styles (style_code, name, category_id, base_sale_price, tax_rate, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("SSG-TST-001", "Test", 1, 100000, 0.0, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()),
        )
        cursor.execute(
            "INSERT INTO variants (style_id, size, color, barcode, quantity, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, "M", "Blue", "TEST001", 10, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()),
        )
        variant_id = cursor.lastrowid
        # Create batch with 10 units - don't double-count in variant.quantity
        # The INSERT already set quantity=10, so we just create the batch record
        cursor.execute(
            "INSERT INTO batches (variant_id, purchase_price, secret_code, quantity_received, quantity_remaining, date_received, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (variant_id, 50000, "abc", 10, 10, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()),
        )

        cursor.execute(
            "INSERT INTO users (username, password_hash, role, is_active, created_at) VALUES (?, ?, ?, 1, ?)",
            ("cashier1", "hash", "cashier", datetime.now(timezone.utc).isoformat()),
        )
        user_id = cursor.lastrowid

        conn.commit()
        conn.close()

        return cm, variant_id, user_id

    def test_void_sale_restocks_items(self, setup_void_test):
        """Test that voiding a sale restocks the items."""
        cm, variant_id, user_id = setup_void_test
        engine = SaleEngine(cm)

        # Make a sale
        cart = [CartItem(variant_id=variant_id, quantity=3, unit_price=100000, tax_rate=0.0)]
        result = engine.process_sale(
            cart=cart, customer_id=None, payment_type="cash", paid_amount=300000, user_id=user_id
        )

        # Check stock reduced
        conn = cm.get_read_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT quantity FROM variants WHERE id = ?", (variant_id,))
        qty_after_sale = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        assert qty_after_sale == 7  # 10 - 3

        # Void the sale
        engine.void_sale(result.sale_id, "Customer changed mind", user_id)

        # Check stock restored
        conn = cm.get_read_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT quantity FROM variants WHERE id = ?", (variant_id,))
        qty_after_void = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        assert qty_after_void == 10  # Restored to original

    def test_void_already_voided_raises_error(self, setup_void_test):
        """Test that voiding an already voided sale raises error."""
        cm, variant_id, user_id = setup_void_test
        engine = SaleEngine(cm)

        cart = [CartItem(variant_id=variant_id, quantity=1, unit_price=100000, tax_rate=0.0)]
        result = engine.process_sale(
            cart=cart, customer_id=None, payment_type="cash", paid_amount=100000, user_id=user_id
        )

        # Void once
        engine.void_sale(result.sale_id, "Test void", user_id)

        # Try to void again
        with pytest.raises(ValueError, match="already voided"):
            engine.void_sale(result.sale_id, "Second void", user_id)


class TestGetSaleByInvoice:
    """Test sale lookup by invoice number."""

    def test_get_sale_by_invoice(self, temp_db_path, connection_manager):
        """Test retrieving a sale by invoice number."""
        cm = connection_manager
        conn = cm.get_read_connection()
        create_tables(conn)
        seed_data(conn)

        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO categories (name, code, tax_rate, created_at) VALUES (?, ?, ?, ?)",
            ("Test", "TST", 0.0, datetime.now(timezone.utc).isoformat()),
        )
        cursor.execute(
            "INSERT INTO styles (style_code, name, category_id, base_sale_price, tax_rate, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("SSG-TST-001", "Test", 1, 100000, 0.0, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()),
        )
        cursor.execute(
            "INSERT INTO variants (style_id, size, color, barcode, quantity, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, "M", "Blue", "TEST001", 10, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()),
        )
        variant_id = cursor.lastrowid
        restock_variant(conn, variant_id, 10, 50000, "abc", {"date_received": datetime.now(timezone.utc).isoformat()})

        cursor.execute(
            "INSERT INTO users (username, password_hash, role, is_active, created_at) VALUES (?, ?, ?, 1, ?)",
            ("cashier1", "hash", "cashier", datetime.now(timezone.utc).isoformat()),
        )
        user_id = cursor.lastrowid

        conn.commit()
        conn.close()

        engine = SaleEngine(cm)
        cart = [CartItem(variant_id=variant_id, quantity=1, unit_price=100000, tax_rate=0.0)]
        result = engine.process_sale(
            cart=cart, customer_id=None, payment_type="cash", paid_amount=100000, user_id=user_id
        )

        # Look up by invoice
        sale = engine.get_sale_by_invoice(result.invoice_number)

        assert sale is not None
        assert sale.invoice_number == result.invoice_number
        assert sale.total_amount == 100000
