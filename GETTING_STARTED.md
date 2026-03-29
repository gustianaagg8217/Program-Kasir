# 🚀 Getting Started - 5 Menit Setup

Panduan tercepat untuk mulai gunakan POS System dalam 5 menit!

---

## 1️⃣ Install Python (1 menit)

**Windows:**
```bash
# Download from: https://www.python.org/downloads/
# Install dengan "Add Python to PATH" ✅
```

**Verify:**
```bash
python --version
```

---

## 2️⃣ Download Files (1 menit)

Copy semua `.py` files ke folder:
```
d:\Program_Kasir\
```

---

## 3️⃣ Run Program! (1 menit)

```bash
cd d:\Program_Kasir
python main.py
```

**✅ POS System started!**

---

## 4️⃣ First Transaction (2 menit)

### Jump ke Menu 1: Kelola Produk
```
Pilih: 1
Input: 1 (Tambah Produk)

Kode Produk: COFFEE
Nama: Kopi Hitam
Harga: 12000
Stok: 50

Status: ✅ Produk ditambahkan
```

### Jump ke Menu 2: Transaksi Penjualan
```
Pilih: 2
Input: 1 (Tambah Item)

Kode Produk: COFFEE
Jumlah: 2

Pilih: 2 (Lihat Item)
→ COFFEE x2 = 24000

Pilih: 3 (Konfirmasi Pembayaran)

Total: 24000
Bayar: 25000
Kembalian: 1000

Status: ✅ Transaksi selesai, struk digenerate
```

---

## 🎯 Selesai!

Anda sudah bisa:
- ✅ Kelola produk
- ✅ Jual barang
- ✅ Generate struk
- ✅ Lihat laporan

---

## 📊 Menu Quick Reference

```
Menu Utama:
├─ 1: Kelola Produk
│  ├─ 1: Tambah Produk
│  ├─ 2: Edit Produk
│  ├─ 3: Hapus Produk
│  └─ 4: Lihat Stok
│
├─ 2: Transaksi Penjualan
│  ├─ 1: Tambah Item
│  ├─ 2: Lihat Item
│  ├─ 3: Konfirmasi Pembayaran
│  └─ 4: Batalkan Transaksi
│
├─ 3: Laporan & Export
│  ├─ 1: Laporan Harian
│  ├─ 2: Laporan Periode
│  ├─ 3: Produk Terlaris
│  ├─ 4: Lihat Stok
│  └─ 5: Export ke CSV
│
└─ 4: Telegram Bot (Optional)
   ├─ 1: Setup Configuration
   ├─ 2: Start Bot
   ├─ 3: Test Connection
   ├─ 4: Show Commands
   └─ 5: Send Test Report
```

---

## 🤖 Setup Telegram Bot (Optional)

Jika ingin notifikasi real-time:

### Step 1: Get Bot Token
```
Buka Telegram → Chat: @BotFather
/start → /newbot → Follow instructions
Copy token (contoh: 1234567890:ABCdefGHIjklmNOPqrsTUVwxyzABC...)
```

### Step 2: Get Chat ID
```
Chat: @userinfobot → /start
Copy Your user ID (contoh: 987654321)
```

### Step 3: Setup in Program
```
Menu 4 → 1 (Setup Configuration)
Bot Token: [paste dari @BotFather]
Admin Chat ID: [paste dari @userinfobot]
Status: ✅ Configuration saved
```

### Step 4: Start Bot
```
Menu 4 → 2 (Start Bot)
Status: ✅ Bot running...
```

**✅ Done! Now Telegram akan notify setiap transaksi**

---

## 💾 File Database

Database otomatis create saat first run:
```
kasir_pos.db
```

Berisi:
- Daftar produk
- Semua transaksi
- Detail item per transaksi

---

## 📁 Generated Files

Setelah pertama kali run:
```
Program_Kasir/
├── kasir_pos.db              (database)
├── telegram_config.json      (config bot - jika telegram digunakan)
├── receipts/                 (folder untuk struk)
│  └── RECEIPT_2024...txt    (struk transaksi)
├── exports/                  (folder CSV export)
│  └── Laporan_20240101.csv  (export laporan)
└── telegram_bot.log          (log file untuk telegram)
```

---

## ⚠️ Common Issues

### "Command not found: python"
```bash
# Di Windows: Gunakan python atau py
python main.py
py main.py

# Di Linux: Gunakan python3
python3 main.py
```

### "ModuleNotFoundError: No module named 'telegram'"
Jika ingin gunakan Telegram Bot:
```bash
pip install python-telegram-bot requests
```

### "Permission denied"
```bash
# Windows: Run as Administrator
# Linux: chmod +x main.py
```

---

## 📞 Help & Documentation

- **Detailed Setup:** See [INSTALL.md](INSTALL.md)
- **Telegram Guide:** See [TELEGRAM_BOT_QUICKSTART.md](TELEGRAM_BOT_QUICKSTART.md)
- **Full Features:** See [README.md](README.md)
- **Telegram Details:** See [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md)

---

## 🎓 Next Learning Steps

1. **Explore Menu 3 (Laporan)**
   - Lihat laporan harian penjualan
   - Generate laporan periode
   - Export ke CSV untuk spreadsheet

2. **Setup Telegram Bot**
   - Real-time notifications
   - Remote reporting
   - Low stock alerts

3. **Read Documentation**
   - README.md: Feature overview
   - INSTALL.md: Advanced setup
   - Code comments: Implementation details

---

## 🞆 Pro Tips

**Tip 1: Batch Import**
```
Buat file CSV dengan format:
kode,nama,harga,stok
PROD001,Kopi,12000,50
PROD002,Teh,10000,30

Bisa import lewat future feature
```

**Tip 2: Daily Backup**
```
Backup kasir_pos.db every day:
Copy kasir_pos.db → kasir_pos_backup_2024MMDD.db
```

**Tip 3: Use Telegram Bot**
```
Send /laporan untuk lihat sales harian
Send /stok untuk check inventory
Send /terlaris untuk lihat top products
```

**Tip 4: Export Reports**
```
Menu 3 → 5 (Export ke CSV)
File saved di: exports/Laporan_YYYYMMDD.csv
Bisa buka di Excel/Google Sheets
```

---

**🎉 Selamat! Anda siap gunakan POS System!**

Jika ada pertanyaan → Lihat [README.md](README.md)

---

Last Updated: 2024
Version: 1.0
