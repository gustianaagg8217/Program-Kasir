# 🔧 Troubleshooting Guide

Solusi lengkap untuk masalah yang mungkin Anda hadapi.

---

## Table of Contents
1. [Installation Issues](#installation-issues)
2. [Runtime Issues](#runtime-issues)
3. [Telegram Bot Issues](#telegram-bot-issues)
4. [Database Issues](#database-issues)
5. [Feature Issues](#feature-issues)
6. [Performance Issues](#performance-issues)

---

## Installation Issues

### Problem 1: "Python not found" / "Command not recognized"

**Symptoms:**
```
'python' is not recognized as an internal or external command
```

**Solutions:**

**Windows:**
```bash
# Try dengan py
py main.py

# Or set PATH manually
"C:\Program Files\Python311\python.exe" main.py

# Or reinstall Python with PATH enabled
# Download: https://www.python.org/downloads/
# ✅ Check: "Add python.exe to PATH" during install
```

**Linux/Mac:**
```bash
# Use python3
python3 main.py

# Or set alias
alias python=python3
python main.py
```

**Verification:**
```bash
python --version
# Should show: Python 3.8.x or higher
```

---

### Problem 2: "pip not found" / "Cannot install packages"

**Symptoms:**
```
'pip' is not recognized
pip: command not found
ERROR: Could not find a version that satisfies the requirement
```

**Solutions:**

**Windows:**
```bash
# Try dengan py -m pip
py -m pip --version

# Install packages dengan py -m pip
py -m pip install python-telegram-bot requests
```

**Linux/Mac:**
```bash
# Use python3 -m pip
python3 -m pip install python-telegram-bot requests

# Or upgrade pip first
python3 -m pip install --upgrade pip
```

**Full Diagnostic:**
```bash
python -m pip --version
python -m pip list
python -m pip install --upgrade pip setuptools wheel
```

---

### Problem 3: "No module named 'telegram'" / Missing dependencies

**Symptoms:**
```
ModuleNotFoundError: No module named 'telegram'
ImportError: cannot import name 'telegram'
```

**Solutions:**

```bash
# Install telegram bot library
pip install python-telegram-bot requests

# Or specific version
pip install python-telegram-bot==20.0 requests==2.28.0

# Verify installation
pip show python-telegram-bot
python -c "import telegram; print(telegram.__version__)"
```

**If still failing:**
```bash
# Use specific Python interpreter
"C:\Program Files\Python311\Scripts\pip.exe" install python-telegram-bot requests

# Or use py
py -m pip install python-telegram-bot requests

# Check installed packages
pip list | grep telegram
```

---

## Runtime Issues

### Problem 1: "Database locked" / Database corruption

**Symptoms:**
```
sqlite3.OperationalError: database is locked
sqlite3.DatabaseError: database disk image is malformed
```

**Solutions:**

**Quick Fix:**
```bash
# Kill any running instances
# Windows
taskkill /f /im python.exe

# Linux/Mac
pkill -f "python main.py"

# Wait 2 seconds, then restart
python main.py
```

**If Still Locked:**
```bash
# Rename old database
rename kasir_pos.db kasir_pos.db.bak

# Restart program (new database will be created)
python main.py
```

**Full Recovery:**
```bash
# Backup old data
copy kasir_pos.db kasir_pos_backup_$(date +%Y%m%d).db

# Delete corrupted database
del kasir_pos.db

# Or use vacuum to repair
python -c "
import sqlite3
conn = sqlite3.connect('kasir_pos.db')
conn.execute('VACUUM')
conn.close()
print('✅ Database repaired')
"

# Restart
python main.py
```

---

### Problem 2: "Character encoding error" / Special characters broken

**Symptoms:**
```
UnicodeDecodeError: 'utf-8' codec can't decode...
Mojibake characters (ภษำญฤี instead of Indonesian)
```

**Solutions:**

**Already handled in main.py:**
```python
sys.stdout.reconfigure(encoding='utf-8')
```

**If still broken on Windows:**
```bash
# Run dengan encoding explicit
chcp 65001
python main.py

# Or set environment variable
set PYTHONIOENCODING=utf-8
python main.py
```

**On Linux/Mac:**
```bash
export PYTHONIOENCODING=utf-8
python3 main.py
```

---

### Problem 3: "No menu appears" / Program exits immediately

**Symptoms:**
```
[Program runs but shows no menu]
[Program crashes immediately]
```

**Solutions:**

**Collect Error Details:**
```bash
# Run dengan verbose output
python main.py 2>&1 | tee debug.log

# Check what's in debug.log
cat debug.log
```

**Common Causes:**

1. **Missing database initialization:**
```bash
# Manually initialize
python -c "
from database import DatabaseManager
db = DatabaseManager()
print('✅ Database initialized')
"
```

2. **Permission denied:**
```bash
# Windows: Run as Administrator
# Linux/Mac:
chmod 755 main.py
python main.py
```

3. **Corrupted main.py:**
```bash
# Check syntax
python -m py_compile main.py

# If error, redownload main.py
```

---

## Telegram Bot Issues

### Problem 1: "Bot token invalid" / Connection refused

**Symptoms:**
```
TelegramError: Unauthorized
ConnectionError: HTTPSConnectionPool timeout
```

**Solutions:**

**Verify Bot Token:**

1. **Get correct token:**
```
Telegram → @BotFather
/start → /newbot → Follow steps
Copy token (format: 123456789:ABCdef...)
```

2. **Check token format:**
```
- Must be: digits:alphanumeric
- Example: 1234567890:ABCdef_GhiJklmNOPqrsTu_vwXyZ-AB
- NOT example "@mybot" or similar
```

3. **Verify in config:**
```bash
# Edit telegram_config.json
{
  "bot_token": "123456789:ABCdef_GhiJklmNOPqrsTu_vwXyZ-AB",
  "enabled": true,
  ...
}
```

**Test Token:**
```bash
python -c "
import requests
token = 'YOUR_TOKEN_HERE'
url = f'https://api.telegram.org/bot{token}/getMe'
response = requests.get(url)
print(response.json())
"
```

---

### Problem 2: "Bot not receiving messages" / Stuck waiting for updates

**Symptoms:**
```
Bot running... waiting for commands [infinite wait]
No response when sending /laporan
```

**Solutions:**

**Check Bot is Running:**
```bash
# In separate terminal
ps aux | grep "telegram_bot.py"
# Should show running process

# Or check port
netstat -an | grep LISTEN
```

**Test Bot Token Manually:**
```bash
# Test dengan curl
curl "https://api.telegram.org/botTOKEN/getMe"

# Should return:
# {"ok":true,"result":{"id":123456789,"is_bot":true,"first_name":"MyBot",...}}
```

**Restart Bot:**
```bash
# Stop current bot
Ctrl+C

# Clear temp files
rm -f telegram_bot.log

# Restart
python main.py → Menu 4 → Start Bot
```

**Check Allowed Chat IDs:**
```json
{
  "allowed_chat_ids": [123456, 789012],  // ← Your ID must be here
  "permissions": ["send_messages", "read_receipts"]
}
```

---

### Problem 3: "Message send failed" / No notifications

**Symptoms:**
```
[Telegram bot running but no messages arrive]
TelegramError: Chat not found
```

**Solutions:**

**Verify Chat IDs:**

1. **Get your Chat ID:**
```
Telegram → @userinfobot
/start
Copy: Your user ID = 123456789
```

2. **Add to config:**
```json
{
  "allowed_chat_ids": [123456789],
  "admin_chat_id": 123456789
}
```

3. **Restart and test:**
```bash
Menu 4 → Setup Configuration
(update allowed_chat_ids)

Menu 4 → Send Test Report
Should receive message: "🧪 TEST REPORT"
```

**Check Internet Connection:**
```bash
# Test connectivity
python -c "
import requests
try:
    response = requests.get('https://api.telegram.org', timeout=5)
    print('✅ Internet OK')
except:
    print('❌ No internet or blocked')
"
```

---

### Problem 4: "Bot keeps crashing" / Repeated errors

**Symptoms:**
```
Bot Error: ... [exits]
Bot restarting... [repeats]
```

**Solutions:**

**Check Logs:**
```bash
# View telegram bot log
tail -f telegram_bot.log

# Or view all logs
cat telegram_bot.log | grep -i error
```

**Common Errors:**

1. **"AttributeError: NoneType has no attribute"**
   - Usually: Database not initialized
   - Fix: Delete kasir_pos.db and restart

2. **"TimeoutError: Connection timeout"**
   - Usually: Internet issue or Telegram API down
   - Fix: Check internet, wait, then restart bot

3. **"ValueError: Invalid token"**
   - Usually: Wrong token format
   - Fix: Re-copy token from @BotFather

**Debug Mode:**
```bash
# Add verbose logging
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)

from telegram_bot import POSTelegramBot
bot = POSTelegramBot()
bot.start_polling()
"
```

---

## Database Issues

### Problem 1: "Database file not found" / New database created

**Symptoms:**
```
Previous data lost after restart
Database reset to empty
```

**Solutions:**

**Locate Database:**
```bash
# Find kasir_pos.db
find . -name "kasir_pos.db"

# Should be in same folder as main.py
```

**Backup and Restore:**
```bash
# Backup current
copy kasir_pos.db kasir_pos_backup.db

# Restore from backup if needed
copy kasir_pos_backup.db kasir_pos.db
```

**Check Database Integrity:**
```bash
python -c "
import sqlite3
try:
    conn = sqlite3.connect('kasir_pos.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM products')
    count = cursor.fetchone()[0]
    print(f'✅ Database OK - {count} products')
except Exception as e:
    print(f'❌ Database Error: {e}')
"
```

---

### Problem 2: "Duplicate entries" / Data duplication

**Symptoms:**
```
Same product appears multiple times
Duplicate transactions in report
```

**Solutions:**

**Check Database:**
```bash
sqlite3 kasir_pos.db "SELECT * FROM products WHERE nama='Kopi';"
# Should show 1 row (or expected number)
```

**Remove Duplicates:**
```bash
sqlite3 kasir_pos.db "
DELETE FROM products 
WHERE rowid NOT IN (
  SELECT MIN(rowid) FROM products GROUP BY kode
);
"
```

**Verify:**
```bash
python -c "
from database import DatabaseManager
db = DatabaseManager()
products = db.get_all_products()
print(f'Total unique products: {len(set(p.kode for p in products))}')
"
```

---

## Feature Issues

### Problem 1: "Cannot add product" / Validation errors

**Symptoms:**
```
❌ Error: [validation message]
Product not added
```

**Common Validations:**

```
Kode Produk:
- Required (tidak boleh kosong)
- Unik (tidak boleh duplicate)
- Max 20 karakter

Nama Produk:
- Required
- Max 100 karakter

Harga:
- Must be > 0
- Must be number

Stok:
- Must be >= 0
- Must be integer
```

**Solutions:**
```bash
# When adding product:
Kode: COFFEE (✓ unik, 6 char)
Nama: Kopi Hitam (✓ descriptive)
Harga: 12000 (✓ number > 0)
Stok: 50 (✓ integer >= 0)
```

---

### Problem 2: "Cannot process transaction" / Payment errors

**Symptoms:**
```
❌ Item tidak boleh kosong
❌ Pembayaran tidak valid
```

**Solutions:**

**Step 1: Add Item**
```
Kode: COFFEE
Qty: 2
Status: ✓ Item added

(Lihat berapa item ada di list)
```

**Step 2: Verify Item**
```
Menu 2 → 2 (Lihat Item)
Should show:
COFFEE x2 = 24000
Total: 24000
```

**Step 3: Payment**
```
Menu 2 → 3 (Konfirmasi Pembayaran)
Total: 24000
Input Bayar: 25000 (must be >= total)
Kembalian: 1000
✓ Transaksi selesai
```

---

### Problem 3: "Reports not generating" / Empty reports

**Symptoms:**
```
Laporan Harian: No data
CSV Export: Empty file
```

**Solutions:**

**Verify Data Exists:**
```bash
python -c "
from database import DatabaseManager
db = DatabaseManager()

# Check products
products = db.get_all_products()
print(f'Products: {len(products)}')

# Check transactions
transactions = db.get_transaksi_harian()
print(f'Transactions today: {len(transactions)}')
"
```

**Re-generate Report:**
```
Menu 3 → 1 (Laporan Harian)
# Should show transactions from today
```

**Export to CSV:**
```
Menu 3 → 5 (Export ke CSV)
# File saved to: exports/Laporan_YYYYMMDD.csv
```

---

## Performance Issues

### Problem 1: "Program slow" / Lag or freezes

**Symptoms:**
```
Menu response delayed
Typing slow
Report generation hangs
```

**Solutions:**

**Check Database Size:**
```bash
python -c "
import os
size = os.path.getsize('kasir_pos.db') / 1024 / 1024
print(f'Database size: {size:.2f} MB')

if size > 10:
    print('⚠️ Large database - consider archiving old data')
"
```

**Optimize Database:**
```bash
python -c "
import sqlite3
conn = sqlite3.connect('kasir_pos.db')
conn.execute('VACUUM')
conn.execute('ANALYZE')
conn.close()
print('✅ Database optimized')
"
```

**Close Other Programs:**
```bash
# If running on slow computer
# Close: Chrome, Spotify, antivirus scans, etc.
# Free up memory: 512MB+
```

---

### Problem 2: "High CPU usage" / Fan running loud

**Symptoms:**
```
CPU at 100%
Fan spinning fast
System sluggish
```

**Solutions:**

**Check Running Process:**
```bash
# Windows
tasklist | find "python"

# Linux/Mac
ps aux | grep python
```

**Limit Resource Usage:**
```python
# In main.py, add before loop:
import time
time.sleep(0.1)  # Slight delay to reduce CPU

# Or use nice priority (Linux)
nice -n 10 python main.py
```

**Archive Old Data:**
```bash
# Move old transactions to archive
python -c "
from database import DatabaseManager
import datetime

db = DatabaseManager()
old_date = datetime.datetime(2023, 1, 1)

# Get and backup transactions before date
# Then delete old transactions
"
```

---

## Still Have Problems?

### Collect Debug Info

```bash
# Save diagnostic info
python -c "
import sys
import sqlite3
print('Python:', sys.version)
print('SQLite:', sqlite3.version)
print('DB Size:', open('kasir_pos.db', 'rb').tell() / 1024 / 1024, 'MB')
" > diagnostic.txt

# View
cat diagnostic.txt
```

### Enable Debug Logging

```python
# Add to main.py
import logging
logging.basicConfig(
    filename='debug.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Then run
python main.py
# Check debug.log for details
```

### Reinstall Everything

```bash
# Clean installation
rm -rf kasir_pos.db telegram_config.json telegram_bot.log
rm -rf __pycache__ *.pyc

# Fresh start
python main.py
```

---

## Need More Help?

1. **Read Documentation:**
   - [README.md](README.md) - Features overview
   - [INSTALL.md](INSTALL.md) - Detailed installation
   - [GETTING_STARTED.md](GETTING_STARTED.md) - Quick start

2. **Check Logs:**
   - `telegram_bot.log` - Telegram bot logs
   - `debug.log` - If debug enabled
   - Windows Event Viewer - For system errors

3. **Contact Support:**
   - Check code comments/docstrings
   - Review error messages carefully
   - Try solutions in order

---

**Most issues resolved dengan restart or reinstall!** 🔄

Last updated: 2024
