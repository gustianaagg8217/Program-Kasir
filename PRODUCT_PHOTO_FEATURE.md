# Fitur Foto Produk - Optional Upload

## Overview
Fitur baru yang memungkinkan user menambahkan foto untuk setiap produk saat proses "Tambah Produk Baru". Foto adalah **OPTIONAL** (tidak wajib) - user bisa lewat/skip jika tidak ingin upload foto.

## Flow Tambah Produk dengan Foto

### Step 1: Input Kode Produk
```
User: "0007"
Bot: "Silakan ketik Nama Produk..."
```

### Step 2: Input Nama Produk
```
User: "Jedai Bulu"
Bot: "Silakan ketik Harga Produk (dalam Rp)..."
```

### Step 3: Input Harga
```
User: "7000"
Bot: "Silakan ketik Stok Awal produk..."
```

### Step 4: Input Stok Awal
```
User: "50"
Bot: 📸 *TAMBAHKAN FOTO PRODUK?*

Foto produk adalah optional (tidak wajib).
Anda bisa upload foto atau langsung skip.

[📷 Upload Foto] [⏭️ Skip (Tidak Ada Foto)]
```

### Step 5A: Upload Foto (Jika Pilih Upload)
```
User: (klik "📷 Upload Foto")
Bot: 📸 *UPLOAD FOTO PRODUK*

Silakan kirim foto produk Anda.
File harus berformat: JPG, PNG, atau JPEG

User: (send photo file)
Bot: [+] *PRODUK BERHASIL DITAMBAHKAN!*

KODE: 0007
NAMA: Jedai Bulu
HARGA: Rp 7.000
STOK: 50 pcs
FOTO: ✅ dengan foto
```

### Step 5B: Skip Foto (Jika Tidak Ingin Upload)
```
User: (klik "⏭️ Skip (Tidak Ada Foto)")
Bot: [+] *PRODUK BERHASIL DITAMBAHKAN!*

KODE: 0007
NAMA: Jedai Bulu
HARGA: Rp 7.000
STOK: 50 pcs
FOTO: tanpa foto
```

## Fitur Detail

### Upload Foto
- **Format**: JPG, PNG, JPEG
- **Lokasi Penyimpanan**: Folder `product_photos/` di root aplikasi
- **Nama File**: `[KODE_PRODUK].jpg` (contoh: `0007.jpg`)
- **Database**: Path foto tersimpan di tabel `products` kolom `foto_path`

### Skip Foto
- User bisa skip dengan tombol "⏭️ Skip"
- Atau ketik apapun di kanan tombol skip
- Atau gunakan `/cancel` untuk batalkan seluruh proses tambah produk

### Database Schema
Tabel `products` ditambah kolom baru:
```sql
foto_path TEXT DEFAULT NULL
```

## Implementation Details

### New Conversation State
- `KELOLA_PRODUK_TAMBAH_FOTO` - State untuk proses foto input

### New Handlers
1. `handle_kp_stok()` - DIMODIFIKASI: Sekarang transit ke state FOTO
2. `handle_kp_upload_foto_btn()` - Tampilkan instruksi upload foto
3. `handle_kp_foto()` - Terima dan simpan foto dari user
4. `handle_kp_skip_foto()` - Handle skip foto dari callback button
5. `handle_kp_skip_foto_text()` - Handle skip foto dari text input
6. `_save_product_to_db()` - Simpan produk ke database dengan foto_path
7. `_save_product_to_db_from_callback()` - Variant untuk callback query

### Updated Methods
- `database.add_product()` - Sekarang accept parameter `foto_path` (optional)
- `DatabaseManager.init_db()` - Tabel products punya kolom `foto_path`

## User Experience

### Keuntungan
✅ Foto produk membantu customer identifikasi produk
✅ Optional - tidak membebani user yang ingin cepat
✅ Mudah upload - cukup send foto
✅ Simpan otomatis - user tidak perlu atur sendiri nama file
✅ Clear feedback - user tahu apakah foto sudah upload

### Error Handling
- ❌ Gagal download foto → Tampilkan error, tanya retry atau skip
- ❌ File bukan foto → MessageHandler hanya terima filters.PHOTO
- ❌ Folder product_photos tidak ada → Auto-create saat pertama kali

## API Reference

### State Constant
```python
KELOLA_PRODUK_TAMBAH_FOTO = 14  # New state untuk foto
```

### Handler Signatures
```python
async def handle_kp_upload_foto_btn(update, context) -> int:
    """Handle button click untuk upload foto"""

async def handle_kp_foto(update, context) -> int:
    """Handle foto upload dari user"""

async def handle_kp_skip_foto(update, context) -> int:
    """Handle skip foto dari button"""

async def handle_kp_skip_foto_text(update, context) -> int:
    """Handle skip foto dari text input"""
```

### Database Method
```python
def add_product(self, kode: str, nama: str, harga: int, stok: int, 
                foto_path: str = None) -> bool:
    """
    Args:
        foto_path (str, optional): Path ke file foto produk
    """
```

## Directory Structure
```
Program-Kasir/
├── telegram_main.py          # Main bot file
├── database.py               # Database manager
├── product_photos/           # 👈 NEW: Folder untuk foto produk
│   ├── 0001.jpg             # Foto produk dengan kode 0001
│   ├── 0002.jpg             # Foto produk dengan kode 0002
│   └── 0007.jpg             # Foto produk dengan kode 0007
└── trades.db                # Database
```

## Testing Checklist

- [ ] Tambah produk dengan foto
  - [ ] Input kode, nama, harga, stok
  - [ ] Klik "📷 Upload Foto"
  - [ ] Send foto file
  - [ ] Verifikasi foto tersimpan di `product_photos/KODE.jpg`
  - [ ] Verifikasi database punya entry `foto_path`

- [ ] Tambah produk tanpa foto
  - [ ] Input kode, nama, harga, stok
  - [ ] Klik "⏭️ Skip"
  - [ ] Verifikasi tidak ada file foto di folder
  - [ ] Verifikasi database punya entry foto_path = NULL

- [ ] Error handling
  - [ ] /cancel saat di state FOTO
  - [ ] Send non-photo file saat di state FOTO
  - [ ] Duplikat kode produk saat save

## Future Enhancements

Possible improvements untuk versi selanjutnya:
- [ ] Tampilkan foto di menu "Lihat Daftar Produk"
- [ ] Compress foto untuk optimize storage
- [ ] Multiple photos per produk
- [ ] Edit foto produk yang sudah ada
- [ ] Preview foto sebelum save
- [ ] Thumbnail cache

## Backward Compatibility

✅ **Backward Compatible**: Produk yang sudah ada sebelumnya (tanpa foto) tetap berfungsi normal.
- Kolom `foto_path` bisa NULL
- Query tetap work tanpa kolom foto_path
- Existing products tidak terpengaruh

---
Last Updated: April 4, 2026
