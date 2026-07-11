"""
Report service for Shoukat Sons Garments POS.

Provides sales, stock, profit, customer, and return/exchange reports.
Profit calculations use secret code decoding (owner-only).
All monetary values are INTEGER cents.
"""

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from database.connection import ConnectionManager


# ===== REPORT DATA CLASSES =====


@dataclass
class DailySalesReport:
    """Sales summary for a single day."""

    date: str
    total_sales: int
    cash_sales: int
    credit_sales: int
    total_items_sold: int
    transaction_count: int
    average_transaction_value: float


@dataclass
class DateRangeSalesReport:
    """Sales summary for a date range with daily breakdown."""

    from_date: str
    to_date: str
    total_sales: int
    cash_sales: int
    credit_sales: int
    total_items_sold: int
    transaction_count: int
    average_transaction_value: float
    daily_breakdown: List[Dict]


@dataclass
class ProductSalesRecord:
    """Sales record grouped by variant."""

    variant_id: int
    style_name: str
    size: str
    color: str
    barcode: str
    quantity_sold: int
    revenue: int
    cost: int
    profit: int
    margin_percent: float


@dataclass
class CategorySalesRecord:
    """Sales record grouped by category."""

    category_id: int
    category_name: str
    quantity_sold: int
    revenue: int
    cost: int
    profit: int
    margin_percent: float


@dataclass
class StockRecord:
    """Current stock level record."""

    variant_id: int
    barcode: str
    style_name: str
    size: str
    color: str
    quantity: int
    reorder_point: int
    purchase_value: int
    sale_value: int
    status: str  # "in_stock", "low_stock", "out_of_stock"


@dataclass
class StockValuation:
    """Total inventory valuation."""

    total_cost_value: int
    total_sale_value: int
    potential_profit: int
    margin_percent: float


@dataclass
class ReorderSuggestion:
    """Reorder suggestion for low stock items."""

    variant_id: int
    barcode: str
    style_name: str
    size: str
    color: str
    current_qty: int
    reorder_point: int
    suggested_order_qty: int


@dataclass
class ProfitReport:
    """Profit summary for a period."""

    from_date: str
    to_date: str
    total_revenue: int
    total_cost: int
    gross_profit: int
    margin_percent: float


@dataclass
class ProductProfitRecord:
    """Profit record by product."""

    variant_id: int
    style_name: str
    size: str
    color: str
    quantity_sold: int
    revenue: int
    cost: int
    profit: int
    margin_percent: float


@dataclass
class CategoryProfitRecord:
    """Profit record by category."""

    category_id: int
    category_name: str
    quantity_sold: int
    revenue: int
    cost: int
    profit: int
    margin_percent: float


@dataclass
class CustomerSummary:
    """Customer summary record."""

    customer_id: int
    name: str
    phone: Optional[str]
    total_purchases: int
    total_paid: int
    total_due: int
    last_purchase_date: Optional[str]


@dataclass
class SaleSummary:
    """Sale summary record."""

    sale_id: int
    invoice_number: str
    sale_date: str
    total_amount: int
    paid_amount: int
    due_amount: int
    payment_type: str
    status: str


@dataclass
class CustomerCreditRecord:
    """Customer credit record."""

    customer_id: int
    name: str
    phone: Optional[str]
    total_due: int
    credit_limit: int
    last_payment_date: Optional[str]
    last_payment_amount: int


@dataclass
class ReturnRecord:
    """Return record."""

    return_id: int
    sale_id: int
    invoice_number: str
    user_id: int
    reason: str
    total_refund: int
    return_date: str


@dataclass
class ExchangeSummary:
    """Exchange summary for a period."""

    from_date: str
    to_date: str
    total_exchanges: int
    even_exchanges: int
    customer_paid_exchanges: int
    refund_exchanges: int
    total_amount_collected: int
    total_amount_refunded: int


# ===== SECRET CODE DECODING =====


def decode_secret_code(code: str, mapping: Dict[str, str]) -> int:
    """
    Decode a secret code back to purchase price in cents.

    Args:
        code: Secret code string (e.g., "RKML").
        mapping: Reverse mapping {encoded_char: original_digit}.

    Returns:
        Decoded purchase price in cents.

    Example:
        With default mapping {"R": "1", "K": "2", "M": "5", "L": "0"},
        "RKML" decodes to 1250 (Rs. 1,250).
    """
    assert code is not None
    assert mapping is not None

    result = ""
    for char in code.upper():
        if char in mapping:
            result += mapping[char]
        else:
            # Unknown char, treat as 0
            result += "0"

    return int(result) if result else 0


# Default secret code mapping (reverse of encoding)
DEFAULT_SECRET_CODE_MAPPING = {
    "R": "1",
    "K": "2",
    "M": "5",
    "L": "0",
    "A": "3",
    "B": "4",
    "C": "6",
    "D": "7",
    "E": "8",
    "F": "9",
}


class ReportService:
    """
    Core reporting service for sales, stock, profit, customers, returns.

    Provides comprehensive business intelligence with owner-only
    profit calculations using secret code decoding.
    """

    def __init__(self, connection_manager: ConnectionManager) -> None:
        """
        Initialize the ReportService.

        Args:
            connection_manager: Database connection manager instance.
        """
        assert connection_manager is not None
        self.cm = connection_manager

    # ===== SALES REPORTS =====

    def get_daily_sales(self, date: str) -> DailySalesReport:
        """
        Get sales summary for a single day.

        Args:
            date: Date string in YYYY-MM-DD format.

        Returns:
            DailySalesReport with totals and averages.
        """
        assert isinstance(date, str) and len(date) == 10

        conn = self.cm.get_read_connection()
        try:
            cursor = conn.cursor()

            # Get sales totals for the day
            cursor.execute(
                """
                SELECT 
                    COUNT(*) as transaction_count,
                    COALESCE(SUM(total_amount), 0) as total_sales,
                    COALESCE(SUM(CASE WHEN payment_type = 'cash' THEN total_amount ELSE 0 END), 0) as cash_sales,
                    COALESCE(SUM(CASE WHEN payment_type = 'credit' THEN total_amount ELSE 0 END), 0) as credit_sales
                FROM sales
                WHERE DATE(sale_date) = DATE(?)
                  AND status NOT IN ('voided', 'held')
                """,
                (date,),
            )
            row = cursor.fetchone()

            transaction_count = row["transaction_count"] or 0
            total_sales = row["total_sales"] or 0
            cash_sales = row["cash_sales"] or 0
            credit_sales = row["credit_sales"] or 0

            # Get total items sold
            cursor.execute(
                """
                SELECT COALESCE(SUM(si.quantity), 0) as total_items
                FROM sale_items si
                JOIN sales s ON si.sale_id = s.id
                WHERE DATE(s.sale_date) = DATE(?)
                  AND s.status NOT IN ('voided', 'held')
                """,
                (date,),
            )
            items_row = cursor.fetchone()
            total_items_sold = items_row["total_items"] or 0

            cursor.close()

            avg_value = total_sales / transaction_count if transaction_count > 0 else 0.0

            return DailySalesReport(
                date=date,
                total_sales=total_sales,
                cash_sales=cash_sales,
                credit_sales=credit_sales,
                total_items_sold=total_items_sold,
                transaction_count=transaction_count,
                average_transaction_value=round(avg_value, 2),
            )
        finally:
            conn.close()

    def get_sales_by_date_range(
        self, from_date: str, to_date: str
    ) -> DateRangeSalesReport:
        """
        Get sales summary for a date range with daily breakdown.

        Args:
            from_date: Start date in YYYY-MM-DD format.
            to_date: End date in YYYY-MM-DD format.

        Returns:
            DateRangeSalesReport with totals and daily breakdown.
        """
        assert isinstance(from_date, str) and len(from_date) == 10
        assert isinstance(to_date, str) and len(to_date) == 10

        conn = self.cm.get_read_connection()
        try:
            cursor = conn.cursor()

            # Get overall totals
            cursor.execute(
                """
                SELECT 
                    COUNT(*) as transaction_count,
                    COALESCE(SUM(total_amount), 0) as total_sales,
                    COALESCE(SUM(CASE WHEN payment_type = 'cash' THEN total_amount ELSE 0 END), 0) as cash_sales,
                    COALESCE(SUM(CASE WHEN payment_type = 'credit' THEN total_amount ELSE 0 END), 0) as credit_sales
                FROM sales
                WHERE DATE(sale_date) BETWEEN DATE(?) AND DATE(?)
                  AND status NOT IN ('voided', 'held')
                """,
                (from_date, to_date),
            )
            row = cursor.fetchone()

            transaction_count = row["transaction_count"] or 0
            total_sales = row["total_sales"] or 0
            cash_sales = row["cash_sales"] or 0
            credit_sales = row["credit_sales"] or 0

            # Get total items sold
            cursor.execute(
                """
                SELECT COALESCE(SUM(si.quantity), 0) as total_items
                FROM sale_items si
                JOIN sales s ON si.sale_id = s.id
                WHERE DATE(s.sale_date) BETWEEN DATE(?) AND DATE(?)
                  AND s.status NOT IN ('voided', 'held')
                """,
                (from_date, to_date),
            )
            items_row = cursor.fetchone()
            total_items_sold = items_row["total_items"] or 0

            # Get daily breakdown
            cursor.execute(
                """
                SELECT 
                    DATE(sale_date) as sale_day,
                    COUNT(*) as transaction_count,
                    COALESCE(SUM(total_amount), 0) as total_sales,
                    COALESCE(SUM(CASE WHEN payment_type = 'cash' THEN total_amount ELSE 0 END), 0) as cash_sales,
                    COALESCE(SUM(CASE WHEN payment_type = 'credit' THEN total_amount ELSE 0 END), 0) as credit_sales
                FROM sales
                WHERE DATE(sale_date) BETWEEN DATE(?) AND DATE(?)
                  AND status NOT IN ('voided', 'held')
                GROUP BY DATE(sale_date)
                ORDER BY sale_day
                """,
                (from_date, to_date),
            )
            daily_rows = cursor.fetchall()
            daily_breakdown = [
                {
                    "date": r["sale_day"],
                    "transactions": r["transaction_count"],
                    "total": r["total_sales"],
                    "cash": r["cash_sales"],
                    "credit": r["credit_sales"],
                }
                for r in daily_rows
            ]

            cursor.close()

            avg_value = total_sales / transaction_count if transaction_count > 0 else 0.0

            return DateRangeSalesReport(
                from_date=from_date,
                to_date=to_date,
                total_sales=total_sales,
                cash_sales=cash_sales,
                credit_sales=credit_sales,
                total_items_sold=total_items_sold,
                transaction_count=transaction_count,
                average_transaction_value=round(avg_value, 2),
                daily_breakdown=daily_breakdown,
            )
        finally:
            conn.close()

    def get_product_wise_sales(
        self,
        from_date: str,
        to_date: str,
        category_id: Optional[int] = None,
    ) -> List[ProductSalesRecord]:
        """
        Get sales grouped by variant with revenue and profit.

        Uses secret code decoding for cost calculation (owner-only).

        Args:
            from_date: Start date in YYYY-MM-DD format.
            to_date: End date in YYYY-MM-DD format.
            category_id: Optional category filter.

        Returns:
            List of ProductSalesRecord with profit calculations.
        """
        assert isinstance(from_date, str) and len(from_date) == 10
        assert isinstance(to_date, str) and len(to_date) == 10

        conn = self.cm.get_read_connection()
        try:
            cursor = conn.cursor()

            category_filter = ""
            params: List = [from_date, to_date]
            if category_id is not None:
                category_filter = "AND c.id = ?"
                params.append(category_id)

            cursor.execute(
                f"""
                SELECT 
                    v.id as variant_id,
                    s.name as style_name,
                    v.size,
                    v.color,
                    v.barcode,
                    SUM(si.quantity) as quantity_sold,
                    SUM(si.total_price) as revenue
                FROM sale_items si
                JOIN variants v ON si.variant_id = v.id
                JOIN styles s ON v.style_id = s.id
                JOIN categories c ON s.category_id = c.id
                JOIN sales sal ON si.sale_id = sal.id
                WHERE DATE(sal.sale_date) BETWEEN DATE(?) AND DATE(?)
                  AND sal.status NOT IN ('voided', 'held')
                  {category_filter}
                GROUP BY v.id
                ORDER BY revenue DESC
                """,
                params,
            )
            rows = cursor.fetchall()

            results: List[ProductSalesRecord] = []
            for row in rows:
                variant_id = row["variant_id"]
                quantity_sold = row["quantity_sold"]
                revenue = row["revenue"]

                # Calculate cost using secret code from batches
                cost = self._get_variant_cost_for_period(
                    conn, variant_id, from_date, to_date, quantity_sold
                )

                profit = revenue - cost
                margin = (profit / revenue * 100) if revenue > 0 else 0.0

                results.append(
                    ProductSalesRecord(
                        variant_id=variant_id,
                        style_name=row["style_name"],
                        size=row["size"],
                        color=row["color"],
                        barcode=row["barcode"],
                        quantity_sold=quantity_sold,
                        revenue=revenue,
                        cost=cost,
                        profit=profit,
                        margin_percent=round(margin, 2),
                    )
                )

            cursor.close()
            return results
        finally:
            conn.close()

    def _get_variant_cost_for_period(
        self,
        conn: sqlite3.Connection,
        variant_id: int,
        from_date: str,
        to_date: str,
        quantity_sold: int,
    ) -> int:
        """
        Get cost for variant sales in a period using FIFO and secret code.

        Args:
            conn: Database connection.
            variant_id: Variant ID.
            from_date: Start date.
            to_date: End date.
            quantity_sold: Total quantity sold.

        Returns:
            Total cost in cents.
        """
        assert conn is not None
        assert isinstance(variant_id, int) and variant_id > 0

        cursor = conn.cursor()

        # Get batches used for this variant in the period (FIFO order)
        cursor.execute(
            """
            SELECT b.secret_code, b.purchase_price, 
                   SUM(CASE WHEN si.batch_id = b.id THEN si.quantity ELSE 0 END) as qty_used
            FROM batches b
            LEFT JOIN sale_items si ON si.batch_id = b.id
            LEFT JOIN sales s ON si.sale_id = s.id
            WHERE b.variant_id = ?
              AND DATE(s.sale_date) BETWEEN DATE(?) AND DATE(?)
            GROUP BY b.id
            ORDER BY b.date_received ASC
            """,
            (variant_id, from_date, to_date),
        )
        batch_rows = cursor.fetchall()
        cursor.close()

        total_cost = 0
        remaining_qty = quantity_sold

        for batch in batch_rows:
            if remaining_qty <= 0:
                break

            secret_code = batch["secret_code"]
            qty_used = min(batch["qty_used"] or 0, remaining_qty)

            # Decode purchase price from secret code
            purchase_price = decode_secret_code(
                secret_code, DEFAULT_SECRET_CODE_MAPPING
            )

            total_cost += purchase_price * qty_used
            remaining_qty -= qty_used

        return total_cost

    def get_category_wise_sales(
        self, from_date: str, to_date: str
    ) -> List[CategorySalesRecord]:
        """
        Get sales grouped by category.

        Args:
            from_date: Start date in YYYY-MM-DD format.
            to_date: End date in YYYY-MM-DD format.

        Returns:
            List of CategorySalesRecord.
        """
        assert isinstance(from_date, str) and len(from_date) == 10
        assert isinstance(to_date, str) and len(to_date) == 10

        conn = self.cm.get_read_connection()
        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT 
                    c.id as category_id,
                    c.name as category_name,
                    SUM(si.quantity) as quantity_sold,
                    SUM(si.total_price) as revenue
                FROM sale_items si
                JOIN variants v ON si.variant_id = v.id
                JOIN styles s ON v.style_id = s.id
                JOIN categories c ON s.category_id = c.id
                JOIN sales sal ON si.sale_id = sal.id
                WHERE DATE(sal.sale_date) BETWEEN DATE(?) AND DATE(?)
                  AND sal.status NOT IN ('voided', 'held')
                GROUP BY c.id
                ORDER BY revenue DESC
                """,
                (from_date, to_date),
            )
            rows = cursor.fetchall()

            results: List[CategorySalesRecord] = []
            for row in rows:
                category_id = row["category_id"]
                quantity_sold = row["quantity_sold"]
                revenue = row["revenue"]

                # Calculate cost for category
                cost = self._get_category_cost_for_period(
                    conn, category_id, from_date, to_date
                )

                profit = revenue - cost
                margin = (profit / revenue * 100) if revenue > 0 else 0.0

                results.append(
                    CategorySalesRecord(
                        category_id=category_id,
                        category_name=row["category_name"],
                        quantity_sold=quantity_sold,
                        revenue=revenue,
                        cost=cost,
                        profit=profit,
                        margin_percent=round(margin, 2),
                    )
                )

            cursor.close()
            return results
        finally:
            conn.close()

    def _get_category_cost_for_period(
        self,
        conn: sqlite3.Connection,
        category_id: int,
        from_date: str,
        to_date: str,
    ) -> int:
        """
        Get total cost for category sales in a period.

        Args:
            conn: Database connection.
            category_id: Category ID.
            from_date: Start date.
            to_date: End date.

        Returns:
            Total cost in cents.
        """
        assert conn is not None
        assert isinstance(category_id, int) and category_id > 0

        cursor = conn.cursor()

        # Get all variants in this category
        cursor.execute(
            """
            SELECT v.id FROM variants v
            JOIN styles s ON v.style_id = s.id
            WHERE s.category_id = ?
            """,
            (category_id,),
        )
        variant_ids = [r["id"] for r in cursor.fetchall()]
        cursor.close()

        total_cost = 0
        for variant_id in variant_ids:
            # Get quantity sold for this variant
            qty_sold = self._get_variant_quantity_sold(
                conn, variant_id, from_date, to_date
            )
            if qty_sold > 0:
                total_cost += self._get_variant_cost_for_period(
                    conn, variant_id, from_date, to_date, qty_sold
                )

        return total_cost

    def _get_variant_quantity_sold(
        self,
        conn: sqlite3.Connection,
        variant_id: int,
        from_date: str,
        to_date: str,
    ) -> int:
        """Get quantity sold for a variant in a period."""
        assert conn is not None
        assert isinstance(variant_id, int) and variant_id > 0

        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COALESCE(SUM(si.quantity), 0) as qty
            FROM sale_items si
            JOIN sales s ON si.sale_id = s.id
            WHERE si.variant_id = ?
              AND DATE(s.sale_date) BETWEEN DATE(?) AND DATE(?)
              AND s.status NOT IN ('voided', 'held')
            """,
            (variant_id, from_date, to_date),
        )
        row = cursor.fetchone()
        cursor.close()
        return row["qty"] if row else 0

    def get_payment_type_breakdown(
        self, from_date: str, to_date: str
    ) -> Dict[str, int]:
        """
        Get cash vs credit vs split totals.

        Args:
            from_date: Start date in YYYY-MM-DD format.
            to_date: End date in YYYY-MM-DD format.

        Returns:
            Dictionary with payment type totals.
        """
        assert isinstance(from_date, str) and len(from_date) == 10
        assert isinstance(to_date, str) and len(to_date) == 10

        conn = self.cm.get_read_connection()
        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT 
                    payment_type,
                    COALESCE(SUM(total_amount), 0) as total
                FROM sales
                WHERE DATE(sale_date) BETWEEN DATE(?) AND DATE(?)
                  AND status NOT IN ('voided', 'held')
                GROUP BY payment_type
                """,
                (from_date, to_date),
            )
            rows = cursor.fetchall()
            cursor.close()

            return {row["payment_type"]: row["total"] for row in rows}
        finally:
            conn.close()

    # ===== STOCK REPORTS =====

    def get_current_stock(
        self,
        category_id: Optional[int] = None,
        stock_status: Optional[str] = None,
    ) -> List[StockRecord]:
        """
        Get current stock levels with filtering.

        Args:
            category_id: Optional category filter.
            stock_status: Optional filter (all/in_stock/low_stock/out_of_stock).

        Returns:
            List of StockRecord.
        """
        conn = self.cm.get_read_connection()
        try:
            cursor = conn.cursor()

            category_filter = ""
            params: List = []
            if category_id is not None:
                category_filter = "WHERE s.category_id = ?"
                params.append(category_id)

            cursor.execute(
                f"""
                SELECT 
                    v.id as variant_id,
                    v.barcode,
                    s.name as style_name,
                    v.size,
                    v.color,
                    v.quantity,
                    v.reorder_point,
                    COALESCE(SUM(b.purchase_price * b.quantity_remaining), 0) as purchase_value,
                    COALESCE(SUM(s.base_sale_price * v.quantity), 0) as sale_value
                FROM variants v
                JOIN styles s ON v.style_id = s.id
                LEFT JOIN batches b ON v.id = b.variant_id AND b.quantity_remaining > 0
                {category_filter}
                GROUP BY v.id
                ORDER BY v.barcode
                """,
                params,
            )
            rows = cursor.fetchall()

            results: List[StockRecord] = []
            for row in rows:
                quantity = row["quantity"]
                reorder_point = row["reorder_point"]

                # Determine stock status
                if quantity == 0:
                    status = "out_of_stock"
                elif quantity <= reorder_point:
                    status = "low_stock"
                else:
                    status = "in_stock"

                # Apply status filter
                if stock_status and stock_status != "all":
                    if stock_status == "low_stock" and status != "low_stock":
                        continue
                    if stock_status == "out_of_stock" and status != "out_of_stock":
                        continue
                    if stock_status == "in_stock" and status != "in_stock":
                        continue

                results.append(
                    StockRecord(
                        variant_id=row["variant_id"],
                        barcode=row["barcode"],
                        style_name=row["style_name"],
                        size=row["size"],
                        color=row["color"],
                        quantity=quantity,
                        reorder_point=reorder_point,
                        purchase_value=row["purchase_value"],
                        sale_value=row["sale_value"],
                        status=status,
                    )
                )

            cursor.close()
            return results
        finally:
            conn.close()

    def get_low_stock_report(self) -> List[StockRecord]:
        """
        Get variants at or below reorder_point.

        Returns:
            List of StockRecord for low stock items.
        """
        return self.get_current_stock(stock_status="low_stock")

    def get_stock_valuation(self) -> StockValuation:
        """
        Get total inventory value at cost, sale price, and potential profit.

        Returns:
            StockValuation with totals and margin.
        """
        conn = self.cm.get_read_connection()
        try:
            cursor = conn.cursor()

            # Get total cost value from batches
            cursor.execute(
                """
                SELECT COALESCE(SUM(b.purchase_price * b.quantity_remaining), 0) as cost_value
                FROM batches b
                WHERE b.quantity_remaining > 0
                """
            )
            cost_row = cursor.fetchone()
            total_cost = cost_row["cost_value"] or 0

            # Get total sale value from variants
            cursor.execute(
                """
                SELECT COALESCE(SUM(v.quantity * s.base_sale_price), 0) as sale_value
                FROM variants v
                JOIN styles s ON v.style_id = s.id
                WHERE v.quantity > 0
                """
            )
            sale_row = cursor.fetchone()
            total_sale = sale_row["sale_value"] or 0

            cursor.close()

            potential_profit = total_sale - total_cost
            margin = (potential_profit / total_sale * 100) if total_sale > 0 else 0.0

            return StockValuation(
                total_cost_value=total_cost,
                total_sale_value=total_sale,
                potential_profit=potential_profit,
                margin_percent=round(margin, 2),
            )
        finally:
            conn.close()

    def get_reorder_suggestions(self) -> List[ReorderSuggestion]:
        """
        Get variants below reorder_point with suggested order quantities.

        Returns:
            List of ReorderSuggestion.
        """
        conn = self.cm.get_read_connection()
        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT 
                    v.id as variant_id,
                    v.barcode,
                    s.name as style_name,
                    v.size,
                    v.color,
                    v.quantity as current_qty,
                    v.reorder_point
                FROM variants v
                JOIN styles s ON v.style_id = s.id
                WHERE v.quantity <= v.reorder_point
                ORDER BY v.quantity ASC
                """
            )
            rows = cursor.fetchall()
            cursor.close()

            results: List[ReorderSuggestion] = []
            for row in rows:
                current_qty = row["current_qty"]
                reorder_point = row["reorder_point"]
                # Suggest ordering enough to reach 2x reorder point
                suggested_qty = max(reorder_point * 2 - current_qty, reorder_point)

                results.append(
                    ReorderSuggestion(
                        variant_id=row["variant_id"],
                        barcode=row["barcode"],
                        style_name=row["style_name"],
                        size=row["size"],
                        color=row["color"],
                        current_qty=current_qty,
                        reorder_point=reorder_point,
                        suggested_order_qty=suggested_qty,
                    )
                )

            return results
        finally:
            conn.close()

    # ===== PROFIT REPORTS =====

    def get_profit_by_period(
        self, from_date: str, to_date: str
    ) -> ProfitReport:
        """
        Get profit summary for a period using secret code decoded costs.

        Args:
            from_date: Start date in YYYY-MM-DD format.
            to_date: End date in YYYY-MM-DD format.

        Returns:
            ProfitReport with revenue, cost, profit, and margin.
        """
        assert isinstance(from_date, str) and len(from_date) == 10
        assert isinstance(to_date, str) and len(to_date) == 10

        conn = self.cm.get_read_connection()
        try:
            cursor = conn.cursor()

            # Get total revenue
            cursor.execute(
                """
                SELECT COALESCE(SUM(total_amount), 0) as revenue
                FROM sales
                WHERE DATE(sale_date) BETWEEN DATE(?) AND DATE(?)
                  AND status NOT IN ('voided', 'held')
                """,
                (from_date, to_date),
            )
            revenue = cursor.fetchone()["revenue"] or 0

            # Get total cost by summing all product costs
            total_cost = self._get_total_cost_for_period(conn, from_date, to_date)

            cursor.close()

            gross_profit = revenue - total_cost
            margin = (gross_profit / revenue * 100) if revenue > 0 else 0.0

            return ProfitReport(
                from_date=from_date,
                to_date=to_date,
                total_revenue=revenue,
                total_cost=total_cost,
                gross_profit=gross_profit,
                margin_percent=round(margin, 2),
            )
        finally:
            conn.close()

    def _get_total_cost_for_period(
        self,
        conn: sqlite3.Connection,
        from_date: str,
        to_date: str,
    ) -> int:
        """Get total cost for all sales in a period using FIFO and secret codes."""
        assert conn is not None

        cursor = conn.cursor()

        # Get all sale items in the period with their batch info
        cursor.execute(
            """
            SELECT si.id, si.variant_id, si.batch_id, si.quantity, b.secret_code, b.purchase_price
            FROM sale_items si
            JOIN sales s ON si.sale_id = s.id
            LEFT JOIN batches b ON si.batch_id = b.id
            WHERE DATE(s.sale_date) BETWEEN DATE(?) AND DATE(?)
              AND s.status NOT IN ('voided', 'held')
            """,
            (from_date, to_date),
        )
        rows = cursor.fetchall()
        cursor.close()

        total_cost = 0
        for row in rows:
            secret_code = row["secret_code"]
            quantity = row["quantity"]

            # Decode purchase price from secret code
            if secret_code:
                purchase_price = decode_secret_code(
                    secret_code, DEFAULT_SECRET_CODE_MAPPING
                )
            else:
                purchase_price = row["purchase_price"] or 0

            total_cost += purchase_price * quantity

        return total_cost

    def get_profit_by_product(
        self, from_date: str, to_date: str
    ) -> List[ProductProfitRecord]:
        """
        Get profit breakdown by product.

        Args:
            from_date: Start date in YYYY-MM-DD format.
            to_date: End date in YYYY-MM-DD format.

        Returns:
            List of ProductProfitRecord.
        """
        # Reuse product_wise_sales which already calculates profit
        product_sales = self.get_product_wise_sales(from_date, to_date)

        return [
            ProductProfitRecord(
                variant_id=ps.variant_id,
                style_name=ps.style_name,
                size=ps.size,
                color=ps.color,
                quantity_sold=ps.quantity_sold,
                revenue=ps.revenue,
                cost=ps.cost,
                profit=ps.profit,
                margin_percent=ps.margin_percent,
            )
            for ps in product_sales
        ]

    def get_profit_by_category(
        self, from_date: str, to_date: str
    ) -> List[CategoryProfitRecord]:
        """
        Get profit breakdown by category.

        Args:
            from_date: Start date in YYYY-MM-DD format.
            to_date: End date in YYYY-MM-DD format.

        Returns:
            List of CategoryProfitRecord.
        """
        # Reuse category_wise_sales which already calculates profit
        category_sales = self.get_category_wise_sales(from_date, to_date)

        return [
            CategoryProfitRecord(
                category_id=cs.category_id,
                category_name=cs.category_name,
                quantity_sold=cs.quantity_sold,
                revenue=cs.revenue,
                cost=cs.cost,
                profit=cs.profit,
                margin_percent=cs.margin_percent,
            )
            for cs in category_sales
        ]

    # ===== CUSTOMER REPORTS =====

    def get_customer_list(self) -> List[CustomerSummary]:
        """
        Get list of all customers with purchase summaries.

        Returns:
            List of CustomerSummary.
        """
        conn = self.cm.get_read_connection()
        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT 
                    c.id as customer_id,
                    c.name,
                    c.phone,
                    c.total_due,
                    COALESCE(SUM(s.total_amount), 0) as total_purchases,
                    COALESCE(MAX(s.sale_date), NULL) as last_purchase_date
                FROM customers c
                LEFT JOIN sales s ON c.id = s.customer_id
                    AND s.status NOT IN ('voided', 'held')
                GROUP BY c.id
                ORDER BY c.name
                """
            )
            rows = cursor.fetchall()

            results: List[CustomerSummary] = []
            for row in rows:
                total_purchases = row["total_purchases"]
                total_due = row["total_due"] or 0
                total_paid = total_purchases - total_due

                results.append(
                    CustomerSummary(
                        customer_id=row["customer_id"],
                        name=row["name"],
                        phone=row["phone"],
                        total_purchases=total_purchases,
                        total_paid=total_paid,
                        total_due=total_due,
                        last_purchase_date=row["last_purchase_date"],
                    )
                )

            cursor.close()
            return results
        finally:
            conn.close()

    def get_customer_purchase_history(self, customer_id: int) -> List[SaleSummary]:
        """
        Get purchase history for a specific customer.

        Args:
            customer_id: Customer ID.

        Returns:
            List of SaleSummary.
        """
        assert isinstance(customer_id, int) and customer_id > 0

        conn = self.cm.get_read_connection()
        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT 
                    id as sale_id,
                    invoice_number,
                    sale_date,
                    total_amount,
                    paid_amount,
                    due_amount,
                    payment_type,
                    status
                FROM sales
                WHERE customer_id = ?
                  AND status NOT IN ('voided', 'held')
                ORDER BY sale_date DESC
                """,
                (customer_id,),
            )
            rows = cursor.fetchall()
            cursor.close()

            return [
                SaleSummary(
                    sale_id=row["sale_id"],
                    invoice_number=row["invoice_number"],
                    sale_date=row["sale_date"],
                    total_amount=row["total_amount"],
                    paid_amount=row["paid_amount"],
                    due_amount=row["due_amount"],
                    payment_type=row["payment_type"],
                    status=row["status"],
                )
                for row in rows
            ]
        finally:
            conn.close()

    def get_customer_credit_report(self) -> List[CustomerCreditRecord]:
        """
        Get all customers with outstanding credit.

        Returns:
            List of CustomerCreditRecord with due amounts.
        """
        conn = self.cm.get_read_connection()
        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT 
                    c.id as customer_id,
                    c.name,
                    c.phone,
                    c.total_due,
                    c.credit_limit,
                    cp.payment_date as last_payment_date,
                    cp.amount as last_payment_amount
                FROM customers c
                LEFT JOIN (
                    SELECT customer_id, MAX(payment_date) as payment_date, amount
                    FROM credit_payments
                    GROUP BY customer_id
                ) cp ON c.id = cp.customer_id
                WHERE c.total_due > 0 OR c.credit_limit > 0
                ORDER BY c.total_due DESC
                """
            )
            rows = cursor.fetchall()
            cursor.close()

            return [
                CustomerCreditRecord(
                    customer_id=row["customer_id"],
                    name=row["name"],
                    phone=row["phone"],
                    total_due=row["total_due"],
                    credit_limit=row["credit_limit"],
                    last_payment_date=row["last_payment_date"],
                    last_payment_amount=row["last_payment_amount"] or 0,
                )
                for row in rows
            ]
        finally:
            conn.close()

    # ===== RETURN/EXCHANGE REPORTS =====

    def get_returns_by_period(
        self, from_date: str, to_date: str
    ) -> List[ReturnRecord]:
        """
        Get returns for a period.

        Args:
            from_date: Start date in YYYY-MM-DD format.
            to_date: End date in YYYY-MM-DD format.

        Returns:
            List of ReturnRecord.
        """
        assert isinstance(from_date, str) and len(from_date) == 10
        assert isinstance(to_date, str) and len(to_date) == 10

        conn = self.cm.get_read_connection()
        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT 
                    r.id as return_id,
                    r.sale_id,
                    s.invoice_number,
                    r.user_id,
                    r.reason,
                    r.total_refund,
                    r.return_date
                FROM returns r
                JOIN sales s ON r.sale_id = s.id
                WHERE DATE(r.return_date) BETWEEN DATE(?) AND DATE(?)
                ORDER BY r.return_date DESC
                """,
                (from_date, to_date),
            )
            rows = cursor.fetchall()
            cursor.close()

            return [
                ReturnRecord(
                    return_id=row["return_id"],
                    sale_id=row["sale_id"],
                    invoice_number=row["invoice_number"],
                    user_id=row["user_id"],
                    reason=row["reason"],
                    total_refund=row["total_refund"],
                    return_date=row["return_date"],
                )
                for row in rows
            ]
        finally:
            conn.close()

    def get_exchange_summary(
        self, from_date: str, to_date: str
    ) -> ExchangeSummary:
        """
        Get exchange summary for a period.

        Args:
            from_date: Start date in YYYY-MM-DD format.
            to_date: End date in YYYY-MM-DD format.

        Returns:
            ExchangeSummary with counts and totals.
        """
        assert isinstance(from_date, str) and len(from_date) == 10
        assert isinstance(to_date, str) and len(to_date) == 10

        conn = self.cm.get_read_connection()
        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT 
                    COUNT(*) as total_exchanges,
                    COALESCE(SUM(CASE WHEN price_difference = 0 THEN 1 ELSE 0 END), 0) as even_exchanges,
                    COALESCE(SUM(CASE WHEN price_difference > 0 THEN 1 ELSE 0 END), 0) as customer_paid,
                    COALESCE(SUM(CASE WHEN price_difference < 0 THEN 1 ELSE 0 END), 0) as refunds,
                    COALESCE(SUM(CASE WHEN price_difference > 0 THEN price_difference ELSE 0 END), 0) as collected,
                    COALESCE(SUM(CASE WHEN price_difference < 0 THEN ABS(price_difference) ELSE 0 END), 0) as refunded
                FROM exchanges
                WHERE DATE(exchange_date) BETWEEN DATE(?) AND DATE(?)
                """,
                (from_date, to_date),
            )
            row = cursor.fetchone()
            cursor.close()

            return ExchangeSummary(
                from_date=from_date,
                to_date=to_date,
                total_exchanges=row["total_exchanges"] or 0,
                even_exchanges=row["even_exchanges"] or 0,
                customer_paid_exchanges=row["customer_paid"] or 0,
                refund_exchanges=row["refunds"] or 0,
                total_amount_collected=row["collected"] or 0,
                total_amount_refunded=row["refunded"] or 0,
            )
        finally:
            conn.close()
