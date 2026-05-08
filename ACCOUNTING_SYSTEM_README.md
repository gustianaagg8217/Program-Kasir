# 📚 Sistem Pembukuan (Accounting System) - Dokumentasi Lengkap

## 🎯 Ringkasan

Sistem pembukuan yang baru telah ditambahkan ke aplikasi POS untuk melacak **income** (pemasukan/penjualan) dan **expense** (pengeluaran/biaya operasional). Sistem ini terintegrasi sepenuhnya dengan sistem transaksi yang ada dan memberikan laporan cashflow real-time.

## ✨ Fitur Utama

### 1. **Automatic Income Recording** 
- Setiap transaksi penjualan yang selesai otomatis dicatat sebagai income
- Linked dengan transaction ID untuk audit trail
- Mendukung transaksi lunas dan cicilan (termin)

### 2. **Manual Expense Input**
- Menambah pengeluaran melalui GUI
- Deskripsi lengkap untuk setiap pengeluaran
- Digunakan untuk biaya operasional, pembelian supply, dll

### 3. **Profit Calculation**
- Otomatis menghitung: **Profit = Total Income - Total Expense**
- Mendukung filtering berdasarkan date range
- Bisa positif (untung) atau negatif (rugi)

### 4. **Cashflow Tracking**
- Riwayat lengkap semua transaksi income dan expense
- Timestamp otomatis untuk setiap entry
- Bisa dihapus/diundo untuk koreksi

### 5. **GUI Integration**
- Menu baru: **📚 Pembukuan** (hanya untuk admin)
- Summary cards menampilkan total income, expense, profit
- Table untuk melihat history/riwayat
- Button untuk refresh data dan tambah pengeluaran
- Date range filtering

---

## 📁 File Structure

### Module Baru:

```
d:\Program-Kasir\
├── cashflow_service.py          # Layanan cashflow (income/expense)
├── accounting_service.py        # Layanan accounting (high-level)
├── test_accounting_integration.py  # Test suite
```

### File yang Dimodifikasi:

```
d:\Program-Kasir\
├── database.py                  # + cashflow table & methods
├── transaction.py               # + accounting integration
├── gui_main.py                  # + accounting service init, new pembukuan UI
```

---

## 🏗️ Architecture

### Layer 1: Database (database.py)
```python
# Cashflow table
CREATE TABLE IF NOT EXISTS cashflow (
    id INTEGER PRIMARY KEY,
    type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
    amount INTEGER NOT NULL,
    description TEXT NOT NULL,
    related_transaction_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)

# Methods:
- add_cashflow(cf_type, amount, description, transaction_id)
- get_total_cashflow(cf_type, start_date, end_date)
- get_cashflow_history(limit, start_date, end_date)
- get_cashflow_stats_for_range(start_date, end_date)
- delete_cashflow(cashflow_id)
```

### Layer 2: Service (cashflow_service.py)
```python
class CashflowService:
    def add_income(amount, description, transaction_id)
    def add_expense(amount, description)
    def get_cashflow_summary(start_date, end_date)
    def get_cashflow_history(limit, start_date, end_date)
    def delete_cashflow(cashflow_id)
    def get_daily_stats(num_days)
```

### Layer 3: Business Logic (accounting_service.py)
```python
class AccountingService:
    def record_income(transaction_id, amount, description)
    def record_expense(amount, description)
    def get_profit(start_date, end_date)
    def get_accounting_report(start_date, end_date)
    def get_history(limit, start_date, end_date)
    def delete_entry(cashflow_id)
```

### Layer 4: Integration (transaction.py)
```python
class TransactionHandler:
    def __init__(self, db, receipt_dir):
        self.accounting_service = AccountingService(db)
    
    def complete_transaction(self, bayar, store_name, ...):
        # ... transaction logic ...
        # Automatic income recording:
        if self.accounting_service and not is_termin:
            self.accounting_service.record_income(
                transaction_id=trans_id,
                amount=total,
                description="Penjualan"
            )
```

### Layer 5: Presentation (gui_main.py)
```python
class POSApplication:
    def __init__(self):
        self.accounting_service = AccountingService(db)
    
    def show_pembukuan(self):
        # Display cashflow summary
        # Show income/expense history
        # Add expense button
        # Date range filtering
```

---

## 🔌 Usage & Integration

### 1. Automatic Income Recording (Transparent to User)

```python
# Dalam transaction.py - complete_transaction()
# Ketika transaksi selesai, income otomatis tercatat:

trans_id = 123
total = 500000

# Ini dilakukan otomatis:
accounting_service.record_income(
    transaction_id=trans_id,
    amount=total,
    description="Penjualan"
)
```

**Kapan dipanggil?**
- Ketika user selesaikan transaksi (click "Selesai Transaksi")
- Setelah stok dikurangi dan transaksi disimpan ke database
- Income tercatat otomatis SEBELUM user melihat struk

**Result:**
- Entry baru di tabel `cashflow` dengan type='income'
- Linked ke transaction ID untuk audit
- Timestamp otomatis

---

### 2. Manual Expense Input (User Action)

**Via GUI:**
1. Go to menu: **📚 Pembukuan**
2. Click button: **➕ Tambah Pengeluaran**
3. Dialog appears:
   - **Deskripsi**: "Pembelian plastik kemasan"
   - **Jumlah**: "150000" (Rp)
4. Click **💾 Simpan**

**Via Python Code:**
```python
from accounting_service import AccountingService

accounting = AccountingService(db)
cf_id = accounting.record_expense(
    amount=150000,
    description="Pembelian plastik kemasan"
)
# Result: Entry added ke cashflow table dengan type='expense'
```

---

### 3. View Cashflow Report

**In GUI (Pembukuan Page):**

```
┌─────────────────────────────────────────────────────────┐
│           PEMBUKUAN & CASHFLOW (ACCOUNTING)             │
├─────────────────────────────────────────────────────────┤
│ Periode: [2026-04-01] hingga [2026-04-28]              │
│                                                         │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────┐│
│ │💵 Total Masuk   │ │💸 Total Keluar   │ │💹 Profit    ││
│ │ Rp 10.000.000   │ │ Rp 2.000.000    │ │ Rp 8.000.000││
│ └─────────────────┘ └─────────────────┘ └─────────────┘│
│                                                         │
│ Riwayat Cashflow:                                       │
│ ┌─────────────────────────────────────────────────────┐│
│ │ Tanggal    │ Tipe      │ Deskripsi     │ Jumlah     ││
│ ├─────────────────────────────────────────────────────┤│
│ │ 2026-04-28 │ Pengeluaran│ Listrik       │ Rp 50.000  ││
│ │ 2026-04-28 │ Pemasukan │ Penjualan     │ Rp 500.000 ││
│ │ 2026-04-27 │ Pengeluaran│ Plastik       │ Rp 100.000 ││
│ │ 2026-04-27 │ Pemasukan │ Penjualan     │ Rp 750.000 ││
│ └─────────────────────────────────────────────────────┘│
│                                                         │
│ [🔄 Refresh]  [➕ Tambah Pengeluaran]                   │
└─────────────────────────────────────────────────────────┘
```

**Via Python Code:**
```python
# Get summary
summary = accounting.cashflow_service.get_cashflow_summary(
    start_date=date(2026, 4, 1),
    end_date=date(2026, 4, 28)
)
print(f"Income:  Rp {summary['total_income']:,}")
print(f"Expense: Rp {summary['total_expense']:,}")
print(f"Profit:  Rp {summary['profit']:,}")

# Get history
history = accounting.get_history(limit=100)
for entry in history:
    print(f"{entry['created_at']} | {entry['type']} | "
          f"{entry['description']} | Rp {entry['amount']:,}")
```

---

## 📊 Database Schema

### Tabel: `cashflow`

| Kolom | Tipe | Keterangan |
|-------|------|-----------|
| `id` | INTEGER | Primary key, auto-increment |
| `type` | TEXT | 'income' atau 'expense' |
| `amount` | INTEGER | Jumlah dalam Rupiah |
| `description` | TEXT | Deskripsi transaksi |
| `related_transaction_id` | INTEGER | FK ke table transactions (opsional) |
| `created_at` | DATETIME | Timestamp otomatis |

### Indices:
- `idx_cashflow_type` - Untuk filtering by type
- `idx_cashflow_date` - Untuk filtering by date
- `idx_cashflow_transaction` - Untuk linking ke transaksi

---

## 🔍 Query Examples

### Get Total Income Today
```python
from datetime import date
today = date.today()
total = db.get_total_cashflow(
    cf_type='income',
    start_date=today,
    end_date=today
)
print(f"Total income today: Rp {total:,}")
```

### Get Profit for Current Month
```python
from datetime import date
today = date.today()
start = date(today.year, today.month, 1)
profit = db.get_total_cashflow('income', start, today) - \
         db.get_total_cashflow('expense', start, today)
print(f"Monthly profit: Rp {profit:,}")
```

### Get All Expenses in Last 7 Days
```python
from datetime import date, timedelta
end = date.today()
start = end - timedelta(days=7)
history = db.get_cashflow_history(limit=100, start_date=start, end_date=end)
expenses = [e for e in history if e['type'] == 'expense']
total = sum(e['amount'] for e in expenses)
print(f"Total expenses (7 days): Rp {total:,}")
```

### Daily Cashflow Stats
```python
stats = db.get_daily_cashflow_stats(num_days=30)
for day_stat in stats:
    print(f"{day_stat['date']}: "
          f"Income=Rp{day_stat['total_income']:,}, "
          f"Expense=Rp{day_stat['total_expense']:,}, "
          f"Profit=Rp{day_stat['profit']:,}")
```

---

## 🎮 GUI Features Detailed

### Show Pembukuan Page

**Akses:** Menu → 📚 Pembukuan (Admin only)

**Komponen:**

1. **Date Range Selector**
   - Dari: [DateEntry widget]
   - Hingga: [DateEntry widget]
   - Default: Dari awal bulan hingga hari ini

2. **Summary Cards** (3 kartu)
   - **💵 Total Pemasukan**: Hijau, show total income
   - **💸 Total Pengeluaran**: Merah, show total expense
   - **💹 Keuntungan Bersih**: Biru (profit ≥ 0) atau Merah (rugi < 0)

3. **Cashflow History Table**
   - Columns: Tanggal | Tipe | Deskripsi | Jumlah | Transaksi ID
   - Sorted by date (newest first)
   - Max 100 entries, scrollable

4. **Action Buttons**
   - **🔄 Refresh**: Reload data from database
   - **➕ Tambah Pengeluaran**: Open expense input dialog

### Add Expense Dialog

**Triggered by:** Click "➕ Tambah Pengeluaran" button

**Dialog contains:**
- **Deskripsi Pengeluaran:** Text input
  - Contoh: "Pembelian plastik kemasan", "Biaya listrik", dll
- **Jumlah Pengeluaran (Rp):** Number input
  - Auto-parse: "Rp 150.000" → 150000
- **[💾 Simpan]** button
- **[Batal]** button

**Validation:**
- Deskripsi tidak boleh kosong
- Jumlah harus berupa angka
- Jumlah harus > 0

**On Save Success:**
- Show popup: "✅ Pengeluaran berhasil dicatat"
- Auto-refresh table
- Close dialog

---

## 🔐 Access Control

**Pembukuan menu hanya accessible untuk:**
- Role: `admin`
- `is_active` status: `True`

**Normal cashier/user TIDAK bisa:**
- Akses Pembukuan menu
- Lihat income/expense data
- Tambah pengeluaran manual

---

## 📈 Future Enhancements

1. **Chart/Visualization**
   - Pie chart: Income vs Expense
   - Line chart: Daily profit trend
   - Bar chart: Top expenses by category

2. **Categories**
   - Add expense category (Utilities, Supply, etc)
   - Filter by category

3. **Budget Management**
   - Set budget limit per category
   - Alert when spending exceeds budget

4. **Export Reports**
   - Export to CSV/Excel
   - Export to PDF dengan formatting

5. **Multi-Period Analysis**
   - Compare month-to-month
   - Year-over-year comparison

6. **Audit Trail**
   - Track who added/deleted entries
   - Reason for deletion/edit

---

## 🧪 Testing

**Run test suite:**
```bash
cd d:\Program-Kasir
python test_accounting_integration.py
```

**Test Coverage:**
- ✅ Module imports
- ✅ Database initialization
- ✅ Service initialization
- ✅ Income recording
- ✅ Expense recording
- ✅ Profit calculation
- ✅ Summary reports
- ✅ History retrieval
- ✅ TransactionHandler integration
- ✅ Database schema verification

---

## ⚡ Quick Start

### Setup (Otomatis)
```python
# Semua setup otomatis saat aplikasi start
# cashflow table dibuat otomatis di _init_database()
```

### Use in GUI
```
1. Run: python gui_main.py
2. Login sebagai admin
3. Menu → 📚 Pembukuan
4. Lihat cashflow summary
5. Click "➕ Tambah Pengeluaran" untuk tambah expense
6. Click "🔄 Refresh" untuk reload data
```

### Use in Code
```python
from accounting_service import AccountingService

db = DatabaseManager()
accounting = AccountingService(db)

# Record income (usually automatic)
cf_id = accounting.record_income(
    transaction_id=123,
    amount=500000,
    description="Penjualan"
)

# Record expense (manual)
cf_id = accounting.record_expense(
    amount=100000,
    description="Pembelian supply"
)

# Get summary
summary = accounting.cashflow_service.get_cashflow_summary()
print(f"Profit: Rp {summary['profit']:,}")
```

---

## 🐛 Troubleshooting

### Income not recording automatically
- Check: TransactionHandler initialized with accounting service?
- Check: `ACCOUNTING_AVAILABLE` = True di transaction.py?
- Check: Transaksi saved successfully (trans_id != None)?

### Can't see Pembukuan menu
- Check: User role is 'admin'?
- Check: User is_active = True?
- Check: ACCOUNTING_AVAILABLE = True di gui_main.py?

### Dialog not showing when add expense
- Check: tkinter Toplevel widget working?
- Check: Dialog.geometry() setting valid size?

---

## 📝 Notes

- Semua amount dalam **Rupiah (Rp)** - integer, bukan float
- Timestamps otomatis dalam **UTC/server timezone**
- Profit calculation: **Income - Expense** (bisa negatif)
- Delete cashflow hanya untuk undo/koreksi, bukan normal operation
- Income otomatis recorded SEBELUM receipt di-print
- Cashflow tracking independent dari transaction items/products

---

## 📞 Support

Untuk questions atau issues:
1. Check test_accounting_integration.py for examples
2. Check logger output (pos.log) untuk error details
3. Review code comments di cashflow_service.py & accounting_service.py

---

**Version:** 1.0  
**Date:** 2026-04-28  
**Status:** Production Ready ✅
