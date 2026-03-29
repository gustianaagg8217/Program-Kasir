# Point of Sale (POS) System 🛒

Sistem Kasir modern lengkap dengan Python & SQLite. Mudah digunakan, maintainable, dan siap dikembangkan ke GUI.

## 📋 Daftar Isi
- [Fitur](#fitur)
- [Struktur Project](#struktur-project)
- [Dokumentasi](#dokumentasi)
- [Setup & Installation](#setup--installation)
- [Panduan Penggunaan](#panduan-penggunaan)
- [Telegram Bot Integration](#telegram-bot-integration)
- [Dokumentasi API](#dokumentasi-api)
- [Contoh Kode](#contoh-kode)
- [FAQ](#faq)

---

## ✨ Fitur

### 1. **Manajemen Produk** 📦
- ✅ Tambah produk baru dengan kode unik, nama, harga, stok
- ✅ Lihat daftar semua produk
- ✅ Edit produk (nama, harga, stok)
- ✅ Hapus produk dari database
- ✅ Info stok dengan status (OK, MINIM, KOSONG)

### 2. **Transaksi Penjualan** 🛒
- ✅ Input item via kode produk & qty
- ✅ Subtotal otomatis per item
- ✅ Total belanja otomatis
- ✅ Input pembayaran fleksibel
- ✅ Hitung kembalian otomatis
- ✅ Validasi stok sebelum transaksi

### 3. **Struk/Receipt** 🧾
- ✅ Tampilkan struk di terminal
- ✅ Format rapi dengan tabel & currency Rupiah
- ✅ Simpan struk otomatis ke file .txt
- ✅ Include: tanggal, invoice, items, total, bayar, kembalian

### 4. **Manajemen Stok** 📊
- ✅ Stok otomatis berkurang saat transaksi
- ✅ Validasi stok tidak boleh minus
- ✅ Alert untuk stok minim
- ✅ Monitoring real-time

### 5. **Laporan & Analisis** 📈
- ✅ Laporan penjualan harian (total, rata-rata, item terjual)
- ✅ Laporan periode (range tanggal)
- ✅ Produk paling laris (top N produk)
- ✅ Informasi stok lengkap
- ✅ Dashboard summary (quick overview)

### 6. **Export & Integration** 💾
- ✅ Export ke CSV (produk laris, stok, transaksi)
- ✅ CSV dapat dibuka di Excel/Google Sheets
- ✅ Format UTF-8 dengan separator ribuan Rupiah

### 7. **Telegram Bot Integration** 🤖
- ✅ Real-time laporan penjualan via Telegram
- ✅ Commands: `/laporan`, `/stok`, `/terlaris`, `/dashboard`
- ✅ Notifikasi transaksi otomatis
- ✅ Alert stok produk minim
- ✅ Multi-user authorization
- ✅ Configuration management via JSON

---

## 🏗️ Struktur Project

```
Program_Kasir/
│
├── main.py                 # Entry point - CLI menu utama ⭐
├── database.py             # SQLite database manager
├── models.py               # OOP models (Product, Transaction, dll)
├── transaction.py          # Transaction & receipt management
├── laporan.py              # Report generator & CSV export
├── telegram_bot.py         # Telegram Bot integration 🤖
│
├── kasir_pos.db            # SQLite database file (auto-created)
├── telegram_config.json    # Telegram Bot configuration
├── receipts/               # Folder untuk simpan struk .txt
├── exports/                # Folder untuk export CSV
│
├── requirements.txt        # Python dependencies
├── README.md              # Dokumentasi utama
└── TELEGRAM_SETUP.md      # Panduan setup Telegram Bot
```

### Penjelasan File:

| File | Fungsi | Responsibility |
|------|--------|-----------------|
| **main.py** | CLI interface & menu | User interaction, workflow |
| **database.py** | SQLite database | DB operations, CRUD, queries |
| **models.py** | OOP models & validation | Business logic, data entities |
| **transaction.py** | Transaction processing | Sale flow, receipt management |
| **laporan.py** | Reporting & export | Analytics, report formatting |
| **telegram_bot.py** | Telegram Bot handler | Bot commands, notifications, integration |

---

## � Dokumentasi

Lengkap berisi panduan lengkap untuk semua aspek sistem:

### 📖 User Documentation

| Dokumentasi | Deskripsi | Link |
|---|---|---|
| **GETTING_STARTED.md** | 🚀 Quick start 5 menit | [Buka](GETTING_STARTED.md) |
| **INSTALL.md** | 📥 Panduan instalasi lengkap | [Buka](INSTALL.md) |
| **TROUBLESHOOTING.md** | 🔧 Solusi masalah umum | [Buka](TROUBLESHOOTING.md) |
| **TELEGRAM_BOT_QUICKSTART.md** | 🤖 Setup Telegram (5 min) | [Buka](TELEGRAM_BOT_QUICKSTART.md) |
| **TELEGRAM_SETUP.md** | 🤖 Setup Telegram detail | [Buka](TELEGRAM_SETUP.md) |

### 👨‍💻 Developer Documentation

| Dokumentasi | Deskripsi | Link |
|---|---|---|
| **ARCHITECTURE.md** | 🏗️ Technical architecture | [Buka](ARCHITECTURE.md) |
| **README.md** | 📖 Main documentation | [Buka](README.md) |

### 🛠️ Quick Setup Scripts

Windows dan Linux/Mac users bisa gunakan script auto-setup:

**Windows:**
```bash
# Double-click: setup.bat
# Atau:
setup.bat
```

**Linux/Mac:**
```bash
chmod +x setup.sh
./setup.sh
```

---

## �🚀 Setup & Installation

### 🔥 Fastest Way (Recommended)

**Windows users:**
```bash
# Double-click setup.bat
# atau jalankan:
setup.bat
```

**Linux/Mac users:**
```bash
chmod +x setup.sh
./setup.sh
```

Script setup akan otomatis:
1. ✅ Check Python installation
2. ✅ Create virtual environment (optional)
3. ✅ Install dependencies
4. ✅ Initialize database
5. ✅ Verify installation

### Manual Setup

#### Requirement:
- Python 3.8+
- No external dependencies (hanya built-in modules)
- Optional: python-telegram-bot untuk Telegram Bot

#### Step 1: Clone/Download Project
```bash
cd Program_Kasir
```

#### Step 2: (Optional) Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

#### Step 3: Install Dependencies (Optional - for Telegram Bot)
```bash
pip install python-telegram-bot requests
```

#### Step 4: Jalankan Program
```bash
python main.py
```

#### Database Initialization
Database otomatis dibuat saat first run:
- `kasir_pos.db` akan dibuat
- 3 tabel: `products`, `transactions`, `transaction_items`

### Next Steps

1. **First time users:** Baca [GETTING_STARTED.md](GETTING_STARTED.md) untuk 5-menit quickstart
2. **Need detailed guidance:** Baca [INSTALL.md](INSTALL.md)
3. **Having issues:** Baca [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
4. **Setting up Telegram Bot:** Baca [TELEGRAM_BOT_QUICKSTART.md](TELEGRAM_BOT_QUICKSTART.md)

---

## 📖 Panduan Penggunaan

### Main Menu
```
🛒 SISTEM POS POINT OF SALE 🛒

1. 📦 Kelola Produk
2. 🛒 Transaksi Penjualan
3. 📊 Laporan & Analisis
4. ⚙️  Settings & Utility
0. 🚪 Keluar dari Sistem
```

### Menu 1: Kelola Produk
```
1. ➕ Tambah Produk          → Input: kode, nama, harga, stok awal
2. 📋 Lihat Daftar Produk    → Display semua produk
3. ✏️  Edit Produk            → Update nama/harga/stok
4. 🗑️  Hapus Produk           → Hapus produk
5. 📊 Info Stok              → Lihat status stok semua produk
```

**Contoh Tambah Produk:**
```
Kode Produk: PROD001
Nama Produk: Mie Goreng
Harga: 15000
Stok Awal: 100

✅ Produk 'Mie Goreng' berhasil ditambahkan!
```

### Menu 2: Transaksi Penjualan
```
1. ➕ Tambah Item            → Kode + Qty
2. 📋 Lihat Item             → Lihat item dalam transaksi
3. 🗑️  Hapus Item             → Hapus item tertentu
4. 💳 Konfirmasi Pembayaran  → Set bayar & selesai
5. ❌ Batalkan Transaksi     → Cancel transaksi
```

**Workflow Transaksi:**
1. Sistem auto-create transaksi baru
2. Scan/input kode produk + qty
3. Item ditambahkan, total auto-update
4. Ulangi step 2-3
5. Pilih "Konfirmasi Pembayaran"
6. Input jumlah uang pembayaran
7. Struk otomatis ditampilkan & disimpan
8. Stok otomatis berkurang

**Contoh Output Transaksi:**
```
STATUS TRANSAKSI SAAT INI
Item      : 2 item (5 qty)
Total     : Rp 45.000

=== Contoh Struk ===
==================================================
TOKO ACCESSORIES G-LIES
Jl. Majalaya, Solokanjeruk, Bandung
==================================================
Tanggal: 2026-03-29 14:30:45
Invoice: #000001

ITEM:
Mie Goreng       2x Rp 15.000 = Rp 30.000
Teh Botol        3x Rp 5.000  = Rp 15.000
--------------------------------------------------
TOTAL          : Rp 45.000
PEMBAYARAN     : Rp 50.000
KEMBALIAN      : Rp 5.000
==================================================
Terima kasih telah berbelanja!
```

### Menu 3: Laporan & Analisis
```
1. 📅 Laporan Harian         → Penjualan hari ini
2. 📆 Laporan Periode        → Range tanggal custom
3. 🏆 Produk Terlaris        → Top N produk by qty
4. 📦 Informasi Stok         → Stock summary
5. 🎨 Dashboard              → Quick overview
6. 💾 Export ke CSV          → Export berbagai laporan
```

**Contoh Laporan Harian:**
```
LAPORAN PENJUALAN HARIAN - 2026-03-29
======================================================================
📊 RINGKASAN:
  Total Penjualan       : Rp 450.000
  Total Transaksi       : 10 transaksi
  Rata-rata Transaksi   : Rp 45.000
  Total Item Terjual    : 25 item
  Rata-rata Item/Trans  : 2.5

🏆 PRODUK TERLARIS:
  1. Mie Goreng             10 qty | Rp 150.000
  2. Teh Botol              12 qty | Rp 60.000
  3. Roti Tawar              3 qty | Rp 60.000
```

### Menu 4: Settings
```
1. 🔄 Reset Database         → Hapus semua data (HATI-HATI!)
2. ℹ️  Tentang Sistem         → Info sistem
```

---

## 🤖 Telegram Bot Integration

### Quick Setup

```bash
# 1. Install dependencies
pip install python-telegram-bot requests

# 2. Run POS System
python main.py

# 3. Go to Menu 4 → Telegram Bot → Setup Configuration
# Fill in your bot token and admin chat ID

# 4. Start bot: Menu 4 → Jalankan Bot
```

### Telegram Bot Commands

| Command | Deskripsi |
|---------|-----------|
| `/laporan` | Laporan penjualan harian |
| `/stok` | Info stok semua produk |
| `/terlaris` | Top 10 produk paling laris |
| `/dashboard` | Quick summary dashboard |
| `/ping` | Test bot connectivity |
| `/help` | Lihat semua commands |

### Example Usage

```
User: /laporan
Bot:
📊 LAPORAN PENJUALAN HARIAN - 2026-03-29
💰 Total Penjualan: Rp 450.000  
📝 Total Transaksi: 10
🏆 TOP 5 PRODUK:
   1. Mie Goreng - 10 qty (Rp 150.000)
   2. Teh Botol - 12 qty (Rp 60.000)
```

### Configuration

Edit `telegram_config.json`:

```json
{
  "bot_token": "YOUR_TOKEN_HERE",
  "allowed_chat_ids": [123456789],
  "enabled": true,
  "admin_chat_id": 123456789,
  "notify_transaction": true,
  "notify_low_stock": true,
  "low_stock_threshold": 20
}
```

### Features

- ✅ Real-time reports dari database
- ✅ Multi-user authorization
- ✅ Transaction notifications (optional)
- ✅ Low stock alerts (optional)
- ✅ Command logging & error handling

### Getting Started

**Lihat:** [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md) untuk panduan lengkap setup Telegram Bot.

---

## 🛠️ API Documentation

### database.py

#### DatabaseManager
```python
from database import DatabaseManager

db = DatabaseManager(db_name="kasir_pos.db")

# PRODUCT OPERATIONS
db.add_product(kode, nama, harga, stok) → bool
db.get_product_by_kode(kode) → dict
db.get_product_by_id(product_id) → dict
db.get_all_products() → list[dict]
db.update_product(kode, nama=None, harga=None, stok=None) → bool
db.delete_product(kode) → bool
db.reduce_stock(product_id, qty) → bool

# TRANSACTION OPERATIONS
db.add_transaction(total, bayar, kembalian) → int (trans_id)
db.add_transaction_item(trans_id, product_id, qty, harga_satuan, subtotal) → bool
db.get_transaction(transaction_id) → dict
db.get_all_transactions() → list[dict]
db.get_transactions_by_date(date_str) → list[dict]

# REPORT OPERATIONS
db.get_total_penjualan_hari_ini() → int
db.get_total_transaksi_hari_ini() → int
db.get_produk_paling_laris(limit=5) → list[dict]
db.get_laporan_harian(date_str=None) → dict
```

### models.py

#### Product
```python
from models import Product, TransactionItem, Transaction, format_rp

# Create product
product = Product(
    kode="PROD001",
    nama="Mie Goreng",
    harga=15000,
    stok=100
)

# Formatting
print(format_rp(15000))  # Output: "Rp 15.000"
print(product.display())  # Formatted display
```

#### TransactionItem
```python
item = TransactionItem(
    product_id=1,
    product_name="Mie Goreng",
    qty=2,
    harga_satuan=15000
)
print(item.display())  # Formatted display with subtotal
```

#### Transaction
```python
trans = Transaction()
trans.add_item(item1)
trans.add_item(item2)
trans.set_bayar(50000)
print(trans.display_receipt())  # Full formatted receipt
```

### transaction.py

#### TransactionService
```python
from transaction import TransactionService

service = TransactionService(db)

# Workflow
trans = service.create_transaction()
service.add_item_by_kode("PROD001", 2)
service.add_item_by_kode("PROD002", 3)
service.set_payment(100000)
trans_id = service.save_transaction()
```

#### ReceiptManager
```python
from transaction import ReceiptManager

receipt_mgr = ReceiptManager(receipt_dir="receipts")

# Generate & display
receipt_text = receipt_mgr.generate_receipt(transaction)
receipt_mgr.display_receipt(transaction)

# Save to file
filepath = receipt_mgr.save_receipt(transaction)
# Output: receipts/receipt_20260329_143045_000001.txt
```

### laporan.py

#### ReportGenerator
```python
from laporan import ReportGenerator, ReportFormatter, CSVExporter

report_gen = ReportGenerator(db)

# Get reports
laporan_harian = report_gen.get_laporan_harian()
laporan_periode = report_gen.get_laporan_periode("2026-03-01", "2026-03-31")
produk_laris = report_gen.get_produk_terlaris(limit=10)
stok_summary = report_gen.get_stok_summary()
dashboard = report_gen.get_dashboard_summary()

# Format & display
formatter = ReportFormatter()
print(formatter.format_laporan_harian(laporan_harian))
print(formatter.format_dashboard(dashboard))

# Export CSV
exporter = CSVExporter()
exporter.export_produk_terlaris(produk_laris)
exporter.export_stok_summary(stok_summary)
exporter.export_transactions(db)
```

---

## 💻 Contoh Kode

### Contoh 1: Tambah Produk Programmatically
```python
from database import DatabaseManager

db = DatabaseManager()
db.add_product("PROD001", "Mie Goreng", 15000, 100)
db.add_product("PROD002", "Teh Botol", 5000, 150)
```

### Contoh 2: Proses Transaksi
```python
from database import DatabaseManager
from transaction import TransactionHandler

db = DatabaseManager()
handler = TransactionHandler(db)

# Start transaction
handler.start_transaction()

# Add items
handler.add_item("PROD001", 2)
handler.add_item("PROD002", 3)

# Display items
handler.display_items()

# Complete & payment
trans_id = handler.complete_transaction(
    bayar=50000,
    store_name="TOKO ACCESSORIES G-LIES",
    store_address="Jl. Majalaya, Solokanjeruk, Bandung"
)
print(f"Transaction ID: {trans_id}")
```

### Contoh 3: Generate Laporan
```python
from database import DatabaseManager
from laporan import ReportGenerator, ReportFormatter

db = DatabaseManager()
gen = ReportGenerator(db)
fmt = ReportFormatter()

# Daily report
laporan = gen.get_laporan_harian("2026-03-29")
print(fmt.format_laporan_harian(laporan))

# Dashboard
dashboard = gen.get_dashboard_summary()
print(fmt.format_dashboard(dashboard))
```

### Contoh 4: Export ke CSV
```python
from database import DatabaseManager
from laporan import ReportGenerator, CSVExporter

db = DatabaseManager()
gen = ReportGenerator(db)
exporter = CSVExporter(export_dir="reports")

# Get & export
produk = gen.get_produk_terlaris(limit=50)
exporter.export_produk_terlaris(produk, filename="top_products.csv")

stok = gen.get_stok_summary()
exporter.export_stok_summary(stok, filename="stock_report.csv")
```

---

## ❓ FAQ

### Q: Database disimpan di mana?
**A:** File `kasir_pos.db` disimpan di folder yang sama dengan `main.py`. Database menggunakan SQLite yang built-in di Python.

### Q: Bagaimana jika stok produk habis?
**A:** Sistem akan otomatis reject transaksi jika stok tidak cukup. Validasi terjadi saat input item.

### Q: Bisa diekspor ke format lain selain CSV?
**A:** Saat ini hanya CSV. Untuk Excel (XLSX), bisa install `openpyxl` dan modif `CSVExporter`. Untuk PDF, bisa gunakan `reportlab`.

### Q: Bagaimana cara backup database?
**A:** Cukup copy file `kasir_pos.db` ke lokasi aman. Database SQLite adalah file binary yang bisa di-backup langsung.

### Q: Bisa dikembangkan ke GUI?
**A:** **Sangat mudah!** Model & service sudah modular & independent. Tinggal buat UI layer dengan PyQt/Tkinter tanpa mengubah core logic.

### Q: Bagaimana cara custom nama toko?
**A:** Edit di `ReceiptManager.generate_receipt()` atau di `main.py` bagian `complete_transaction()`.

### Q: Jika restart, data tidak hilang?
**A:** Benar! Semua data disimpan di SQLite. Makanya database-driven, bukan JSON/file.

### Q: Bisa multi-user?
**A:** SQLite single-writer, jadi tidak ideal untuk multi-concurrent user. Untuk itu, upgrade ke PostgreSQL/MySQL.

### Q: Bagaimana dengan security?
**A:** Saat ini tidak ada enkripsi. Untuk production, tambahkan password protection & enkripsi database.

### Q: Bagaimana setup Telegram Bot?
**A:** 
1. Install: `pip install python-telegram-bot requests`
2. Buat bot dengan @BotFather di Telegram
3. Setup di Menu 4 → Telegram Bot → Setup Configuration
4. Jalankan bot dari Menu 4
**Lihat:** [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md) untuk panduan lengkap.

### Q: Apa itu Bot Token dan Chat ID?
**A:** 
- **Bot Token**: Kunci unik dari @BotFather untuk identifikasi bot Anda
- **Chat ID**: ID unik Telegram Anda (dapatkan dari @userinfobot)

### Q: Bisa mengirim notifikasi otomatis saat transaksi?
**A:** Ya! Aktifkan di `telegram_config.json`: set `"notify_transaction": true`

### Q: Bisa multiple admins/users?
**A:** Ya! Tambahkan multiple Chat IDs ke `allowed_chat_ids` di config.

---

## 🔧 Development Future Enhancements

- [ ] Web API (Flask/FastAPI)
- [ ] GUI Desktop (PyQt/Tkinter)
- [ ] Mobile App (Android)
- [ ] Database upgrade (PostgreSQL/MySQL)
- [ ] User authentication
- [ ] Discount & promo system
- [ ] Multi-branch support
- [ ] Barcode scanning integration
- [ ] Print support
- [ ] Real-time sync
- [ ] Voice notifications via Telegram

---

## 📄 License

Free to use & modify for personal/business use. No warranties.

---

## 📞 Support

Untuk masalah atau saran, silakan buat issue atau hubungi developer.

**Happy Coding! 🚀**
