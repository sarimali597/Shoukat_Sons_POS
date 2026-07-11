"""
Test data generator for Shoukat Sons Garments POS.

Generates realistic test data for integration and e2e tests.
"""

import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List


class TestDataGenerator:
    """Generate realistic test data for integration and e2e tests."""

    def __init__(self) -> None:
        """Initialize the test data generator with seed for reproducibility."""
        random.seed(42)  # Fixed seed for reproducible tests
        self.categories = ["Shirt", "Pant", "Kurta", "Waistcoat", "Blazer"]
        self.sizes = ["S", "M", "L", "XL", "XXL"]
        self.colors = [
            "Blue",
            "Red",
            "Green",
            "Black",
            "White",
            "Navy",
            "Grey",
            "Brown",
        ]
        self.names = [
            "Ahmed Khan",
            "Ali Hassan",
            "Bilal Ahmed",
            "Fahad Malik",
            "Hassan Raza",
            "Imran Shah",
            "Kamran Ali",
            "Mohsin Javaid",
            "Noman Akram",
            "Omar Farooq",
            "Qasim Ibrahim",
            "Rizwan Mahmood",
            "Salman Aslam",
            "Tariq Jameel",
            "Usman Ghani",
            "Waseem Abbas",
            "Yasir Nadeem",
            "Zubair Tariq",
        ]
        self.cities = [
            "Lahore",
            "Karachi",
            "Islamabad",
            "Rawalpindi",
            "Faisalabad",
            "Multan",
            "Peshawar",
            "Quetta",
        ]

    def generate_styles(self, count: int = 10) -> List[Dict]:
        """
        Generate sample style data.

        Args:
            count: Number of styles to generate.

        Returns:
            List of style dictionaries.
        """
        assert count > 0

        styles = []
        for i in range(count):
            category = random.choice(self.categories)
            style_code = f"SSG-{category[:3].upper()}-{str(i + 1).zfill(3)}"
            base_price = random.randint(150000, 500000)  # Rs. 1500-5000 in cents

            styles.append(
                {
                    "style_code": style_code,
                    "name": f"{category} Style {i + 1}",
                    "category_name": category,
                    "base_sale_price": base_price,
                    "tax_rate": 17.0,
                    "season": random.choice(["Summer", "Winter", "Spring", "Fall"]),
                    "description": f"A quality {category.lower()} style",
                }
            )

        return styles

    def generate_variants(
        self, style_id: int, sizes: List[str] = None, colors: List[str] = None
    ) -> List[Dict]:
        """
        Generate variant data for a style.

        Args:
            style_id: ID of the parent style.
            sizes: Optional list of sizes. Uses default if None.
            colors: Optional list of colors. Uses default if None.

        Returns:
            List of variant dictionaries.
        """
        assert style_id > 0

        if sizes is None:
            sizes = self.sizes
        if colors is None:
            colors = self.colors[:4]  # Use first 4 colors by default

        variants = []
        for size in sizes:
            for color in colors:
                barcode = f"SSG{str(style_id).zfill(3)}-{size}-{color[:3].upper()}"
                quantity = random.randint(5, 50)
                reorder_point = random.randint(3, 10)

                variants.append(
                    {
                        "style_id": style_id,
                        "size": size,
                        "color": color,
                        "barcode": barcode,
                        "quantity": quantity,
                        "reorder_point": reorder_point,
                    }
                )

        return variants

    def generate_customers(self, count: int = 20) -> List[Dict]:
        """
        Generate sample customer data.

        Args:
            count: Number of customers to generate.

        Returns:
            List of customer dictionaries.
        """
        assert count > 0

        customers = []
        for i in range(count):
            name = random.choice(self.names)
            city = random.choice(self.cities)
            phone = f"03{random.randint(10, 49)}{random.randint(1000000, 9999999)}"

            customers.append(
                {
                    "name": f"{name} {i + 1}",
                    "phone": phone,
                    "address": f"Shop {i + 1}, {city} Market, {city}",
                    "total_due": 0,
                    "credit_limit": random.randint(50000, 500000),  # Rs. 500-5000
                }
            )

        return customers

    def generate_sales(
        self,
        count: int = 50,
        variant_ids: List[int] = None,
        customer_ids: List[int] = None,
        user_id: int = 1,
    ) -> List[Dict]:
        """
        Generate sample sale data.

        Args:
            count: Number of sales to generate.
            variant_ids: Optional list of variant IDs to use.
            customer_ids: Optional list of customer IDs to use.
            user_id: User ID for all sales.

        Returns:
            List of sale dictionaries.
        """
        assert count > 0
        assert user_id > 0

        if variant_ids is None:
            variant_ids = [1, 2, 3, 4, 5]
        if customer_ids is None:
            customer_ids = [None]  # Mix of walk-in and registered

        sales = []
        base_date = datetime.now(timezone.utc) - timedelta(days=30)

        for i in range(count):
            num_items = random.randint(1, 5)
            sale_items = []
            subtotal = 0
            tax_amount = 0

            for _ in range(num_items):
                variant_id = random.choice(variant_ids)
                quantity = random.randint(1, 3)
                unit_price = random.randint(100000, 400000)  # Rs. 1000-4000
                tax_rate = 17.0
                discount = random.choice([0, 0, 0, 5000, 10000])  # Mostly no discount

                item_total = (unit_price * quantity) + (
                    unit_price * quantity * tax_rate / 100
                ) - discount
                subtotal += unit_price * quantity
                tax_amount += unit_price * quantity * tax_rate / 100

                sale_items.append(
                    {
                        "variant_id": variant_id,
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "tax_rate": tax_rate,
                        "discount": discount,
                        "total": int(item_total),
                    }
                )

            total_amount = subtotal + tax_amount - sum(item["discount"] for item in sale_items)
            payment_type = random.choice(["cash", "cash", "cash", "credit", "upi"])

            if payment_type == "credit":
                paid_amount = random.randint(0, int(total_amount * 0.5))
                customer_id = random.choice(customer_ids[1:]) if len(customer_ids) > 1 else 1
            else:
                paid_amount = int(total_amount)
                customer_id = random.choice(customer_ids)

            sale_date = base_date + timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))

            sales.append(
                {
                    "customer_id": customer_id,
                    "user_id": user_id,
                    "sale_date": sale_date.isoformat(),
                    "items": sale_items,
                    "subtotal": int(subtotal),
                    "tax_amount": int(tax_amount),
                    "discount_amount": sum(item["discount"] for item in sale_items),
                    "total_amount": int(total_amount),
                    "paid_amount": paid_amount,
                    "payment_type": payment_type,
                    "status": "completed",
                }
            )

        return sales

    def generate_inventory_batches(
        self, variant_id: int, count: int = 3, vendor_id: int = None
    ) -> List[Dict]:
        """
        Generate inventory batch data for a variant.

        Args:
            variant_id: ID of the variant.
            count: Number of batches to generate.
            vendor_id: Optional vendor ID.

        Returns:
            List of batch dictionaries.
        """
        assert variant_id > 0
        assert count > 0

        batches = []
        base_date = datetime.now(timezone.utc) - timedelta(days=60)

        for i in range(count):
            purchase_price = random.randint(80000, 200000)  # Rs. 800-2000
            quantity = random.randint(10, 50)
            secret_code = "".join(random.choices("RKMLNPWS", k=6))

            batch_date = base_date + timedelta(days=i * 10)

            batches.append(
                {
                    "variant_id": variant_id,
                    "purchase_price": purchase_price,
                    "secret_code": secret_code,
                    "quantity_received": quantity,
                    "quantity_remaining": quantity - random.randint(0, quantity // 2),
                    "vendor_id": vendor_id,
                    "bilty_no": f"BILTY{random.randint(1000, 9999)}",
                    "bill_no": f"BILL{random.randint(1000, 9999)}",
                    "date_received": batch_date.isoformat(),
                }
            )

        return batches
