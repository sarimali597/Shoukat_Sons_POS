"""
Product service for managing styles, variants, and batches.

Handles style creation with auto-generated codes, variant matrix generation,
barcode creation, secret code encoding, and product search operations.
All monetary values are stored as INTEGER cents.
"""

import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from config import SECRET_CODE_MAPPING
from database.models import Batch, Style, Variant
from database.queries import (
    CREATE_BATCH,
    CREATE_STYLE,
    CREATE_VARIANT,
    DELETE_STYLE,
    GET_VARIANTS_BY_STYLE,
    GET_VARIANT_BY_BARCODE,
    UPDATE_VARIANT_QUANTITY,
)


class ProductService:
    """Service class for product operations."""
    
    def __init__(self, connection_manager=None):
        """Initialize product service."""
        self.cm = connection_manager


def _generate_style_code(conn: sqlite3.Connection, category_code: str) -> str:
    """
    Generate the next sequential style code for a category.

    Args:
        conn: Database connection.
        category_code: Category code (e.g., 'SH', 'PA').

    Returns:
        Generated style code in format SSG-[CATEGORY]-[NNN].
    """
    assert conn is not None
    assert isinstance(category_code, str) and len(category_code) > 0

    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT style_code FROM styles 
        WHERE style_code LIKE ? 
        ORDER BY style_code DESC 
        LIMIT 1
        """,
        (f"SSG-{category_code.upper()}-%",),
    )
    row = cursor.fetchone()
    cursor.close()

    if row is None:
        next_num = 1
    else:
        # Extract the number from the last code
        last_code = row[0]
        try:
            next_num = int(last_code.split("-")[-1]) + 1
        except (ValueError, IndexError):
            next_num = 1

    return f"SSG-{category_code.upper()}-{next_num:03d}"


def _generate_barcode(style_id: int, size: str, color: str) -> str:
    """
    Generate a barcode for a variant.

    Format: SSG[style_id_zero_padded]-[size]-[color_abbr]

    Args:
        style_id: Parent style ID.
        size: Size value (S, M, L, etc.).
        color: Color name.

    Returns:
        Barcode string.
    """
    assert isinstance(style_id, int) and style_id > 0
    assert isinstance(size, str) and len(size) > 0
    assert isinstance(color, str) and len(color) > 0

    color_abbr = color[:3].upper()
    return f"SSG{style_id:03d}-{size}-{color_abbr}"


def _encode_secret_code(purchase_price: int) -> str:
    """
    Encode purchase price using the secret code mapping.

    Args:
        purchase_price: Price in cents.

    Returns:
        Encoded string using character mapping.
    """
    assert isinstance(purchase_price, int) and purchase_price >= 0

    price_str = str(purchase_price)
    encoded = "".join(SECRET_CODE_MAPPING.get(digit, digit) for digit in price_str)
    return encoded


def _calculate_sale_price(purchase_price: int, override: Optional[int] = None) -> int:
    """
    Calculate sale price with default 220% markup.

    Args:
        purchase_price: Cost price in cents.
        override: Optional manual override value.

    Returns:
        Sale price in cents.
    """
    assert isinstance(purchase_price, int) and purchase_price >= 0

    if override is not None:
        return override

    # Default 220% markup
    return int(purchase_price * 2.20)


def create_style(conn: sqlite3.Connection, style_data: Dict) -> int:
    """
    Create a style record with auto-generated style code.

    Args:
        conn: Database connection.
        style_data: Dictionary containing:
            - name: Style name
            - category_id: Category ID
            - description: Optional description
            - base_sale_price: Default sale price in cents
            - tax_rate: GST percentage
            - season: Optional season tag

    Returns:
        New style ID.
    """
    assert conn is not None
    assert isinstance(style_data, dict)
    assert "name" in style_data and len(style_data["name"]) > 0
    assert "category_id" in style_data and style_data["category_id"] > 0
    assert "base_sale_price" in style_data and style_data["base_sale_price"] > 0

    # Get category code for style code generation
    cursor = conn.cursor()
    cursor.execute("SELECT code FROM categories WHERE id = ?", (style_data["category_id"],))
    cat_row = cursor.fetchone()
    if cat_row is None:
        cursor.close()
        raise ValueError(f"Category {style_data['category_id']} not found")
    category_code = cat_row[0]
    cursor.close()

    # Generate style code
    style_code = _generate_style_code(conn, category_code)
    now = datetime.now(timezone.utc).isoformat()

    cursor = conn.cursor()
    cursor.execute(
        CREATE_STYLE,
        (
            style_code,
            style_data["name"],
            style_data["category_id"],
            style_data.get("description"),
            style_data["base_sale_price"],
            style_data.get("tax_rate", 0.0),
            style_data.get("season"),
            now,
            now,
        ),
    )
    style_id = cursor.lastrowid
    conn.commit()
    cursor.close()

    return style_id  # type: ignore


def create_variants(
    conn: sqlite3.Connection,
    style_id: int,
    sizes: List[str],
    colors: List[str],
    base_purchase_price: int,
    batch_data: Dict,
    sale_price_overrides: Optional[Dict[Tuple[str, str], int]] = None,
) -> List[int]:
    """
    Generate all size-color combinations for a style.

    Creates variant records and an initial batch for each.

    Args:
        conn: Database connection.
        style_id: Parent style ID.
        sizes: List of size values.
        colors: List of color names.
        base_purchase_price: Purchase price in cents for all variants.
        batch_data: Batch information (vendor_id, bilty_no, bill_no, date_received).
        sale_price_overrides: Optional dict mapping (size, color) to custom sale prices.

    Returns:
        List of created variant IDs.
    """
    assert conn is not None
    assert isinstance(style_id, int) and style_id > 0
    assert isinstance(sizes, list) and len(sizes) > 0
    assert isinstance(colors, list) and len(colors) > 0
    assert isinstance(base_purchase_price, int) and base_purchase_price > 0
    assert isinstance(batch_data, dict)

    variant_ids = []
    now = datetime.now(timezone.utc).isoformat()
    sale_price_overrides = sale_price_overrides or {}

    cursor = conn.cursor()

    for size in sizes:
        for color in colors:
            barcode = _generate_barcode(style_id, size, color)
            secret_code = _encode_secret_code(base_purchase_price)
            sale_price = _calculate_sale_price(
                base_purchase_price, sale_price_overrides.get((size, color))
            )

            # Create variant
            cursor.execute(
                CREATE_VARIANT,
                (
                    style_id,
                    size,
                    color,
                    barcode,
                    batch_data.get("quantity_per_variant", 1),
                    5,  # reorder_point
                    "local",
                    now,
                    now,
                    now,
                ),
            )
            variant_id = cursor.lastrowid
            variant_ids.append(variant_id)

            # Create batch record
            cursor.execute(
                CREATE_BATCH,
                (
                    variant_id,
                    base_purchase_price,
                    secret_code,
                    batch_data.get("quantity_per_variant", 1),
                    batch_data.get("quantity_per_variant", 1),
                    batch_data.get("vendor_id"),
                    batch_data.get("bilty_no"),
                    batch_data.get("bill_no"),
                    batch_data.get("date_received", now),
                    now,
                ),
            )

    conn.commit()
    cursor.close()

    return variant_ids


def get_variant_by_barcode(conn: sqlite3.Connection, barcode: str) -> Optional[Variant]:
    """
    Look up a variant by its barcode.

    Args:
        conn: Database connection.
        barcode: Barcode string to search.

    Returns:
        Variant object or None if not found.
    """
    assert conn is not None
    assert isinstance(barcode, str) and len(barcode) > 0

    cursor = conn.cursor()
    cursor.execute(GET_VARIANT_BY_BARCODE, (barcode,))
    row = cursor.fetchone()
    cursor.close()

    if row is None:
        return None
    return Variant.from_row(row)


def search_styles(
    conn: sqlite3.Connection,
    query: str,
    category_id: Optional[int] = None,
    stock_status: Optional[str] = None,
) -> List[Style]:
    """
    Search styles by name, code, or description with optional filters.

    Args:
        conn: Database connection.
        query: Search term (matches name, style_code, or description).
        category_id: Optional category filter.
        stock_status: Optional filter ('in_stock', 'low_stock', 'out_of_stock').

    Returns:
        List of matching Style objects.
    """
    assert conn is not None
    assert isinstance(query, str)

    cursor = conn.cursor()

    # Build dynamic query based on filters
    base_query = """
        SELECT DISTINCT s.*, c.name as category_name
        FROM styles s
        JOIN categories c ON s.category_id = c.id
        LEFT JOIN variants v ON s.id = v.style_id
        WHERE (s.name LIKE ? OR s.style_code LIKE ? OR s.description LIKE ?)
    """
    params = [f"%{query}%", f"%{query}%", f"%{query}%"]

    if category_id is not None:
        base_query += " AND s.category_id = ?"
        params.append(category_id)

    if stock_status == "low_stock":
        base_query += " AND v.quantity <= v.reorder_point"
    elif stock_status == "out_of_stock":
        base_query += " AND v.quantity = 0"
    elif stock_status == "in_stock":
        base_query += " AND v.quantity > v.reorder_point"

    base_query += " ORDER BY s.style_code"

    cursor.execute(base_query, params)
    rows = cursor.fetchall()
    cursor.close()

    return [Style.from_row(row) for row in rows]


def get_variant_matrix(
    conn: sqlite3.Connection, style_id: int
) -> Dict[Tuple[str, str], int]:
    """
    Return stock levels for all size-color combinations of a style.

    Args:
        conn: Database connection.
        style_id: Style ID to get matrix for.

    Returns:
        Dict mapping (size, color) tuples to quantity values.
    """
    assert conn is not None
    assert isinstance(style_id, int) and style_id > 0

    cursor = conn.cursor()
    cursor.execute(GET_VARIANTS_BY_STYLE, (style_id,))
    rows = cursor.fetchall()
    cursor.close()

    stock = {}
    for row in rows:
        size = row["size"]
        color = row["color"]
        quantity = row["quantity"]
        stock[(size, color)] = quantity

    return stock


def update_variant_stock(
    conn: sqlite3.Connection, variant_id: int, quantity_delta: int, reason: str
) -> None:
    """
    Adjust variant stock. Positive for restock, negative for deduction.

    Args:
        conn: Database connection.
        variant_id: Variant to update.
        quantity_delta: Amount to add (positive) or deduct (negative).
        reason: Reason for adjustment (for audit trail).
    """
    assert conn is not None
    assert isinstance(variant_id, int) and variant_id > 0
    assert isinstance(quantity_delta, int) and quantity_delta != 0
    assert isinstance(reason, str) and len(reason) > 0

    cursor = conn.cursor()
    cursor.execute(UPDATE_VARIANT_QUANTITY, (quantity_delta, variant_id))
    conn.commit()
    cursor.close()


def get_low_stock_variants(conn: sqlite3.Connection) -> List[Variant]:
    """
    Return all variants where quantity <= reorder_point.

    Args:
        conn: Database connection.

    Returns:
        List of low-stock Variant objects.
    """
    assert conn is not None

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

    return [Variant.from_row(row) for row in rows]


def delete_style(conn: sqlite3.Connection, style_id: int) -> None:
    """
    Delete a style and all its variants (cascade delete via FK).

    Args:
        conn: Database connection.
        style_id: Style ID to delete.
    """
    assert conn is not None
    assert isinstance(style_id, int) and style_id > 0

    cursor = conn.cursor()
    # Variants will be deleted via ON DELETE CASCADE
    cursor.execute(DELETE_STYLE, (style_id,))
    conn.commit()
    cursor.close()
