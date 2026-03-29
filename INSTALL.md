# 📥 Installation Guide - POS System

Panduan lengkap instalasi Point of Sale System dari awal sampai siap pakai.

---

## 📋 Requirement

- **Python**: 3.8 atau lebih baru
- **Sistem Operasi**: Windows, Linux, macOS
- **Memory**: Minimal 512MB
- **Disk Space**: 50MB
- **Internet**: Hanya jika ingin menggunakan Telegram Bot

---

## ✅ Step 1: Verify Python Installation

### Windows
```bash
python --version
```

### Linux/Mac
```bash
python3 --version
```

Harus menunjukkan Python 3.8+

---

## 📁 Step 2: Setup Project Folder

### Option A: Copy Existing Files
Jika sudah download project, copy semua file ke folder:
```
d:\Program_Kasir\
```

### Option B: Manual Setup
```bash
# Create folder
mkdir Program_Kasir
cd Program_Kasir

# Dapatkan files dari repository atau setup dari scratch
```

---

## 📦 Step 3: Install Dependencies

### Required (Core POS)
```bash
# Tidak ada external dependencies diperlukan!
# POS system menggunakan hanya Python built-in modules
```

### Optional (Telegram Bot)
```bash
pip install python-telegram-bot requests
```

### Verify Installation
```bash
# Test core modules (built-in, no install needed)
python -c "import sqlite3; print('✅ sqlite3 OK')"
python -c "import csv; print('✅ csv OK')"
python -c "import json; print('✅ json OK')"

# Test optional Telegram module (if installed)
python -c "import telegram; print('✅ telegram OK')" 2>/dev/null || echo "⚠️ telegram not installed (optional)"
```

---

## 🚀 Step 4: First Run (Database Setup)

### Run Main Program
```bash
python main.py
```

Expected output:
```
✅ Database tabel berhasil diinisialisasi
✅ POS System siap digunakan!

======================================================================
🛒 SISTEM POS POINT OF SALE 🛒
======================================================================
```

**Database automatically created:**
- `kasir_pos.db` (SQLite database)

---

## 🛒 Step 5: Quick Test

### Add Sample Data

From Menu:
```
1. Kelola Produk
   → Tambah Produk
   → Kode: PROD001
   → Nama: Mie Goreng
   → Harga: 15000
   → Stok: 100
```

### Run Transaction

From Menu:
```
2. Transaksi Penjualan
   → Add item: PROD001, qty: 2
   → Lihat item (should show 1 item)
   → Konfirmasi pembayaran
   → Input: 50000
   → Struk auto-generated
```

**✅ POS System Working!**

---

## 🤖 Step 6: Setup Telegram Bot (Optional)

### Prerequisites
```bash
# Already installed? Check
pip show python-telegram-bot
```

### If Not Installed
```bash
pip install python-telegram-bot requests
```

### Quick Setup
From Menu:
```
4. Telegram Bot
   → Setup Configuration
   → Enter Bot Token (from @BotFather)
   → Enter Admin Chat ID (from @userinfobot)
```

**See:** [TELEGRAM_BOT_QUICKSTART.md](TELEGRAM_BOT_QUICKSTART.md) for 5-min setup

---

## 📂 Project Structure After Installation

```
Program_Kasir/
├── main.py                   # Main program (start here)
├── database.py               # Database manager
├── models.py                 # OOP models
├── transaction.py            # Transaction logic
├── laporan.py                # Reports & export
├── telegram_bot.py           # Telegram integration (optional)
│
├── kasir_pos.db              # SQLite database (auto-created)
├── telegram_config.json      # Telegram config (auto-created)
├── telegram_bot.log          # Bot logs (if telegram used)
│
├── receipts/                 # Folder for receipts
├── exports/                  # Folder for CSV exports
│
├── requirements.txt          # Python dependencies
├── README.md                 # Main documentation
├── INSTALL.md               # This file
├── TELEGRAM_SETUP.md        # Telegram detailed guide
└── TELEGRAM_BOT_QUICKSTART.md # Telegram quick setup

```

---

## 🔍 Verify Setup

### Test Core Functions

**1. Database**
```bash
python -c "
from database import DatabaseManager
db = DatabaseManager()
print('✅ Database OK')
print(db.get_database_stats())
"
```

**2. Models**
```bash
python -c "
from models import Product, format_rp
p = Product(kode='TEST', nama='Test', harga=10000, stok=10)
print(f'✅ Models OK: {p}')
print(f'✅ Format: {format_rp(10000)}')
"
```

**3. Transaction**
```bash
python -c "
from transaction import TransactionService
from database import DatabaseManager
db = DatabaseManager()
ts = TransactionService(db)
print('✅ Transaction Service OK')
"
```

**4. Reports**
```bash
python -c "
from laporan import ReportGenerator
from database import DatabaseManager
db = DatabaseManager()
rg = ReportGenerator(db)
print('✅ Report Generator OK')
"
```

**5. Telegram (if installed)**
```bash
python -c "
from telegram_bot import POSTelegramBot, TELEGRAM_AVAILABLE
print(f'✅ Telegram Available: {TELEGRAM_AVAILABLE}')
" 2>/dev/null || echo "⚠️ Telegram not available"
```

---

## 🐛 Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'telegram'"
**Solution:**
```bash
pip install python-telegram-bot requests
```

### Issue: "Database file not found"
**Solution:**
1. Delete `kasir_pos.db` (if exist)
2. Run `python main.py`
3. Database auto-created on first run

### Issue: "Port/Permission Error"
**Solution:**
1. Run as Administrator (Windows)
2. Check if another instance running
3. Kill process: `pkill -f "python main.py"`

### Issue: "Character encoding error (Windows)"
**Solution:**
Already handled in main.py with:
```python
sys.stdout.reconfigure(encoding='utf-8')
```

---

## 📝 Configuration Files

### telegram_config.json (if using Telegram)
Auto-created on first run. Edit manually:
```json
{
  "bot_token": "YOUR_TOKEN",
  "allowed_chat_ids": [12345],
  "enabled": true,
  "admin_chat_id": 12345,
  "notify_transaction": true,
  "notify_low_stock": true,
  "low_stock_threshold": 20
}
```

---

## 🚀 Running the Application

### Start POS System
```bash
python main.py
```

### Start Just Telegram Bot
```bash
python telegram_bot.py
```

### With Virtual Environment (Recommended)

**Create venv:**
```bash
python -m venv venv
```

**Activate venv:**

Windows:
```bash
venv\Scripts\activate
```

Linux/Mac:
```bash
source venv/bin/activate
```

**Install packages:**
```bash
pip install python-telegram-bot requests
```

**Run:**
```bash
python main.py
```

**Deactivate when done:**
```bash
deactivate
```

---

## 📚 Next Steps

1. **Read Main Documentation:**
   ```
   README.md
   ```

2. **Setup Telegram (Optional):**
   ```
   TELEGRAM_BOT_QUICKSTART.md → TELEGRAM_SETUP.md
   ```

3. **Learn Code Structure:**
   - database.py: Database operations
   - models.py: Business logic
   - transaction.py: Sales flow
   - laporan.py: Reports & analytics
   - main.py: CLI interface
   - telegram_bot.py: Telegram integration

4. **Explore Features:**
   - Add products and run transactions
   - Generate daily reports
   - Export to CSV
   - Test Telegram commands

---

## 💻 System Requirements for Different Scenarios

### Minimal (Core POS Only)
- Python 3.8+
- 20MB disk space
- No external libraries needed

### Standard (POS + Telegram)
- Python 3.8+
- 50MB disk space
- Internet connection
- `python-telegram-bot` & `requests` packages

### Production
- Python 3.9+
- 100MB+ disk space
- Database: PostgreSQL (recommended)
- Web server: Gunicorn/uWSGI
- Reverse proxy: Nginx
- SSL certificate
- Monitoring tools

---

## 🔐 Security Notes

### Development
```python
# Current: localhost only, no auth
python main.py
```

### Production
1. Add user authentication
2. Encrypt sensitive data
3. Use HTTPS for web API
4. Database backup strategy
5. Log monitoring

---

## 📞 Getting Help

1. **Check Logs:**
   ```bash
   tail telegram_bot.log  # Telegram logs
   ```

2. **Read Documentation:**
   - README.md - Main features
   - TELEGRAM_SETUP.md - Bot detailed guide
   - Code comments (extensive docstrings)

3. **Test Connectivity:**
   ```bash
   python telegram_bot.py  # Standalone test
   ```

---

## ✅ Installation Checklist

- [ ] Python 3.8+ installed
- [ ] Project folder created
- [ ] All Python files copied
- [ ] First run successful (database created)
- [ ] Can add product via Menu 1
- [ ] Can run transaction via Menu 2
- [ ] Can see reports via Menu 3
- [ ] (Optional) Telegram bot setup & running
- [ ] Read main README.md
- [ ] Tested all core features

---

**🎉 Installation Complete! Selamat menggunakan POS System!**

For more details, see [README.md](README.md)
