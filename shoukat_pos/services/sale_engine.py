"""
Sale processing engine with ACID guarantees for Shoukat Sons Garments POS.

Handles atomic sale transactions, invoice generation, held sales, voiding,
and credit limit validation. All monetary values are INTEGER cents.
"""

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from database.connection import ConnectionManager
from database.models import Customer, Sale, SaleItem
from services.inventory_service import deduct_stock


@dataclass
class CartItem:
    """Represents an item in the shopping cart."""

    variant_id: int
    quantity: int
    unit_price: int  # cents
    tax_rate: float
    discount: int = 0  # cents


@dataclass
class SaleResult:
    """Result of a processed sale."""

    sale_id: int
    invoice_number: str
    subtotal: int
    tax_amount: int
    discount_amount: int
    grand_total: int
    change_due: int
    due_amount: int


@dataclass
class HeldSale:
    """Represents a held sale for later resumption."""

    id: int
    customer_id: Optional[int]
    user_id: int
    items: List[CartItem]
    created_at: str


class InsufficientStockError(Exception):
    """Raised when stock is insufficient for a sale."""

    pass


class CreditLimitExceededError(Exception):
    """Raised when credit sale exceeds customer limit."""

    pass


class ValidationError(Exception):
    """Raised when sale data fails validation."""

    pass


class SaleEngine:
    """
    Core sale processing engine with ACID transaction guarantees.

    Handles atomic sale processing, invoice generation, held sales,
    voiding, and credit limit validation.
    """

    def __init__(self, connection_manager: ConnectionManager) -> None:
        """
        Initialize the SaleEngine.

        Args:
            connection_manager: Database connection manager instance.
        """
        assert connection_manager is not None
        self.cm = connection_manager

    def _generate_invoice_number(self, conn: sqlite3.Connection, sale_date: str) -> str:
        """
        Generate unique invoice number for a given date.

        Format: INV-YYYYMMDD-NNNN where NNNN is sequential per day.

        Args:
            conn: Database connection within transaction.
            sale_date: ISO 8601 date string.

        Returns:
            Generated invoice number.
        """
        assert conn is not None
        assert isinstance(sale_date, str) and len(sale_date) > 0

        cursor = conn.cursor()
        date_part = sale_date[:10].replace("-", "")  # YYYYMMDD
        prefix = f"INV-{date_part}-"

        # Get max sequence for today using LIKE with % wildcard
        cursor.execute(
            """
            SELECT MAX(CAST(SUBSTR(invoice_number, ?) AS INTEGER)) as max_seq
            FROM sales
            WHERE invoice_number LIKE ?
            """,
            (len(prefix) + 1, f"{prefix}%"),
        )
        result = cursor.fetchone()
        max_seq = result[0] if result and result[0] else 0
        next_seq = max_seq + 1

        cursor.close()
        return f"{prefix}{next_seq:04d}"

    def _validate_cart(self, cart: List[CartItem]) -> None:
        """
        Validate cart data before processing.

        Args:
            cart: List of CartItem to validate.

        Raises:
            ValidationError: If cart is invalid.
        """
        assert cart is not None

        if not cart or len(cart) == 0:
            raise ValidationError("Cart cannot be empty")

        for i, item in enumerate(cart):
            if item.quantity <= 0:
                raise ValidationError(f"Item {i}: quantity must be positive")
            if item.unit_price <= 0:
                raise ValidationError(f"Item {i}: unit_price must be positive")
            if item.tax_rate < 0:
                raise ValidationError(f"Item {i}: tax_rate cannot be negative")

    def _check_stock_availability(
        self, conn: sqlite3.Connection, cart: List[CartItem]
    ) -> None:
        """
        Check if all cart items have sufficient stock.

        Args:
            conn: Database connection.
            cart: List of CartItem to check.

        Raises:
            InsufficientStockError: If any item has insufficient stock.
        """
        assert conn is not None
        assert cart is not None

        cursor = conn.cursor()
        for item in cart:
            cursor.execute(
                "SELECT quantity FROM variants WHERE id = ?", (item.variant_id,)
            )
            row = cursor.fetchone()
            if row is None or row[0] < item.quantity:
                cursor.close()
                raise InsufficientStockError(
                    f"Insufficient stock for variant {item.variant_id}"
                )
        cursor.close()

    def _calculate_totals(
        self, cart: List[CartItem]
    ) -> Tuple[int, int, int, int]:
        """
        Calculate sale totals from cart items.

        Args:
            cart: List of CartItem.

        Returns:
            Tuple of (subtotal, tax_amount, discount_amount, grand_total) in cents.
        """
        assert cart is not None

        subtotal = 0
        tax_amount = 0
        discount_amount = 0

        for item in cart:
            line_total = item.unit_price * item.quantity
            subtotal += line_total
            tax_amount += round(line_total * item.tax_rate / 100)
            discount_amount += item.discount

        grand_total = subtotal + tax_amount - discount_amount
        return subtotal, tax_amount, discount_amount, grand_total

    def process_sale(
        self,
        cart: List[CartItem],
        customer_id: Optional[int],
        payment_type: str,
        paid_amount: int,
        user_id: int,
        sale_date: Optional[str] = None,
    ) -> SaleResult:
        """
        Process a complete sale atomically.

        Args:
            cart: List of CartItem (variant_id, qty, unit_price, tax_rate).
            customer_id: None for walk-in customer.
            payment_type: "cash", "credit", or "split".
            paid_amount: Amount paid in cents (for cash/split).
            user_id: Cashier processing the sale.
            sale_date: ISO 8601 date string, defaults to today.

        Returns:
            SaleResult with sale_id, invoice_number, totals, change_due.

        Raises:
            InsufficientStockError: If any item has insufficient stock.
            CreditLimitExceededError: If credit sale exceeds customer limit.
            ValidationError: If cart is empty or totals don't match.
        """
        assert cart is not None
        assert payment_type in ("cash", "credit", "split")
        assert isinstance(paid_amount, int) and paid_amount >= 0
        assert isinstance(user_id, int) and user_id > 0

        if sale_date is None:
            sale_date = datetime.now(timezone.utc).isoformat()

        # Validate cart
        self._validate_cart(cart)

        def _process(conn: sqlite3.Connection) -> SaleResult:
            cursor = conn.cursor()

            # Check stock availability
            self._check_stock_availability(conn, cart)

            # Calculate totals
            subtotal, tax_amount, discount_amount, grand_total = self._calculate_totals(
                cart
            )

            # Handle payment type specifics
            due_amount = 0
            change_due = 0

            if payment_type == "cash":
                change_due = paid_amount - grand_total
                if change_due < 0:
                    raise ValidationError("Paid amount less than grand total")
            elif payment_type == "credit":
                # Validate customer exists and credit limit
                if customer_id is None:
                    raise ValidationError("Customer required for credit sale")

                cursor.execute(
                    "SELECT total_due, credit_limit FROM customers WHERE id = ?",
                    (customer_id,),
                )
                cust_row = cursor.fetchone()
                if cust_row is None:
                    cursor.close()
                    raise ValidationError(f"Customer {customer_id} not found")

                current_due = cust_row[0]
                credit_limit = cust_row[1]
                new_due = grand_total  # Full amount on credit

                if current_due + new_due > credit_limit:
                    cursor.close()
                    raise CreditLimitExceededError(
                        f"Credit limit exceeded. Current: {current_due}, "
                        f"New: {new_due}, Limit: {credit_limit}"
                    )

                due_amount = new_due
            elif payment_type == "split":
                # For split, paid_amount is cash portion
                due_amount = max(0, grand_total - paid_amount)
                change_due = 0 if due_amount > 0 else paid_amount - grand_total

            # Generate invoice number
            invoice_number = self._generate_invoice_number(conn, sale_date)

            # Create sales record
            cursor.execute(
                """
                INSERT INTO sales (
                    invoice_number, customer_id, user_id, sale_date,
                    subtotal, tax_amount, discount_amount, total_amount,
                    paid_amount, due_amount, payment_type, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed', ?)
                """,
                (
                    invoice_number,
                    customer_id,
                    user_id,
                    sale_date,
                    subtotal,
                    tax_amount,
                    discount_amount,
                    grand_total,
                    paid_amount,
                    due_amount,
                    payment_type,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            sale_id = cursor.lastrowid

            # Process each cart item
            for item in cart:
                # Deduct stock (FIFO)
                if not deduct_stock(conn, item.variant_id, item.quantity):
                    cursor.close()
                    raise InsufficientStockError(
                        f"Failed to deduct stock for variant {item.variant_id}"
                    )

                # Get batch_id for this item (first batch with remaining stock)
                cursor.execute(
                    """
                    SELECT id FROM batches
                    WHERE variant_id = ? AND quantity_remaining > 0
                    ORDER BY date_received ASC LIMIT 1
                    """,
                    (item.variant_id,),
                )
                batch_row = cursor.fetchone()
                batch_id = batch_row[0] if batch_row else None

                # Calculate item tax
                item_tax = round(
                    item.unit_price * item.quantity * item.tax_rate / 100
                )
                item_total = (
                    item.unit_price * item.quantity + item_tax - item.discount
                )

                # Create sale_items record
                cursor.execute(
                    """
                    INSERT INTO sale_items (
                        sale_id, variant_id, batch_id, quantity,
                        unit_price, tax_amount, total_price, is_returned
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                    """,
                    (
                        sale_id,
                        item.variant_id,
                        batch_id,
                        item.quantity,
                        item.unit_price,
                        item_tax,
                        item_total,
                    ),
                )

            # Update customer total_due if credit sale
            if payment_type == "credit" and customer_id is not None:
                cursor.execute(
                    "UPDATE customers SET total_due = total_due + ? WHERE id = ?",
                    (due_amount, customer_id),
                )

            cursor.close()

            return SaleResult(
                sale_id=sale_id,
                invoice_number=invoice_number,
                subtotal=subtotal,
                tax_amount=tax_amount,
                discount_amount=discount_amount,
                grand_total=grand_total,
                change_due=change_due,
                due_amount=due_amount,
            )

        with self.cm.execute_transaction() as conn:
            return _process(conn)

    def hold_sale(
        self, cart: List[CartItem], customer_id: Optional[int], user_id: int
    ) -> int:
        """
        Save a cart as a held sale for later resumption.

        Args:
            cart: List of CartItem in the held sale.
            customer_id: Optional customer for the held sale.
            user_id: User holding the sale.

        Returns:
            held_sale_id for later retrieval.
        """
        assert cart is not None
        assert isinstance(user_id, int) and user_id > 0

        import json

        def _hold(conn: sqlite3.Connection) -> int:
            cursor = conn.cursor()

            # Serialize cart items to JSON
            cart_data = [
                {
                    "variant_id": item.variant_id,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "tax_rate": item.tax_rate,
                    "discount": item.discount,
                }
                for item in cart
            ]
            cart_json = json.dumps(cart_data)

            cursor.execute(
                """
                INSERT INTO held_sales (customer_id, user_id, cart_data, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    customer_id,
                    user_id,
                    cart_json,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            held_sale_id = cursor.lastrowid
            cursor.close()
            return held_sale_id

        with self.cm.execute_transaction() as conn:
            return _hold(conn)

    def resume_sale(self, held_sale_id: int) -> HeldSale:
        """
        Retrieve a held sale by ID.

        Args:
            held_sale_id: ID of the held sale to retrieve.

        Returns:
            HeldSale with cart items.

        Raises:
            ValueError: If held sale not found.
        """
        assert isinstance(held_sale_id, int) and held_sale_id > 0

        import json

        conn = self.cm.get_read_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, customer_id, user_id, cart_data, created_at
                FROM held_sales
                WHERE id = ? AND status = 'held'
                """,
                (held_sale_id,),
            )
            row = cursor.fetchone()
            cursor.close()

            if row is None:
                raise ValueError(f"Held sale {held_sale_id} not found")

            cart_data = json.loads(row["cart_data"])
            items = [
                CartItem(
                    variant_id=item["variant_id"],
                    quantity=item["quantity"],
                    unit_price=item["unit_price"],
                    tax_rate=item["tax_rate"],
                    discount=item.get("discount", 0),
                )
                for item in cart_data
            ]

            return HeldSale(
                id=row["id"],
                customer_id=row["customer_id"],
                user_id=row["user_id"],
                items=items,
                created_at=row["created_at"],
            )
        finally:
            conn.close()

    def void_sale(self, sale_id: int, reason: str, user_id: int) -> None:
        """
        Void a completed sale. Restocks all items. Logs to audit.

        Args:
            sale_id: ID of the sale to void.
            reason: Reason for voiding.
            user_id: User voiding the sale.

        Raises:
            ValueError: If sale not found or already voided.
        """
        assert isinstance(sale_id, int) and sale_id > 0
        assert isinstance(reason, str) and len(reason) > 0
        assert isinstance(user_id, int) and user_id > 0

        def _void(conn: sqlite3.Connection) -> None:
            cursor = conn.cursor()

            # Check sale exists and is not already voided
            cursor.execute(
                "SELECT status, total_amount, customer_id, payment_type FROM sales WHERE id = ?",
                (sale_id,),
            )
            row = cursor.fetchone()
            if row is None:
                cursor.close()
                raise ValueError(f"Sale {sale_id} not found")
            if row["status"] == "voided":
                cursor.close()
                raise ValueError(f"Sale {sale_id} already voided")

            # Get sale items for restocking
            cursor.execute(
                "SELECT variant_id, quantity FROM sale_items WHERE sale_id = ?",
                (sale_id,),
            )
            items = cursor.fetchall()

            # Restock variants
            for item in items:
                cursor.execute(
                    "UPDATE variants SET quantity = quantity + ? WHERE id = ?",
                    (item["quantity"], item["variant_id"]),
                )
                # Also restore batch quantities
                cursor.execute(
                    """
                    UPDATE batches SET quantity_remaining = quantity_remaining + ?
                    WHERE variant_id = ?
                    """,
                    (item["quantity"], item["variant_id"]),
                )

            # Update customer total_due if it was a credit sale
            if row["payment_type"] == "credit" and row["customer_id"]:
                cursor.execute(
                    "UPDATE customers SET total_due = total_due - ? WHERE id = ?",
                    (row["total_amount"], row["customer_id"]),
                )

            # Mark sale as voided
            cursor.execute(
                "UPDATE sales SET status = 'voided' WHERE id = ?", (sale_id,)
            )

            # Log audit entry
            cursor.execute(
                """
                INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, user_id, hmac_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "sales",
                    sale_id,
                    "VOIDED",
                    f'{{"status": "completed", "reason": "{reason}"}}',
                    '{"status": "voided"}',
                    user_id,
                    "",
                ),
            )

            cursor.close()

        with self.cm.execute_transaction() as conn:
            _void(conn)

    def get_sale_by_invoice(self, invoice_number: str) -> Optional[Sale]:
        """
        Look up a sale by invoice number.

        Args:
            invoice_number: Invoice number to search for.

        Returns:
            Sale object if found, None otherwise.
        """
        assert isinstance(invoice_number, str) and len(invoice_number) > 0

        conn = self.cm.get_read_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM sales WHERE invoice_number = ?", (invoice_number,)
            )
            row = cursor.fetchone()
            cursor.close()

            if row:
                return Sale.from_row(row)
            return None
        finally:
            conn.close()
