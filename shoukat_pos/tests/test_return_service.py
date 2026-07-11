"""
Tests for the ReturnService in Shoukat Sons Garments POS.

Tests cover return processing, exchanges, credit adjustments,
and FIFO restocking with ACID guarantees.
"""

import pytest
import random
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import List

from database.connection import ConnectionManager
from database.schema import create_tables, seed_data
from services.sale_engine import SaleEngine, CartItem
from services.return_service import (
    ReturnService,
    ReturnItem,
    ValidationError,
    SaleNotFoundError,
)


class TestReturnServiceBasic:
    """Test basic return functionality."""

    @pytest.fixture
    def setup_db(self, tmp_path):
        """Set up test database with sample data."""
        db_path = tmp_path / "test_returns.db"
        cm = ConnectionManager(str(db_path))

        # Create tables and seed data
        conn = cm.get_read_connection()
        try:
            create_tables(conn)
            seed_data(conn)
        finally:
            conn.close()

        # Add a test product
        conn = cm.get_read_connection()
        try:
            cursor = conn.cursor()

            # Create a style with unique code per test
            import random
            style_code = f"SSG-SH-{random.randint(100, 999)}"
            cursor.execute(
                """
                INSERT INTO styles (style_code, name, category_id, base_sale_price, tax_rate, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (style_code, "Test Shirt", 1, 2000, 17.0, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat())
            )
            style_id = cursor.lastrowid

            # Create variants
            cursor.execute(
                """
                INSERT INTO variants (style_id, size, color, barcode, quantity, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (style_id, "M", "Blue", f"TEST{random.randint(1000, 9999)}", 10, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat())
            )
            variant_m_blue = cursor.lastrowid

            cursor.execute(
                """
                INSERT INTO variants (style_id, size, color, barcode, quantity, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (style_id, "L", "Blue", f"TEST{random.randint(1000, 9999)}", 10, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat())
            )
            variant_l_blue = cursor.lastrowid

            # Create batches
            cursor.execute(
                """
                INSERT INTO batches (variant_id, purchase_price, secret_code, quantity_received, quantity_remaining, date_received, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (variant_m_blue, 1000, "ABC", 10, 10, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat())
            )
            batch_m = cursor.lastrowid

            cursor.execute(
                """
                INSERT INTO batches (variant_id, purchase_price, secret_code, quantity_received, quantity_remaining, date_received, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (variant_l_blue, 1000, "ABC", 10, 10, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat())
            )
            batch_l = cursor.lastrowid

            # Create a test user
            cursor.execute(
                """
                INSERT INTO users (username, password_hash, role, is_active, created_at)
                VALUES (?, ?, ?, 1, ?)
                """,
                (f"cashier{random.randint(100, 999)}", "hash123", "cashier", datetime.now(timezone.utc).isoformat())
            )
            user_id = cursor.lastrowid

            conn.commit()
            cursor.close()
        finally:
            conn.close()

        return cm, variant_m_blue, variant_l_blue, batch_m, batch_l, user_id

    def test_return_single_item(self, setup_db):
        """Test returning a single item from a sale."""
        cm, variant_m_blue, variant_l_blue, batch_m, batch_l, user_id = setup_db

        # First, create a sale
        sale_engine = SaleEngine(cm)
        cart = [
            CartItem(variant_id=variant_m_blue, quantity=2, unit_price=2000, tax_rate=17.0)
        ]
        sale_result = sale_engine.process_sale(
            cart=cart,
            customer_id=None,
            payment_type="cash",
            paid_amount=5000,
            user_id=user_id,
        )

        # Get sale items
        return_service = ReturnService(cm)
        sale_items = return_service.get_sale_items_for_return(sale_result.sale_id)

        assert len(sale_items) == 1
        assert sale_items[0].quantity == 2

        # Process return of 1 item
        return_items = [ReturnItem(sale_item_id=sale_items[0].id, return_qty=1)]
        return_result = return_service.process_return(
            sale_id=sale_result.sale_id,
            items=return_items,
            reason="Changed Mind",
            user_id=user_id,
        )

        assert return_result.return_id > 0
        assert return_result.refund_amount > 0
        assert len(return_result.restocked_items) == 1

        # Verify stock was restocked
        conn = cm.get_read_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT quantity FROM variants WHERE id = ?", (variant_m_blue,))
            row = cursor.fetchone()
            # Original 10 - 2 sold + 1 returned = 9
            assert row["quantity"] == 9
            cursor.close()
        finally:
            conn.close()

    def test_return_all_items_marks_sale_as_returned(self, setup_db):
        """Test that returning all items marks sale as 'returned'."""
        cm, variant_m_blue, variant_l_blue, batch_m, batch_l, user_id = setup_db

        # Create a sale
        sale_engine = SaleEngine(cm)
        cart = [
            CartItem(variant_id=variant_m_blue, quantity=1, unit_price=2000, tax_rate=17.0)
        ]
        sale_result = sale_engine.process_sale(
            cart=cart,
            customer_id=None,
            payment_type="cash",
            paid_amount=3000,
            user_id=user_id,
        )

        # Get sale items
        return_service = ReturnService(cm)
        sale_items = return_service.get_sale_items_for_return(sale_result.sale_id)

        # Return all items
        return_items = [ReturnItem(sale_item_id=sale_items[0].id, return_qty=1)]
        return_service.process_return(
            sale_id=sale_result.sale_id,
            items=return_items,
            reason="Defective",
            user_id=user_id,
        )

        # Verify sale status
        conn = cm.get_read_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM sales WHERE id = ?", (sale_result.sale_id,))
            row = cursor.fetchone()
            assert row["status"] == "returned"
            cursor.close()
        finally:
            conn.close()

    def test_partial_return_marks_sale_as_partial(self, setup_db):
        """Test that partial return marks sale as 'partial_return'."""
        cm, variant_m_blue, variant_l_blue, batch_m, batch_l, user_id = setup_db

        # Create a sale with 2 items
        sale_engine = SaleEngine(cm)
        cart = [
            CartItem(variant_id=variant_m_blue, quantity=2, unit_price=2000, tax_rate=17.0)
        ]
        sale_result = sale_engine.process_sale(
            cart=cart,
            customer_id=None,
            payment_type="cash",
            paid_amount=5000,
            user_id=user_id,
        )

        # Return only 1 item
        return_service = ReturnService(cm)
        sale_items = return_service.get_sale_items_for_return(sale_result.sale_id)
        return_items = [ReturnItem(sale_item_id=sale_items[0].id, return_qty=1)]
        return_service.process_return(
            sale_id=sale_result.sale_id,
            items=return_items,
            reason="Wrong Size",
            user_id=user_id,
        )

        # Verify sale status
        conn = cm.get_read_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM sales WHERE id = ?", (sale_result.sale_id,))
            row = cursor.fetchone()
            assert row["status"] == "partial_return"
            cursor.close()
        finally:
            conn.close()


class TestCreditSaleReturn:
    """Test returns for credit sales."""

    @pytest.fixture
    def setup_credit_sale(self, tmp_path):
        """Set up database with a credit sale."""
        db_path = tmp_path / "test_credit_return.db"
        cm = ConnectionManager(str(db_path))

        conn = cm.get_read_connection()
        try:
            create_tables(conn)
            seed_data(conn)
        finally:
            conn.close()

        conn = cm.get_read_connection()
        try:
            cursor = conn.cursor()

            # Create style and variant
            cursor.execute(
                """
                INSERT INTO styles (style_code, name, category_id, base_sale_price, tax_rate, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (f"SSG-SH-{random.randint(100, 999)}", "Test Shirt", 1, 2000, 17.0, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat())
            )
            style_id = cursor.lastrowid

            cursor.execute(
                """
                INSERT INTO variants (style_id, size, color, barcode, quantity, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (style_id, "M", "Blue", f"TEST{random.randint(1000, 9999)}", 10, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat())
            )
            variant_id = cursor.lastrowid

            cursor.execute(
                """
                INSERT INTO batches (variant_id, purchase_price, secret_code, quantity_received, quantity_remaining, date_received, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (variant_id, 1000, "ABC", 10, 10, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat())
            )

            # Create customer with credit limit
            cursor.execute(
                """
                INSERT INTO customers (name, phone, total_due, credit_limit, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("Test Customer", "03001234567", 0, 50000, datetime.now(timezone.utc).isoformat())
            )
            customer_id = cursor.lastrowid

            # Create user
            cursor.execute(
                """
                INSERT INTO users (username, password_hash, role, is_active, created_at)
                VALUES (?, ?, ?, 1, ?)
                """,
                (f"cashier{random.randint(100, 999)}", "hash123", "cashier", datetime.now(timezone.utc).isoformat())
            )
            user_id = cursor.lastrowid

            conn.commit()
            cursor.close()
        finally:
            conn.close()

        return cm, variant_id, customer_id, user_id

    def test_credit_sale_return_reduces_total_due(self, setup_credit_sale):
        """Test that returning a credit sale item reduces customer total_due."""
        cm, variant_id, customer_id, user_id = setup_credit_sale

        # Create a credit sale
        sale_engine = SaleEngine(cm)
        cart = [
            CartItem(variant_id=variant_id, quantity=1, unit_price=2000, tax_rate=17.0)
        ]
        sale_result = sale_engine.process_sale(
            cart=cart,
            customer_id=customer_id,
            payment_type="credit",
            paid_amount=0,
            user_id=user_id,
        )

        # Verify customer total_due increased
        conn = cm.get_read_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT total_due FROM customers WHERE id = ?", (customer_id,))
            row = cursor.fetchone()
            original_due = row["total_due"]
            assert original_due > 0
            cursor.close()
        finally:
            conn.close()

        # Process return
        return_service = ReturnService(cm)
        sale_items = return_service.get_sale_items_for_return(sale_result.sale_id)
        return_items = [ReturnItem(sale_item_id=sale_items[0].id, return_qty=1)]
        return_service.process_return(
            sale_id=sale_result.sale_id,
            items=return_items,
            reason="Changed Mind",
            user_id=user_id,
        )

        # Verify customer total_due decreased
        conn = cm.get_read_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT total_due FROM customers WHERE id = ?", (customer_id,))
            row = cursor.fetchone()
            assert row["total_due"] < original_due
            cursor.close()
        finally:
            conn.close()


class TestExchange:
    """Test exchange functionality."""

    @pytest.fixture
    def setup_exchange(self, tmp_path):
        """Set up database for exchange tests."""
        db_path = tmp_path / "test_exchange.db"
        cm = ConnectionManager(str(db_path))

        conn = cm.get_read_connection()
        try:
            create_tables(conn)
            seed_data(conn)
        finally:
            conn.close()

        conn = cm.get_read_connection()
        try:
            cursor = conn.cursor()

            # Create style
            cursor.execute(
                """
                INSERT INTO styles (style_code, name, category_id, base_sale_price, tax_rate, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (f"SSG-SH-{random.randint(100, 999)}", "Test Shirt", 1, 2000, 17.0, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat())
            )
            style_id = cursor.lastrowid

            # Create two variants of same style (different sizes)
            cursor.execute(
                """
                INSERT INTO variants (style_id, size, color, barcode, quantity, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (style_id, "M", "Blue", f"TEST{random.randint(1000, 9999)}", 10, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat())
            )
            variant_m = cursor.lastrowid

            cursor.execute(
                """
                INSERT INTO variants (style_id, size, color, barcode, quantity, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (style_id, "L", "Blue", f"TEST{random.randint(1000, 9999)}", 10, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat())
            )
            variant_l = cursor.lastrowid

            # Create batches
            cursor.execute(
                """
                INSERT INTO batches (variant_id, purchase_price, secret_code, quantity_received, quantity_remaining, date_received, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (variant_m, 1000, "ABC", 10, 10, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat())
            )
            cursor.execute(
                """
                INSERT INTO batches (variant_id, purchase_price, secret_code, quantity_received, quantity_remaining, date_received, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (variant_l, 1000, "ABC", 10, 10, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat())
            )

            # Create user
            cursor.execute(
                """
                INSERT INTO users (username, password_hash, role, is_active, created_at)
                VALUES (?, ?, ?, 1, ?)
                """,
                (f"cashier{random.randint(100, 999)}", "hash123", "cashier", datetime.now(timezone.utc).isoformat())
            )
            user_id = cursor.lastrowid

            conn.commit()
            cursor.close()
        finally:
            conn.close()

        return cm, variant_m, variant_l, user_id

    def test_even_exchange_no_price_difference(self, setup_exchange):
        """Test exchange with same price (even exchange)."""
        cm, variant_m, variant_l, user_id = setup_exchange

        # Create a sale
        sale_engine = SaleEngine(cm)
        cart = [
            CartItem(variant_id=variant_m, quantity=1, unit_price=2000, tax_rate=17.0)
        ]
        sale_result = sale_engine.process_sale(
            cart=cart,
            customer_id=None,
            payment_type="cash",
            paid_amount=3000,
            user_id=user_id,
        )

        # Get sale item
        return_service = ReturnService(cm)
        sale_items = return_service.get_sale_items_for_return(sale_result.sale_id)
        original_item = sale_items[0]

        # Process exchange (same price)
        exchange_result = return_service.process_exchange(
            original_sale_id=sale_result.sale_id,
            original_item_id=original_item.id,
            new_variant_id=variant_l,
            new_qty=1,
            reason="Wrong Size",
            user_id=user_id,
        )

        assert exchange_result.exchange_id > 0
        assert exchange_result.price_difference == 0
        assert not exchange_result.payment_required
        assert not exchange_result.refund_required

        # Verify stock levels
        conn = cm.get_read_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT quantity FROM variants WHERE id = ?", (variant_m,))
            row_m = cursor.fetchone()
            cursor.execute("SELECT quantity FROM variants WHERE id = ?", (variant_l,))
            row_l = cursor.fetchone()
            # M: 10 - 1 sold + 1 returned = 10
            # L: 10 - 1 exchanged = 9
            assert row_m["quantity"] == 10
            assert row_l["quantity"] == 9
            cursor.close()
        finally:
            conn.close()

    def test_exchange_different_size_same_style(self, setup_exchange):
        """Test that exchange works within same style."""
        cm, variant_m, variant_l, user_id = setup_exchange

        # Create a sale
        sale_engine = SaleEngine(cm)
        cart = [
            CartItem(variant_id=variant_m, quantity=1, unit_price=2000, tax_rate=17.0)
        ]
        sale_result = sale_engine.process_sale(
            cart=cart,
            customer_id=None,
            payment_type="cash",
            paid_amount=3000,
            user_id=user_id,
        )

        return_service = ReturnService(cm)
        sale_items = return_service.get_sale_items_for_return(sale_result.sale_id)

        # Exchange should work (same style)
        exchange_result = return_service.process_exchange(
            original_sale_id=sale_result.sale_id,
            original_item_id=sale_items[0].id,
            new_variant_id=variant_l,
            new_qty=1,
            reason="Wrong Size",
            user_id=user_id,
        )

        assert exchange_result.exchange_id > 0


class TestReturnValidation:
    """Test return validation and error handling."""

    @pytest.fixture
    def setup_validation(self, tmp_path):
        """Set up database for validation tests."""
        db_path = tmp_path / "test_validation.db"
        cm = ConnectionManager(str(db_path))

        conn = cm.get_read_connection()
        try:
            create_tables(conn)
            seed_data(conn)
        finally:
            conn.close()

        conn = cm.get_read_connection()
        try:
            cursor = conn.cursor()

            # Create style and variant
            cursor.execute(
                """
                INSERT INTO styles (style_code, name, category_id, base_sale_price, tax_rate, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (f"SSG-SH-{random.randint(100, 999)}", "Test Shirt", 1, 2000, 17.0, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat())
            )
            style_id = cursor.lastrowid

            cursor.execute(
                """
                INSERT INTO variants (style_id, size, color, barcode, quantity, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (style_id, "M", "Blue", f"TEST{random.randint(1000, 9999)}", 10, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat())
            )
            variant_id = cursor.lastrowid

            cursor.execute(
                """
                INSERT INTO batches (variant_id, purchase_price, secret_code, quantity_received, quantity_remaining, date_received, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (variant_id, 1000, "ABC", 10, 10, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat())
            )

            # Create user
            cursor.execute(
                """
                INSERT INTO users (username, password_hash, role, is_active, created_at)
                VALUES (?, ?, ?, 1, ?)
                """,
                (f"cashier{random.randint(100, 999)}", "hash123", "cashier", datetime.now(timezone.utc).isoformat())
            )
            user_id = cursor.lastrowid

            conn.commit()
            cursor.close()
        finally:
            conn.close()

        return cm, variant_id, user_id

    def test_return_nonexistent_sale_raises_error(self, setup_validation):
        """Test that returning from nonexistent sale raises error."""
        cm, variant_id, user_id = setup_validation
        return_service = ReturnService(cm)

        with pytest.raises(SaleNotFoundError):
            return_service.process_return(
                sale_id=99999,
                items=[ReturnItem(sale_item_id=1, return_qty=1)],
                reason="Changed Mind",
                user_id=user_id,
            )

    def test_return_from_voided_sale_raises_error(self, setup_validation):
        """Test that returning from voided sale raises error."""
        cm, variant_id, user_id = setup_validation

        # Create and void a sale
        sale_engine = SaleEngine(cm)
        cart = [
            CartItem(variant_id=variant_id, quantity=1, unit_price=2000, tax_rate=17.0)
        ]
        sale_result = sale_engine.process_sale(
            cart=cart,
            customer_id=None,
            payment_type="cash",
            paid_amount=3000,
            user_id=user_id,
        )

        # Void the sale
        sale_engine.void_sale(sale_result.sale_id, "Test void", user_id)

        # Try to return
        return_service = ReturnService(cm)
        with pytest.raises(SaleNotFoundError):
            return_service.process_return(
                sale_id=sale_result.sale_id,
                items=[ReturnItem(sale_item_id=1, return_qty=1)],
                reason="Changed Mind",
                user_id=user_id,
            )

    def test_return_quantity_exceeds_sold_raises_error(self, setup_validation):
        """Test that returning more than sold raises error."""
        cm, variant_id, user_id = setup_validation

        # Create a sale
        sale_engine = SaleEngine(cm)
        cart = [
            CartItem(variant_id=variant_id, quantity=1, unit_price=2000, tax_rate=17.0)
        ]
        sale_result = sale_engine.process_sale(
            cart=cart,
            customer_id=None,
            payment_type="cash",
            paid_amount=3000,
            user_id=user_id,
        )

        # Try to return more than sold
        return_service = ReturnService(cm)
        sale_items = return_service.get_sale_items_for_return(sale_result.sale_id)

        with pytest.raises(ValidationError):
            return_service.process_return(
                sale_id=sale_result.sale_id,
                items=[ReturnItem(sale_item_id=sale_items[0].id, return_qty=5)],
                reason="Changed Mind",
                user_id=user_id,
            )

    def test_invalid_reason_raises_error(self, setup_validation):
        """Test that invalid return reason raises error."""
        cm, variant_id, user_id = setup_validation

        # Create a sale
        sale_engine = SaleEngine(cm)
        cart = [
            CartItem(variant_id=variant_id, quantity=1, unit_price=2000, tax_rate=17.0)
        ]
        sale_result = sale_engine.process_sale(
            cart=cart,
            customer_id=None,
            payment_type="cash",
            paid_amount=3000,
            user_id=user_id,
        )

        return_service = ReturnService(cm)
        sale_items = return_service.get_sale_items_for_return(sale_result.sale_id)

        with pytest.raises(AssertionError):
            return_service.process_return(
                sale_id=sale_result.sale_id,
                items=[ReturnItem(sale_item_id=sale_items[0].id, return_qty=1)],
                reason="Invalid Reason",
                user_id=user_id,
            )
