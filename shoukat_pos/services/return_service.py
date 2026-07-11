"""
Return service for Shoukat Sons Garments POS.

Handles returns and exchanges with ACID transaction guarantees.
Supports FIFO restocking, credit adjustments, and audit logging.
All monetary values are INTEGER cents.
"""

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from database.connection import ConnectionManager
from database.models import Sale, SaleItem


@dataclass
class ReturnItem:
    """Represents an item being returned."""

    sale_item_id: int
    return_qty: int


@dataclass
class ReturnResult:
    """Result of a processed return."""

    return_id: int
    refund_amount: int
    restocked_items: List[Dict]
    return_date: str


@dataclass
class ExchangeResult:
    """Result of a processed exchange."""

    exchange_id: int
    old_variant_id: int
    new_variant_id: int
    price_difference: int
    payment_required: bool
    refund_required: bool


class ValidationError(Exception):
    """Raised when return/exchange data fails validation."""

    pass


class SaleNotFoundError(Exception):
    """Raised when sale is not found or already voided."""

    pass


class ReturnService:
    """
    Core return and exchange processing with ACID guarantees.

    Handles atomic return processing, FIFO restocking, exchanges with
    price difference handling, and credit adjustments.
    """

    VALID_REASONS = (
        "Defective",
        "Wrong Size",
        "Wrong Color",
        "Changed Mind",
        "Other",
    )

    def __init__(self, connection_manager: ConnectionManager) -> None:
        """
        Initialize the ReturnService.

        Args:
            connection_manager: Database connection manager instance.
        """
        assert connection_manager is not None
        self.cm = connection_manager

    def get_sale_items_for_return(self, sale_id: int) -> List[SaleItem]:
        """
        Get items from a sale that are eligible for return.

        Args:
            sale_id: ID of the original sale.

        Returns:
            List of SaleItem that haven't been fully returned.

        Raises:
            SaleNotFoundError: If sale doesn't exist or is voided.
        """
        assert isinstance(sale_id, int) and sale_id > 0

        conn = self.cm.get_read_connection()
        try:
            cursor = conn.cursor()

            # Check sale exists and is not voided
            cursor.execute(
                """
                SELECT id, status FROM sales WHERE id = ?
                """,
                (sale_id,),
            )
            sale_row = cursor.fetchone()

            if sale_row is None:
                cursor.close()
                raise SaleNotFoundError(f"Sale {sale_id} not found")

            if sale_row["status"] == "voided":
                cursor.close()
                raise SaleNotFoundError(f"Sale {sale_id} is voided")

            # Get sale items that haven't been fully returned
            cursor.execute(
                """
                SELECT * FROM sale_items
                WHERE sale_id = ? AND is_returned = 0
                """,
                (sale_id,),
            )
            rows = cursor.fetchall()
            cursor.close()

            return [SaleItem.from_row(row) for row in rows]
        finally:
            conn.close()

    def _calculate_refund_amount(
        self, conn: sqlite3.Connection, sale_item_id: int, return_qty: int
    ) -> int:
        """
        Calculate refund amount for a returned item.

        Args:
            conn: Database connection.
            sale_item_id: ID of the sale item.
            return_qty: Quantity being returned.

        Returns:
            Refund amount in cents (including proportional tax).
        """
        assert conn is not None
        assert isinstance(sale_item_id, int) and sale_item_id > 0
        assert isinstance(return_qty, int) and return_qty > 0

        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT unit_price, tax_amount, quantity FROM sale_items
            WHERE id = ?
            """,
            (sale_item_id,),
        )
        row = cursor.fetchone()

        if row is None:
            cursor.close()
            raise ValidationError(f"Sale item {sale_item_id} not found")

        unit_price = row["unit_price"]
        tax_amount = row["tax_amount"]
        original_qty = row["quantity"]

        # Calculate proportional tax
        tax_per_item = tax_amount / original_qty if original_qty > 0 else 0
        refund = (unit_price + tax_per_item) * return_qty

        cursor.close()
        return int(refund)

    def process_return(
        self,
        sale_id: int,
        items: List[ReturnItem],
        reason: str,
        user_id: int,
    ) -> ReturnResult:
        """
        Process a return atomically.

        Args:
            sale_id: Original sale ID.
            items: List of ReturnItem (sale_item_id, return_qty).
            reason: One of Defective/Wrong Size/Wrong Color/Changed Mind/Other.
            user_id: Cashier processing the return.

        Returns:
            ReturnResult with return_id, refund_amount, restocked_items.

        Raises:
            ValidationError: If return_qty > original sold qty.
            SaleNotFoundError: If sale doesn't exist or is already voided.
        """
        assert isinstance(sale_id, int) and sale_id > 0
        assert items is not None and len(items) > 0
        assert reason in self.VALID_REASONS
        assert isinstance(user_id, int) and user_id > 0

        def _process(conn: sqlite3.Connection) -> ReturnResult:
            cursor = conn.cursor()

            # Validate sale exists and is not voided
            cursor.execute(
                "SELECT id, status, customer_id, payment_type, total_amount FROM sales WHERE id = ?",
                (sale_id,),
            )
            sale_row = cursor.fetchone()

            if sale_row is None:
                cursor.close()
                raise SaleNotFoundError(f"Sale {sale_id} not found")

            if sale_row["status"] == "voided":
                cursor.close()
                raise SaleNotFoundError(f"Sale {sale_id} is voided")

            customer_id = sale_row["customer_id"]
            payment_type = sale_row["payment_type"]

            total_refund = 0
            restocked_items: List[Dict] = []

            # Process each return item
            for item in items:
                # Get original sale item
                cursor.execute(
                    """
                    SELECT si.*, v.id as variant_id, v.style_id
                    FROM sale_items si
                    JOIN variants v ON si.variant_id = v.id
                    WHERE si.id = ? AND si.sale_id = ?
                    """,
                    (item.sale_item_id, sale_id),
                )
                sale_item = cursor.fetchone()

                if sale_item is None:
                    cursor.close()
                    raise ValidationError(
                        f"Sale item {item.sale_item_id} not found in sale {sale_id}"
                    )

                original_qty = sale_item["quantity"]
                already_returned = sale_item["is_returned"] if "is_returned" in sale_item.keys() else 0

                # Check if already fully returned
                if already_returned:
                    cursor.close()
                    raise ValidationError(
                        f"Sale item {item.sale_item_id} already returned"
                    )

                # Validate return quantity
                if item.return_qty > original_qty:
                    cursor.close()
                    raise ValidationError(
                        f"Return quantity {item.return_qty} exceeds sold quantity {original_qty}"
                    )

                # Calculate refund for this item
                refund = self._calculate_refund_amount(
                    conn, item.sale_item_id, item.return_qty
                )
                total_refund += refund

                # Restock: increment variant quantity
                cursor.execute(
                    """
                    UPDATE variants SET quantity = quantity + ? WHERE id = ?
                    """,
                    (item.return_qty, sale_item["variant_id"]),
                )

                # Restock: increment batch quantity_remaining (reverse FIFO)
                batch_id = sale_item["batch_id"] if "batch_id" in sale_item.keys() else None
                if batch_id:
                    cursor.execute(
                        """
                        UPDATE batches SET quantity_remaining = quantity_remaining + ?
                        WHERE id = ?
                        """,
                        (item.return_qty, batch_id),
                    )

                # Mark sale item as returned (or partial)
                if item.return_qty >= original_qty:
                    cursor.execute(
                        "UPDATE sale_items SET is_returned = 1 WHERE id = ?",
                        (item.sale_item_id,),
                    )
                else:
                    # Partial return - keep is_returned = 0 but could track partial
                    pass

                restocked_items.append(
                    {
                        "variant_id": sale_item["variant_id"],
                        "quantity": item.return_qty,
                        "refund": refund,
                    }
                )

            # Update sale status if all items returned
            cursor.execute(
                """
                SELECT COUNT(*) as remaining FROM sale_items
                WHERE sale_id = ? AND is_returned = 0
                """,
                (sale_id,),
            )
            remaining = cursor.fetchone()["remaining"]

            new_status = "returned" if remaining == 0 else "partial_return"
            cursor.execute(
                "UPDATE sales SET status = ? WHERE id = ?",
                (new_status, sale_id),
            )

            # If credit sale, reduce customer total_due
            if payment_type == "credit" and customer_id is not None:
                cursor.execute(
                    """
                    UPDATE customers SET total_due = total_due - ? WHERE id = ?
                    """,
                    (total_refund, customer_id),
                )

            # Create return record
            return_date = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                """
                INSERT INTO returns (
                    sale_id, user_id, reason, total_refund, return_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    sale_id,
                    user_id,
                    reason,
                    total_refund,
                    return_date,
                    return_date,
                ),
            )
            return_id = cursor.lastrowid

            # Create return_items records
            for item in items:
                refund = self._calculate_refund_amount(
                    conn, item.sale_item_id, item.return_qty
                )
                cursor.execute(
                    """
                    INSERT INTO return_items (
                        return_id, sale_item_id, quantity, refund_amount
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (return_id, item.sale_item_id, item.return_qty, refund),
                )

            cursor.close()

            return ReturnResult(
                return_id=return_id,
                refund_amount=total_refund,
                restocked_items=restocked_items,
                return_date=return_date,
            )

        with self.cm.execute_transaction() as conn:
            return _process(conn)

    def process_exchange(
        self,
        original_sale_id: int,
        original_item_id: int,
        new_variant_id: int,
        new_qty: int,
        reason: str,
        user_id: int,
    ) -> ExchangeResult:
        """
        Process an exchange: return old variant, sell new variant.

        Calculates price difference and handles:
        - Difference = 0: Even exchange, no payment
        - Difference > 0: Customer pays difference (cash/credit)
        - Difference < 0: Refund difference or store credit

        Args:
            original_sale_id: ID of original sale.
            original_item_id: ID of item being exchanged.
            new_variant_id: ID of new variant.
            new_qty: Quantity of new variant.
            reason: Exchange reason.
            user_id: Cashier processing the exchange.

        Returns:
            ExchangeResult with exchange details.

        Raises:
            ValidationError: If exchange is invalid.
            SaleNotFoundError: If original sale not found.
            InsufficientStockError: If new variant has insufficient stock.
        """
        assert isinstance(original_sale_id, int) and original_sale_id > 0
        assert isinstance(original_item_id, int) and original_item_id > 0
        assert isinstance(new_variant_id, int) and new_variant_id > 0
        assert isinstance(new_qty, int) and new_qty > 0
        assert reason in self.VALID_REASONS
        assert isinstance(user_id, int) and user_id > 0

        from services.inventory_service import deduct_stock

        def _process(conn: sqlite3.Connection) -> ExchangeResult:
            cursor = conn.cursor()

            # Get original sale item details
            cursor.execute(
                """
                SELECT si.*, v.style_id, v.base_price as old_price
                FROM sale_items si
                JOIN variants v ON si.variant_id = v.id
                WHERE si.id = ? AND si.sale_id = ?
                """,
                (original_item_id, original_sale_id),
            )
            old_item = cursor.fetchone()

            if old_item is None:
                cursor.close()
                raise SaleNotFoundError(
                    f"Sale item {original_item_id} not found in sale {original_sale_id}"
                )

            if "is_returned" in old_item.keys() and old_item["is_returned"]:
                cursor.close()
                raise ValidationError(f"Sale item {original_item_id} already returned")

            old_variant_id = old_item["variant_id"]
            old_qty = old_item["quantity"]
            old_unit_price = old_item["unit_price"]

            # Get new variant details
            cursor.execute(
                """
                SELECT v.*, s.id as style_id FROM variants v
                JOIN styles s ON v.style_id = s.id
                WHERE v.id = ?
                """,
                (new_variant_id,),
            )
            new_variant = cursor.fetchone()

            if new_variant is None:
                cursor.close()
                raise ValidationError(f"Variant {new_variant_id} not found")

            # Check new variant stock
            if new_variant["quantity"] < new_qty:
                cursor.close()
                raise ValidationError(
                    f"Insufficient stock for variant {new_variant_id}"
                )

            # Verify same style (exchange within same product)
            if new_variant["style_id"] != old_item["style_id"]:
                cursor.close()
                raise ValidationError(
                    "Can only exchange within the same style/product"
                )

            new_unit_price = new_variant["base_price"]

            # Calculate price difference
            old_total = old_unit_price * old_qty
            new_total = new_unit_price * new_qty
            price_diff = new_total - old_total

            # Restock old variant (reverse FIFO)
            cursor.execute(
                "UPDATE variants SET quantity = quantity + ? WHERE id = ?",
                (old_qty, old_variant_id),
            )

            # Restock old batch
            batch_id = old_item["batch_id"] if "batch_id" in old_item.keys() else None
            if batch_id:
                cursor.execute(
                    "UPDATE batches SET quantity_remaining = quantity_remaining + ? WHERE id = ?",
                    (old_qty, batch_id),
                )

            # Deduct new variant stock (FIFO)
            if not deduct_stock(conn, new_variant_id, new_qty):
                cursor.close()
                raise ValidationError(
                    f"Failed to deduct stock for variant {new_variant_id}"
                )

            # Get new batch for tracking
            cursor.execute(
                """
                SELECT id FROM batches
                WHERE variant_id = ? AND quantity_remaining > 0
                ORDER BY date_received ASC LIMIT 1
                """,
                (new_variant_id,),
            )
            new_batch_row = cursor.fetchone()
            new_batch_id = new_batch_row[0] if new_batch_row else None

            # Mark old item as returned
            cursor.execute(
                "UPDATE sale_items SET is_returned = 1 WHERE id = ?",
                (original_item_id,),
            )

            # Create new sale item for the exchange
            new_tax = round(new_total * 17 / 100)  # Default 17% GST
            new_item_total = new_total + new_tax

            cursor.execute(
                """
                INSERT INTO sale_items (
                    sale_id, variant_id, batch_id, quantity,
                    unit_price, tax_amount, total_price, is_returned
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    original_sale_id,
                    new_variant_id,
                    new_batch_id,
                    new_qty,
                    new_unit_price,
                    new_tax,
                    new_item_total,
                ),
            )

            # Create exchange record
            exchange_date = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                """
                INSERT INTO exchanges (
                    sale_id, old_item_id, new_variant_id, quantity,
                    price_difference, reason, user_id, exchange_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    original_sale_id,
                    original_item_id,
                    new_variant_id,
                    new_qty,
                    price_diff,
                    reason,
                    user_id,
                    exchange_date,
                    exchange_date,
                ),
            )
            exchange_id = cursor.lastrowid

            cursor.close()

            return ExchangeResult(
                exchange_id=exchange_id,
                old_variant_id=old_variant_id,
                new_variant_id=new_variant_id,
                price_difference=price_diff,
                payment_required=price_diff > 0,
                refund_required=price_diff < 0,
            )

        with self.cm.execute_transaction() as conn:
            return _process(conn)

    def get_returns_by_date(
        self, from_date: str, to_date: str
    ) -> List[Dict]:
        """
        Get returns within a date range.

        Args:
            from_date: Start date (ISO 8601 format).
            to_date: End date (ISO 8601 format).

        Returns:
            List of return records with details.
        """
        assert isinstance(from_date, str) and len(from_date) > 0
        assert isinstance(to_date, str) and len(to_date) > 0

        conn = self.cm.get_read_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT r.*, u.name as user_name, s.invoice_number
                FROM returns r
                JOIN users u ON r.user_id = u.id
                JOIN sales s ON r.sale_id = s.id
                WHERE r.return_date BETWEEN ? AND ?
                ORDER BY r.return_date DESC
                """,
                (from_date, to_date),
            )
            rows = cursor.fetchall()
            cursor.close()

            return [dict(row) for row in rows]
        finally:
            conn.close()
