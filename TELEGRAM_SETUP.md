# 🤖 Telegram Bot Setup Guide - POS System

Panduan lengkap untuk setup dan menggunakan Telegram Bot dengan POS System.

---

## 📋 Daftar Isi
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Setup Step-by-Step](#setup-step-by-step)
- [Commands](#commands)
- [Configuration](#configuration)
- [Notifications](#notifications)
- [Troubleshooting](#troubleshooting)

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install python-telegram-bot requests
```

### 2. Create Telegram Bot (BotFather)
- Open Telegram
- Search for **@BotFather**
- Send `/newbot`
- Follow instructions
- Copy the **TOKEN** (save it!)

### 3. Get Your Chat ID
- Open Telegram
- Search for **@userinfobot**
- Send `/start`
- Copy your **Chat ID** (numeric value)

### 4. Configure POS System
```bash
# Run main.py
python main.py

# Navigate to: Menu 4 → Telegram Bot → Setup Configuration
# Fill in:
# - Bot Token (from BotFather)
# - Admin Chat ID (from userinfobot)
```

### 5. Start Bot
```
Menu 4 → Telegram Bot → Jalankan Bot (Polling)
```

**✅ Done! Bot is now running.**

---

## 📦 Installation

### Prerequisites
- Python 3.8+
- Telegram account
- Internet connection

### Step 1: Install Library
```bash
pip install python-telegram-bot requests
```

Verify installation:
```bash
python -c "import telegram; print(telegram.__version__)"
```

### Step 2: Check Compatibility
```bash
# Run telegram_bot.py standalone
python telegram_bot.py
```

If error:
```
❌ python-telegram-bot tidak terinstall!
Install dengan: pip install python-telegram-bot
```

Then install the missing package.

---

## 📝 Setup Step-by-Step

### Step 1: Create Bot in Telegram

**1a. Open Telegram & Find BotFather**
- Search for `@BotFather`
- Click on it

**1b. Create New Bot**
- Send message: `/newbot`
- Reply with desired bot name (e.g., "POS Bot")
- Reply with username (e.g., `my_pos_bot_123`) - must end with "bot"
- BotFather will give you the **TOKEN**

**Example Response:**
```
Done! Congratulations on your new bot.
You will find it at t.me/my_pos_bot_123
Use this token to access the HTTP API:
1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefgh

Keep your token secure and store it safely!
```

**Save the TOKEN!** (part after the colon)

### Step 2: Get Your Chat ID

**2a. Find userinfobot**
- Search for `@userinfobot` on Telegram
- Click on it, send `/start`

**Example Response:**
```
✅ Your user ID is: 123456789
```

**Save your Chat ID!** (numeric value)

### Step 3: Configure telegram_config.json

```json
{
  "bot_token": "1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefgh",
  "allowed_chat_ids": [123456789],
  "enabled": true,
  "admin_chat_id": 123456789,
  "notify_transaction": true,
  "notify_low_stock": true,
  "low_stock_threshold": 20
}
```

**Or use Menu 4 in POS System for interactive setup.**

### Step 4: Run Telegram Bot

**Option A: Via POS Menu**
```
python main.py
→ Menu 4 (Telegram Bot)
→ Setup Configuration (fill token & chat ID)
→ Jalankan Bot
```

**Option B: Standalone**
```bash
python telegram_bot.py
```

**✅ Bot is running!** You'll see:
```
======================================================================
🤖 TELEGRAM BOT SEDANG BERJALAN
======================================================================
Bot Token: 1234567890:ABCDEFGHIJ...
Admin Chat ID: 123456789
Allowed Users: 1
======================================================================
```

---

## 💬 Commands

### Available Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/laporan` | Daily sales report | Shows total sales, transactions, top products |
| `/stok` | Stock information | Shows all products with status (OK, LOW, EMPTY) |
| `/terlaris` | Top selling products | Top 10 products by quantity |
| `/dashboard` | Quick summary | Today's sales + top products + low stock alert |
| `/ping` | Test connection | Confirms bot is online |
| `/help` | Show all commands | Displays this list |

### Example Usage

**Command: /laporan**
```
Request: /laporan
Response:
📊 LAPORAN PENJUALAN HARIAN - 2026-03-29

📊 RINGKASAN:
  Total Penjualan       : Rp 450.000
  Total Transaksi       : 10 transaksi
  Rata-rata Transaksi   : Rp 45.000
  Total Item Terjual    : 25 item

🏆 TOP 5 PRODUK:
  1. Mie Goreng                10 qty | Rp 150.000
  2. Teh Botol                 12 qty | Rp 60.000
  3. Roti Tawar                 3 qty | Rp 60.000
```

**Command: /stok**
```
Request: /stok
Response:
📦 INFO STOK PRODUK

🟢 STOK OK (8)
  • Mie Goreng: 50 unit
  • Roti Tawar: 25 unit
  ... dan 6 lainnya

🟡 STOK MINIM (2)
  ⚠️ Teh Botol: 15 unit
  ⚠️ Kopi Instan: 8 unit

🔴 STOK KOSONG (1)
  ❌ Jus Jeruk: Stok habis
```

---

## ⚙️ Configuration

### telegram_config.json Structure

```json
{
  "bot_token": "string",              // Token from BotFather
  "allowed_chat_ids": [int],          // List of allowed user IDs
  "enabled": boolean,                 // Enable/disable bot
  "admin_chat_id": int,               // Admin's chat ID
  "notify_transaction": boolean,      // Send transaction notifications
  "notify_low_stock": boolean,        // Send low stock alerts
  "low_stock_threshold": int          // Alert if stok < this value
}
```

### Example Configurations

**Basic Setup (Single Admin)**
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

**Multi-User Setup**
```json
{
  "bot_token": "YOUR_TOKEN_HERE",
  "allowed_chat_ids": [123456789, 987654321, 555555555],
  "enabled": true,
  "admin_chat_id": 123456789,
  "notify_transaction": true,
  "notify_low_stock": true,
  "low_stock_threshold": 20
}
```

**Notifications Disabled**
```json
{
  "bot_token": "YOUR_TOKEN_HERE",
  "allowed_chat_ids": [123456789],
  "enabled": true,
  "admin_chat_id": 123456789,
  "notify_transaction": false,
  "notify_low_stock": false,
  "low_stock_threshold": 20
}
```

---

## 🔔 Notifications

### Transaction Notifications

When enabled, bot sends notification for every transaction:

```
💳 TRANSAKSI BARU

ID: #000001
Produk: Mie Goreng
Qty: 2
Total: Rp 30.000
Waktu: 14:30:45
```

**Enable/Disable:**
- Edit `telegram_config.json`
- Set `"notify_transaction": true/false`

### Low Stock Alerts

When stock falls below threshold:

```
⚠️ STOK PRODUK MINIM

Produk: Teh Botol
Stok Tersisa: 15 unit
Threshold: 20 unit
Waktu: 14:30:45
```

**Configure:**
- Edit `telegram_config.json`
- Set `"low_stock_threshold": 20` (or custom value)
- Set `"notify_low_stock": true`

---

## 🐛 Troubleshooting

### Problem: "python-telegram-bot not installed"

**Solution:**
```bash
pip install python-telegram-bot requests
```

### Problem: "Bot Token not configured"

**Solution:**
1. Run `python main.py`
2. Go to Menu 4 → Setup Configuration
3. Enter bot token from BotFather
4. Enter admin chat ID

### Problem: "Anda tidak memiliki akses ke bot ini"

**This means:** Your chat ID is not in `allowed_chat_ids`

**Solution:**
1. Get your chat ID using @userinfobot
2. Edit `telegram_config.json` OR
3. Use POS Menu 4 → Setup Configuration to add yourself

### Problem: "Bot tidak responsif"

**Solution:**
1. Check if bot is running: `Menu 4 → Jalankan Bot`
2. Test connection: `Menu 4 → Test Connection`
3. Check internet connection
4. Run `tail telegram_bot.log` to see logs

### Problem: "Error sending message"

**Common Issues:**
- Chat ID is wrong → verify with @userinfobot
- Bot token is invalid → regenerate at @BotFather
- Chat ID not in allowed_chat_ids → add to config
- No internet connection → check your connection

### Problem: "Bot stops running"

**Solution:**
Keep running in terminal, don't close window.

**For Persistent Running:**
- Windows: Use Task Scheduler or `pythonw` wrapper
- Linux: Use systemd service or screen/tmux
- Docker: Containerize the application

### Checking Logs

All errors logged to `telegram_bot.log`:

```bash
# View recent logs
tail -20 telegram_bot.log

# Search for errors
grep "ERROR" telegram_bot.log
```

---

## 💡 Advanced Usage

### Sending Notifications from POS

```python
from telegram_bot import POSTelegramBot

bot = POSTelegramBot()

# Send transaction notification
await bot.send_transaction_notification(
    transaction_id=1,
    product_name="Mie Goreng",
    qty=2,
    total=30000
)

# Send low stock alert
await bot.send_low_stock_alert(
    product_name="Teh Botol",
    stok=15
)

# Send daily report
await bot.send_daily_report()
```

### Custom Messages

```python
# Send custom message to admin
await bot.bot.send_message(
    chat_id=bot.config_manager.config.get("admin_chat_id"),
    text="Your custom message here",
    parse_mode="Markdown"
)
```

### Multiple Admins

Add multiple chat IDs to `allowed_chat_ids`:

```json
"allowed_chat_ids": [12345, 67890, 11111]
```

Each user can use all commands independently.

---

## 📱 Mobile Experience

### Best Practices

1. **Pin Bot Chat**
   - Right-click bot chat
   - Select "Pin Chat"
   - Easy access from top

2. **Notifications**
   - Enable notifications for important alerts
   - Disable for frequent commands

3. **Command Shortcuts**
   - Long-press on command option
   - Copy for quick access

---

## 🔐 Security Notes

1. **Keep Token Secret**
   - Never share bot token
   - Don't commit `telegram_config.json` to GitHub

2. **Verify Chat IDs**
   - Only add trusted Telegram IDs
   - Regular audit of `allowed_chat_ids`

3. **Database Access**
   - Bot reads real-time from SQLite database
   - No payments or sensitive operations

---

## 📚 Resources

- [python-telegram-bot docs](https://python-telegram-bot.readthedocs.io/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [BotFather Guide](https://core.telegram.org/bots#botfather)

---

## ✅ Checklist

- [ ] Install python-telegram-bot
- [ ] Create bot with @BotFather  
- [ ] Get chat ID from @userinfobot
- [ ] Configure telegram_config.json
- [ ] Test connection via POS Menu
- [ ] Send test report
- [ ] Enable notifications (if needed)
- [ ] Start bot polling

---

**🎉 Telegram Bot Setup Complete! Enjoy real-time POS updates on Telegram!**
