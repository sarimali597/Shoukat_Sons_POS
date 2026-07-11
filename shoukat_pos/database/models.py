"""
Dataclass entities for database models.

Each entity represents a table row with type hints, validation methods,
and factory methods for creating from sqlite3.Row objects.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Category:
    """Represents a product category."""

    id: Optional[int] = None
    name: str = ""
    code: str = ""
    tax_rate: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def from_row(cls, row) -> "Category":
        """Create Category from sqlite3.Row."""
        assert row is not None
        return cls(
            id=row["id"],
            name=row["name"],
            code=row["code"],
            tax_rate=row["tax_rate"],
            created_at=row["created_at"],
        )

    def validate(self) -> bool:
        """Validate category data."""
        return bool(self.name and self.code)


@dataclass
class Vendor:
    """Represents a vendor/supplier."""

    id: Optional[int] = None
    name: str = ""
    location: Optional[str] = None
    phone: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def from_row(cls, row) -> "Vendor":
        """Create Vendor from sqlite3.Row."""
        assert row is not None
        return cls(
            id=row["id"],
            name=row["name"],
            location=row["location"],
            phone=row["phone"],
            created_at=row["created_at"],
        )

    def validate(self) -> bool:
        """Validate vendor data."""
        return bool(self.name)


@dataclass
class User:
    """Represents a system user."""

    id: Optional[int] = None
    username: str = ""
    password_hash: str = ""
    role: str = ""
    is_active: int = 1
    last_login: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def from_row(cls, row) -> "User":
        """Create User from sqlite3.Row."""
        assert row is not None
        return cls(
            id=row["id"],
            username=row["username"],
            password_hash=row["password_hash"],
            role=row["role"],
            is_active=row["is_active"],
            last_login=row["last_login"],
            created_at=row["created_at"],
        )

    def validate(self) -> bool:
        """Validate user data."""
        return bool(self.username and self.password_hash and self.role)

    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == "admin"


@dataclass
class Customer:
    """Represents a customer."""

    id: Optional[int] = None
    name: str = ""
    phone: Optional[str] = None
    address: Optional[str] = None
    total_due: int = 0
    credit_limit: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def from_row(cls, row) -> "Customer":
        """Create Customer from sqlite3.Row."""
        assert row is not None
        return cls(
            id=row["id"],
            name=row["name"],
            phone=row["phone"],
            address=row["address"],
            total_due=row["total_due"],
            credit_limit=row["credit_limit"],
            created_at=row["created_at"],
        )

    def validate(self) -> bool:
        """Validate customer data."""
        return bool(self.name)


@dataclass
class Style:
    """Represents a product style (parent definition)."""

    id: Optional[int] = None
    style_code: str = ""
    name: str = ""
    category_id: int = 0
    description: Optional[str] = None
    base_sale_price: int = 0
    tax_rate: float = 0.0
    season: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def from_row(cls, row) -> "Style":
        """Create Style from sqlite3.Row."""
        assert row is not None
        return cls(
            id=row["id"],
            style_code=row["style_code"],
            name=row["name"],
            category_id=row["category_id"],
            description=row["description"],
            base_sale_price=row["base_sale_price"],
            tax_rate=row["tax_rate"],
            season=row["season"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def validate(self) -> bool:
        """Validate style data."""
        return bool(self.style_code and self.name and self.category_id and self.base_sale_price > 0)


@dataclass
class Variant:
    """Represents a size-color variant of a style."""

    id: Optional[int] = None
    style_id: int = 0
    size: str = ""
    color: str = ""
    barcode: str = ""
    quantity: int = 0
    reorder_point: int = 5
    sync_status: str = "local"
    modified_at: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def from_row(cls, row) -> "Variant":
        """Create Variant from sqlite3.Row."""
        assert row is not None
        return cls(
            id=row["id"],
            style_id=row["style_id"],
            size=row["size"],
            color=row["color"],
            barcode=row["barcode"],
            quantity=row["quantity"],
            reorder_point=row["reorder_point"],
            sync_status=row["sync_status"],
            modified_at=row["modified_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def validate(self) -> bool:
        """Validate variant data."""
        return bool(self.style_id and self.size and self.color and self.barcode)


@dataclass
class Batch:
    """Represents a purchase batch with cost tracking."""

    id: Optional[int] = None
    variant_id: int = 0
    purchase_price: int = 0
    secret_code: str = ""
    quantity_received: int = 0
    quantity_remaining: int = 0
    vendor_id: Optional[int] = None
    bilty_no: Optional[str] = None
    bill_no: Optional[str] = None
    date_received: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def from_row(cls, row) -> "Batch":
        """Create Batch from sqlite3.Row."""
        assert row is not None
        return cls(
            id=row["id"],
            variant_id=row["variant_id"],
            purchase_price=row["purchase_price"],
            secret_code=row["secret_code"],
            quantity_received=row["quantity_received"],
            quantity_remaining=row["quantity_remaining"],
            vendor_id=row["vendor_id"],
            bilty_no=row["bilty_no"],
            bill_no=row["bill_no"],
            date_received=row["date_received"],
            created_at=row["created_at"],
        )

    def validate(self) -> bool:
        """Validate batch data."""
        return bool(
            self.variant_id and self.purchase_price > 0 and self.quantity_received > 0
        )


@dataclass
class Sale:
    """Represents a sale transaction."""

    id: Optional[int] = None
    invoice_number: str = ""
    customer_id: Optional[int] = None
    user_id: int = 0
    sale_date: str = ""
    subtotal: int = 0
    tax_amount: int = 0
    discount_amount: int = 0
    total_amount: int = 0
    paid_amount: int = 0
    due_amount: int = 0
    payment_type: str = ""
    status: str = "completed"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def from_row(cls, row) -> "Sale":
        """Create Sale from sqlite3.Row."""
        assert row is not None
        return cls(
            id=row["id"],
            invoice_number=row["invoice_number"],
            customer_id=row["customer_id"],
            user_id=row["user_id"],
            sale_date=row["sale_date"],
            subtotal=row["subtotal"],
            tax_amount=row["tax_amount"],
            discount_amount=row["discount_amount"],
            total_amount=row["total_amount"],
            paid_amount=row["paid_amount"],
            due_amount=row["due_amount"],
            payment_type=row["payment_type"],
            status=row["status"],
            created_at=row["created_at"],
        )

    def validate(self) -> bool:
        """Validate sale data."""
        return bool(self.invoice_number and self.user_id and self.total_amount > 0)


@dataclass
class SaleItem:
    """Represents an item in a sale."""

    id: Optional[int] = None
    sale_id: int = 0
    variant_id: int = 0
    batch_id: Optional[int] = None
    quantity: int = 0
    unit_price: int = 0
    tax_amount: int = 0
    total_price: int = 0
    is_returned: int = 0

    @classmethod
    def from_row(cls, row) -> "SaleItem":
        """Create SaleItem from sqlite3.Row."""
        assert row is not None
        return cls(
            id=row["id"],
            sale_id=row["sale_id"],
            variant_id=row["variant_id"],
            batch_id=row["batch_id"],
            quantity=row["quantity"],
            unit_price=row["unit_price"],
            tax_amount=row["tax_amount"],
            total_price=row["total_price"],
            is_returned=row["is_returned"],
        )

    def validate(self) -> bool:
        """Validate sale item data."""
        return bool(self.sale_id and self.variant_id and self.quantity > 0 and self.unit_price > 0)


@dataclass
class AuditLog:
    """Represents an audit log entry."""

    id: Optional[int] = None
    table_name: str = ""
    record_id: int = 0
    action: str = ""
    old_values: Optional[str] = None
    new_values: Optional[str] = None
    user_id: Optional[int] = None
    timestamp: str = ""
    hmac_hash: str = ""

    @classmethod
    def from_row(cls, row) -> "AuditLog":
        """Create AuditLog from sqlite3.Row."""
        assert row is not None
        return cls(
            id=row["id"],
            table_name=row["table_name"],
            record_id=row["record_id"],
            action=row["action"],
            old_values=row["old_values"],
            new_values=row["new_values"],
            user_id=row["user_id"],
            timestamp=row["timestamp"],
            hmac_hash=row["hmac_hash"],
        )

    def validate(self) -> bool:
        """Validate audit log data."""
        return bool(self.table_name and self.record_id and self.action and self.hmac_hash)
