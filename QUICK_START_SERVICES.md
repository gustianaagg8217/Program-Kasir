# ============================================================================
# QUICK START GUIDE - Using the Refactored SERVICE LAYER
# ============================================================================

## 🚀 Quick Start (5 minutes)

### 1. Initialize the Service Factory

```python
from src.service import ServiceFactory

# Create factory (initializes all services & repositories with DI)
factory = ServiceFactory(db_path=\"kasir_pos.db\")

# Get services
product_svc = factory.product_service()
transaction_svc = factory.transaction_service()
stock_svc = factory.stock_service()
auth_svc = factory.auth_service()
```


### 2. Authentication Example

```python
from src.core import AuthenticationError

auth_svc = factory.auth_service()

try:
    # Login user
    session = auth_svc.login(username=\"admin\", password=\"password123\")
    
    print(f\"✅ Logged in as: {session.nama_lengkap} ({session.role})\")
    # Output: ✅ Logged in as: Administrator (admin)
    
    # Check permissions
    if session.has_permission(\"produk.create\"):
        print(\"User can create products\")
    
except AuthenticationError as e:
    print(f\"❌ Login failed: {e.message}\")
```


### 3. Product Management Example

```python
from src.core import ProductValidationError

product_svc = factory.product_service()

# Create product
try:
    product = product_svc.create_product(
        kode=\"COLA750\",
        nama=\"Coca Cola 750ml\",
        harga=25000,
        stok=100,
        min_stok=20,
        kategori=\"Minuman\"
    )
    print(f\"✅ Product created: ID={product.id}\")
    
except ProductValidationError as e:
    print(f\"❌ Validation error: {e.message}\")

# Get product
product = product_svc.get_product_by_kode(\"COLA750\")
print(f\"Product: {product.nama}, Price: Rp {product.harga:,}, Stock: {product.stok}\")

# Update product
product_svc.update_product(
    product_id=product.id,
    harga=26000,  # Price increase
    nama=\"Coca Cola 750ml (Updated)\"
)
print(\"✅ Product updated\")

# List products
products = product_svc.list_products()
print(f\"Total products: {len(products)}\")
for p in products:
    print(f\"  - {p.kode}: {p.nama} (Rp {p.harga:,})\")

# Search products
results = product_svc.search_products_by_name(\"cola\")
print(f\"Found {len(results)} products matching 'cola'\")

# Get low stock products
low_stock = product_svc.get_low_stock_products()
if low_stock:
    print(f\"⚠️  {len(low_stock)} products with low stock:\")
    for p in low_stock:
        print(f\"  - {p.nama}: {p.stok} units (min: {p.min_stok})\")
```


### 4. Transaction Processing Example (Main Feature)

```python
from src.core import InsufficientStockError, TransactionError, PaymentError, format_rp

transaction_svc = factory.transaction_service()
session = auth_svc.login(\"cashier1\", \"pass123\")

# ┌─ Step 1: Create new transaction
transaction = transaction_svc.create_transaction(cashier_id=session.user_id)
print(\"✅ New transaction created\")

# ┌─ Step 2: Add items
try:
    transaction_svc.add_item(
        product_id=1,
        product_code=\"COLA750\",
        product_name=\"Coca Cola 750ml\",
        qty=5,
        harga_satuan=25000,
        discount_pct=10.0,  # 10% discount
        tax_pct=10.0        # 10% tax
    )
    print(f\"✅ Item 1 added - Subtotal: {format_rp(5 * 25000)}\")
    
    transaction_svc.add_item(
        product_id=2,
        product_code=\"SPRITE500\",
        product_name=\"Sprite 500ml\",
        qty=3,
        harga_satuan=15000,
        discount_pct=5.0,
        tax_pct=10.0
    )
    print(f\"✅ Item 2 added - Subtotal: {format_rp(3 * 15000)}\")
    
except InsufficientStockError as e:
    print(f\"❌ Stock issue: {e.message}\")
except Exception as e:
    print(f\"❌ Error adding item: {e.message}\")

# ┌─ Step 3: View transaction summary
print(f\"\\n📋 Transaction Summary:\")
print(f\"Total items: {len(transaction.items)}\")
print(f\"Subtotal (before tax): {format_rp(transaction.total_sebelum_pajak)}\")
print(f\"Tax: {format_rp(transaction.total_pajak)}\")
print(f\"Total: {format_rp(transaction.total)}\")

# ┌─ Step 4: Process payment
try:
    amount_received, change = transaction_svc.process_payment(
        payment_method=\"cash\",
        amount_received=200000  # Customer pays 200k
    )
    print(f\"\\n💰 Payment Processed:\")
    print(f\"Amount received: {format_rp(amount_received)}\")
    print(f\"Change: {format_rp(change)}\")
    
except PaymentError as e:
    print(f\"❌ Payment error: {e.message}\")

# ┌─ Step 5: Complete transaction (saves to DB & deducts stock)
try:
    transaction_id = transaction_svc.complete_transaction()
    print(f\"\\n✅ Transaction completed! ID: {transaction_id}\")
    print(f\"Stock has been automatically deducted.\")
    print(f\"Receipt can now be printed.\")
    
except TransactionError as e:
    print(f\"❌ Transaction failed: {e.message}\")
```


### 5. Stock Management Example

```python
stock_svc = factory.stock_service()

# Deduct stock when selling (automatic with complete_transaction)
# But can also be manual:
try:
    new_stock = stock_svc.deduct_stock(
        product_id=1,
        qty_to_deduct=10,
        notes=\"Manual deduction for damage\"
    )
    print(f\"✅ Stock deducted. New level: {new_stock}\")
except InsufficientStockError as e:
    print(f\"❌ {e.message}\")

# Add stock during restocking
new_stock = stock_svc.add_stock(
    product_id=1,
    qty_to_add=50,
    notes=\"Restock from supplier ABC\"
)
print(f\"✅ Stock added. New level: {new_stock}\")

# Adjust stock (for inventory corrections)
adjustment = stock_svc.adjust_stock(
    product_id=1,
    new_stock_level=100,
    reason=\"Physical inventory count correction\"
)
print(f\"✅ Stock adjusted by {adjustment} units\")

# View stock movements history
movements = stock_svc.get_product_movements(product_id=1)
print(f\"\\n📊 Stock movements for product 1:\")
for m in movements:
    operation_label = \"➕ In\" if m.qty_change > 0 else \"➖ Out\"
    print(f\"{m.created_at} | {operation_label} {abs(m.qty_change)} | {m.operation}\")
```


### 6. User Management Example

```python
from src.core import ValidationError

auth_svc = factory.auth_service()

# Create new user
try:
    new_user = auth_svc.create_user(
        username=\"cashier2\",
        password=\"securepass123\",
        role=\"cashier\",
        nama_lengkap=\"Budi Santoso\"
    )
    print(f\"✅ User created: {new_user.username}\")
except ValidationError as e:
    print(f\"❌ Validation error: {e.message}\")

# List all users
users = auth_svc.list_users()
print(f\"\\nTotal active users: {len(users)}\")
for u in users:
    print(f\"  - {u.username} ({u.role}) - {u.nama_lengkap}\")

# Get user details
user = auth_svc.get_user(user_id=2)
if user:
    print(f\"User: {user.nama_lengkap} ({user.role})\")
    
    # Get user permissions
    permissions = auth_svc.get_user_permissions(user.role)
    print(f\"Permissions: {', '.join(permissions[:3])}...\")

# Update user
auth_svc.update_user(
    user_id=2,
    nama_lengkap=\"Budi Santoso (Updated)\"
)
print(\"✅ User updated\")

# Change user password
try:
    success = auth_svc.change_password(
        user_id=2,
        old_password=\"securepass123\",
        new_password=\"newpass456\"
    )
    print(f\"✅ Password changed\")
except Exception as e:
    print(f\"❌ {e.message}\")

# Deactivate user
auth_svc.deactivate_user(user_id=2)
print(\"✅ User deactivated\")
```


### 7. Error Handling Best Practices

```python
from src.core import (
    POSException,
    ValidationError, AuthenticationError, AuthorizationError,
    InsufficientStockError, ProductNotFoundError,
    TransactionError, PaymentError, DatabaseError
)

def safe_transaction_processing():
    \"\"\"Example of proper error handling.\"\"\"
    
    try:
        # Business logic here
        transaction_svc.complete_transaction()
        
    # Handle specific errors with user-friendly messages
    except ValidationError as e:
        print(f\"❌ Please check your input: {e.message}\")
        if e.field:
            print(f\"   Field: {e.field}\")
    
    except InsufficientStockError as e:
        print(f\"❌ Stock problem: {e.message}\")
        print(f\"   Product: {e.product_name}\")
        print(f\"   Required: {e.required}, Available: {e.available}\")
    
    except PaymentError as e:
        print(f\"❌ Payment issue: {e.message}\")
    
    except AuthenticationError as e:
        print(f\"❌ Login failed: {e.message}\")
    
    except AuthorizationError as e:
        print(f\"❌ Permission denied: {e.message}\")
        print(f\"   Required role: {e.required_role}\")
    
    except DatabaseError as e:
        print(f\"❌ Database error: {e.message}\")
        if e.operation:
            print(f\"   Operation: {e.operation}\")
    
    except TransactionError as e:
        print(f\"❌ Transaction failed: {e.message}\")
    
    except POSException as e:
        # Catch-all for any POS exception
        print(f\"❌ POS Error [{e.code}]: {e.message}\")
    
    except Exception as e:
        # Unexpected error
        print(f\"❌ Unexpected error: {str(e)}\")
        import traceback
        traceback.print_exc()


# Safe function call
safe_transaction_processing()
```


### 8. Complete Workflow Example

```python
def complete_sales_workflow():
    \"\"\"
    Complete workflow: Login → Create Transaction → Add Items → Process → Complete
    \"\"\"
    
    try:
        factory = ServiceFactory()
        
        # 1️⃣ AUTHENTICATION
        auth_svc = factory.auth_service()
        session = auth_svc.login(\"cashier1\", \"password123\")
        print(f\"✅ Logged in: {session.nama_lengkap}\")
        
        # 2️⃣ CHECK PERMISSION
        if not session.has_permission(\"transaksi.create\"):
            print(\"❌ Permission denied\")
            return
        
        # 3️⃣ CREATE TRANSACTION
        transaction_svc = factory.transaction_service()
        transaction_svc.create_transaction(cashier_id=session.user_id)
        print(\"✅ Transaction started\")
        
        # 4️⃣ ADD ITEMS
        items_to_process = [
            {\"kode\": \"COLA750\", \"qty\": 5},
            {\"kode\": \"SPRITE500\", \"qty\": 3},
        ]
        
        product_svc = factory.product_service()
        for item in items_to_process:
            product = product_svc.get_product_by_kode(item[\"kode\"])
            
            if not product:
                print(f\"⚠️  Product {item['kode']} not found, skipping\")
                continue
            
            transaction_svc.add_item(
                product_id=product.id,
                product_code=product.kode,
                product_name=product.nama,
                qty=item[\"qty\"],
                harga_satuan=product.harga,
                discount_pct=0.0,
                tax_pct=10.0
            )
            print(f\"✅ Added: {product.nama} x {item['qty']}\")
        
        # 5️⃣ SHOW SUMMARY
        trans = transaction_svc.current_transaction
        print(f\"\\n📋 Summary: {len(trans.items)} items, Total: {format_rp(trans.total)}\")
        
        # 6️⃣ PROCESS PAYMENT
        transaction_svc.process_payment(
            payment_method=\"cash\",
            amount_received=200000
        )
        print(f\"💰 Payment: {format_rp(transaction_svc.current_transaction.kembalian)} change\")
        
        # 7️⃣ COMPLETE
        transaction_id = transaction_svc.complete_transaction()
        print(f\"\\n✅ SUCCESS! Transaction ID: {transaction_id}\")
        print(\"✅ Stock deducted automatically\")
        print(\"✅ Receipt ready to print\")
        
    except Exception as e:
        print(f\"❌ Error: {e.message if hasattr(e,'message') else str(e)}\")


# Run complete workflow
complete_sales_workflow()
```


## 📚 Comparison: Old vs New

### Old Code
```python
# Mixed concerns - hard to test, maintain
db = DatabaseManager()
transaction = Transaction()
transaction.add_item(product_id=1, qty=5)
transaction.save_to_db(db)  # Business logic in UI

# Validation scattered
if qty <= 0:
    # invalid
elif stok < qty:
    # invalid
```

### New Code
```python
# Clean separation of concerns
factory = ServiceFactory()
transaction_svc = factory.transaction_service()

transaction_svc.create_transaction()
transaction_svc.add_item(product_id=1, qty=5)  # Validation inside
transaction_id = transaction_svc.complete_transaction()  # Atomic operation

# All validation centralized
# All errors are custom exceptions (easy to handle)
# All logging automatic
```


## 🎯 Key Benefits

✅ **No direct database access** in presentation code
✅ **Automatic validation** on all inputs
✅ **Automatic logging** of all operations
✅ **Consistent error handling** with custom exceptions
✅ **Atomic transactions** (stock deduction + save together)
✅ **Easy testing** (mock repositories)
✅ **Reusable services** (CLI, API, GUI can all use same services)


## 📖 Next Steps

1. **Replace old `main.py`** with presentation layer using these services
2. **Remove old modules** (database.py, transaction.py, models.py) after migration
3. **Add caching** for heavy queries
4. **Add performance monitoring**
5. **Implement analytics** using the data layer


---

**Remember**: Always use Services, never access Database directly!
