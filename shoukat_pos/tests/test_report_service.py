"""
Tests for ReportService in Shoukat Sons Garments POS.

Tests cover sales reports, stock reports, profit calculations with
secret code decoding, customer reports, and return/exchange reports.
All monetary values are INTEGER cents.
"""

import pytest
from datetime import datetime, timezone

from database.connection import ConnectionManager
from database.schema import create_tables, seed_data
from services.report_service import (
    ReportService,
    decode_secret_code,
    DEFAULT_SECRET_CODE_MAPPING,
)


@pytest.fixture
def connection_manager():
    """Create a test database connection manager."""
    cm = ConnectionManager()
    conn = cm.get_read_connection()
    try:
        create_tables(conn)
        seed_data(conn)
        yield cm
    finally:
        conn.close()
        cm.close_all()


@pytest.fixture
def report_service(connection_manager):
    """Create a ReportService instance with test data."""
    return ReportService(connection_manager)


@pytest.fixture
def populated_db(connection_manager):
    """Create database with sample sales, products, and customers."""
    cm = connection_manager
    conn = cm.get_read_connection()
    try:
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        today = now[:10]
        
        # Use microsecond-based unique identifiers to avoid collisions
        import time
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        
        # Add extra uniqueness with time.sleep if needed
        time.sleep(0.001)  # 1ms delay for uniqueness

        # Create a category for this test run
        cursor.execute(
            "INSERT INTO categories (name, code, tax_rate, created_at) VALUES (?, ?, ?, ?)",
            (f"Report Test {ts}", f"RPT{ts}", 0.0, now),
        )
        category_id = cursor.lastrowid

        # Create a style for this test run
        style_code = f"RPT-SH-{ts}"
        cursor.execute(
            "INSERT INTO styles (style_code, name, category_id, base_sale_price, tax_rate, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (style_code, f"Report Test Shirt {ts}", category_id, 250000, 0.0, now, now),
        )
        style_id = cursor.lastrowid

        # Create variants for this test run
        barcode_m = f"RPT12345678{ts}1"
        barcode_l = f"RPT12345678{ts}2"
        
        cursor.execute(
            "INSERT INTO variants (style_id, size, color, barcode, quantity, reorder_point, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (style_id, "M", "Blue", barcode_m, 50, 5, now, now),
        )
        variant_m_blue = cursor.lastrowid

        cursor.execute(
            "INSERT INTO variants (style_id, size, color, barcode, quantity, reorder_point, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (style_id, "L", "Blue", barcode_l, 30, 5, now, now),
        )
        variant_l_blue = cursor.lastrowid

        # Create batches with secret codes
        cursor.execute(
            "INSERT INTO batches (variant_id, purchase_price, secret_code, quantity_received, quantity_remaining, date_received, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (variant_m_blue, 1250, "RKML", 100, 50, today, now),
        )
        batch1_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO batches (variant_id, purchase_price, secret_code, quantity_received, quantity_remaining, date_received, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (variant_l_blue, 1400, "RKKA", 80, 50, today, now),
        )
        batch2_id = cursor.lastrowid

        # Create a customer for this test
        cursor.execute(
            "INSERT INTO customers (name, phone, total_due, credit_limit, created_at) VALUES (?, ?, ?, ?, ?)",
            (f"Report Test Customer {ts}", f"0300{ts}67", 0, 50000, now),
        )
        customer_id = cursor.lastrowid

        # Create a user for this test
        cursor.execute(
            "INSERT INTO users (username, password_hash, role, is_active, created_at) VALUES (?, ?, ?, ?, ?)",
            (f"rptuser{ts}", "hash123", "cashier", 1, now),
        )
        user_id = cursor.lastrowid

        # Create sales with unique invoice numbers
        inv1 = f"INV-RPT-{ts}-001"
        inv2 = f"INV-RPT-{ts}-002"
        
        cursor.execute(
            "INSERT INTO sales (invoice_number, customer_id, user_id, sale_date, subtotal, tax_amount, discount_amount, total_amount, paid_amount, due_amount, payment_type, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (inv1, customer_id, user_id, today, 250000, 0, 0, 250000, 250000, 0, "cash", "completed", now),
        )
        sale1_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO sales (invoice_number, customer_id, user_id, sale_date, subtotal, tax_amount, discount_amount, total_amount, paid_amount, due_amount, payment_type, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (inv2, customer_id, user_id, today, 500000, 0, 0, 500000, 0, 500000, "credit", "completed", now),
        )
        sale2_id = cursor.lastrowid

        # Update customer's total_due for the credit sale
        cursor.execute(
            "UPDATE customers SET total_due = total_due + ? WHERE id = ?",
            (500000, customer_id),
        )

        # Create sale items
        cursor.execute(
            "INSERT INTO sale_items (sale_id, variant_id, batch_id, quantity, unit_price, tax_amount, total_price, is_returned) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (sale1_id, variant_m_blue, batch1_id, 1, 250000, 0, 250000, 0),
        )

        cursor.execute(
            "INSERT INTO sale_items (sale_id, variant_id, batch_id, quantity, unit_price, tax_amount, total_price, is_returned) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (sale2_id, variant_l_blue, batch2_id, 2, 250000, 0, 500000, 0),
        )

        conn.commit()
        cursor.close()

        yield cm
    finally:
        conn.close()


class TestSecretCodeDecoding:
    """Tests for secret code decoding function."""

    def test_decode_rkml(self):
        """Test decoding 'RKML' to 1250."""
        result = decode_secret_code("RKML", DEFAULT_SECRET_CODE_MAPPING)
        assert result == 1250

    def test_decode_rkka(self):
        """Test decoding 'RKKA' to 1223 (R=1, K=2, K=2, A=3)."""
        result = decode_secret_code("RKKA", DEFAULT_SECRET_CODE_MAPPING)
        assert result == 1223

    def test_decode_empty_string(self):
        """Test decoding empty string returns 0."""
        result = decode_secret_code("", DEFAULT_SECRET_CODE_MAPPING)
        assert result == 0

    def test_decode_unknown_chars(self):
        """Test decoding with unknown characters treats them as 0."""
        result = decode_secret_code("XYZ", DEFAULT_SECRET_CODE_MAPPING)
        assert result == 0

    def test_decode_lowercase(self):
        """Test decoding handles lowercase input."""
        result = decode_secret_code("rkml", DEFAULT_SECRET_CODE_MAPPING)
        assert result == 1250


class TestDailySalesReport:
    """Tests for daily sales reports."""

    def test_get_daily_sales_with_data(self, populated_db, report_service):
        """Test getting daily sales when data exists."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        report = report_service.get_daily_sales(today)

        assert report.date == today
        # At least our 2 test transactions should exist
        assert report.transaction_count >= 2
        assert report.total_sales >= 750000  # 250000 + 500000
        assert report.cash_sales >= 250000
        assert report.credit_sales >= 500000
        assert report.total_items_sold >= 3  # 1 + 2
        assert report.average_transaction_value > 0

    def test_get_daily_sales_no_data(self, connection_manager, report_service):
        """Test getting daily sales when no data exists."""
        future_date = "2099-12-31"
        report = report_service.get_daily_sales(future_date)

        assert report.date == future_date
        assert report.transaction_count == 0
        assert report.total_sales == 0
        assert report.average_transaction_value == 0.0


class TestDateRangeSalesReport:
    """Tests for date range sales reports."""

    def test_get_sales_by_date_range(self, populated_db, report_service):
        """Test getting sales for a date range."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        report = report_service.get_sales_by_date_range(today, today)

        assert report.from_date == today
        assert report.to_date == today
        assert report.transaction_count >= 2
        assert report.total_sales >= 750000
        assert len(report.daily_breakdown) >= 1

    def test_get_payment_type_breakdown(self, populated_db, report_service):
        """Test payment type breakdown."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        breakdown = report_service.get_payment_type_breakdown(today, today)

        assert "cash" in breakdown
        assert "credit" in breakdown
        assert breakdown["cash"] >= 250000
        assert breakdown["credit"] >= 500000


class TestStockReports:
    """Tests for stock-related reports."""

    def test_get_current_stock(self, populated_db, report_service):
        """Test getting current stock levels."""
        stock = report_service.get_current_stock()

        assert len(stock) >= 2
        # Check at least one variant has expected properties
        assert any(s.quantity == 50 and s.status == "in_stock" for s in stock)

    def test_get_low_stock_report_empty(self, connection_manager, report_service):
        """Test low stock report returns items below reorder point."""
        # This test verifies the function works - seed data may have low stock items
        low_stock = report_service.get_low_stock_report()

        # All returned items should actually be low stock (qty <= reorder_point)
        for item in low_stock:
            assert item.quantity <= item.reorder_point
            assert item.status == "low_stock"

    def test_get_stock_valuation(self, populated_db, report_service):
        """Test stock valuation calculation."""
        valuation = report_service.get_stock_valuation()

        assert valuation.total_cost_value > 0
        assert valuation.total_sale_value > 0
        assert valuation.potential_profit == valuation.total_sale_value - valuation.total_cost_value


class TestProfitReports:
    """Tests for profit calculations using secret code decoding."""

    def test_get_profit_by_period(self, populated_db, report_service):
        """Test profit calculation with secret code decoded costs."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        profit = report_service.get_profit_by_period(today, today)

        assert profit.total_revenue >= 750000
        # Cost should be decoded from secret codes
        assert profit.total_cost > 0
        assert profit.gross_profit == profit.total_revenue - profit.total_cost
        assert 0 <= profit.margin_percent <= 100

    def test_get_product_wise_sales_with_profit(self, populated_db, report_service):
        """Test product-wise sales includes profit calculations."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        products = report_service.get_product_wise_sales(today, today)

        assert len(products) > 0
        for product in products:
            assert product.revenue >= 0
            assert product.cost >= 0
            assert product.profit == product.revenue - product.cost
            if product.revenue > 0:
                assert 0 <= product.margin_percent <= 100


class TestCustomerReports:
    """Tests for customer-related reports."""

    def test_get_customer_list(self, populated_db, report_service):
        """Test getting customer list with purchase summaries."""
        customers = report_service.get_customer_list()

        assert len(customers) >= 1
        # Find our test customer by phone pattern
        test_customer = next((c for c in customers if "Report Test Customer" in c.name), None)
        if test_customer:
            assert test_customer.total_purchases >= 750000
            assert test_customer.total_due >= 500000
            assert test_customer.total_paid >= 250000

    def test_get_customer_purchase_history(self, populated_db, report_service):
        """Test getting purchase history for a customer."""
        # Get customer ID from database
        cm = populated_db
        conn = cm.get_read_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM customers WHERE name LIKE ?", ("Report Test Customer%",))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if row:
            customer_id = row["id"]
            history = report_service.get_customer_purchase_history(customer_id)

            assert len(history) >= 2
            invoice_numbers = [h.invoice_number for h in history]
            assert any("INV-RPT" in inv for inv in invoice_numbers)

    def test_get_customer_credit_report(self, populated_db, report_service):
        """Test customer credit report shows outstanding balances."""
        credit_report = report_service.get_customer_credit_report()

        # Should include customers with total_due > 0 or credit_limit > 0
        assert len(credit_report) >= 1


class TestReturnExchangeReports:
    """Tests for return and exchange reports."""

    def test_get_returns_by_period_empty(self, populated_db, report_service):
        """Test returns report when no returns exist."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        returns = report_service.get_returns_by_period(today, today)

        assert len(returns) == 0

    def test_get_exchange_summary_empty(self, populated_db, report_service):
        """Test exchange summary when no exchanges exist."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        summary = report_service.get_exchange_summary(today, today)

        assert summary.total_exchanges == 0
        assert summary.even_exchanges == 0
        assert summary.customer_paid_exchanges == 0
        assert summary.refund_exchanges == 0
        assert summary.total_amount_collected == 0
        assert summary.total_amount_refunded == 0


class TestReorderSuggestions:
    """Tests for reorder suggestions."""

    def test_get_reorder_suggestions_when_all_stocked(self, connection_manager, report_service):
        """Test reorder suggestions when all items are well stocked."""
        # Fresh database has no items, so no suggestions
        suggestions = report_service.get_reorder_suggestions()

        assert len(suggestions) == 0

    def test_get_reorder_suggestions_with_low_stock(self, connection_manager, report_service):
        """Test reorder suggestions when items are below reorder point."""
        cm = connection_manager
        conn = cm.get_read_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now(timezone.utc).isoformat()

            # Create a category
            cursor.execute(
                "INSERT INTO categories (name, code, tax_rate, created_at) VALUES (?, ?, ?, ?)",
                ("Low Stock Test", f"LST{now.replace('-', '')[:15]}", 0.0, now),
            )
            category_id = cursor.lastrowid

            # Create a style
            cursor.execute(
                "INSERT INTO styles (style_code, name, category_id, base_sale_price, tax_rate, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (f"LST-SH-{now.replace('-', '')[:15]}", "Low Stock Shirt", category_id, 200000, 0.0, now, now),
            )
            style_id = cursor.lastrowid

            # Create low stock variant
            cursor.execute(
                "INSERT INTO variants (style_id, size, color, barcode, quantity, reorder_point, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (style_id, "S", "Red", f"LST99999999{now.replace('-', '')[:8]}", 2, 10, now, now),
            )

            conn.commit()
            cursor.close()

            suggestions = report_service.get_reorder_suggestions()

            assert len(suggestions) >= 1
            # Find our low stock item
            low_stock_item = next((s for s in suggestions if s.current_qty == 2), None)
            if low_stock_item:
                assert low_stock_item.reorder_point == 10
                assert low_stock_item.suggested_order_qty > 0
        finally:
            conn.close()
