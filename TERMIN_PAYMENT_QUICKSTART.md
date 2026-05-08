# 🎯 QUICK START - Pembayaran Termin/Cicilan

## 5 Langkah Mudah

### 1️⃣ **Jual Produk (Seperti Biasa)**
```
GUI → Tab Transaksi
Input produk & quantity
Set discount/pajak jika perlu
Lihat total di bawah
```

### 2️⃣ **Pilih Tipe Pembayaran**
```
Klik "Proses Pembayaran"
↓
Dialog Pembayaran muncul
↓
Pilih: "💰 Lunas" ATAU "📅 Termin"
```

### 3️⃣ **Jika Pilih TERMIN**
```
✓ Nama Customer: [Masukkan nama]
✓ Jumlah Cicilan: [2-12]
✓ Tanggal Cicilan 1: [Pilih dari calendar]
✓ Interval (hari): [30, 60, 90, dll]
```

### 4️⃣ **Sistem Hitung Jadwal Otomatis**
```
Contoh: 3x cicilan, interval 30 hari
├─ Cicilan 1: Rp 1.000.000 (Tgl 2026-05-28)
├─ Cicilan 2: Rp 1.000.000 (Tgl 2026-06-27)
└─ Cicilan 3: Rp 1.000.000 (Tgl 2026-07-27)
```

### 5️⃣ **Catat Pembayaran Saat Customer Bayar**
```
GUI → Menu Laporan & Analisis
↓
Tab "💳 Pembayaran Termin"
↓
Pilih invoice → "✅ Catat Pembayaran Termin"
↓
Input jumlah pembayaran
↓
Sistem update otomatis
```

---

## 💡 Tips Praktis

### 🔹 **Aturan Jadwal Pembayaran**
| Cicilan | Interval Umum | Contoh Total |
|---------|---------------|--------------|
| 2x | 30-45 hari | Rp 2.000.000 |
| 3x | 30 hari | Rp 3.000.000 |
| 6x | 30 hari | Rp 6.000.000+ |
| 12x | 30 hari | Rp 12.000.000+ |

### 🔹 **Down Payment (DP)**
```
Saat checkout:
└─ Tanya DP? 
   └─ Ya → Input jumlah DP
   └─ Tidak → Bayar pertama di cicilan 1
```

### 🔹 **Pembayaran Overdue**
- Invoice dengan cicilan belum terbayar & sudah past due_date
- Monitor di Tab "Pembayaran Termin"
- Sistem akan menampilkan indikator overdue

---

## 📊 Monitoring Dashboard

### Di Tab "💳 Pembayaran Termin" Bisa Lihat:

```
SUMMARY:
├─ Total Invoice Termin: 5 invoices
├─ Total Pembayaran: Rp 50.000.000
├─ Sudah Dibayar: Rp 30.000.000
└─ Sisa Pembayaran: Rp 20.000.000

DAFTAR INVOICE:
# Invoice      Customer        Total      Dibayar     Sisa         Jatuh Tempo    %
1  INV-202604  PT ABC         5.000.000  3.000.000   2.000.000    2026-05-28    60%
2  INV-202605  CV XYZ         10.000.000 0           10.000.000   2026-06-15    0%
...
```

### Right-click Pada Invoice Untuk:
- Melihat detail pembayaran
- Schedule cicilan lengkap
- Status setiap cicilan

---

## ✅ Checklist Setup

- [x] Database migration done (kolom & tabel baru)
- [x] Payment type dialog ready
- [x] Termin service configured
- [x] Reporting tab added
- [x] GUI integration complete

### Untuk Testing:
1. ✓ Buat transaksi normal (lunas) → Harus work
2. ✓ Buat transaksi termin (3x) → Jadwal muncul
3. ✓ Catat pembayaran cicilan → Status update
4. ✓ Lihat tab pembayaran termin → Summary muncul

---

## 🔧 Troubleshooting

### ❌ Dialog pembayaran tidak muncul?
```
→ Pastikan items di cart ada
→ Checkout dengan item yang valid
```

### ❌ Jadwal pembayaran error?
```
→ Cek input:
   - Nama customer harus diisi
   - Jumlah cicilan 2-12
   - Tanggal tidak bisa sebelum hari ini
   - Interval 7-365 hari
```

### ❌ Pencatatan pembayaran gagal?
```
→ Cek:
   - Jumlah pembayaran = schedule amount
   - Invoice belum selesai (status != completed)
   - Ada cicilan pending untuk dibayar
```

### ❌ Tab Pembayaran Termin kosong?
```
→ Kemungkinan:
   - Belum ada invoice termin (buat dulu)
   - Semua invoice termin sudah lunas
   - Refresh GUI (buka tab lain, kembali ke tab ini)
```

---

## 📞 Support

**File Dokumentasi Lengkap:**
- `TERMIN_PAYMENT_FEATURE.md` - Detail teknis

**Contoh Kode Integration:**
```python
from payment_service import TerminPaymentService

termin = TerminPaymentService(db)
success, msg, invoice_id = termin.create_termin_invoice(
    transaction_id=123,
    customer_name="PT ABC",
    payment_schedule=[
        {'amount': 1000000, 'due_date': '2026-05-28'},
        {'amount': 1000000, 'due_date': '2026-06-28'},
    ]
)
```

---

**🎯 Ready to Go!** Fitur pembayaran termin sudah siap digunakan.
