# 🚀 Stok Opname - Quick Start

## Instalasi

1. File sudah tersedia:
   - `stok_opname.py` - Backend logic
   - `gui_main.py` - GUI integration (sudah updated)

2. Database tables otomatis dibuat saat pertama kali dijalankan

## 3 Steps Cepat

### Step 1: Buat Session
```
Menu → Stok Opname → Session Baru
↓
Isi tanggal + keterangan
↓
Klik "Buat Session"
```

### Step 2: Input Stok
```
Tab: Session Aktif
↓
Cari produk → Input stok fisik → Catatan (opsional)
↓
Klik "Tambah Item" (ulangi untuk produk lain)
```

### Step 3: Selesaikan
```
Klik "Selesaikan Session"
↓
Konfirmasi
↓
Stok terupdate otomatis ✅
```

## Menu di GUI

```
📊 Sidebar Menu
├── 🏠 Dashboard
├── 📦 Produk
├── 📋 Stok Opname  ← NEW!
│   ├── 📊 Session Aktif
│   ├── ➕ Session Baru
│   └── 📜 Riwayat
├── 🛒 Transaksi
├── 📊 Laporan
├── 🤖 Telegram Bot
└── ⚙️ Settings
```

## Shortcut Fitur

- **Buat Session**: Menu → Stok Opname → Session Baru
- **Input Stok**: Menu → Stok Opname → Session Aktif
- **Lihat Laporan**: Menu → Stok Opname → Riwayat

## Integrasi dengan Fitur Lain

✅ **Dengan Produk**: Produk dipilih dari daftar produk aktif
✅ **Dengan Laporan**: History tersimpan di database
✅ **Dengan Dashboard**: Tidak ada perubahan

---

## Testing Commands

```python
# Test import
python -c "from stok_opname import StokOpnameService; print('✅ OK')"

# Test database init
python -c "from database import DatabaseManager; from stok_opname import StokOpnameService; db=DatabaseManager(); svc=StokOpnameService(db); print('✅ DB Init OK')"

# Run GUI
python gui_main.py
```

---

## Files Modified/Created

| File | Type | Status |
|------|------|--------|
| stok_opname.py | NEW | ✅ Created |
| gui_main.py | MODIFIED | ✅ Updated |
| STOK_OPNAME_GUIDE.md | NEW | ✅ Created |
| STOK_OPNAME_QUICKSTART.md | NEW | ✅ Created |

---

## Troubleshooting Cepat

```
❌ "Import Error stok_opname"
→ Pastikan file stok_opname.py ada di folder yang sama dengan gui_main.py

❌ "Produk tidak ditemukan"
→ Buat produk dulu di menu "Produk" sebelum stok opname

❌ Database error
→ Pastikan database sudah ter-initialize (jalankan gui_main.py dulu)

❌ Session tidak muncul
→ Session berstatus 'active' baru muncul di Session Aktif
→ Yang selesai ada di riwayat
```

---

**Status**: ✅ Ready to Use  
**Tested on**: Python 3.8+  
**Last Update**: 2024
