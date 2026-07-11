"""
Named SQL query constants for database operations.

All queries use parameterized placeholders (?) exclusively.
No string concatenation is allowed.
"""

# =============================================================================
# Categories
# =============================================================================

CREATE_CATEGORY = """
INSERT INTO categories (name, code, tax_rate, created_at)
VALUES (?, ?, ?, ?)
"""

GET_ALL_CATEGORIES = """
SELECT * FROM categories ORDER BY name
"""

GET_CATEGORY_BY_ID = """
SELECT * FROM categories WHERE id = ?
"""

GET_CATEGORY_BY_CODE = """
SELECT * FROM categories WHERE code = ?
"""

UPDATE_CATEGORY = """
UPDATE categories SET name = ?, code = ?, tax_rate = ?
WHERE id = ?
"""

DELETE_CATEGORY = """
DELETE FROM categories WHERE id = ?
"""

# =============================================================================
# Vendors
# =============================================================================

CREATE_VENDOR = """
INSERT INTO vendors (name, location, phone, created_at)
VALUES (?, ?, ?, ?)
"""

GET_ALL_VENDORS = """
SELECT * FROM vendors ORDER BY name
"""

GET_VENDOR_BY_ID = """
SELECT * FROM vendors WHERE id = ?
"""

UPDATE_VENDOR = """
UPDATE vendors SET name = ?, location = ?, phone = ?
WHERE id = ?
"""

DELETE_VENDOR = """
DELETE FROM vendors WHERE id = ?
"""

# =============================================================================
# Users
# =============================================================================

CREATE_USER = """
INSERT INTO users (username, password_hash, role, is_active, created_at)
VALUES (?, ?, ?, ?, ?)
"""

GET_ALL_USERS = """
SELECT * FROM users ORDER BY username
"""

GET_USER_BY_ID = """
SELECT * FROM users WHERE id = ?
"""

GET_USER_BY_USERNAME = """
SELECT * FROM users WHERE username = ?
"""

UPDATE_USER = """
UPDATE users SET username = ?, password_hash = ?, role = ?, is_active = ?
WHERE id = ?
"""

UPDATE_USER_LAST_LOGIN = """
UPDATE users SET last_login = ? WHERE id = ?
"""

DELETE_USER = """
DELETE FROM users WHERE id = ?
"""

# =============================================================================
# Customers
# =============================================================================

CREATE_CUSTOMER = """
INSERT INTO customers (name, phone, address, total_due, credit_limit, created_at)
VALUES (?, ?, ?, ?, ?, ?)
"""

GET_ALL_CUSTOMERS = """
SELECT * FROM customers ORDER BY name
"""

GET_CUSTOMER_BY_ID = """
SELECT * FROM customers WHERE id = ?
"""

GET_CUSTOMER_BY_PHONE = """
SELECT * FROM customers WHERE phone = ?
"""

UPDATE_CUSTOMER = """
UPDATE customers SET name = ?, phone = ?, address = ?, 
total_due = ?, credit_limit = ?
WHERE id = ?
"""

UPDATE_CUSTOMER_DUE = """
UPDATE customers SET total_due = total_due + ? WHERE id = ?
"""

DELETE_CUSTOMER = """
DELETE FROM customers WHERE id = ?
"""

# =============================================================================
# Styles
# =============================================================================

CREATE_STYLE = """
INSERT INTO styles (style_code, name, category_id, description, 
base_sale_price, tax_rate, season, created_at, updated_at)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

GET_ALL_STYLES = """
SELECT s.*, c.name as category_name 
FROM styles s 
JOIN categories c ON s.category_id = c.id 
ORDER BY s.style_code
"""

GET_STYLE_BY_ID = """
SELECT * FROM styles WHERE id = ?
"""

GET_STYLE_BY_CODE = """
SELECT * FROM styles WHERE style_code = ?
"""

GET_STYLES_BY_CATEGORY = """
SELECT * FROM styles WHERE category_id = ? ORDER BY style_code
"""

UPDATE_STYLE = """
UPDATE styles SET name = ?, category_id = ?, description = ?, 
base_sale_price = ?, tax_rate = ?, season = ?
WHERE id = ?
"""

DELETE_STYLE = """
DELETE FROM styles WHERE id = ?
"""

# =============================================================================
# Variants
# =============================================================================

CREATE_VARIANT = """
INSERT INTO variants (style_id, size, color, barcode, quantity, 
reorder_point, sync_status, modified_at, created_at, updated_at)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

GET_ALL_VARIANTS = """
SELECT v.*, s.name as style_name, s.style_code 
FROM variants v 
JOIN styles s ON v.style_id = s.id 
ORDER BY s.style_code, v.size, v.color
"""

GET_VARIANT_BY_ID = """
SELECT * FROM variants WHERE id = ?
"""

GET_VARIANT_BY_BARCODE = """
SELECT * FROM variants WHERE barcode = ?
"""

GET_VARIANTS_BY_STYLE = """
SELECT * FROM variants WHERE style_id = ? ORDER BY size, color
"""

GET_VARIANTS_LOW_STOCK = """
SELECT v.*, s.name as style_name 
FROM variants v 
JOIN styles s ON v.style_id = s.id 
WHERE v.quantity <= v.reorder_point 
ORDER BY v.quantity
"""

UPDATE_VARIANT = """
UPDATE variants SET size = ?, color = ?, barcode = ?, quantity = ?, 
reorder_point = ?, sync_status = ?, modified_at = ?
WHERE id = ?
"""

UPDATE_VARIANT_QUANTITY = """
UPDATE variants SET quantity = quantity + ? WHERE id = ?
"""

DELETE_VARIANT = """
DELETE FROM variants WHERE id = ?
"""

# =============================================================================
# Batches
# =============================================================================

CREATE_BATCH = """
INSERT INTO batches (variant_id, purchase_price, secret_code, 
quantity_received, quantity_remaining, vendor_id, bilty_no, bill_no, 
date_received, created_at)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

GET_ALL_BATCHES = """
SELECT b.*, v.barcode, s.name as style_name 
FROM batches b 
JOIN variants v ON b.variant_id = v.id 
JOIN styles s ON v.style_id = s.id 
ORDER BY b.date_received DESC
"""

GET_BATCH_BY_ID = """
SELECT * FROM batches WHERE id = ?
"""

GET_BATCHES_BY_VARIANT = """
SELECT * FROM batches WHERE variant_id = ? ORDER BY date_received
"""

GET_BATCHES_WITH_STOCK = """
SELECT * FROM batches WHERE quantity_remaining > 0 ORDER BY date_received
"""

UPDATE_BATCH = """
UPDATE batches SET purchase_price = ?, secret_code = ?, 
quantity_received = ?, quantity_remaining = ?, vendor_id = ?, 
bilty_no = ?, bill_no = ?
WHERE id = ?
"""

UPDATE_BATCH_REMAINING = """
UPDATE batches SET quantity_remaining = quantity_remaining - ? 
WHERE id = ?
"""

DELETE_BATCH = """
DELETE FROM batches WHERE id = ?
"""

# =============================================================================
# Sales
# =============================================================================

CREATE_SALE = """
INSERT INTO sales (invoice_number, customer_id, user_id, sale_date, 
subtotal, tax_amount, discount_amount, total_amount, paid_amount, 
due_amount, payment_type, status, created_at)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

GET_ALL_SALES = """
SELECT s.*, u.username as cashier_name, c.name as customer_name 
FROM sales s 
LEFT JOIN users u ON s.user_id = u.id 
LEFT JOIN customers c ON s.customer_id = c.id 
ORDER BY s.sale_date DESC
"""

GET_SALE_BY_ID = """
SELECT * FROM sales WHERE id = ?
"""

GET_SALE_BY_INVOICE = """
SELECT * FROM sales WHERE invoice_number = ?
"""

GET_SALES_BY_DATE_RANGE = """
SELECT * FROM sales 
WHERE sale_date BETWEEN ? AND ? 
ORDER BY sale_date DESC
"""

GET_SALES_BY_STATUS = """
SELECT * FROM sales WHERE status = ? ORDER BY sale_date DESC
"""

UPDATE_SALE = """
UPDATE sales SET customer_id = ?, subtotal = ?, tax_amount = ?, 
discount_amount = ?, total_amount = ?, paid_amount = ?, due_amount = ?, 
payment_type = ?, status = ?
WHERE id = ?
"""

UPDATE_SALE_STATUS = """
UPDATE sales SET status = ? WHERE id = ?
"""

DELETE_SALE = """
DELETE FROM sales WHERE id = ?
"""

# =============================================================================
# Sale Items
# =============================================================================

CREATE_SALE_ITEM = """
INSERT INTO sale_items (sale_id, variant_id, batch_id, quantity, 
unit_price, tax_amount, total_price, is_returned)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""

GET_SALE_ITEMS_BY_SALE = """
SELECT si.*, v.barcode, v.size, v.color, s.name as style_name 
FROM sale_items si 
JOIN variants v ON si.variant_id = v.id 
JOIN styles s ON v.style_id = s.id 
WHERE si.sale_id = ?
"""

GET_SALE_ITEM_BY_ID = """
SELECT * FROM sale_items WHERE id = ?
"""

UPDATE_SALE_ITEM = """
UPDATE sale_items SET variant_id = ?, batch_id = ?, quantity = ?, 
unit_price = ?, tax_amount = ?, total_price = ?, is_returned = ?
WHERE id = ?
"""

DELETE_SALE_ITEM = """
DELETE FROM sale_items WHERE sale_id = ?
"""

DELETE_SALE_ITEM_BY_ID = """
DELETE FROM sale_items WHERE id = ?
"""

# =============================================================================
# Audit Log
# =============================================================================

CREATE_AUDIT_LOG = """
INSERT INTO audit_log (table_name, record_id, action, old_values, 
new_values, user_id, hmac_hash)
VALUES (?, ?, ?, ?, ?, ?, ?)
"""

GET_AUDIT_LOG_BY_TABLE = """
SELECT * FROM audit_log WHERE table_name = ? ORDER BY timestamp DESC
"""

GET_AUDIT_LOG_BY_RECORD = """
SELECT * FROM audit_log WHERE table_name = ? AND record_id = ? 
ORDER BY timestamp DESC
"""

GET_AUDIT_LOG_BY_USER = """
SELECT * FROM audit_log WHERE user_id = ? ORDER BY timestamp DESC
"""

GET_AUDIT_LOG_BY_DATE_RANGE = """
SELECT * FROM audit_log 
WHERE timestamp BETWEEN ? AND ? 
ORDER BY timestamp DESC
"""

# =============================================================================
# Inventory / Stock Operations
# =============================================================================

DEDUCT_STOCK = """
UPDATE variants SET quantity = quantity - ? WHERE id = ?
"""

ADD_STOCK = """
UPDATE variants SET quantity = quantity + ? WHERE id = ?
"""

GET_TOTAL_STOCK_BY_STYLE = """
SELECT SUM(quantity) as total_quantity 
FROM variants WHERE style_id = ?
"""

GET_STOCK_VALUE = """
SELECT SUM(v.quantity * b.purchase_price) as total_value 
FROM variants v 
JOIN batches b ON v.id = b.variant_id 
WHERE b.quantity_remaining > 0
"""
