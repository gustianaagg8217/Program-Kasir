# 🏗️ Architecture & Technical Overview

Dokumentasi teknis lengkap untuk developer dan advanced users.

---

## Table of Contents
1. [System Architecture](#system-architecture)
2. [Module Overview](#module-overview)
3. [Data Models](#data-models)
4. [Database Schema](#database-schema)
5. [API Reference](#api-reference)
6. [Data Flow](#data-flow)
7. [Design Patterns](#design-patterns)
8. [Error Handling](#error-handling)
9. [Performance Considerations](#performance-considerations)
10. [Extension Points](#extension-points)

---

## System Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────┐
│          USER INTERFACE (main.py)               │
│         CLI Menu-Driven Interface               │
└──────────────┬──────────────────────────────────┘
               │
       ┌───────┴────────────┬──────────────┬─────────────┐
       │                    │              │             │
┌──────▼──────┐  ┌──────────▼────┐  ┌────▼──────────┐ ┌─▼─────────────┐
│ PRODUCT     │  │ TRANSACTION   │  │  REPORT       │ │   TELEGRAM    │
│ MANAGEMENT  │  │  & SALES      │  │  & ANALYTICS  │ │     BOT       │
│             │  │               │  │               │ │               │
│ models.py   │  │ transaction.py│  │  laporan.py   │ │ telegram_bot  │
│             │  │               │  │               │ │ .py           │
└──────┬──────┘  └───────┬───────┘  └────┬──────────┘ └─┬─────────────┘
       │                 │               │             │
       └─────────────────┼───────────────┼─────────────┘
                         │               │
                    ┌────▼───────────────▼────┐
                    │   DATABASE ENGINE       │
                    │   (database.py)         │
                    │   SQLite3 Manager       │
                    └────┬────────────────────┘
                         │
                    ┌────▼────────────────┐
                    │   kasir_pos.db      │
                    │   (SQLite DB)       │
                    └─────────────────────┘
```

---

## Module Overview

### 1. **main.py** — CLI Interface & Orchestrator

**Responsibility:** User interaction, menu navigation, cross-module coordination

**Key Components:**
```python
class POSSystem:
    - __init__(): Initialize all modules
    - run(): Main loop
    - menu_utama(): Main menu dispatcher
    - menu_produk(): Product management menu
    - menu_transaksi(): Sales transaction menu
    - menu_laporan(): Reporting menu
    - menu_telegram(): Telegram bot menu
```

**Dependencies:**
```
Imports from:
- database.py (DatabaseManager)
- models.py (Product, ValidationError)
- transaction.py (TransactionHandler)
- laporan.py (ReportGenerator, CSVExporter)
- telegram_bot.py (POSTelegramBot, TelegramConfigManager)
```

**Responsibilities:**
- ✓ Display menus and get user input
- ✓ Validate menu choices
- ✓ Route to appropriate handlers
- ✓ Handle errors gracefully
- ✓ Log important operations

---

### 2. **models.py** — Business Entities & Validation

**Responsibility:** Data classes, business logic rules, validation

**Key Components:**
```python
@dataclass
class Product:
    - kode: str (product code)
    - nama: str (product name)
    - harga: int (price in rupiah)
    - stok: int (inventory count)

@dataclass
class Transaction:
    - id: int
    - tanggal: str (YYYY-MM-DD format)
    - jam: str (HH:MM:SS format)
    - total: int
    - bayar: int
    - kembalian: int
    - status: str (completed/cancelled)

@dataclass
class TransactionItem:
    - id: int
    - transaksi_id: int
    - product_kode: str
    - qty: int
    - harga_satuan: int
    - subtotal: int

class ValidationError(Exception):
    - Custom exception for validation failures

class ProductManager:
    - validate_product_input()
    - validate_product_uniqueness()
    - validate_stock_level()

Functions:
- format_rp(amount): Format rupiah currency
- validate_*(): Various validation functions
```

**Validation Rules:**

| Field | Rule | Example |
|-------|------|---------|
| Kode | Min 3, Max 20, unique, alphanumeric | COFFEE, PROD001 |
| Nama | Min 1, Max 100, string | Kopi Hitam |
| Harga | > 0, integer | 15000 |
| Stok | >= 0, integer | 50 |
| Qty | > 0, integer | 2 |

---

### 3. **database.py** — Data Persistence Layer

**Responsibility:** SQLite database operations, data access

**Key Components:**
```python
class DatabaseManager:
    def __init__():
        - Create DB connection
        - Initialize tables
        - Enable constraints

    # Product Operations
    - add_product(kode, nama, harga, stok)
    - get_product(kode)
    - get_all_products()
    - update_product(kode, ...)
    - delete_product(kode)
    - get_stok_summary()
    
    # Transaction Operations
    - add_transaksi(total, bayar, kembalian)
    - add_transaksi_item(transaksi_id, kode, qty, ...)
    - get_transaksi_harian(date)
    - get_transaksi_periode(from_date, to_date)
    
    # Reporting
    - get_database_stats()
    - get_penjualan_harian()
    - get_produk_terlaris(limit)
    - get_stock_analysis()

    # Utilities
    - execute_query(sql)
    - close()
```

**Context Manager Support:**
```python
# Auto-commit/rollback with context manager
with DatabaseManager() as db:
    db.add_product(...)  # auto-commits on exit
```

---

### 4. **transaction.py** — Business Logic Layer

**Responsibility:** Transaction processing workflow, receipt generation

**Key Components:**
```python
class TransactionService:
    def __init__(db):
        - Cache database reference
    
    Methods:
    - add_item(kode, qty): Add item to cart
    - remove_item(index): Remove item
    - get_items(): Get current cart
    - set_payment(total, nominal): Process payment
    - save_transaction(): Persist to database
    - get_kembalian(): Calculate change
    - validate_stock(): Check inventory

class ReceiptManager:
    def __init__(db):
        - Initialize receipt handler
    
    Methods:
    - generate_receipt(transaksi): Create receipt
    - save_receipt(transaksi_id): Save to file
    - display_receipt(transaksi): Print to console
    - format_receipt(): Format output

class TransactionHandler:
    def __init__(db):
        - High-level handler
    
    Methods:
    - process_transaction(): Complete flow
    - handle_error(): Error recovery
    - create_and_save(): Full lifecycle
```

**Transaction Workflow:**
```
START
  ↓
ADD ITEM → [qty, harga] → Cart
  ↓
VALIDATE STOCK
  ↓
PAYMENT PROCESS
  ├─ Cek: nominal >= total
  ├─ Hitung: kembalian
  └─ Set: pembayaran valid
  ↓
SAVE TRANSACTION
  ├─ Insert transaksi row
  ├─ Insert items rows
  └─ Update stok
  ↓
GENERATE RECEIPT
  ├─ Format text
  ├─ Save file
  └─ Display
  ↓
END
```

---

### 5. **laporan.py** — Reporting & Analytics

**Responsibility:** Report generation, data analysis, CSV export

**Key Components:**
```python
class ReportGenerator:
    def __init__(db):
        - Initialize report engine
    
    Methods:
    - get_laporan_harian(date): Daily sales report
    - get_laporan_periode(from, to): Period report
    - get_produk_terlaris(limit=5): Top products
    - get_stok_summary(): Inventory status
    - get_dashboard(): Summary dashboard
    - generate_html_report(): HTML export
    
class ReportFormatter:
    def __init__():
        - Format utilities
    
    Methods:
    - format_table(data): ASCII table
    - format_header(title): Header text
    - format_footer(): Footer text
    - format_currency(amount): Rupiah format
    - format_date(date): Date format
    - format_percentage(value): % format

class CSVExporter:
    def __init__(db):
        - CSV export handler
    
    Methods:
    - export_laporan(filename, data): Export to CSV
    - export_stok(filename): Export inventory
    - export_terlaris(filename): Export top products
```

**Report Examples:**

| Report Type | Source | Output Format |
|------------|--------|---|
| Laporan Harian | TODAY transactions | Console + CSV |
| Laporan Periode | Date range | Console + CSV |
| Produk Terlaris | Transaction items | Ranking table |
| Stok | All products | Inventory summary |
| Dashboard | All data | Summary statistics |

---

### 6. **telegram_bot.py** — External Integration

**Responsibility:** Telegram bot integration, real-time notifications

**Key Components:**
```python
class TelegramConfigManager:
    def __init__():
        - Initialize config handler
    
    Methods:
    - load_config(): Load from JSON
    - save_config(config): Save to JSON
    - validate_config(): Validation
    - get_allowed_ids(): Get auth list
    - set_bot_token(token): Set API key

class POSTelegramBot:
    def __init__():
        - Initialize bot with token from config
    
    Command Handlers:
    - cmd_laporan(): /laporan (daily report)
    - cmd_stok(): /stok (inventory check)
    - cmd_terlaris(): /terlaris (top products)
    - cmd_dashboard(): /dashboard (summary)
    - cmd_ping(): /ping (health check)
    - cmd_help(): /help (help text)
    
    Notification Methods:
    - send_transaction_notification(): New sale alert
    - send_low_stock_alert(): Stock alert
    - send_daily_report(): Schedule report
    - send_message(chat_id, text): Send message
    
    Utilities:
    - check_authorization(update): Verify sender
    - start_polling(): Run bot
    - stop_polling(): Stop bot
```

**Telegram Command Reference:**

| Command | Description | Response |
|---------|-------------|----------|
| /laporan | Get daily sales report | Sales summary |
| /stok | Check inventory status | Stock levels |
| /terlaris | Top 5 products | Ranking |
| /dashboard | Get summary | All metrics |
| /ping | Health check | Pong + timestamp |
| /help | Show help | Command list |

---

## Data Models

### Product Model

```python
@dataclass
class Product:
    kode: str           # PK, 3-20 chars, unique
    nama: str           # Product name, 1-100 chars
    harga: int          # Price > 0
    stok: int           # Stock >= 0
```

**Methods:**
```python
def __str__() → "PROD001 - Kopi Hitam (Rp 15.000) [50 stok]"
def is_valid() → bool
def to_dict() → dict
def from_dict(data) → Product
```

---

### Transaction Model

```python
@dataclass
class Transaction:
    id: int             # Auto-increment, PK
    tanggal: str        # YYYY-MM-DD
    jam: str            # HH:MM:SS
    total: int          # Gross total > 0
    bayar: int          # Amount paid >= total
    kembalian: int      # Change = bayar - total
    status: str         # "completed" or "cancelled"
```

**Relationships:**
```
Transaction 1:N TransactionItem
- One transaction has many items
- Foreign key: transaksi_id
```

---

### TransactionItem Model

```python
@dataclass
class TransactionItem:
    id: int             # Auto-increment, PK
    transaksi_id: int   # FK to Transaction
    product_kode: str   # FK to Product
    qty: int            # > 0
    harga_satuan: int   # Price at time of sale
    subtotal: int       # qty × harga_satuan
```

---

## Database Schema

### Physical Schema

**Table: products**
```sql
CREATE TABLE products (
    kode TEXT PRIMARY KEY,
    nama TEXT NOT NULL UNIQUE,
    harga INTEGER NOT NULL CHECK(harga > 0),
    stok INTEGER NOT NULL CHECK(stok >= 0),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT harga_positive CHECK(harga > 0),
    CONSTRAINT stok_non_negative CHECK(stok >= 0)
);
```

**Table: transaksi**
```sql
CREATE TABLE transaksi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tanggal TEXT NOT NULL,
    jam TEXT NOT NULL,
    total INTEGER NOT NULL CHECK(total > 0),
    bayar INTEGER NOT NULL CHECK(bayar >= total),
    kembalian INTEGER NOT NULL CHECK(kembalian >= 0),
    status TEXT DEFAULT 'completed',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_status CHECK(status IN ('completed', 'cancelled'))
);
```

**Table: transaksi_items**
```sql
CREATE TABLE transaksi_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaksi_id INTEGER NOT NULL,
    product_kode TEXT NOT NULL,
    qty INTEGER NOT NULL CHECK(qty > 0),
    harga_satuan INTEGER NOT NULL,
    subtotal INTEGER NOT NULL,
    
    FOREIGN KEY(transaksi_id) REFERENCES transaksi(id),
    FOREIGN KEY(product_kode) REFERENCES products(kode),
    
    CONSTRAINT qty_positive CHECK(qty > 0)
);
```

**Indexes:**
```sql
CREATE INDEX idx_transaksi_tanggal ON transaksi(tanggal);
CREATE INDEX idx_transaksi_items_product ON transaksi_items(product_kode);
CREATE INDEX idx_transaksi_items_transaksi ON transaksi_items(transaksi_id);
```

---

## API Reference

### DatabaseManager API

#### Product Operations

```python
# Add product
def add_product(kode: str, nama: str, harga: int, stok: int) -> Product
    Raises: sqlite3.IntegrityError if kode already exists

# Get product
def get_product(kode: str) -> Product | None
    Returns: Product object or None

# Get all products
def get_all_products() -> list[Product]
    Returns: All products as list

# Update product
def update_product(kode: str, **kwargs) -> bool
    Available: nama, harga, stok
    Returns: True if updated

# Delete product
def delete_product(kode: str) -> bool
    Returns: True if deleted
```

#### Transaction Operations

```python
# Add transaction
def add_transaksi(total: int, bayar: int, kembalian: int) -> int
    Returns: transaksi_id

# Add transaction item
def add_transaksi_item(transaksi_id: int, product_kode: str, 
                       qty: int, harga_satuan: int) -> int
    Returns: item_id

# Get daily transactions
def get_transaksi_harian(date: str = None) -> list[Transaction]
    Args: date in YYYY-MM-DD format (default: today)
    
# Get period transactions
def get_transaksi_periode(from_date: str, to_date: str) -> list[Transaction]
    Args: dates in YYYY-MM-DD format
```

---

## Data Flow

### Transaction Flow Diagram

```
┌─────────────────────────────────────────────────────┐
│ USER ADDS ITEM (Menu 2)                             │
└──────────────┬──────────────────────────────────────┘
               │
               ▼
        ┌─────────────────────┐
        │ TransactionService  │
        │ add_item()          │
        └──────────┬──────────┘
                   │
                   ▼
        ┌──────────────────────────────────┐
        │ Validate:                        │
        │ - Product exists (DB.query)      │
        │ - Qty > 0                        │
        │ - Stock available                │
        └──────────────┬───────────────────┘
                       │ (if valid)
                       ▼
                 ┌──────────────┐
                 │ Add to Cart  │
                 │ (in memory)  │
                 └──────┬───────┘
                        │
        ┌───────────────┤
        │   (repeat for more items)
        │
        ▼
┌──────────────────────────────────┐
│ USER CONFIRMS PAYMENT (Menu 2.3) │
└────────────┬─────────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│ Validate:                        │
│ - Nominal >= Total               │
│ - Calculate Kembalian            │
└────────────┬─────────────────────┘
             │ (if valid)
             ▼
┌──────────────────────────────────┐
│ SAVE TRANSACTION                 │
│ TransactionHandler.process()     │
└────────────┬─────────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│ 1. Insert transaksi row (DB)     │
│ 2. Insert items rows (DB)        │
│ 3. Update product stok (DB)      │
│ 4. Commit transaction            │
└────────────┬─────────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│ GENERATE RECEIPT                 │
│ 1. Format receipt text           │
│ 2. Save to receipts/ folder      │
│ 3. Display on console            │
│ 4. (Optional) Send Telegram      │
└────────────┬─────────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│ END - TRANSACTION COMPLETE ✅    │
└──────────────────────────────────┘
```

---

## Design Patterns

### 1. **Service Layer Pattern**

```python
# Separation of concerns
UI (main.py)
    ↓
Service Layer (transaction.py, laporan.py)
    ↓
Data Access (database.py)
    ↓
Data (SQLite)
```

**Benefit:** Easy to test, modify, extend

---

### 2. **Context Manager Pattern**

```python
# For resource management
with DatabaseManager() as db:
    db.add_product(...)
    # Auto-commit on exit
    # Auto-rollback on error
    # Auto-close on done
```

---

### 3. **Data Class Pattern**

```python
@dataclass
class Product:
    # Type hints + auto-generated __init__, __repr__, etc
    kode: str
    nama: str
    harga: int
    stok: int
```

**Benefit:** Clean, readable, Pythonic

---

### 4. **Manager Pattern**

```python
class DatabaseManager:
    # Single responsibility: database operations only
    # Reusable across modules
    # Easy mocking for tests
```

---

### 5. **Command Handler Pattern (Telegram)**

```python
# Each command is separate method
async def cmd_laporan(update, context):
    """Handle /laporan command"""

async def cmd_stok(update, context):
    """Handle /stok command"""

# Benefits:
# - Easy to add new commands
# - Decoupled command logic
# - Testable
```

---

## Error Handling

### Custom Exceptions

```python
class ValidationError(Exception):
    """Raised when input validation fails"""
    pass
```

**Usage:**
```python
raise ValidationError("Harga harus > 0")
# Caught at UI level and displayed to user
```

### Exception Hierarchy

```
Exception
├── ValidationError (custom)
├── sqlite3.IntegrityError (DB constraint)
├── sqlite3.OperationalError (DB locked)
└── TelegramError (API error)
```

### Error Handling Strategy

```python
# Level 1: Prevention (validation)
if not validate_input(data):
    raise ValidationError(...)

# Level 2: Database constraints
try:
    db.add_product(...)
except sqlite3.IntegrityError:
    # Handle duplicate, constraint violation

# Level 3: User feedback
except Exception as e:
    print(f"❌ Error: {e}")
    logger.error(str(e))
```

---

## Performance Considerations

### Database Optimization

**1. Indexing:**
```sql
CREATE INDEX idx_transaksi_tanggal ON transaksi(tanggal);
-- Speeds up: queries filtering by date
-- Cost: Slower writes, more storage
```

**2. Connection Pooling:**
```python
# Current: Single connection (efficient for CLI)
# Future: Connection pool for multi-threaded server
```

**3. Query Optimization:**
```python
# Bad: N+1 queries
for item in transaksi_items:
    product = db.get_product(item.product_kode)

# Good: Single query with JOIN
SELECT ti.*, p.nama, p.harga 
FROM transaksi_items ti
JOIN products p ON ti.product_kode = p.kode
```

### Memory Management

**1. Lazy Loading:**
```python
# Load all products at once (small dataset)
products = db.get_all_products()

# Better: Paginate for large datasets
products = db.get_products(page=1, limit=100)
```

**2. Object Caching:**
```python
# Cache frequently accessed data
self.product_cache = {}
for p in db.get_all_products():
    self.product_cache[p.kode] = p
```

---

## Extension Points

### Adding New Features

**1. New Report Type:**
```python
# In laporan.py:
class ReportGenerator:
    def get_laporan_custom(self, params):
        """Custom report implementation"""
        data = self.db.execute_query(custom_sql)
        return self.format_table(data)

# In main.py:
def menu_laporan(self):
    # Add new menu option
    elif choice == '6':
        self.laporan_generator.get_laporan_custom()
```

**2. New Telegram Command:**
```python
# In telegram_bot.py:
@command_handler("custom")
async def cmd_custom(self, update, context):
    """Handle /custom command"""
    data = self.get_custom_data()
    await update.message.reply_text(data)

# Register command in start_polling()
```

**3. New Data Model:**
```python
# In models.py:
@dataclass
class Supplier:
    id: int
    nama: str
    alamat: str
    telepon: str

# In database.py:
def add_supplier(self, nama, alamat, telepon):
    """Add new supplier"""
```

---

## Testing Architecture

**Unit Test Example:**
```python
# test_models.py
def test_product_validation():
    with pytest.raises(ValidationError):
        Product(kode="X", nama="", harga=-1, stok=-1)

# test_database.py
def test_database_operations():
    db = DatabaseManager(":memory:")  # In-memory DB
    db.add_product("TEST", "Test", 1000, 10)
    product = db.get_product("TEST")
    assert product.nama == "Test"
```

---

## Security Considerations

### Input Validation
```python
# All inputs validated before DB insert
# Protection against SQL injection (parameterized queries)
# Protection against malicious input
```

### SQL Injection Prevention
```python
# ✅ SAFE: Parameterized query
db.execute("SELECT * FROM products WHERE kode = ?", (kode,))

# ❌ DANGEROUS: String concatenation
db.execute(f"SELECT * FROM products WHERE kode = '{kode}'")
```

### Authentication
```python
# Telegram: allowed_chat_ids list
# Future: User authentication layer
```

---

**End of Architecture Documentation**
