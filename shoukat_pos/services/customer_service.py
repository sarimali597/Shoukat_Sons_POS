"""
Customer service for Shoukat Sons Garments POS.

Handles customer CRUD operations, credit ledger management,
payment recording, and credit limit validation.
All monetary values are INTEGER cents.
"""

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

from database.models import Customer


@dataclass
class LedgerEntry:
    """Represents an entry in the customer ledger."""

    id: int
    date: str
    description: str
    debit: int  # Amount owed (sales)
    credit: int  # Amount paid
    balance: int  # Running balance
    reference: str  # Invoice number or payment reference


def create_customer(
    conn: sqlite3.Connection,
    name: str,
    phone: str,
    address: str = "",
    credit_limit: int = 0,
) -> int:
    """
    Create a new customer.

    Args:
        conn: Database connection.
        name: Customer name.
        phone: Phone number (unique).
        address: Optional address.
        credit_limit: Credit limit in cents (default 0).

    Returns:
        customer_id of the created customer.
    """
    assert conn is not None
    assert isinstance(name, str) and len(name) > 0
    assert isinstance(phone, str) and len(phone) > 0
    assert isinstance(address, str)
    assert isinstance(credit_limit, int) and credit_limit >= 0

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO customers (name, phone, address, total_due, credit_limit, created_at)
        VALUES (?, ?, ?, 0, ?, ?)
        """,
        (name, phone, address, credit_limit, datetime.now(timezone.utc).isoformat()),
    )
    customer_id = cursor.lastrowid
    conn.commit()
    cursor.close()

    return customer_id


def get_customer_by_phone(
    conn: sqlite3.Connection, phone: str
) -> Optional[Customer]:
    """
    Look up a customer by phone number.

    Args:
        conn: Database connection.
        phone: Phone number to search for.

    Returns:
        Customer object if found, None otherwise.
    """
    assert conn is not None
    assert isinstance(phone, str) and len(phone) > 0

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customers WHERE phone = ?", (phone,))
    row = cursor.fetchone()
    cursor.close()

    if row:
        return Customer.from_row(row)
    return None


def get_customer_by_id(conn: sqlite3.Connection, customer_id: int) -> Optional[Customer]:
    """
    Look up a customer by ID.

    Args:
        conn: Database connection.
        customer_id: Customer ID to search for.

    Returns:
        Customer object if found, None otherwise.
    """
    assert conn is not None
    assert isinstance(customer_id, int) and customer_id > 0

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
    row = cursor.fetchone()
    cursor.close()

    if row:
        return Customer.from_row(row)
    return None


def get_customer_ledger(
    conn: sqlite3.Connection, customer_id: int
) -> List[LedgerEntry]:
    """
    Return full running ledger: all credit sales and payments, oldest first.

    Args:
        conn: Database connection.
        customer_id: Customer ID to get ledger for.

    Returns:
        List of LedgerEntry with running balance.
    """
    assert conn is not None
    assert isinstance(customer_id, int) and customer_id > 0

    cursor = conn.cursor()

    # Get all credit sales for this customer
    cursor.execute(
        """
        SELECT id, invoice_number as reference, sale_date as date, 
               total_amount as debit, 0 as credit, 'Credit Sale' as description
        FROM sales
        WHERE customer_id = ? AND payment_type = 'credit' AND status != 'voided'
        UNION ALL
        SELECT id, payment_ref as reference, payment_date as date,
               0 as debit, amount as credit, 'Payment Received' as description
        FROM credit_payments
        WHERE customer_id = ?
        ORDER BY date ASC
        """,
        (customer_id, customer_id),
    )
    rows = cursor.fetchall()
    cursor.close()

    # Calculate running balance
    ledger: List[LedgerEntry] = []
    running_balance = 0

    for row in rows:
        debit = row["debit"] if row["debit"] else 0
        credit = row["credit"] if row["credit"] else 0
        running_balance += debit - credit

        ledger.append(
            LedgerEntry(
                id=row["id"],
                date=row["date"],
                description=row["description"],
                debit=debit,
                credit=credit,
                balance=running_balance,
                reference=row["reference"],
            )
        )

    return ledger


def add_credit_payment(
    conn: sqlite3.Connection,
    customer_id: int,
    amount: int,
    payment_method: str,
    notes: str = "",
    user_id: int = 0,
) -> None:
    """
    Record a payment against customer balance. Updates total_due.

    Args:
        conn: Database connection.
        customer_id: Customer making the payment.
        amount: Payment amount in cents.
        payment_method: Method of payment (cash, card, etc.).
        notes: Optional notes about the payment.
        user_id: User recording the payment.
    """
    assert conn is not None
    assert isinstance(customer_id, int) and customer_id > 0
    assert isinstance(amount, int) and amount > 0
    assert isinstance(payment_method, str) and len(payment_method) > 0
    assert isinstance(notes, str)
    assert isinstance(user_id, int) and user_id >= 0

    cursor = conn.cursor()

    # Check customer exists
    cursor.execute("SELECT id FROM customers WHERE id = ?", (customer_id,))
    if cursor.fetchone() is None:
        cursor.close()
        raise ValueError(f"Customer {customer_id} not found")

    # Insert payment record
    cursor.execute(
        """
        INSERT INTO credit_payments (
            customer_id, amount, payment_method, notes, user_id, payment_date
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            customer_id,
            amount,
            payment_method,
            notes,
            user_id,
            datetime.now(timezone.utc).isoformat(),
        ),
    )

    # Update customer total_due
    cursor.execute(
        "UPDATE customers SET total_due = total_due - ? WHERE id = ?",
        (amount, customer_id),
    )

    conn.commit()
    cursor.close()


def get_customer_due(conn: sqlite3.Connection, customer_id: int) -> int:
    """
    Get the current amount due from a customer.

    Args:
        conn: Database connection.
        customer_id: Customer ID to check.

    Returns:
        Amount due in cents.
    """
    assert conn is not None
    assert isinstance(customer_id, int) and customer_id > 0

    cursor = conn.cursor()
    cursor.execute("SELECT total_due FROM customers WHERE id = ?", (customer_id,))
    row = cursor.fetchone()
    cursor.close()

    return row[0] if row else 0


def get_all_customers(conn: sqlite3.Connection) -> List[Customer]:
    """
    Get all customers ordered by name.

    Args:
        conn: Database connection.

    Returns:
        List of all Customer objects.
    """
    assert conn is not None

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customers ORDER BY name ASC")
    rows = cursor.fetchall()
    cursor.close()

    return [Customer.from_row(row) for row in rows]


def update_customer(
    conn: sqlite3.Connection,
    customer_id: int,
    name: Optional[str] = None,
    phone: Optional[str] = None,
    address: Optional[str] = None,
    credit_limit: Optional[int] = None,
) -> None:
    """
    Update customer information.

    Args:
        conn: Database connection.
        customer_id: Customer ID to update.
        name: New name (optional).
        phone: New phone (optional).
        address: New address (optional).
        credit_limit: New credit limit (optional).
    """
    assert conn is not None
    assert isinstance(customer_id, int) and customer_id > 0

    updates = []
    params: List = []

    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if phone is not None:
        updates.append("phone = ?")
        params.append(phone)
    if address is not None:
        updates.append("address = ?")
        params.append(address)
    if credit_limit is not None:
        updates.append("credit_limit = ?")
        params.append(credit_limit)

    if not updates:
        return

    params.append(customer_id)
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE customers SET {', '.join(updates)} WHERE id = ?", params
    )
    conn.commit()
    cursor.close()
