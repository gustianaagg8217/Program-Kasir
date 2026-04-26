# 📋 Panduan Stok Opname (Inventory Count)

## Deskripsi Fitur

Stok Opname adalah fitur untuk melakukan penghitungan stok fisik produk dan membandingkannya dengan stok yang tercatat di sistem. Fitur ini membantu:

✅ **Verifikasi Stok** - Memastikan stok sistem akurat dengan kondisi real di gudang
✅ **Deteksi Perbedaan** - Menemukan selisih antara stok sistem vs stok fisik
✅ **Update Otomatis** - Menyesuaikan stok sistem berdasarkan hasil opname
✅ **Audit Trail** - Mencatat history semua stok opname yang dilakukan
✅ **Laporan Detail** - Menyediakan report dengan breakdown per produk

---

## Cara Menggunakan

### 1️⃣ Membuat Session Baru

1. Dari menu sidebar, klik **"📋 Stok Opname"**
2. Pilih tab **"➕ Session Baru"**
3. Isi form:
   - **Tanggal Opname**: Tanggal ketika opname dilakukan (default: hari ini)
   - **Keterangan**: Catatan tambahan (opsional, misal: "Opname rutin bulanan", "Opname setelah inventori")
4. Klik tombol **"✅ Buat Session"**

**Hasil**: System akan membuat session baru dan memasukkan semua produk aktif ke dalam session

---

### 2️⃣ Input Stok Fisik

1. Pilih tab **"📊 Session Aktif"**
2. Pilih session yang ingin digunakan dari dropdown
3. Untuk setiap produk:
   - **Cari Produk**: Ketik kode atau nama produk di field pencarian
   - **Stok Fisik**: Masukkan jumlah stok yang dihitung dari fisik
   - **Catatan**: Tambahkan catatan jika ada (opsional, misal: "Produk rusak 2 pcs", "Stok tertukar")
   - Klik **"➕ Tambah Item"**

**Catatan Penting**:
- Anda bisa input stok secara bertahap, tidak perlu sekaligus
- Stok yang belum diinput akan menunjukkan status "⏳ Pending"
- Produk yang sudah diinput akan berubah status menjadi "✅ Counted"

---

### 3️⃣ Melihat Selisih Stok

Di tab **"📊 Session Aktif"**, kolom "Selisih" menunjukkan perbedaan antara stok fisik dan stok sistem:

- **Angka Positif (+)** → Stok fisik lebih banyak dari sistem (ada pengakuan stok)
- **Angka Negatif (-)** → Stok fisik kurang dari sistem (ada kehilangan stok)
- **0** → Stok cocok dengan sistem

**Contoh**:
```
Produk: Kabel USB
Stok Sistem: 50 pcs
Stok Fisik: 48 pcs
Selisih: -2 (kurang 2 pcs)
```

---

### 4️⃣ Menyelesaikan Session

1. Di tab **"📊 Session Aktif"**, setelah semua stok diinput
2. Klik tombol **"✅ Selesaikan Session"**
3. Sistem akan:
   - Menampilkan ringkasan perubahan stok
   - Meminta konfirmasi final
   - Update stok produk di database
   - Mengubah status session menjadi "Selesai"

**Penting**: 
- Produk yang belum diinput (status "⏳ Pending") akan tetap menggunakan stok sistem
- Stok akan langsung diupdate setelah session selesai

---

### 5️⃣ Melihat Riwayat & Laporan

1. Pilih tab **"📜 Riwayat"**
2. Lihat daftar semua session stok opname yang pernah dilakukan
3. Untuk melihat detail laporan:
   - Pilih session dari tabel
   - Klik tombol **"👁️ Lihat Detail"**
   - Akan menampilkan:
     - Total item dalam session
     - Item yang berbeda (discrepancy)
     - Detail per produk dengan keterangan

---

## Istilah Penting

| Istilah | Penjelasan |
|---------|-----------|
| **Session** | Satu kali proses stok opname dengan tanggal tertentu |
| **Stok Sistem** | Jumlah stok yang tercatat di database |
| **Stok Fisik** | Jumlah stok yang dihitung secara manual |
| **Selisih** | Perbedaan antara stok fisik dan stok sistem |
| **Status Pending** | Item belum diinput stok fisiknya |
| **Status Counted** | Item sudah diinput stok fisiknya |
| **Status Verified** | Item sudah diverifikasi (future feature) |

---

## Kasus Penggunaan

### 📌 Opname Rutin Bulanan
**Tujuan**: Verifikasi stok setiap akhir bulan

1. Buat session baru dengan tanggal akhir bulan
2. Inventory semua produk di gudang
3. Input hasil penghitungan ke sistem
4. Selesaikan session
5. Review laporan untuk produk yang hilang/bertambah

### 📌 Opname Setelah Awal Tahun
**Tujuan**: Menyesuaikan stok dengan kondisi nyata di awal tahun

1. Buat session dengan tanggal 31 Desember/1 Januari
2. Lakukan penghitungan menyeluruh
3. Input semua hasil
4. Selesaikan untuk update stok

### 📌 Audit Stok Spesifik
**Tujuan**: Memeriksa stok produk tertentu yang dicurigai

1. Buat session
2. Input hanya produk yang dicurigai
3. Sisanya biarkan pending
4. Lihat selisihnya di laporan

---

## Tips & Trik

💡 **Efisiensi Input**:
- Gunakan barcode scanner jika tersedia (scan kode produk)
- Input stok dengan urut untuk menghindari miss
- Gunakan catatan untuk dokumentasi

💡 **Manajemen Session**:
- Buat session terpisah untuk area berbeda (jika diperlukan)
- Gunakan keterangan untuk identifikasi jenis opname
- Jangan lupa simpan laporan sebelum membuat session baru

💡 **Review Laporan**:
- Fokus pada item dengan selisih signifikan
- Cari pola untuk produk yang sering hilang
- Archive laporan untuk audit trail

---

## Troubleshooting

### ❌ "Produk tidak ditemukan"
**Solusi**: 
- Pastikan kode/nama produk benar (cek di menu Produk)
- Produk harus aktif (tidak dihapus)
- Coba gunakan kode pendek tanpa spasi

### ❌ Session tidak muncul di "Session Aktif"
**Solusi**:
- Pastikan session berstatus 'active' (belum diselesaikan)
- Refresh halaman atau buat session baru
- Check di tab "Riwayat" untuk history

### ❌ Stok tidak terupdate setelah selesaikan session
**Solusi**:
- Pastikan ada item yang diinput (minimal 1 produk)
- Check koneksi database
- Lihat tab "📦 Produk" untuk verifikasi stok

---

## Database Schema

### Tabel: `stok_opname_sessions`
```sql
- id (Primary Key)
- tanggal (DATE)
- keterangan (TEXT)
- status (TEXT) - 'active', 'completed', 'cancelled'
- created_at (TIMESTAMP)
- created_by (TEXT)
- completed_at (TIMESTAMP, nullable)
```

### Tabel: `stok_opname_items`
```sql
- id (Primary Key)
- session_id (Foreign Key → stok_opname_sessions)
- product_id (Foreign Key → products)
- stok_sistem (INTEGER)
- stok_fisik (INTEGER, default 0)
- selisih (INTEGER, default 0)
- status (TEXT) - 'pending', 'counted', 'verified'
- catatan (TEXT, nullable)
- created_at (TIMESTAMP)
```

---

## API Usage (untuk developer)

```python
from stok_opname import StokOpnameService
from database import DatabaseManager

# Initialize
db = DatabaseManager()
service = StokOpnameService(db)

# Create session
session_id = service.create_session(
    tanggal='2024-01-15',
    keterangan='Opname bulanan',
    created_by='admin'
)

# Update item
service.update_item(
    item_id=1,
    stok_fisik=50,
    catatan='Produk bagus',
    status='counted'
)

# Get session report
report = service.get_session_report(session_id)

# Complete session
service.complete_session(session_id)
```

---

## Fitur Future

🔜 **Planned Features**:
- ✨ Import stok dari Excel/CSV
- ✨ Barcode scanner integration
- ✨ Photo capture untuk produk dengan selisih
- ✨ Multi-location support
- ✨ Approval workflow
- ✨ Schedule opname otomatis

---

## Support & Contact

Untuk pertanyaan atau laporan bug:
- Hubungi tim development
- Check log files di folder `logs/`
- Submit issue dengan detail dan screenshot

---

**Last Updated**: April 2024  
**Version**: 1.0  
**Author**: POS Development Team
