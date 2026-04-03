# 🛒 PANDUAN PENGGUNAAN GUI SISTEM POS

## 🚀 Cara Menjalankan GUI

### Opsi 1: Menggunakan Batch File (Rekomendasi)
Cukup double-click file **`run_gui.bat`** di folder Program_Kasir.

File ini akan otomatis:
- ✅ Mengecek instalasi Python
- ✅ Menginstall dependencies yang diperlukan
- ✅ Menjalankan aplikasi GUI

### Opsi 2: Command Line
```bash
# Install dependencies terlebih dahulu
pip install -r requirements_gui.txt

# Jalankan aplikasi
python gui_main.py
```

---

## 📋 Fitur-Fitur GUI

### 1. **Dashboard 📊**
- Menampilkan ringkasan statistik sistem
- Total produk, penjualan hari ini, transaksi hari ini
- Menampilkan transaksi terakhir
- Akses cepat ke fungsi utama (Transaksi Baru, Tambah Produk, Laporan)

### 2. **Manajemen Produk 📦**
- **Lihat Produk**: Menampilkan semua produk dalam bentuk table
- **Tambah Produk**: Membuka dialog untuk input produk baru
  - Kode Produk (misal: PROD001)
  - Nama Produk
  - Harga (Rp)
  - Stok Awal
- **Edit Produk**: Double-click pada produk untuk mengedit
- **Hapus Produk**: Hapus produk dengan konfirmasi

### 3. **Proses Transaksi 🛒**
- **Interface 2 Kolom**:
  - **Kiri**: Input item dengan:
    - Pencarian produk (dropdown dengan nama & kode)
    - Input jumlah (quantity)
    - Tombol "Tambah Item"
  - **Kanan**: Keranjang belanja dengan detail items
    - Nomor, Produk, Qty, Harga satuan, Subtotal
    - Total belanja otomatis terhitung

- **Pembayaran**:
  - Input jumlah pembayaran
  - Sistem otomatis hitung kembalian
  - Konfirmasi transaksi

### 4. **Laporan & Analisis 📊**
Terdapat 4 tab laporan:

#### **Tab 1: Laporan Harian 📅**
- Summary penjualan hari ini
  - Total Penjualan
  - Total Transaksi
  - Rata-rata Transaksi
  - Transaksi Tertinggi
- Daftar semua transaksi hari ini

#### **Tab 2: Laporan Periode 📆**
- Pilih rentang tanggal (dari - sampai)
- Klik "Tampilkan Laporan"
- Menampilkan detail laporan periode tersebut

#### **Tab 3: Produk Terlaris 🏆**
- Top 20 produk dengan penjualan terbanyak
- Informasi: Produk, Qty Terjual, Total Penjualan

#### **Tab 4: Informasi Stok 📦**
- Daftar semua produk dan status stok
- Status:
  - ✅ Normal (stok > 5)
  - ⚡ Minim (stok 1-5)
  - ⚠️ Habis (stok 0)

### 5. **Telegram Bot 🤖**
- Konfigurasi Bot Token
- Setup Admin Chat ID
- Test Koneksi
- Send Test Report
- (Fitur lebih lengkap dapat dikembangkan lebih lanjut)

### 6. **Pengaturan ⚙️**
- **Database Info**: Menampilkan statistik database
- **Tentang Sistem**: Informasi versi dan fitur
- **Zone Berbahaya**: Reset database (hapus semua data)

---

## 🎨 Tampilan & User Interface

### Desain Modern
- **Warna Profesional**: Biru, ungu, hijau, merah untuk visualisasi data
- **Font Jelas**: Segoe UI untuk readability optimal
- **Layout Intuitif**: Sidebar untuk navigasi, content area utama

### Komponen UI yang User-Friendly
- ✅ **Button dengan Icon**: Setiap tombol memiliki emoji untuk identifikasi cepat
- ✅ **Table/Treeview**: Data ditampilkan dalam format table yang rapi
- ✅ **Input Dialog**: Form untuk input data
- ✅ **Message Box**: Notifikasi sukses, peringatan, error
- ✅ **Status Indicator**: Visual feedback untuk setiap aksi

---

## 🎯 Workflow Transaksi Cepat

1. Klik menu **🛒 Transaksi**
2. Pilih produk dari dropdown
3. Input jumlah (qty)
4. Klik **➕ Tambah Item**
5. Produk muncul di keranjang (kanan)
6. Ulangi step 2-4 untuk menambah lebih banyak item
7. Input jumlah pembayaran di bagian **💳 Pembayaran**
8. Klik **✅ Proses Pembayaran**
9. Transaksi selesai!

---

## 🛠️ Troubleshooting

### GUI tidak bisa dijalankan
**Solusi**:
```bash
# Pastikan Python versi 3.8+ terinstall
python --version

# Reinstall dependencies
pip install --upgrade tkcalendar pillow python-telegram-bot requests
```

### Database error
- Pastikan file `trades.db` ada di folder
- Jika rusak, bisa direset dari menu **⚙️ Pengaturan** → **🚨 Reset Database**

### Telegram Bot tidak bisa terkoneksi
- Pastikan Bot Token benar
- Pastikan koneksi internet lancar
- Test koneksi dari menu **🤖 Telegram Bot** → **🧪 Test Koneksi**

---

## 📝 Catatan Penting

1. **Backup Data**: Lakukan backup database (`trades.db`) secara berkala
2. **Single Instance**: Hanya satu window GUI yang bisa dijalankan pada saat bersamaan
3. **Demo Mode**: Gunakan akun demo di MT5 untuk testing sebelum live trading
4. **Monitoring**: Monitor log di terminal untuk debug jika ada error

---

## 💡 Tips & Tricks

- **Pencarian Cepat**: Di Transaksi, ketik kode produk di combobox untuk mencari
- **Shortcut**: Gunakan Tab untuk navigasi antar field dalam form
- **Export Data**: Dari Dashboard, bisa export laporan ke CSV untuk analisis lebih lanjut
- **Refresh**: Data otomatis refresh saat berpindah menu

---

## 📞 Dukungan & Update

Jika ada masalah atau saran fitur:
- Update dependencies: `pip install --upgrade -r requirements_gui.txt`
- Check database integrity dari menu Settings
- Lihat log terminal untuk detail error

Selamat menggunakan! 🎉
