# 🤖 Telegram Bot - Quick Start Guide (5 Menit)

Panduan cepat setup Telegram Bot dalam 5 menit!

---

## 🚀 5-Menit Setup

### Step 1: Install Library (1 menit)
```bash
pip install python-telegram-bot requests
```

### Step 2: Create Bot di Telegram (2 menit)

1. **Open Telegram**
   - Search: `@BotFather`
   - Click on BotFather

2. **Create New Bot**
   - Send message: `/newbot`
   - When asked for name: `My POS Bot`
   - When asked for username: `my_pos_bot_123` (harus unik & end with "bot")

3. **Copy Token**
   BotFather akan reply:
   ```
   Done! Congratulations on your new bot.
   ...
   Use this token to access the HTTP API:
   1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefgh
   ```
   **SAVE TOKEN** (bagian setelah colon)

### Step 3: Get Your Chat ID (1 menit)

1. **Open Telegram**
   - Search: `@userinfobot`
   - Send: `/start`

2. **Copy Chat ID**
   userinfobot akan reply:
   ```
   Your user ID is: 123456789
   ```
   **SAVE CHAT ID**

### Step 4: Setup POS System (1 menit)

Run POS:
```bash
python main.py
```

Go to:
```
Menu 4 (Telegram Bot)
→ Setup Configuration
→ Enter Bot Token (from BotFather)
→ Enter Admin Chat ID (from userinfobot)
```

### Step 5: Start Bot

From Menu:
```
Menu 4 (Telegram Bot)
→ Jalankan Bot (Polling)
```

**✅ DONE! Bot is running!**

---

## 💬 Gunakan Bot

Open Telegram → Search your bot → Try commands:

```
/laporan      → Today's sales report
/stok         → Stock information
/terlaris     → Top selling products
/dashboard    → Quick summary
/ping         → Test bot
/help         → All commands
```

---

## 🔧 Troubleshooting

### "Bot tidak responsif"
- ✅ Pastikan terminal dengan bot masih running
- ✅ Cek internet connection
- ✅ Kirim `/ping` untuk test

### "Unauthorized access"
- ✅ Chat ID Anda belum di `allowed_chat_ids`
- ✅ Re-run setup configuration
- ✅ Pastikan chat ID benar (dari @userinfobot)

### "Bot Token error"
- ✅ Pastikan token benar (dari @BotFather)
- ✅ Jangan ada spasi di awal/akhir
- ✅ Regenerate token bila perlu (@BotFather → /token)

---

## 📚 Next Steps

- ✅ **Full Setup Guide:** [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md)
- ✅ **API Reference:** See `telegram_bot.py` docstrings
- ✅ **Configuration:** Edit `telegram_config.json`

---

## 📝 Common Config

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

---

**Happy Telegramming! 🎉**
