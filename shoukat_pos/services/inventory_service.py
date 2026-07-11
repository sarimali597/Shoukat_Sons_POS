"""
Inventory service for stock management with FIFO batch tracking.

Handles stock deduction (FIFO order), restocking with new batches,
stock valuation, reorder suggestions, and manual adjustments.
All monetary values are stored as INTEGER cents.
"""

import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional

from database.models import Batch, Variant
from database.queries import (
    CREATE_BATCH,
    GET_BATCHES_BY_VARIANT,
    GET_BATCHES_WITH_STOCK,
    UPDATE_BATCH_REMAINING,
    UPDATE_VARIANT_QUANTITY,
)


class InventoryService:
    """Service class for inventory operations."""
    
    def __init__(self, connection_manager=None):
        """Initialize inventory service."""
        self.cm = connection_manager
    
    def get_low_stock_variants(self, conn=None):
        """Get variants at or below reorder point.
        
        Args:
            conn: Optional database connection. If not provided, uses connection manager.
            
        Returns:
            List of low-stock Variant objects.
        """
        if conn is None and self.cm:
            with self.cm.get_write_connection() as conn:
                return self._get_low_stock(conn)
        elif conn:
            return self._get_low_stock(conn)
        else:
            return []
    
    def _get_low_stock(self, conn):
        """Internal method to get low stock variants."""
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT v.*, s.name as style_name
            FROM variants v
            JOIN styles s ON v.style_id = s.id
            WHERE v.quantity <= v.reorder_point
            ORDER BY v.quantity
            """
        )
        rows = cursor.fetchall()
        cursor.close()
        from database.models import Variant
        return [Variant.from_row(row) for row in rows]


def deduct_stock(conn: sqlite3.Connection, variant_id: int, qty: int) -> bool:
    """
    Deduct stock from variant and its batches in FIFO order.

    Args:
        conn: Database connection.
        variant_id: Variant to deduct from.
        qty: Quantity to deduct.

    Returns:
        True if sufficient stock exists and deduction succeeded.
    """
    assert conn is not None
    assert isinstance(variant_id, int) and variant_id > 0
    assert isinstance(qty, int) and qty > 0

    cursor = conn.cursor()

    # Check total available stock
    cursor.execute("SELECT quantity FROM variants WHERE id = ?", (variant_id,))
    row = cursor.fetchone()
    if row is None or row[0] < qty:
        cursor.close()
        return False

    # Get batches with remaining stock in FIFO order (oldest first)
    cursor.execute(
        """
        SELECT id, quantity_remaining FROM batches 
        WHERE variant_id = ? AND quantity_remaining > 0 
        ORDER BY date_received ASC
        """,
        (variant_id,),
    )
    batches = cursor.fetchall()

    remaining_to_deduct = qty
    for batch in batches:
        if remaining_to_deduct <= 0:
            break

        batch_id, batch_remaining = batch
        deduct_from_batch = min(remaining_to_deduct, batch_remaining)

        # Update batch remaining
        cursor.execute(UPDATE_BATCH_REMAINING, (deduct_from_batch, batch_id))

        remaining_to_deduct -= deduct_from_batch

    # Update variant quantity
    cursor.execute(UPDATE_VARIANT_QUANTITY, (-qty, variant_id))

    cursor.close()

    return True


def restock_variant(
    conn: sqlite3.Connection,
    variant_id: int,
    qty: int,
    purchase_price: int,
    secret_code: str,
    batch_data: Dict,
) -> None:
    """
    Add stock to a variant by creating a new batch record.

    Args:
        conn: Database connection.
        variant_id: Variant to restock.
        qty: Quantity to add.
        purchase_price: Cost price in cents.
        secret_code: Encoded purchase price.
        batch_data: Additional batch info (vendor_id, bilty_no, bill_no, etc.).
    """
    assert conn is not None
    assert isinstance(variant_id, int) and variant_id > 0
    assert isinstance(qty, int) and qty > 0
    assert isinstance(purchase_price, int) and purchase_price > 0
    assert isinstance(secret_code, str) and len(secret_code) > 0
    assert isinstance(batch_data, dict)

    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()

    # Create new batch
    cursor.execute(
        CREATE_BATCH,
        (
            variant_id,
            purchase_price,
            secret_code,
            qty,
            qty,  # quantity_remaining starts equal to received
            batch_data.get("vendor_id"),
            batch_data.get("bilty_no"),
            batch_data.get("bill_no"),
            batch_data.get("date_received", now),
            now,
        ),
    )

    # Update variant quantity
    cursor.execute(UPDATE_VARIANT_QUANTITY, (qty, variant_id))

    conn.commit()
    cursor.close()


def get_stock_valuation(conn: sqlite3.Connection) -> Dict[str, int]:
    """
    Return total inventory value at cost and at sale price.

    Args:
        conn: Database connection.

    Returns:
        Dict with 'cost_value' and 'sale_value' in cents.
    """
    assert conn is not None

    cursor = conn.cursor()

    # Calculate cost value from batches
    cursor.execute(
        """
        SELECT SUM(b.quantity_remaining * b.purchase_price) as cost_value
        FROM batches b
        WHERE b.quantity_remaining > 0
        """
    )
    cost_row = cursor.fetchone()
    cost_value = cost_row[0] if cost_row and cost_row[0] else 0

    # Calculate sale value from variants
    cursor.execute(
        """
        SELECT SUM(v.quantity * s.base_sale_price) as sale_value
        FROM variants v
        JOIN styles s ON v.style_id = s.id
        WHERE v.quantity > 0
        """
    )
    sale_row = cursor.fetchone()
    sale_value = sale_row[0] if sale_row and sale_row[0] else 0

    cursor.close()

    return {"cost_value": cost_value, "sale_value": sale_value}


def get_reorder_suggestions(conn: sqlite3.Connection) -> List[Dict]:
    """
    List variants below reorder_point with recommended order quantities.

    Args:
        conn: Database connection.

    Returns:
        List of dicts with variant info and suggested order quantity.
    """
    assert conn is not None

    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT v.*, s.name as style_name, s.style_code
        FROM variants v
        JOIN styles s ON v.style_id = s.id
        WHERE v.quantity <= v.reorder_point
        ORDER BY v.quantity ASC
        """
    )
    rows = cursor.fetchall()
    cursor.close()

    suggestions = []
    for row in rows:
        # Suggest ordering enough to reach 2x reorder point
        current = row["quantity"]
        target = row["reorder_point"] * 2
        suggested_qty = max(target - current, row["reorder_point"])

        suggestions.append(
            {
                "variant_id": row["id"],
                "style_name": row["style_name"],
                "style_code": row["style_code"],
                "size": row["size"],
                "color": row["color"],
                "barcode": row["barcode"],
                "current_quantity": current,
                "reorder_point": row["reorder_point"],
                "suggested_order_quantity": suggested_qty,
            }
        )

    return suggestions


def adjust_stock(
    conn: sqlite3.Connection,
    variant_id: int,
    new_qty: int,
    reason: str,
    user_id: int,
) -> None:
    """
    Manual stock adjustment after physical count.

    Args:
        conn: Database connection.
        variant_id: Variant to adjust.
        new_qty: New total quantity after adjustment.
        reason: Reason for adjustment (e.g., "Physical count", "Damaged").
        user_id: User performing the adjustment.
    """
    assert conn is not None
    assert isinstance(variant_id, int) and variant_id > 0
    assert isinstance(new_qty, int) and new_qty >= 0
    assert isinstance(reason, str) and len(reason) > 0
    assert isinstance(user_id, int) and user_id > 0

    cursor = conn.cursor()

    # Get current quantity
    cursor.execute("SELECT quantity FROM variants WHERE id = ?", (variant_id,))
    row = cursor.fetchone()
    if row is None:
        cursor.close()
        raise ValueError(f"Variant {variant_id} not found")

    old_qty = row[0]
    delta = new_qty - old_qty

    # Update variant quantity directly (not via delta)
    cursor.execute("UPDATE variants SET quantity = ? WHERE id = ?", (new_qty, variant_id))

    # Log audit entry
    cursor.execute(
        """
        INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, user_id, hmac_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "variants",
            variant_id,
            "ADJUSTMENT",
            f'{{"quantity": {old_qty}, "reason": "{reason}"}}',
            f'{{"quantity": {new_qty}}}',
            user_id,
            "",  # HMAC hash would be computed by audit_logger module
        ),
    )

    conn.commit()
    cursor.close()
