# ============================================================================
# REFACTORED ARCHITECTURE DOCUMENTATION
# ============================================================================
# Program-Kasir POS System - Clean Layered Architecture (v2.0)
# ============================================================================

## 📁 NEW FOLDER STRUCTURE

```
Program-Kasir/
├── src/                                 # NEW: Refactored application code
│   │
│   ├── __init__.py                     # Main entry point for all layers
│   │
│   ├── core/                           # CORE LAYER (Models, Validators, Exceptions)
│   │   ├── __init__.py
│   │   ├── exceptions.py               # ✨ NEW: Custom exception classes
│   │   ├── models.py                   # Domain models (Product, Transaction, User, etc)
│   │   └── validators.py               # ✨ NEW: Centralized validation rules
│   │
│   ├── repository/                     # REPOSITORY LAYER (Data Access)
│   │   ├── __init__.py
│   │   ├── base_repository.py          # Abstract base repository
│   │   ├── product_repository.py       # Product & Inventory data access
│   │   ├── transaction_repository.py   # Transaction data access
│   │   ├── user_repository.py          # User data access
│   │   └── repository_factory.py       # ✨ NEW: Repository factory for DI
│   │
│   ├── service/                        # SERVICE LAYER (Business Logic) ⭐ MAIN REFACTOR
│   │   ├── __init__.py
│   │   ├── base_service.py             # ✨ NEW: Base service + ProductService
│   │   ├── stock_service.py            # ✨ NEW: Stock management service
│   │   ├── transaction_service.py      # ✨ NEW: Transaction processing service
│   │   ├── auth_service.py             # ✨ NEW: Authentication service
│   │   └── service_factory.py          # ✨ NEW: Service factory for DI
│   │
│   └── presentation/                   # PRESENTATION LAYER (CLI) - TODO
│       └── __init__.py
│
├── (legacy files - still used)         # Backward compatibility
│   ├── database.py                     # (can be removed after full migration)
│   ├── models.py
│   ├── transaction.py
│   ├── auth_manager.py
│   ├── config_manager.py
│   ├── logger_config.py
│   └── ...other files
│
├── REFACTORING_PLAN.md                 # This file
└── ...other files
```


## 🏗️ LAYERED ARCHITECTURE OVERVIEW

### Layer 1: CORE LAYER (`src/core/`)
**Purpose**: Domain models, validation rules, custom exceptions, utilities

**Components**:
- `exceptions.py`: Custom exception hierarchy (ValidationError, AuthenticationError, etc)
- `models.py`: Domain entities using @dataclass (Product, Transaction, User, etc)
- `validators.py`: Centralized validation rules for all entities

**Characteristics**:
- ✅ Zero dependencies on other layers
- ✅ Pure data classes (no business logic)
- ✅ Reusable across entire application
- ✅ Easy to test

**Example**:
```python
from src.core import Product, ValidationError, ProductValidator

# Validate input
kode = ProductValidator.validate_kode("PROD001")
nama = ProductValidator.validate_nama("Produk Bagus")

# Use domain models
product = Product(id=1, kode=kode, nama=nama, harga=50000, stok=100)
```


### Layer 2: REPOSITORY LAYER (`src/repository/`)
**Purpose**: All database access operations (CRUD)

**Components**:
- `base_repository.py`: Abstract base class with common methods
- `product_repository.py`: ProductRepository, InventoryRepository
- `transaction_repository.py`: TransactionRepository
- `user_repository.py`: UserRepository
- `repository_factory.py`: Factory for DI

**Characteristics**:
- ✅ Isolates SQL queries
- ✅ Provides consistent interface (CRUD)
- ✅ Built-in caching support
- ✅ Atomic transactions
- ✅ Easy to mock for testing

**Example**:
```python
from src.repository import RepositoryFactory

factory = RepositoryFactory()
product_repo = factory.product_repository()

# Get product with caching
product = product_repo.get_by_kode("PROD001")

# Update stock (atomic)
new_stock = product_repo.update_stok(product_id=1, qty_change=-10)
```


### Layer 3: SERVICE LAYER (`src/service/`)  ⭐ **MAIN REFACTORING**
**Purpose**: All business logic (orchestration, validation, complex operations)

**Components**:
- `base_service.py`: BaseService class + ProductService
- `stock_service.py`: Stock management (deduct, add, validate stok)
- `transaction_service.py`: Transaction processing (create, add items, complete)
- `auth_service.py`: Authentication & user management
- `service_factory.py`: Factory for DI

**Workflow**:
1. Service validates input using validators
2. Service checks business rules
3. Service calls repository for data access
4. Service logs all operations
5. Service returns domain models

**Characteristics**:
- ✅ No SQL queries (uses repositories)
- ✅ No direct UI concerns (returns data objects)
- ✅ Comprehensive error handling
- ✅ Logging every operation
- ✅ Dependency injection
- ✅ Easy to unit test (just mock repositories)

**Example**:
```python
from src.service import ServiceFactory

factory = ServiceFactory()
transaction_svc = factory.transaction_service()
product_svc = factory.product_service()

# Create transaction
transaction = transaction_svc.create_transaction(cashier_id=1)

# Add items
transaction_svc.add_item(
    product_id=1,
    product_code="PROD001",
    product_name="Produk Bagus",
    qty=5,
    harga_satuan=50000
)

# Process payment
amount, change = transaction_svc.process_payment("cash", 300000)

# Complete (saves + deducts stock)
transaction_id = transaction_svc.complete_transaction()
```


### Layer 4: PRESENTATION LAYER (`src/presentation/`)  - TODO
**Purpose**: CLI interface, user interaction

**Will contain**:
- Menu handlers
- Input/output formatting
- User experience (loading indicators, confirmations, etc)
- Session management

**Characteristics**:
- ✅ Zero business logic
- ✅ Calls services only
- ✅ Format output using models.format_rp()
- ✅ Handle user input validation
- ✅ Catch exceptions & show friendly messages


## 🔄 DATA FLOW EXAMPLE

### Scenario: Customer Buys 5 items

```
┌─────────────────────────────────────────────────────────┐
│ PRESENTATION LAYER (CLI)                                 │
│ User inputs: kode produk, qty                            │
└────────────────────┬────────────────────────────────────┘
                     │ calls
                     ▼
┌─────────────────────────────────────────────────────────┐
│ SERVICE LAYER                                            │
│ TransactionService.add_item(                             │
│   - Validates qty using QuantityValidator               │
│   - Calls StockService.validate_stock_available()       │
│   - StockService -> ProductRepository.get_by_id()       │
│   - Checks if stock >= qty                              │
│   - Creates TransactionItem object                      │
│ )                                                        │
└────────────────────┬────────────────────────────────────┘
                     │ returns
                     ▼
┌─────────────────────────────────────────────────────────┐
│ Success: Item added to transaction                      │
│ Back to PRESENTATION: Show summary                      │
└─────────────────────────────────────────────────────────┘

[REPEAT for each item]

Then:

┌─────────────────────────────────────────────────────────┐
│ USER COMPLETES TRANSACTION (PRESENTATION)               │
│ TransactionService.complete_transaction()               │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ SERVICE LAYER: TransactionService                       │
│ 1. Save transaction to DB                               │
│    -> TransactionRepository.create()                    │
│ 2. Deduct stock for each item                           │
│    -> StockService.deduct_stock()                       │
│    -> ProductRepository.update_stok()                   │
│ 3. Record inventory movements                           │
│    -> InventoryRepository.create()                      │
│ 4. Log transaction completion                           │
└────────────────────┬────────────────────────────────────┘
                     │ returns
                     ▼
┌─────────────────────────────────────────────────────────┐
│ Transaction ID = 12345                                  │
│ PRESENTATION: Generate receipt & show to user           │
└─────────────────────────────────────────────────────────┘
```


## ⚙️ KEY IMPROVEMENTS

### Before (Old Architecture)
```python
# Business logic MIXED with database access
class TransactionHandler:
    def complete_transaction(self, transaction):
        # Database operations mixed in
        cursor.execute("INSERT INTO transactions ...")
        cursor.execute("UPDATE products SET stok = stok - ?")
        # No validation
        # No error handling
        # Logging scattered
```

### After (New Architecture)
```python
# Clean separation: Service orchestrates, Repository accesses DB
class TransactionService:
    def complete_transaction(self):
        # 1. Validation done in validators
        # 2. Business logic (stock deduction) via StockService
        # 3. Database access via repositories
        # 4. Comprehensive logging
        # 5. Error handling with custom exceptions
        
        try:
            self.repositories['transaction'].create(transaction)
            self.stock_service.deduct_stock(...)
            self.repositories['inventory'].create(...)
            self._log_operation(...)
            return transaction_id
        except InsufficientStockError as e:
            self._log_error(...)
            raise
```

### Benefits
✅ **Testability**: Mock repositories, test services in isolation
✅ **Maintainability**: Business logic in one place (service)
✅ **Reusability**: Services usable by CLI, API, GUI
✅ **Scalability**: Easy to add new services
✅ **Error Handling**: Custom exceptions, consistent handling
✅ **Logging**: Every operation logged
✅ **Caching**: Built-in via repositories
✅ **Validation**: Centralized, reusable validators


## 🔌 DEPENDENCY INJECTION

Uses factory pattern for dependency injection:

```python
from src.service import ServiceFactory

# Create factory (handles all dependencies)
service_factory = ServiceFactory("kasir_pos.db")

# Get services (singleton instances)
product_service = service_factory.product_service()
transaction_service = service_factory.transaction_service()
stock_service = service_factory.stock_service()
auth_service = service_factory.auth_service()

# Services are already connected with their repositories
# No need to manually pass dependencies
```


## 📋 MIGRATION PATH

### Phase 1: ✅ COMPLETED
- [x] Create core layer (exceptions, models, validators)
- [x] Create repository layer (data access)
- [x] Create service layer (business logic)
- [x] Create service factory

### Phase 2: TODO - NEXT
- [ ] Create presentation layer (refactor main.py)
- [ ] Update existing code to use new services
- [ ] Gradual replacement of old modules

### Phase 3: TODO
- [ ] Add caching layer
- [ ] Add performance monitoring
- [ ] Add advanced analytics

### Phase 4: TODO
- [ ] Remove old modules (database.py, models.py, transaction.py, etc)
- [ ] Final cleanup & documentation


## 🧪 TESTING EXAMPLE

Old way (hard to test):
```python
# All mixed together, hard to mock
def test_transaction():
    db = DatabaseManager()  # Real database!
    service = TransactionService(db)
    result = service.complete_transaction()
    # Limited testing
```

New way (easy to test):
```python
# Easy to mock repositories
class MockProductRepository:
    def get_by_id(self, id):
        return Product(id=1, kode=\"TEST\", stok=100, ...)

class MockTransactionRepository:
    def create(self, transaction):
        return 999

# Test with mocks
factory = ServiceFactory()
factory.repository_factory._product_repo = MockProductRepository()
factory.repository_factory._transaction_repo = MockTransactionRepository()

service = factory.transaction_service()
result = service.complete_transaction()

assert result == 999  # Easy to assert!
```


## 📚 USAGE GUIDE

### For CLI/Presentation Layer
```python
from src.service import ServiceFactory

factory = ServiceFactory()

# Login
auth = factory.auth_service()
session = auth.login(\"admin\", \"password123\")

# Create transaction
transaction_svc = factory.transaction_service()
trans = transaction_svc.create_transaction(session.user_id)

# Add items
transaction_svc.add_item(
    product_id=1, product_code=\"ABC\", product_name=\"Item\",
    qty=5, harga_satuan=50000
)

# Complete
trans_id = transaction_svc.complete_transaction()
print(f\"Transaction saved: {trans_id}\")
```

### For Error Handling
```python
from src.core import (
    InsufficientStockError, ValidationError, AuthenticationError
)

try:
    transaction_svc.complete_transaction()
except InsufficientStockError as e:
    print(f\"❌ {e.message}\")  # \"Stok tidak cukup...\"
except ValidationError as e:
    print(f\"❌ Validasi gagal: {e.field} - {e.message}\")
except AuthenticationError as e:
    print(f\"❌ Login failed: {e.message}\")
except Exception as e:
    print(f\"❌ Unexpected error: {e}\")
```


## 🎯 NEXT STEPS

1. **Test the new architecture** with existing code
2. **Create presentation layer** (refactor CLI in main.py)
3. **Migrate existing functionality** to use new services
4. **Add performance optimizations** (caching, indexing)
5. **Implement advanced features** (analytics, smart suggestions)
6. **Remove old modules** when safe

---

**Status**: ✅ Core layers complete. Ready for phase 2 (presentation layer).
**Date**: April 2026
