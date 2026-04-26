# 🏗️ REFACTORING PHASE 1-2: SCALABLE ARCHITECTURE

## 📌 Ringkasan

Phase 1-2 mengimplementasikan **arsitektur berlapis** (layered architecture) untuk memisahkan:
- **GUI Layer** (Tkinter) - Only UI rendering
- **Service Layer** - Business logic
- **Repository Layer** - Database access
- **Utilities** - Config, error handling

Ini adalah langkah pertama menuju sistem yang scalable, maintainable, dan ready untuk web/API migration di masa depan.

---

## 🎯 Deliverables Phase 1-2

### ✅ Struktur Folder Baru

```
Program-Kasir/
├── app/
│   ├── __init__.py                          ← Module description & architecture docs
│   ├── services/
│   │   ├── __init__.py
│   │   ├── product_service.py               ← Product business logic (EXAMPLE)
│   │   ├── transaction_service.py           ← TODO Phase 3
│   │   └── user_service.py                  ← TODO Phase 3
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── product_repository.py            ← Product database access (EXAMPLE)
│   │   ├── transaction_repository.py        ← TODO Phase 3
│   │   └── user_repository.py               ← TODO Phase 3
│   ├── models/
│   │   └── __init__.py                      ← TODO: Enhanced data models
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── demand_prediction.py             ← Placeholder AI module
│   │   └── smart_restock.py                 ← TODO Phase 3
│   └── utils/
│       ├── __init__.py
│       ├── config_loader.py                 ← Global configuration (IMPLEMENTED ✅)
│       ├── error_handler.py                 ← Centralized error handling (IMPLEMENTED ✅)
│       └── __init__.py
```

### ✅ Modules Implemented

#### 1. **app/utils/config_loader.py** ✅
```python
from app.utils.config_loader import config, is_feature_enabled

# Usage:
store_name = config.get("store.name")
is_telegram_enabled = is_feature_enabled("telegram")
is_ai_enabled = is_feature_enabled("ai")
```

**Fitur:**
- Singleton pattern (one instance globally)
- Dot notation untuk akses nested keys
- Feature flags support
- Default config jika file tidak ada
- Reload capability (untuk development)

---

#### 2. **app/utils/error_handler.py** ✅
```python
from app.utils.error_handler import ErrorHandler, PosError, ValidationError

# Usage di services:
try:
    product = product_service.create_product(...)
except Exception as e:
    error_code, user_message = ErrorHandler.handle(e, "product_creation")
    messagebox.showerror("Error", user_message)
```

**Fitur:**
- Custom PosError exceptions hierarchy
- Type-safe error handling
- User-friendly error messages
- Automatic logging
- Error codes untuk tracking

---

#### 3. **app/repositories/product_repository.py** ✅ (CONTOH)
```python
from app.repositories.product_repository import ProductRepository

# Usage:
repo = ProductRepository(db)
product = repo.get_by_kode("SKU001")
products = repo.list_all(limit=100)
repo.update(product_id, nama="New Name", harga=50000)
```

**CRUD Operations:**
- ✅ `create()` - Insert produk baru
- ✅ `get_by_id()` - Get by product ID
- ✅ `get_by_kode()` - Get by product kode
- ✅ `list_all()` - List dengan pagination
- ✅ `update()` - Update fields
- ✅ `delete()` - Delete produk
- ✅ `search()` - Search by kode or nama
- ✅ `get_low_stock()` - Get low stock products

---

#### 4. **app/services/product_service.py** ✅ (CONTOH)
```python
from app.services.product_service import ProductService

# Usage:
service = ProductService(product_repo)
product = service.get_product("SKU001")
service.reduce_stock("SKU001", 5)  # Untuk transaksi
service.increase_stock("SKU001", 10)  # Untuk stok opname
```

**Business Logic Methods:**
- ✅ `create_product()` - With validation & duplicate check
- ✅ `get_product()` - By kode
- ✅ `list_products()` - All products
- ✅ `update_product()` - With validation
- ✅ `delete_product()` - With existence check
- ✅ `search_products()` - Search & filter
- ✅ `reduce_stock()` - For transactions (with stock check)
- ✅ `increase_stock()` - For inventory adjustments
- ✅ `get_low_stock_products()` - Low stock alerts
- ✅ `get_total_inventory_value()` - Calculate total value

---

#### 5. **app/ai/demand_prediction.py** ✅ (PLACEHOLDER)
```python
from app.ai.demand_prediction import DemandPredictor

# Usage (Phase 3+):
predictor = DemandPredictor()
prediction = predictor.predict_demand(product_id=1, days_ahead=7)
top_products = predictor.predict_top_products(top_n=10)
```

**Status:** Placeholder untuk Phase 3 (ML implementation with XGBoost)

---

### ✅ Config.json Updated

Tambahan feature flags:
```json
{
  "features": {
    "telegram": false,
    "ai": false,
    "stok_opname": true,
    "backup": true,
    "async_operations": true,
    "new_architecture": true
  },
  "app": {
    "debug": false,
    "async_enabled": true,
    "cache_enabled": true,
    "use_new_services": true
  }
}
```

---

## 📚 ARSITEKTUR LAYER

### Diagram Data Flow

```
User Input (GUI)
    ↓
    ↓ (Tkinter UI - no logic)
    ↓
Service Layer
    ↓ (Business rules, validation, transactions)
    ├─→ ProductService
    ├─→ TransactionService
    └─→ UserService
    ↓
Repository Layer
    ↓ (Database access only)
    ├─→ ProductRepository
    ├─→ TransactionRepository
    └─→ UserRepository
    ↓
Database (SQLite)
```

### Responsibility Breakdown

| Layer | Tanggung Jawab | Contoh |
|-------|---|---|
| **GUI** | Render, user input, call services | `button.click() → product_service.create_product()` |
| **Service** | Business logic, validation, transactions | Cek stok, hitung harga, validasi input |
| **Repository** | Database CRUD only | Insert, select, update, delete |
| **Database** | Data persistence | SQLite tables |

---

## 🔄 Contoh Usage di GUI

### Sebelum (Masalah):
```python
# ❌ GUI mencampur logic & database
def add_product(self):
    # Business logic di GUI
    try:
        kode = self.kode_entry.get()
        nama = self.nama_entry.get()
        
        # Database access langsung
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO products...")  # Logic & DB campur!
            
        messagebox.showinfo("OK", "Sukses")
    except Exception as e:
        messagebox.showerror("Error", str(e))  # User error message berisi technical details
```

### Sesudah (Benar):
```python
# ✅ GUI hanya render & call service
from app.services.product_service import ProductService
from app.utils.error_handler import ErrorHandler

def add_product(self):
    try:
        kode = self.kode_entry.get()
        nama = self.nama_entry.get()
        harga = int(self.harga_entry.get())
        qty = int(self.qty_entry.get())
        
        # Call service (business logic ter-encapsulate)
        product = self.product_service.create_product(kode, nama, harga, qty)
        
        messagebox.showinfo("✅ Sukses", f"Produk {product.nama} berhasil dibuat!")
        
    except Exception as e:
        error_code, user_message = ErrorHandler.handle(e, "product_creation")
        messagebox.showerror("Error", user_message)  # User-friendly message
```

---

## 🚀 Testing Phase 1-2

### Import Test
```python
# Test imports work
from app.utils.config_loader import config, is_feature_enabled
from app.utils.error_handler import ErrorHandler, PosError
from app.repositories.product_repository import ProductRepository
from app.services.product_service import ProductService
from app.ai.demand_prediction import DemandPredictor

print("✅ All imports successful")
```

### Config Test
```python
from app.utils.config_loader import config

store_name = config.get("store.name")
print(f"Store: {store_name}")

is_ai_enabled = is_feature_enabled("ai")
print(f"AI Enabled: {is_ai_enabled}")
```

### Service Test
```python
from database import DatabaseManager
from app.repositories.product_repository import ProductRepository
from app.services.product_service import ProductService

db = DatabaseManager()
repo = ProductRepository(db)
service = ProductService(repo)

# Test CRUD
product = service.create_product("TEST001", "Test Produk", 50000, 10)
print(f"✅ Created: {product.nama}")

fetched = service.get_product("TEST001")
print(f"✅ Fetched: {fetched.nama if fetched else 'Not found'}")
```

---

## 📋 Phase 3-4 Planning

### Phase 3: Security & AI Placeholders
- ✅ Add bcrypt password hashing
- ✅ UserService & UserRepository
- ✅ TransactionService & TransactionRepository
- ✅ AI demand prediction placeholders

### Phase 4: Async & Printing
- ✅ Async operations (threading untuk heavy tasks)
- ✅ Cross-platform printing (Windows/Linux/Mac)
- ✅ GUI refactoring ke new architecture

### Phase 5: Migration Ready
- ✅ API ready (dapat langsung diconvert ke FastAPI)
- ✅ React frontend ready
- ✅ WebSocket support

---

## 📝 Best Practices Diimplementasikan

1. ✅ **Single Responsibility Principle** - Tiap layer punya 1 responsibility
2. ✅ **Dependency Injection** - Services inject repositories
3. ✅ **Error Handling** - Centralized, consistent error management
4. ✅ **Logging** - All operations logged untuk debugging
5. ✅ **Configuration Management** - Global config dengan feature flags
6. ✅ **Type Safety** - Type hints di semua functions
7. ✅ **Documentation** - Docstrings untuk semua public methods
8. ✅ **Testability** - Layered design memudahkan unit testing

---

## ⚠️ Migration Path (Phase 1-2 → Production)

### Step-by-step untuk adopt new architecture:

1. **Keep existing code running** - Belum refactor GUI
2. **Use new services for new features** - Stok Opname bisa langsung pake ProductService
3. **Gradual migration** - Product management → Refactor ke ProductService
4. **Test thoroughly** - Ensure no feature regression
5. **Production deployment** - Full migration setelah semua tested

---

## 🎓 Dokumentasi untuk Developer

Setiap module punya comprehensive docstrings:
- Purpose & responsibility
- Usage examples
- Parameters & return types
- Error cases & exceptions

Gunakan IDE intellisense untuk explore:
```python
from app.services.product_service import ProductService
service = ProductService(...)  # Ctrl+Click untuk see documentation
```

---

## ✅ Phase 1-2 COMPLETE

Seluruh Phase 1-2 sudah implemented. Sistem siap untuk:
- ✅ Phase 3: Add security + more services
- ✅ Phase 4: Add async/threading
- ✅ Phase 5: GUI refactoring + production deployment

Seluruh existing features tetap jalan (backward compatible).

---

**Status:** Ready untuk Phase 3 🚀
