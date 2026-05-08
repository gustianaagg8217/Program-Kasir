# Implementasi Fitur Diskon Akumulasi Manual + Promo

## Ringkasan Fitur
Sistem telah diimplementasikan untuk mengakumulasikan (menggabungkan) diskon manual dengan diskon promosi secara otomatis. Diskon dari berbagai sumber ditampilkan dengan breakdown detail untuk transparansi kasir.

## Sumber Diskon yang Terakumulasi

### 1. **Diskon Per-Item Promosi** 
- Diterapkan otomatis saat produk ditambahkan ke keranjang
- Berdasarkan kuantitas dan jenis promo (bundle, harga khusus, dll)
- Ditampilkan di kolom "Diskon" dalam tabel keranjang

### 2. **Diskon Manual Persentase** (%)
- Diinput kasir via field "Diskon (%)"
- Shortcut: **F2** untuk fokus ke field ini
- Dihitung dari subtotal setelah dikurangi diskon per-item promo
- Contoh: 5% dari Rp 200.000 = Rp 10.000

### 3. **Diskon Manual Fixed** (Rp)
- Diinput kasir via field "Diskon (Rp)"
- Jumlah tetap dalam Rupiah
- Dapat dikombinasikan dengan diskon persentase
- Contoh: Diskon Rp 25.000

### 4. **Diskon Promosi Transaksi**
- Diterapkan berdasarkan total belanja
- Contoh: Beli >= Rp 500.000 dapat diskon 10%
- Diterapkan via tombol atau command

## Cara Kerja Akumulasi

```
Subtotal (sebelum diskon) = Rp 200.000
├─ Diskon Per-Item Promo  = Rp 20.000  (promo bundle/harga khusus)
├─ Diskon Manual %        = Rp 10.000  (5% dari subtotal)
├─ Diskon Manual Rp       = Rp 15.000  (fixed amount)
└─ Diskon Transaksi Promo = Rp 5.000   (jika ada promo total)
   ───────────────────────────────────
   TOTAL DISKON           = Rp 50.000
   ───────────────────────────────────

Subtotal setelah diskon    = Rp 150.000
Pajak (jika ada)           = Rp 15.000  (10%)
───────────────────────────────────────
TOTAL BELANJA              = Rp 165.000
```

## Antarmuka Pengguna

### Tabel Keranjang (Kolom Baru)
```
No | Produk    | Qty | Harga     | Diskon      | Subtotal
───────────────────────────────────────────────────────────
1  | Ubi Bakar | 10  | 22.000    | -10% (Rp..) | 198.000
2  | Toros 2kg | 5   | 75        | -Fixed      | 375
```

### Ringkasan Diskon (Enhanced)
```
Diskon: -Rp 50.000
  Terakumulasi dari:
  • Manual %: 5% = Rp 10.000
  • Manual Rp: Rp 15.000  
  • Promo: Rp 20.000
  • Promo Transaksi: Rp 5.000
```

### Control Diskon
```
┌─────────────────────────────────────┐
│ Diskon (%)     [____]  ← F2 untuk fokus
│ Diskon (Rp)    [____________]
│ Pajak - PPN (%) [____]
└─────────────────────────────────────┘
```

## Fitur yang Diimplementasikan

### ✅ Completed
1. **Akumulasi Diskon Otomatis**
   - Diskon dari berbagai sumber dikombinasikan secara automatis
   - Validasi: Total diskon tidak melebihi subtotal

2. **Breakdown Detail Diskon**
   - Setiap jenis diskon ditampilkan terpisah
   - Transparansi penuh untuk kasir

3. **Kolom Diskon Per-Item**
   - Menampilkan diskon promo di setiap baris produk
   - Format: "-10%" atau "-Rp 5.000/unit"

4. **Enhanced Receipt (Struk)**
   - Menampilkan breakdown diskon di struk
   - Per-item promotional discount ditampilkan
   - Total diskon dan komponennya terlihat jelas

5. **Validasi Input**
   - Diskon % harus 0-100%
   - Diskon Rp harus non-negatif
   - Total diskon tidak boleh melebihi subtotal

## File yang Dimodifikasi

### 1. **models.py**
- `Transaction.calculate_total()` - Enhanced untuk menghitung per-item promos
- `Transaction.get_discount_breakdown()` - Mengembalikan breakdown detail
- Tambah field: `discount_breakdown` (dict dengan detail setiap sumber diskon)

### 2. **transaction.py**
- `TransactionHandler.get_items()` - Enhanced return dengan promotional discount info
- Setiap item sekarang include: `discount_text`, `discount_amount`, `promotion_name`

### 3. **gui_main.py**
- **Cart Display**: Tambah kolom "Diskon" di treeview keranjang
- **_update_cart_display()** - Enhanced untuk tampilkan breakdown lengkap
- **_generate_receipt_text()** - Enhanced untuk tampilkan diskon detail di struk
- **_update_discount()** - Validasi dan update diskon %
- **_update_discount_amount()** - Validasi dan update diskon Rp

## Contoh Penggunaan

### Scenario: Kasir menginput diskon manual untuk transaksi dengan promo

1. **Produk ditambahkan ke keranjang**
   ```
   Ubi Bakar (10 x 22.000) = 220.000
   └─ Promo: Buy 10+ get 10% = -22.000 (setelah diskon = 198.000)
   ```

2. **Kasir menginput diskon manual 5%**
   ```
   Field "Diskon (%)" = 5
   ```

3. **Sistem menghitung akumulasi**
   ```
   Subtotal: 198.000
   - Diskon 5%: 9.900
   - Diskon per-item promo: 22.000 (sudah dalam subtotal)
   ────────────────────
   Total Diskon: 31.900
   Setelah diskon: 166.100
   ```

4. **Kasir juga input diskon fixed Rp 10.000**
   ```
   Field "Diskon (Rp)" = 10000
   ```

5. **Sistem recalculate**
   ```
   Total Diskon = 22.000 (promo per-item) + 9.900 (manual %) + 10.000 (manual Rp)
               = 41.900
   ```

## Teknologi Digunakan
- **Python 3.8+**
- **Tkinter** untuk GUI
- **SQLite** untuk database
- **Models & Services pattern** untuk business logic

## Testing Checklist

- [x] Diskon % dapat diinput dan dihitung
- [x] Diskon Rp dapat diinput dan dihitung  
- [x] Diskon % + Diskon Rp terakumulasi
- [x] Diskon promo per-item terakumulasi
- [x] Total diskon tidak melebihi subtotal
- [x] Breakdown ditampilkan di cart summary
- [x] Breakdown ditampilkan di receipt
- [x] Validasi input (0-100% untuk diskon %)
- [x] F2 shortcut untuk fokus diskon %
- [x] Tax dihitung dari subtotal setelah diskon

## Future Improvements

1. **Diskon Kategori** - Diskon untuk kategori produk tertentu
2. **Diskon Member** - Diskon berdasarkan customer ID
3. **History Diskon** - Log semua diskon yang diterapkan
4. **Analytics Diskon** - Dashboard dengan statistik diskon
5. **Diskon Conditional** - Diskon otomatis berdasarkan aturan (e.g., jam, hari, stock)

---
**Implementation Date**: 2026-05-08  
**Status**: ✅ COMPLETE  
**Version**: 1.0
