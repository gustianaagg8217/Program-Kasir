# ============================================================================
# QUICK REFERENCE GUIDE - SERVICE LAYER API
# ============================================================================
# Common operations & method reference for the refactored POS system

## 🔧 QUICK SETUP

```python
from src.service import ServiceFactory

factory = ServiceFactory(db_path=\"kasir_pos.db\")
```


## 👤 AUTHENTICATION (auth_service)

```python
auth_svc = factory.auth_service()

# Login
session = auth_svc.login(username=\"admin\", password=\"pass123\")

# Check permission
if session.has_permission(\"transaksi.create\"):
    print(\"Can create transaction\")

# Create user
user = auth_svc.create_user(
    username=\"cashier1\",
    password=\"pass123\",
    role=\"cashier\",
    nama_lengkap=\"Budi Santoso\"
)

# List users
users = auth_svc.list_users()

# Update user
auth_svc.update_user(user_id=1, nama_lengkap=\"New Name\")

# Change password
auth_svc.change_password(
    user_id=1,
    old_password=\"old_pass\",
    new_password=\"new_pass\"
)

# Deactivate user
auth_svc.deactivate_user(user_id=1)
```


## 🛍️ PRODUCT MANAGEMENT (product_service)

```python
product_svc = factory.product_service()

# Create product
product = product_svc.create_product(
    kode=\"COLA750\",
    nama=\"Coca Cola 750ml\",
    harga=25000,
    stok=100,
    min_stok=20,
    kategori=\"Minuman\"
)

# Get product
product = product_svc.get_product_by_kode(\"COLA750\")
product = product_svc.get_product_by_id(1)

# List products
products = product_svc.list_products()

# Search products
results = product_svc.search_products_by_name(\"cola\")

# Update product
product_svc.update_product(
    product_id=1,
    harga=26000,
    nama=\"Updated Name\"
)

# Delete product
product_svc.delete_product(product_id=1)

# Get low stock
low_stock = product_svc.get_low_stock_products()
```


## 📦 STOCK MANAGEMENT (stock_service)

```python
stock_svc = factory.stock_service()

# Validate stock available
stock_svc.validate_stock_available(product_id=1, qty_needed=10)

# Deduct stock (for sales)
new_stock = stock_svc.deduct_stock(
    product_id=1,
    qty_to_deduct=5,
    notes=\"Sale transaction #123\"
)

# Add stock (for restock)
new_stock = stock_svc.add_stock(
    product_id=1,
    qty_to_add=50,
    notes=\"Restock from supplier ABC\"
)

# Adjust stock (corrections)
adjustment = stock_svc.adjust_stock(
    product_id=1,
    new_stock_level=100,
    reason=\"Physical count correction\"
)

# low stock alert
low_stock = stock_svc.get_low_stock_products()

# Get stock movements
movements = stock_svc.get_product_movements(product_id=1)
```


## 💳 TRANSACTION PROCESSING (transaction_service)

```python
transaction_svc = factory.transaction_service()

# 1. Create transaction
transaction_svc.create_transaction(cashier_id=1)

# 2. Add items
transaction_svc.add_item(
    product_id=1,
    product_code=\"COLA750\",
    product_name=\"Coca Cola 750ml\",
    qty=5,
    harga_satuan=25000,
    discount_pct=10.0,
    tax_pct=10.0
)

# 2b. Add more items
transaction_svc.add_item(product_id=2, ...)

# 3. Modify items (optional)
transaction_svc.update_item_qty(item_index=0, new_qty=10)
transaction_svc.set_item_discount(item_index=0, discount_pct=15.0)
transaction_svc.set_item_tax(item_index=0, tax_pct=5.0)
transaction_svc.remove_item(item_index=1)

# 4. Get summary
trans = transaction_svc.current_transaction
print(f\"Total: {trans.total}\")
print(f\"Items: {len(trans.items)}\")

# 5. Process payment
amount, change = transaction_svc.process_payment(
    payment_method=\"cash\",
    amount_received=200000
)

# 6. Complete transaction (ATOMIC - saves + deducts stock)
transaction_id = transaction_svc.complete_transaction()

# Optional: Cancel transaction
transaction_svc.cancel_transaction()

# Get transaction summary
summary = transaction_svc.get_transaction_summary(transaction_id=1)

# List transactions
transactions = transaction_svc.list_transactions_by_date(
    target_date=datetime.today()
)
```


## ❌ ERROR HANDLING

```python
from src.core import (
    ValidationError, AuthenticationError,
    InsufficientStockError, TransactionError,
    PaymentError, DatabaseError
)

try:
    transaction_svc.complete_transaction()
    
except ValidationError as e:
    print(f\"Input error: {e.message}\")
    
except InsufficientStockError as e:
    print(f\"Stock problem: {e.product_name}\")
    print(f\"Need: {e.required}, Have: {e.available}\")
    
except PaymentError as e:
    print(f\"Payment error: {e.message}\")
    
except TransactionError as e:
    print(f\"Transaction error: {e.message}\")
    
except AuthenticationError as e:
    print(f\"Login error: {e.message}\")
    
except DatabaseError as e:
    print(f\"Database error: {e.message}\")
    
except Exception as e:
    print(f\"Unexpected error: {e}\")
```


## 📊 COMMON WORKFLOWS

### Complete Sale Transaction
```python
factory = ServiceFactory()
auth_svc = factory.auth_service()
transaction_svc = factory.transaction_service()

# 1. Login
session = auth_svc.login(\"cashier1\", \"password\")

# 2. Create transaction
transaction_svc.create_transaction(cashier_id=session.user_id)

# 3. Add items (repeat for each product)
transaction_svc.add_item(
    product_id=1, product_code=\"PROD001\", product_name=\"Item\",
    qty=5, harga_satuan=25000, discount_pct=0.0, tax_pct=10.0
)

# 4. Show total
trans = transaction_svc.current_transaction
print(f\"Total: {trans.total}\")

# 5. Process payment
amount, change = transaction_svc.process_payment(\"cash\", 200000)
print(f\"Change: {change}\")

# 6. Complete
transaction_id = transaction_svc.complete_transaction()
# Stock automatically deducted!
print(f\"Transaction ID: {transaction_id}\")
```


### Restock & Stock Adjustment
```python
stock_svc = factory.stock_service()

# Add stock during restock
new_stock = stock_svc.add_stock(
    product_id=1,
    qty_to_add=100,
    notes=\"Restock from supplier\"
)
print(f\"New stock: {new_stock}\")

# Adjust for physical count
adjustment = stock_svc.adjust_stock(
    product_id=1,
    new_stock_level=95,
    reason=\"Physical inventory count\"
)
print(f\"Adjusted by: {adjustment}\")

# Check low stock
low = stock_svc.get_low_stock_products()
for p in low:
    print(f\"Low stock: {p.nama} - {p.stok} units\")
```


### User Management
```python
auth_svc = factory.auth_service()

# Create users
admin = auth_svc.create_user(
    username=\"admin\",
    password=\"admin123\",
    role=\"admin\",
    nama_lengkap=\"Administrator\"
)

cashier = auth_svc.create_user(
    username=\"cashier1\",
    password=\"cashier123\",
    role=\"cashier\",
    nama_lengkap=\"Budi Santoso\"
)

# List users
users = auth_svc.list_users()
for u in users:
    print(f\"{u.username} - {u.role}\")

# Update user
auth_svc.update_user(user_id=1, nama_lengkap=\"New Name\")

# Deactivate user
auth_svc.deactivate_user(user_id=2)

# User permissions
if auth_svc.check_permission(session, \"produk.create\"):
    print(\"Can create products\")
```


## 📈 METRICS & REPORTING (Future Phase)

```python
# Coming in Phase 3

# Get daily sales
daily_report = report_svc.get_daily_sales(date=datetime.today())

# Get product sales
product_report = report_svc.get_product_sales(start_date, end_date)

# Get low stock alert
low_stock = report_svc.get_low_stock_products()

# Get profit summary
profit = report_svc.get_profit_summary(date=datetime.today())

# Export to CSV
report_svc.export_transactions_to_csv(start_date, end_date)
```


## 💡 USEFUL UTILITIES

```python
from src.core import format_rp

# Format currency
price = 25000
print(format_rp(price))  # \"Rp 25.000\"

# Use in models
product.harga
transaction.total
transaction.kembalian
```


## 🔐 PERMISSIONS REFERENCE

### Admin Permissions
```
produk.create      - Create products
produk.read        - Read products
produk.update      - Update products
produk.delete      - Delete products
transaksi.create   - Create transactions
transaksi.read     - Read transactions
transaksi.list     - List all transactions
transaksi.delete   - Delete transactions (cancel)
laporan.view_all   - View all reports
laporan.export     - Export reports
user.create        - Create users
user.read          - Read user info
user.update        - Update users
user.delete        - Delete users
settings.*         - All settings
```

### Cashier Permissions
```
produk.read        - View products
produk.search      - Search products
transaksi.create   - Create transactions
transaksi.read     - View transactions
laporan.view_own   - View own transactions
settings.change_password
```


## 🎯 COMMON PATTERNS

### Safe Operation
```python
try:
    result = service.operation(...)
    print(f\"✅ Success: {result}\")
except ValidationError as e:
    print(f\"❌ Validation error: {e.message}\")
except Exception as e:
    print(f\"❌ Error: {e.message if hasattr(e, 'message') else str(e)}\")
```

### Check Then Act
```python
try:
    stock_svc.validate_stock_available(product_id=1, qty_needed=10)
    # Stock is available, proceed
    new_stock = stock_svc.deduct_stock(product_id=1, qty_to_deduct=10)
except InsufficientStockError as e:
    # Handle low stock
    print(f\"Cannot sell: {e.message}\")
```

### With Permission Check
```python
try:
    auth_svc.require_permission(session, \"transaksi.create\")
    # User has permission, proceed
    transaction_svc.create_transaction()
except AuthorizationError as e:
    # Handle permission denied
    print(f\"Access denied: {e.message}\")
```


## 📚 RELATED DOCUMENTATION

- [REFACTORING_ARCHITECTURE.md](REFACTORING_ARCHITECTURE.md) - Full architecture
- [QUICK_START_SERVICES.md](QUICK_START_SERVICES.md) - Detailed examples
- [FILE_STRUCTURE.md](FILE_STRUCTURE.md) - Code organization
- [SERVICE_LAYER_DELIVERY.md](SERVICE_LAYER_DELIVERY.md) - What was delivered


## 💬 NOTES

**Remember**:
- Always use Services, never DatabaseManager directly
- Always validate input (errors are caught)
- Always handle custom exceptions
- Check permissions before operations
- Stock deduction is automatic with complete_transaction()


---

This is the **quick reference**. For more details, see the full documentation files.
