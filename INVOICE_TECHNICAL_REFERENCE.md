# Invoice System - Technical Reference

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                   GUI Layer (gui_main.py)              │
│  ├─ show_invoices()                                     │
│  ├─ _show_invoice_detail_dialog_by_id()                │
│  └─ Sidebar menu integration                           │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────v──────────────────────────────────────────┐
│          Service Layer (invoice/)                       │
│  ├─ InvoiceService                                      │
│  │  ├─ create_invoice_from_transaction()               │
│  │  ├─ get_all_invoices()                              │
│  │  └─ query methods                                   │
│  └─ InvoicePDFGenerator                                │
│     └─ generate_invoice_pdf()                          │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────v──────────────────────────────────────────┐
│        Data Layer (database.py)                         │
│  ├─ invoices table                                      │
│  ├─ invoice_items table                                │
│  └─ DatabaseManager methods                            │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────v──────────────────────────────────────────┐
│         Storage (kasir_pos.db + invoices/)             │
│  ├─ SQLite database                                     │
│  └─ PDF files                                          │
└─────────────────────────────────────────────────────────┘
```

## Data Flow

### Transaction to Invoice

```
User completes payment
        │
        ↓
_process_payment() called
        │
        ├─ transaction_handler.complete_transaction(bayar)
        │  └─ Returns: trans_id
        │
        ├─ transaction_handler.print_receipt()
        │  └─ Saves receipt to receipts/
        │
        ├─ NEW: invoice_service.create_invoice_from_transaction(trans_id)
        │  ├─ Fetch transaction from db.get_transaction(trans_id)
        │  ├─ Generate invoice_number: INV-YYYYMMDD-HHMMSS
        │  ├─ Create Invoice object
        │  ├─ Add items to Invoice
        │  ├─ Save to database
        │  └─ Returns: invoice_id
        │
        ├─ NEW: invoice_pdf_generator.generate_invoice_pdf(invoice_data)
        │  ├─ Format invoice data
        │  ├─ Generate PDF with reportlab
        │  ├─ Save to invoices/
        │  └─ Returns: filepath
        │
        └─ Show success message
           Success ✓
           Invoice saved ✓
           PDF generated ✓
```

### Invoice Retrieval

```
User clicks "🧾 Invoice" menu
        │
        ├─ show_invoices() called
        │  │
        │  ├─ AsyncOperation.start()
        │  │  └─ db.get_all_invoices(limit=100)
        │  │     ├─ Query: SELECT * FROM invoices
        │  │     └─ Return: List[Dict]
        │  │
        │  └─ Display in TreeView
        │     ├─ Columns: No, Invoice#, Date, Total, Payment
        │     └─ Search functionality enabled
        │
        └─ User can:
           ├─ Search by invoice number
           ├─ Double-click to view detail
           └─ Export selected to PDF
```

## Module Details

### invoice_model.py

**InvoiceItem** (Dataclass)
```python
@dataclass
class InvoiceItem:
    nama: str              # Product name
    qty: int               # Quantity
    harga_satuan: int      # Price per unit
    subtotal: int          # Qty * harga_satuan
    
    def to_dict() → dict
```

**Invoice** (Dataclass)
```python
@dataclass
class Invoice:
    id: Optional[int]                    # Database ID
    invoice_number: Optional[str]        # Format: INV-YYYYMMDD-HHMMSS
    total: int                           # Total amount
    bayar: int                           # Amount paid
    kembalian: int                       # Change
    created_at: Optional[datetime]       # Timestamp
    items: List[InvoiceItem]            # Line items
    discount_percent: float              # Discount %
    discount_amount: int                 # Discount amount
    tax_percent: float                   # Tax %
    tax_amount: int                      # Tax amount
    
    def add_item(item: InvoiceItem)
    def get_items_count() → int
    def to_dict() → dict
```

### invoice_service.py

**InvoiceService** Class

```python
class InvoiceService:
    def __init__(self, db: DatabaseManager)
    
    # Generate invoice number
    def generate_invoice_number() → str
        # Returns: "INV-20260428-143022"
        # Format: INV-YYYYMMDD-HHMMSS
    
    # Create invoice from transaction
    def create_invoice_from_transaction(transaction_id: int) → Optional[int]
        # 1. Fetch transaction from database
        # 2. Generate invoice number
        # 3. Create Invoice object
        # 4. Save to database
        # 5. Return invoice_id or None
    
    # Save invoice to database
    def _save_invoice_to_database(invoice: Invoice) → Optional[int]
        # 1. Insert invoice header
        # 2. Insert items
        # 3. Return invoice_id
    
    # Retrieve invoices
    def get_all_invoices(limit=None, offset=0) → List[Dict]
    def get_invoice_detail(invoice_id: int) → Optional[Dict]
    def get_invoice_by_number(invoice_number: str) → Optional[Dict]
    def get_invoices_by_date(date_str: str) → List[Dict]
```

### invoice_pdf.py

**InvoicePDFGenerator** Class

```python
class InvoicePDFGenerator:
    def __init__(self, invoice_dir: str = "invoices")
        # Creates invoices/ directory if missing
        # Checks reportlab availability
    
    def generate_invoice_pdf(
        invoice_data: Dict,
        store_name: str,
        store_address: str,
        store_phone: Optional[str]
    ) → Optional[str]
        # 1. Check reportlab available
        # 2. Create PDF document
        # 3. Add header (store info)
        # 4. Add invoice info
        # 5. Add items table
        # 6. Add summary
        # 7. Add footer
        # 8. Save to invoices/{invoice_number}.pdf
        # 9. Return filepath or None
    
    def get_invoice_filepath(invoice_number: str) → str
        # Returns: invoices/{invoice_number}.pdf
```

## Database Schema

### invoices Table

```sql
CREATE TABLE invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number TEXT UNIQUE NOT NULL,
    total INTEGER NOT NULL,
    bayar INTEGER NOT NULL,
    kembalian INTEGER NOT NULL,
    discount_percent REAL DEFAULT 0,
    discount_amount INTEGER DEFAULT 0,
    tax_percent REAL DEFAULT 0,
    tax_amount INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)

CREATE INDEX idx_invoices_number ON invoices(invoice_number)
CREATE INDEX idx_invoices_date ON invoices(created_at)
```

### invoice_items Table

```sql
CREATE TABLE invoice_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    nama TEXT NOT NULL,
    qty INTEGER NOT NULL,
    harga_satuan INTEGER NOT NULL,
    subtotal INTEGER NOT NULL,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id)
)

CREATE INDEX idx_invoice_items_invoice_id ON invoice_items(invoice_id)
```

## GUI Components

### show_invoices()

Location: `gui_main.py:2896`

Features:
- Async loading of invoice list
- Search by invoice number
- TreeView display (No, Invoice#, Date, Total, Payment)
- Pagination (100 invoices per page)
- Double-click handler
- Export PDF button
- View detail button

```python
def show_invoices(self):
    # 1. Clear content area
    # 2. Show loading indicator
    # 3. Load invoices async: load_invoices()
    # 4. On load complete: on_invoices_loaded()
    #    ├─ Display search bar
    #    ├─ Create TreeView
    #    ├─ Add scrollbar
    #    ├─ Bind search filtering
    #    ├─ Bind double-click
    #    └─ Add action buttons
```

### _show_invoice_detail_dialog_by_id(invoice_id: int)

Location: `gui_main.py:3087`

Features:
- Modal dialog
- Invoice header info
- Items table
- Summary with totals
- Export PDF button

```python
def _show_invoice_detail_dialog_by_id(invoice_id: int):
    # 1. Get invoice detail from database
    # 2. Create dialog window
    # 3. Show header with invoice number
    # 4. Display items in TreeView
    # 5. Show summary (subtotal, discount, tax, total, bayar, kembalian)
    # 6. Add Export PDF button
    # 7. Show in modal dialog
```

## Integration Points

### In gui_main.py

#### _init_backend()
```python
# Line ~283
self.invoice_service = InvoiceService(self.db)
self.invoice_pdf_generator = InvoicePDFGenerator(invoice_dir="invoices")
logger.info("✅ Invoice service initialized")
```

#### _create_sidebar()
```python
# Line ~425
menu_items.insert(..., ("🧾 Invoice", self.show_invoices, True))
```

#### _process_payment()
```python
# Line ~2388
# After complete_transaction() and print_receipt():

try:
    invoice_id = self.invoice_service.create_invoice_from_transaction(trans_id)
    if invoice_id:
        invoice_detail = self.db.get_invoice_detail(invoice_id)
        if invoice_detail:
            invoice_data = invoice_detail['invoice']
            pdf_filepath = self.invoice_pdf_generator.generate_invoice_pdf(
                invoice_data,
                store_name="TOKO UBI BAROKAH IBU AWANG",
                store_address="Jl. Desa Mekarbakti, pertigaan Cilembu.",
                store_phone=None
            )
except Exception as e:
    logger.error(f"Invoice creation error: {e}")
    # Transaction flow continues despite error
```

## Error Handling

### Transaction Level
```python
try:
    invoice_id = self.invoice_service.create_invoice_from_transaction(trans_id)
except Exception as e:
    logger.error(f"Invoice error: {e}")
    # Transaction still completes successfully
```

### Database Level
```python
try:
    with self.db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(...)
        conn.commit()
except sqlite3.IntegrityError:
    logger.warning(f"Invoice number already exists")
    return None
except Exception as e:
    logger.error(f"Database error: {e}", exc_info=True)
    return None
```

### GUI Level
```python
try:
    invoices = self.db.get_all_invoices()
    if invoices is None:
        error_label.config(text="❌ Error loading invoices")
    elif not invoices:
        empty_label.config(text="📭 Belum ada invoice")
except Exception as e:
    logger.error(f"Error loading invoices: {e}")
    messagebox.showerror("Error", f"Gagal load: {e}")
```

## Performance Considerations

### Database Queries
- `get_all_invoices()`: O(1) with limit
- `get_invoice_by_number()`: O(log n) with index
- `get_invoices_by_date()`: O(n) scan with index
- `get_invoice_detail()`: O(1) + O(m) where m=items

### UI Performance
- Async loading prevents UI blocking
- Pagination limits data load
- Search done in-memory after load
- PDF generation doesn't block UI

### Optimization Tips
```python
# Limit query results
invoices = db.get_all_invoices(limit=50, offset=0)

# Use indices for searching
invoice = db.get_invoice_by_number('INV-20260428-143022')

# Cache frequently accessed data
self._current_filtered_invoices = filtered
```

## Testing Scenarios

### Test 1: Basic Invoice Creation
```
1. Start application
2. Login as admin/admin123
3. Complete a transaction
4. Verify database has invoice
5. Check invoices/ folder for PDF
```

### Test 2: Invoice List
```
1. Click "🧾 Invoice" menu
2. Verify list loads
3. Search by invoice number
4. Verify search works
5. Clear search
```

### Test 3: Invoice Details
```
1. Open invoice list
2. Double-click an invoice
3. Verify dialog shows details
4. Verify items displayed correctly
5. Verify totals calculated
```

### Test 4: PDF Export
```
1. Open invoice details
2. Click "📄 Export PDF"
3. Verify PDF generated
4. Open PDF and verify content
```

## Debugging Tips

### Enable Detailed Logging
```python
# In logger_config.py or main
logger.setLevel(logging.DEBUG)
```

### Check Database
```sql
-- SQLite command line
sqlite3 kasir_pos.db
SELECT * FROM invoices;
SELECT * FROM invoice_items;
.schema invoices
```

### Monitor Logs
```bash
# Terminal
tail -f pos.log | grep -i invoice

# Or search for specific issues
grep -i "error\|warning" pos.log | tail -20
```

### Test Invoice Service Directly
```python
from invoice.invoice_service import InvoiceService
from database import DatabaseManager

db = DatabaseManager()
service = InvoiceService(db)

# Test invoice creation
invoice_id = service.create_invoice_from_transaction(1)
print(f"Created invoice: {invoice_id}")

# Test retrieval
invoice = service.get_invoice_detail(invoice_id)
print(f"Invoice number: {invoice['invoice']['invoice_number']}")
```

## Code Quality Metrics

### Type Hints
- ✅ All function signatures have type hints
- ✅ Return types specified
- ✅ Optional types used correctly

### Docstrings
- ✅ All classes documented
- ✅ All methods documented
- ✅ Parameters described
- ✅ Return values described

### Error Handling
- ✅ Try-except blocks used
- ✅ Specific exceptions caught
- ✅ Fallback behavior defined
- ✅ Logging at all error points

### Code Style
- ✅ PEP 8 compliant
- ✅ Consistent naming
- ✅ Clear variable names
- ✅ Proper formatting

---

**This technical reference provides developers with all the implementation details needed to maintain, extend, or debug the Invoice System.**
