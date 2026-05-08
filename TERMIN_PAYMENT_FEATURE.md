# Fitur Pembayaran Termin/Cicilan - Program Kasir

## 📋 Ringkasan Fitur

Fitur pembayaran termin/cicilan memungkinkan toko untuk:
- Menjual produk dengan sistem pembayaran cicilan/termin
- Melacak jadwal pembayaran termin untuk setiap invoice
- Mencatat pembayaran cicilan yang masuk
- Menghasilkan laporan pembayaran termin
- Mengelola invoice yang belum lunas

## 🎯 Use Cases

### 1. **Penjualan dengan Termin**
Customer membeli produk dengan sistem pembayaran cicilan:
- Cicilan 2x sampai 12x
- Pembayaran Down Payment (DP) atau cicilan mulai dari cicilan pertama
- Jadwal pembayaran otomatis dihitung dari tanggal DP + interval

### 2. **Tracking Pembayaran**
Admin/kasir dapat melacak:
- Daftar invoice termin yang belum lunas
- Progress pembayaran setiap invoice
- Sisa pembayaran dan jatuh tempo
- Invoice yang overdue

### 3. **Pencatatan Pembayaran**
Mencatat pembayaran cicilan:
- Input jumlah pembayaran termin
- Sistem otomatis mengupdate status pembayaran
- Notifikasi jika cicilan selesai

## 🔧 Komponen Teknis

### Database Changes

#### Tabel Baru: `termin_payments`
```sql
CREATE TABLE termin_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    transaction_id INTEGER,
    payment_amount INTEGER NOT NULL,
    payment_date DATE NOT NULL,
    due_date DATE NOT NULL,
    status TEXT DEFAULT 'pending',
    notes TEXT DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id),
    FOREIGN KEY (transaction_id) REFERENCES transactions(id)
)
```

#### Kolom Baru di Tabel `transactions` dan `invoices`
- `payment_type` (TEXT): 'lunas' atau 'termin'
- `payment_status` (TEXT): 'pending' atau 'completed'
- `due_date` (DATE): Tanggal jatuh tempo
- `customer_name` (TEXT): Nama customer untuk termin

### Service Layer

#### `TerminPaymentService` (payment_service.py)
Class untuk mengelola logika pembayaran termin:

**Methods:**
- `create_termin_invoice()`: Membuat invoice termin dengan jadwal pembayaran
- `record_termin_payment()`: Mencatat pembayaran cicilan
- `get_termin_summary()`: Ambil summary pembayaran termin
- `get_overdue_payments()`: Ambil pembayaran yang jatuh tempo

### Database Manager (database.py)

**Methods untuk Termin:**
- `add_termin_payment()`: Tambah cicilan pembayaran
- `get_termin_payments_by_invoice()`: Ambil semua cicilan per invoice
- `update_termin_payment_status()`: Update status cicilan
- `get_unpaid_termin_invoices()`: Ambil invoice termin yang belum lunas
- `calculate_total_paid_termin()`: Hitung total yang sudah dibayar
- `get_overdue_termin_payments()`: Ambil pembayaran yang overdue

### GUI Changes

#### Dialog Pembayaran (PaymentTypeDialog)
Dialog untuk memilih tipe pembayaran saat checkout:
- **Pilihan 1: Lunas** - Pembayaran penuh langsung
- **Pilihan 2: Termin** - Pembayaran cicilan dengan:
  - Input nama customer
  - Jumlah cicilan (2-12x)
  - Tanggal termin pertama
  - Interval antar cicilan (days)

#### Proses Checkout dengan Termin
1. Customer memilih produk dan checkout
2. Dialog pembayaran muncul untuk memilih termin/lunas
3. Jika termin:
   - Input data customer dan jadwal
   - Tanya DP atau bayar sebagian
   - Create invoice termin
   - Generate jadwal pembayaran otomatis

#### Tab Laporan Baru: "💳 Pembayaran Termin"
Di menu Laporan & Analisis:
- **Summary**: Total invoice termin, dibayar, sisa
- **Daftar Invoice**: List termin dengan progress
- **Record Payment**: Catat pembayaran termin yang masuk

## 📊 Data Flow

### Create Termin Invoice
```
Transaction Created
    ↓
Select "Termin" at Checkout
    ↓
Input Customer & Schedule (2x sampai 12x)
    ↓
Create Invoice (payment_type='termin')
    ↓
Generate Termin Payments (table termin_payments)
    ↓
Invoice ready for tracking
```

### Record Termin Payment
```
View Termin Payments Tab
    ↓
Select Invoice
    ↓
Input Payment Amount
    ↓
System validates against scheduled amount
    ↓
Update payment status to 'completed'
    ↓
Check if all paid → Update invoice status
```

## 🚀 Cara Menggunakan

### Untuk Admin/Owner

#### 1. Membuat Penjualan Termin
```
1. Buka GUI → Tab Transaksi
2. Input produk dan quantity seperti biasa
3. Klik "Proses Pembayaran"
4. Dialog muncul, pilih "Termin"
5. Input nama customer
6. Tentukan jumlah cicilan (mis: 3x)
7. Pilih tanggal cicilan pertama
8. Tentukan interval antar cicilan (mis: 30 hari)
9. Sistem hitung otomatis jadwal pembayaran
10. Klik "Lanjutkan"
```

#### 2. Mencatat Pembayaran Termin
```
1. Buka GUI → Menu Laporan & Analisis
2. Klik Tab "💳 Pembayaran Termin"
3. Lihat daftar invoice termin yang belum lunas
4. Pilih invoice yang akan dicatat pembayarannya
5. Klik "✅ Catat Pembayaran Termin"
6. Input jumlah pembayaran (sistem validasi)
7. Klik OK
8. Sistem update status pembayaran otomatis
```

#### 3. Monitoring Invoice Termin
```
1. Di Tab "Pembayaran Termin" bisa lihat:
   - Summary: Total invoice, sudah dibayar, sisa
   - Progress pembayaran setiap invoice (%)
   - Jatuh tempo cicilan
   - Status setiap cicilan
2. Right-click pada invoice untuk detail
```

### Contoh Skenario Penjualan Termin

**Penjualan Barang Rp 3.000.000 dengan Cicilan 3x**

```
Tanggal Transaksi: 2026-04-28
Customer: PT ABC Company
Produk: 10x Produk A @ Rp 300.000

Total: Rp 3.000.000
Pilih: Termin (3x cicilan)
Tanggal Cicilan 1: 2026-05-28
Interval: 30 hari

Jadwal Otomatis:
- Cicilan 1: Rp 1.000.000 (jatuh tempo: 2026-05-28)
- Cicilan 2: Rp 1.000.000 (jatuh tempo: 2026-06-27)
- Cicilan 3: Rp 1.000.000 (jatuh tempo: 2026-07-27)
```

## 🔍 Monitoring & Reporting

### Query Report

**Invoices Termin Belum Lunas:**
```sql
SELECT * FROM unpaid_termin_invoices
```

**Payment Schedule untuk Invoice:**
```sql
SELECT * FROM termin_payments WHERE invoice_id = ?
ORDER BY due_date
```

**Overdue Payments:**
```sql
SELECT * FROM overdue_termin_payments
```

## ⚠️ Validasi & Error Handling

### Validasi Input
- ✅ Nama customer harus diisi
- ✅ Jumlah cicilan: 2-12
- ✅ Interval: 7-365 hari
- ✅ Total jadwal = Total transaksi

### Error Handling
- ✅ Duplicate payment prevention
- ✅ Amount validation saat pencatatan
- ✅ Transaction integrity maintained
- ✅ Invoice status auto-update

## 📱 API/Method Reference

### PaymentService Integration
```python
from payment_service import TerminPaymentService

termin_service = TerminPaymentService(db)

# Create termin invoice
success, msg, invoice_id = termin_service.create_termin_invoice(
    transaction_id=123,
    customer_name="PT ABC",
    payment_schedule=[
        {'amount': 1000000, 'due_date': '2026-05-28', 'notes': 'Cicilan 1'},
        {'amount': 1000000, 'due_date': '2026-06-28', 'notes': 'Cicilan 2'},
    ]
)

# Record payment
success, msg = termin_service.record_termin_payment(
    invoice_id=456,
    payment_amount=1000000,
    notes="Pembayaran cicilan 1"
)

# Get summary
summary = termin_service.get_termin_summary(invoice_id=456)
```

## 🐛 Known Limitations

1. **Panjang cicilan maksimal 12 bulan** - Bisa diperpanjang di setting
2. **DP tidak bisa lebih besar dari total** - By design untuk keamanan
3. **Payment otomatis terbayar sequentially** - Tidak bisa skip cicilan
4. **No email notification** - Reminder manual diperlukan

## 🔐 Security Notes

- ✅ Invoice status changes logged
- ✅ Payment amount validated
- ✅ Customer info captured
- ✅ Due date tracking untuk reminder
- ✅ All transactions in termin_payments table for audit

## 📚 Related Files

- `database.py` - Termin payment database operations
- `payment_service.py` - TerminPaymentService class
- `gui_main.py` - PaymentTypeDialog dan termin UI
- `transaction.py` - Transaction service integration
- `invoice/invoice_service.py` - Invoice creation from transaction

## 🎓 Training Points

1. **Understand workflow** - Transaksi → Invoice → Termin Schedule → Payment Tracking
2. **Jadwal payment kalkulasi** - Amount per cicilan, date intervals
3. **Payment recording** - Sequential validation, status update
4. **Monitoring** - Report tab untuk track pending payments
5. **Error handling** - Amount validation, duplicate prevention

## 🚀 Future Enhancements

- [ ] Email reminder untuk pembayaran jatuh tempo
- [ ] WhatsApp integration untuk notifikasi pembayaran
- [ ] Grace period untuk overdue payments
- [ ] Payment history detail per invoice
- [ ] Discount untuk pembayaran dimuka
- [ ] Automatic downgrade jika overdue
- [ ] Integration dengan reminder sistem

---

**Version:** 1.0  
**Last Updated:** 2026-04-28  
**Feature Status:** ✅ Complete & Ready to Use
