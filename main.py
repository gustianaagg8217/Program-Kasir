# ============================================================================
# MAIN.PY - Point of Sale (POS) System - CLI Interface
# ============================================================================
# Fungsi: Entry point utama sistem POS dengan menu interaktif
# Mengintegrasikan semua modul: database, models, transaction, laporan
# Updated: Added config management dan authentication system
# ============================================================================

import os
import sys
import time
from datetime import datetime

# Import semua modules
from database import DatabaseManager
from models import ProductManager, ValidationError, format_rp
from transaction import TransactionService, TransactionHandler, ReceiptManager
from laporan import ReportGenerator, ReportFormatter, CSVExporter
from telegram_bot import POSTelegramBot, TelegramConfigManager, TELEGRAM_AVAILABLE
from config_manager import get_config, ConfigManager
from auth_manager import AuthManager, User
from logger_config import get_logger, setup_logging

# Setup logging dulu sebelum semua operasi
setup_logging()
logger = get_logger(__name__)

# ============================================================================
# POS SYSTEM - Main class yang manage semua operasi
# ============================================================================

class POSSystem:
    """
    Main POS System class yang mengintegrasikan semua operasi.
    
    Fitur baru:
    - Configuration management (config.json)
    - User authentication & authorization
    - Role-based access control (admin, cashier)
    - Comprehensive logging
    
    Attributes:
        db (DatabaseManager): Database instance
        config (ConfigManager): Configuration manager
        auth (AuthManager): Authentication manager
        product_manager (ProductManager): Product management
        transaction_handler (TransactionHandler): Transaction handling
        report_generator (ReportGenerator): Report generation
        report_formatter (ReportFormatter): Report formatting
        csv_exporter (CSVExporter): CSV export
        
    Methods:
        run(): Jalankan sistem
        login(): Login flow
        show_main_menu(): Tampilkan menu utama sesuai role
    """
    
    def __init__(self):
        """Inisialisasi POS System."""
        print("\n🚀 Inisialisasi POS System...")
        
        try:
            # Load configuration
            self.config = get_config()
            logger.info("Configuration manager initialized")
            
            # Inisialisasi database
            self.db = DatabaseManager()
            logger.info("Database initialized")
            
            # Inisialisasi authentication
            self.auth = AuthManager(self.db)
            logger.info("Authentication manager initialized")
            
            # Inisialisasi managers
            self.product_manager = ProductManager(self.db)
            self.transaction_handler = TransactionHandler(self.db)
            self.report_generator = ReportGenerator(self.db)
            self.report_formatter = ReportFormatter()
            self.csv_exporter = CSVExporter()
            
            # Inisialisasi Telegram Bot
            self.telegram_bot = None
            if TELEGRAM_AVAILABLE:
                try:
                    self.telegram_bot = POSTelegramBot()
                    logger.info("Telegram bot initialized")
                except Exception as e:
                    logger.warning(f"Telegram bot init failed: {e}")
                    print(f"⚠️ Telegram bot init failed: {e}")
            
            print("✅ POS System siap digunakan!\n")
            logger.info("POS System initialization complete")
            
        except Exception as e:
            logger.error(f"Failed to initialize POS System: {e}", exc_info=True)
            print(f"❌ Error initializing system: {e}")
            raise
    
    # ========================================================================
    # LOGIN & AUTHENTICATION
    # ========================================================================
    
    def login_flow(self) -> bool:
        """
        Interactive login flow.
        
        User dapat login atau menggunakan demo mode.
        
        Returns:
            bool: True jika berhasil login, False jika cancel
        """
        self.clear_screen()
        print("=" * 70)
        print(self.config.get_store_name().center(70))
        print("LOGIN SISTEM POS".center(70))
        print("=" * 70)
        
        # Show options
        print("\n1. 🔑 Login dengan Username & Password")
        print("2. 📌 Demo Mode (Admin)")
        print("3. 🚪 Keluar")
        
        choice = input("\n👉 Pilih opsi (1-3): ").strip()
        
        if choice == '1':
            return self._try_login()
        elif choice == '2':
            return self._demo_login()
        elif choice == '3':
            return False
        else:
            print("❌ Pilihan tidak valid")
            time.sleep(2)
            return self.login_flow()
    
    def _try_login(self) -> bool:
        """
        Attempt user login dengan username & password.
        
        Returns:
            bool: True jika berhasil login
        """
        print("\n" + "-" * 70)
        print("LOGIN")
        print("-" * 70 + "\n")
        
        username = input("Username: ").strip()
        if not username:
            print("❌ Username tidak boleh kosong")
            time.sleep(2)
            return self.login_flow()
        
        password = input("Password: ").strip()
        if not password:
            print("❌ Password tidak boleh kosong")
            time.sleep(2)
            return self.login_flow()
        
        # Attempt login
        success, message = self.auth.login(username, password)
        print(f"\n{message}")
        
        if success:
            logger.info(f"User logged in: {username}")
            time.sleep(1)
            return True
        else:
            time.sleep(2)
            return self.login_flow()
    
    def _demo_login(self) -> bool:
        """
        Login dengan demo admin account.
        Untuk testing dan demo purposes.
        
        Returns:
            bool: True
        """
        # Check if demo user exists, create if not
        if not self.db.user_exists():
            print("\n📌 Creating demo admin account...")
            self.db.create_user("admin", "admin123", role="admin")
            logger.info("Demo admin account created")
        
        success, message = self.auth.login("admin", "admin123")
        print(f"\n{message}")
        logger.info(f"Demo login: {self.auth.get_username()}")
        
        time.sleep(1)
        return success
    
    def show_login_status(self):
        """Tampilkan status login di main menu."""
        user = self.auth.get_current_user()
        if user:
            role_display = "👨‍💼 Admin" if user.is_admin() else "💼 Cashier"
            return f"{role_display} | {user.username}"
        return "❌ Not Logged In"
    
    @staticmethod
    def clear_screen():
        """Clear terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    @staticmethod
    def pause():
        """Pause dan tunggu user input."""
        input("\n⏸️  Tekan ENTER untuk lanjut...")
    
    @staticmethod
    def get_safe_int(prompt: str, min_val: int = None, max_val: int = None) -> int or None:
        """
        Get integer input dari user dengan validasi.
        
        Args:
            prompt (str): Pertanyaan untuk user
            min_val (int): Minimum value
            max_val (int): Maximum value
            
        Returns:
            int: Input yang valid
            None: Jika user cancel
        """
        while True:
            try:
                result = input(prompt)
                if result.lower() in ['q', 'cancel', 'b']:  # Shortcut untuk back
                    return None
                
                value = int(result)
                
                if min_val is not None and value < min_val:
                    print(f"❌ Nilai minimal: {min_val}")
                    continue
                if max_val is not None and value > max_val:
                    print(f"❌ Nilai maksimal: {max_val}")
                    continue
                
                return value
            except ValueError:
                print("❌ Input harus berupa angka (atau 'q' untuk cancel)")
    
    @staticmethod
    def draw_header(title: str):
        """Draw formatted header."""
        print("\n" + "=" * 70)
        print(title.center(70))
        print("=" * 70 + "\n")
    
    # ========================================================================
    # MENU - KELOLA PRODUK
    # ========================================================================
    
    def menu_produk(self):
        """Menu untuk manajemen produk."""
        while True:
            self.clear_screen()
            self.draw_header("📦 MENU KELOLA PRODUK")
            
            print("1. ➕ Tambah Produk")
            print("2. 📋 Lihat Daftar Produk")
            print("3. ✏️  Edit Produk")
            print("4. 🗑️  Hapus Produk")
            print("5. 📊 Info Stok")
            print("0. ↩️  Kembali ke Menu Utama")
            
            choice = input("\n👉 Pilih menu (0-5): ").strip()
            
            if choice == '1':
                self.tambah_produk()
            elif choice == '2':
                self.lihat_produk()
            elif choice == '3':
                self.edit_produk()
            elif choice == '4':
                self.hapus_produk()
            elif choice == '5':
                self.info_stok()
            elif choice == '0':
                break
            else:
                print("❌ Pilihan tidak valid")
                self.pause()
    
    def tambah_produk(self):
        """Proses tambah produk baru dengan kode otomatis."""
        self.clear_screen()
        self.draw_header("➕ TAMBAH PRODUK BARU")
        
        try:
            # Generate kode otomatis
            kode = self.product_manager.get_next_product_code()
            print(f"✅ Kode Produk (otomatis): {kode}\n")
            
            nama = input("Nama Produk (max 20 karakter): ").strip()
            if not nama:
                print("❌ Nama tidak boleh kosong")
                self.pause()
                return
            if len(nama) > 20:
                print("❌ Nama produk maksimal 20 karakter")
                self.pause()
                return
            
            harga = self.get_safe_int("Harga (Rupiah): ", min_val=1)
            if harga is None:
                return
            
            stok = self.get_safe_int("Stok Awal: ", min_val=0)
            if stok is None:
                return
            
            # Tambah ke database
            if self.product_manager.add_product(kode, nama, harga, stok):
                print(f"\n✅ Produk '{nama}' berhasil ditambahkan!")
                print(f"   Kode: {kode}")
                print(f"   Harga: {format_rp(harga)}")
                print(f"   Stok: {stok}")
            else:
                print("❌ Gagal menambahkan produk")
            
            self.pause()
        except Exception as e:
            print(f"❌ Error: {e}")
            self.pause()
    
    def lihat_produk(self):
        """Tampilkan daftar semua produk."""
        self.clear_screen()
        self.draw_header("📋 DAFTAR PRODUK")
        
        products = self.product_manager.list_products()
        
        if not products:
            print("⚠️ Belum ada produk dalam database")
            self.pause()
            return
        
        print("No. | Kode       | Nama Produk          | Harga       | Stok")
        print("-" * 70)
        
        for i, prod in enumerate(products, 1):
            print(f"{i:>2}. | {prod.kode:<10} | {prod.nama:<20} | {format_rp(prod.harga):<11} | {prod.stok:>4}")
        
        print("-" * 70)
        print(f"Total Produk: {len(products)}")
        
        self.pause()
    
    def edit_produk(self):
        """Edit data produk yang ada."""
        self.clear_screen()
        self.draw_header("✏️  EDIT PRODUK")
        
        kode = input("Masukkan Kode Produk yang akan diedit: ").strip().upper()
        product = self.product_manager.get_product(kode)
        
        if product is None:
            print(f"❌ Produk '{kode}' tidak ditemukan")
            self.pause()
            return
        
        print(f"\n📦 Produk saat ini:")
        print(f"   Nama: {product.nama}")
        print(f"   Harga: {format_rp(product.harga)}")
        print(f"   Stok: {product.stok}\n")
        
        print("Field yang bisa diedit (kosongkan jika tidak ingin mengubah):")
        
        nama = input("  Nama baru (max 20 karakter): ").strip()
        harga_str = input("  Harga baru: ").strip()
        stok_str = input("  Stok baru: ").strip()
        
        # Persiapkan data update
        update_data = {}
        if nama:
            if len(nama) > 20:
                print("❌ Nama produk maksimal 20 karakter")
                self.pause()
                return
            update_data['nama'] = nama
        if harga_str:
            try:
                update_data['harga'] = int(harga_str)
            except ValueError:
                print("❌ Harga harus berupa angka")
                self.pause()
                return
        if stok_str:
            try:
                update_data['stok'] = int(stok_str)
            except ValueError:
                print("❌ Stok harus berupa angka")
                self.pause()
                return
        
        if not update_data:
            print("⚠️ Tidak ada data yang diubah")
            self.pause()
            return
        
        if self.product_manager.update_product(kode, **update_data):
            print("✅ Produk berhasil diupdate!")
        else:
            print("❌ Gagal mengupdate produk")
        
        self.pause()
    
    def hapus_produk(self):
        """Hapus produk dari database."""
        self.clear_screen()
        self.draw_header("🗑️  HAPUS PRODUK")
        
        kode = input("Masukkan Kode Produk yang akan dihapus: ").strip().upper()
        product = self.product_manager.get_product(kode)
        
        if product is None:
            print(f"❌ Produk '{kode}' tidak ditemukan")
            self.pause()
            return
        
        print(f"\n⚠️ Produk yang akan dihapus:")
        print(f"   Kode: {product.kode}")
        print(f"   Nama: {product.nama}")
        print(f"   Harga: {format_rp(product.harga)}")
        print(f"   Stok: {product.stok}")
        
        confirm = input("\n🚨 Apakah anda yakin ingin menghapus? (y/n): ").strip().lower()
        
        if confirm == 'y':
            if self.product_manager.delete_product(kode):
                print("✅ Produk berhasil dihapus!")
            else:
                print("❌ Gagal menghapus produk")
        else:
            print("❌ Penghapusan dibatalkan")
        
        self.pause()
    
    def info_stok(self):
        """Tampilkan informasi stok."""
        self.clear_screen()
        self.draw_header("📊 INFORMASI STOK PRODUK")
        
        stok_list = self.report_generator.get_stok_summary()
        
        if not stok_list:
            print("⚠️ Belum ada produk")
            self.pause()
            return
        
        print(self.report_formatter.format_stok_summary(stok_list))
        self.pause()
    
    # ========================================================================
    # MENU - TRANSAKSI PENJUALAN
    # ========================================================================
    
    def menu_transaksi(self):
        """Menu untuk proses transaksi penjualan."""
        self.clear_screen()
        self.draw_header("🛒 TRANSAKSI PENJUALAN")
        
        # Mulai transaksi baru
        self.transaction_handler.start_transaction()
        
        while True:
            print("\n" + "=" * 70)
            print("STATUS TRANSAKSI SAAT INI")
            print("=" * 70)
            
            summary = self.transaction_handler.get_transaction_summary()
            if summary:
                print(f"Item      : {summary['items_count']} item ({summary['qty_total']} qty)")
                print(f"Total     : {format_rp(summary['total'])}")
                if summary['bayar'] > 0:
                    print(f"Pembayaran: {format_rp(summary['bayar'])}")
                    print(f"Kembalian : {format_rp(summary['kembalian'])}")
                
                # Display detail items secara singkat jika ada
                if summary['items_count'] > 0:
                    print(f"\n📋 Detail Items ({summary['items_count']} item):")
                    print("-" * 70)
                    # Get items untuk display
                    items = self.transaction_handler.get_items()
                    for idx, item in enumerate(items, 1):
                        product = self.product_manager.get_product(item['kode'])
                        if product:
                            print(f"   {idx}. {product.nama} x{item['qty']} = {format_rp(item['subtotal'])}")
                    print("-" * 70)
            else:
                print("Belum ada item")
            
            print("\n" + "-" * 70)
            print("1. ➕ Tambah Item")
            print("2. 📋 Lihat Item")
            print("3. 🗑️  Hapus Item")
            print("4. 💳 Konfirmasi Pembayaran")
            print("5. ❌ Batalkan Transaksi")
            print("0. ↩️  Kembali (CANCEL)")
            
            choice = input("\n👉 Pilih menu (0-5): ").strip()
            
            if choice == '1':
                self.tambah_item_transaksi()
            elif choice == '2':
                self.transaction_handler.display_items()
                self.pause()
            elif choice == '3':
                idx = self.get_safe_int("Nomor item yang dihapus: ", min_val=1)
                if idx is not None:
                    self.transaction_handler.remove_item(idx)
                    self.pause()
            elif choice == '4':
                self.konfirmasi_pembayaran()
                break
            elif choice == '5':
                confirm = input("Batalkan transaksi? (y/n): ").strip().lower()
                if confirm == 'y':
                    self.transaction_handler.cancel_transaction()
                break
            elif choice == '0':
                self.transaction_handler.cancel_transaction()
                break
            else:
                print("❌ Pilihan tidak valid")
    
    def tambah_item_transaksi(self):
        """Tambah item ke transaksi dengan display produk real-time."""
        print("\n" + "-" * 70)
        print("TAMBAH ITEM KE TRANSAKSI")
        print("-" * 70)
        
        # Input kode produk
        kode = input("Kode Produk: ").strip().upper()
        if not kode:
            return
        
        # Lookup produk dari database
        try:
            product = self.product_manager.get_product(kode)
            
            if not product:
                print(f"\n❌ Produk dengan kode '{kode}' tidak ditemukan!")
                self.pause()
                return
            
            # Display produk yang ditemukan
            print(f"\n✅ Produk ditemukan!")
            print(f"   📦 Nama: {product.nama}")
            print(f"   💰 Harga: {format_rp(product.harga)}")
            print(f"   📊 Stok: {product.stok} pcs")
            
            # Check stok
            if product.stok <= 0:
                print(f"\n❌ Stok tidak tersedia!")
                self.pause()
                return
            
            # Input qty dengan info stok
            print(f"\n(Tersedia: {product.stok} pcs)")
            qty = self.get_safe_int("Jumlah (qty): ", min_val=1)
            
            if qty is None:
                return
            
            # Validate qty tidak melebihi stok
            if qty > product.stok:
                print(f"\n❌ Jumlah melebihi stok yang tersedia! (Stok: {product.stok})")
                self.pause()
                return
            
            # Add item ke transaksi
            self.transaction_handler.add_item(kode, qty)
            
            # Display summary item yang ditambahkan
            print(f"\n✅ Item berhasil ditambahkan!")
            subtotal = product.harga * qty
            print(f"   {qty}x {product.nama} = {format_rp(subtotal)}")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            self.pause()
    
    def konfirmasi_pembayaran(self):
        """Proses konfirmasi pembayaran dan selesaikan transaksi."""
        print("\n" + "=" * 70)
        print("KONFIRMASI PEMBAYARAN")
        print("=" * 70)
        
        summary = self.transaction_handler.get_transaction_summary()
        if not summary or summary['items_count'] == 0:
            print("❌ Transaksi kosong (tidak ada item)")
            self.pause()
            return
        
        print(f"\n📊 RINCIAN TRANSAKSI")
        print(f"Subtotal Belanja: {format_rp(summary['total'])}")
        
        # Input Diskon
        print("\n💰 DISKON (Opsional)")
        print("   Kosongkan jika tidak ada diskon")
        diskon_input = input("   Masukkan diskon dalam % (0-100): ").strip()
        
        diskon_persen = 0
        if diskon_input:
            try:
                diskon_persen = float(diskon_input)
                if diskon_persen < 0 or diskon_persen > 100:
                    print("   ❌ Diskon harus antara 0-100%")
                    self.pause()
                    return
            except ValueError:
                print("   ❌ Input harus berupa angka")
                self.pause()
                return
        
        # Input Pajak
        print("\n🏛️  PAJAK (PPN) (Opsional)")
        print("   Kosongkan jika tidak ada pajak")
        pajak_input = input("   Masukkan pajak dalam % (0-100): ").strip()
        
        pajak_persen = 0
        if pajak_input:
            try:
                pajak_persen = float(pajak_input)
                if pajak_persen < 0 or pajak_persen > 100:
                    print("   ❌ Pajak harus antara 0-100%")
                    self.pause()
                    return
            except ValueError:
                print("   ❌ Input harus berupa angka")
                self.pause()
                return
        
        # Set discount dan tax di transaction
        transaction = self.transaction_handler.transaction_service.get_current_transaction()
        if transaction:
            try:
                if diskon_persen > 0:
                    transaction.set_discount(diskon_persen)
                if pajak_persen > 0:
                    transaction.set_tax(pajak_persen)
            except Exception as e:
                print(f"❌ Error saat set diskon/pajak: {e}")
                self.pause()
                return
        
        # Update summary setelah diskon/pajak
        summary = self.transaction_handler.get_transaction_summary()
        print(f"\n📋 PERHITUNGAN TOTAL")
        if transaction:
            print(f"Subtotal        : {format_rp(transaction.subtotal)}")
            if transaction.discount_amount > 0:
                print(f"Diskon ({diskon_persen}%): -{format_rp(transaction.discount_amount)}")
            if transaction.tax_amount > 0:
                print(f"Pajak ({pajak_persen}%) : +{format_rp(transaction.tax_amount)}")
        print(f"Total Akhir     : {format_rp(summary['total'])}")
        
        bayar = self.get_safe_int("\n💳 Jumlah Pembayaran: ", min_val=summary['total'])
        
        if bayar is None:
            return
        
        # Complete transaction (tanpa print receipt dulu)
        trans_id = self.transaction_handler.complete_transaction(
            bayar,
            store_name=self.config.get_store_name(),
            store_address=self.config.get_store_address(),
            print_receipt=False
        )
        
        if trans_id:
            print(f"\n✅ Transaksi selesai! ID: {trans_id}")
            
            # Tanya user apakah ingin cetak resi
            print("\n" + "-" * 70)
            cetak = input("🖨️  Apakah ingin cetak resi? (y/n): ").strip().lower()
            
            if cetak == 'y':
                print("\n📋 STRUK TRANSAKSI")
                print("-" * 70)
                self.transaction_handler.print_receipt(
                    store_name=self.config.get_store_name(),
                    store_address=self.config.get_store_address()
                )
            else:
                print("\n⏭️  Resi tidak dicetak (tersimpan di folder receipts)")
        else:
            print("❌ Gagal meproses transaksi")
        
        self.pause()
    
    # ========================================================================
    # MENU - LAPORAN
    # ========================================================================
    
    def menu_laporan(self):
        """Menu untuk melihat laporan."""
        while True:
            self.clear_screen()
            self.draw_header("📊 LAPORAN & ANALISIS")
            
            print("1. 📅 Laporan Harian")
            print("2. 📆 Laporan Periode Tanggal")
            print("3. 🏆 Produk Terlaris")
            print("4. 📦 Informasi Stok")
            print("5. 🎨 Dashboard")
            print("6. 💾 Export ke CSV")
            print("7. 🖨️  Cetak Ulang Resi")
            print("0. ↩️  Kembali ke Menu Utama")
            
            choice = input("\n👉 Pilih menu (0-7): ").strip()
            
            if choice == '1':
                self.laporan_harian()
            elif choice == '2':
                self.laporan_periode()
            elif choice == '3':
                self.laporan_produk_terlaris()
            elif choice == '4':
                self.info_stok()
            elif choice == '5':
                self.tampilkan_dashboard()
            elif choice == '6':
                self.export_csv()
            elif choice == '7':
                self.cetak_ulang_resi()
            elif choice == '0':
                break
            else:
                print("❌ Pilihan tidak valid")
                self.pause()
    
    def laporan_harian(self):
        """Tampilkan laporan penjualan harian."""
        self.clear_screen()
        laporan = self.report_generator.get_laporan_harian()
        print(self.report_formatter.format_laporan_harian(laporan))
        self.pause()
    
    def laporan_periode(self):
        """Tampilkan laporan periode tanggal."""
        self.clear_screen()
        self.draw_header("📆 LAPORAN PERIODE TANGGAL")
        
        start = input("Tanggal mulai (YYYY-MM-DD): ").strip()
        end = input("Tanggal akhir (YYYY-MM-DD): ").strip()
        
        try:
            laporan = self.report_generator.get_laporan_periode(start, end)
            if laporan:
                print(self.report_formatter.format_laporan_periode(laporan))
        except Exception as e:
            print(f"❌ Error: {e}")
        
        self.pause()
    
    def laporan_produk_terlaris(self):
        """Tampilkan laporan produk terlaris."""
        self.clear_screen()
        produk_laris = self.report_generator.get_produk_terlaris(limit=10)
        print(self.report_formatter.format_produk_terlaris(produk_laris))
        self.pause()
    
    def tampilkan_dashboard(self):
        """Tampilkan dashboard summary."""
        self.clear_screen()
        dashboard = self.report_generator.get_dashboard_summary()
        print(self.report_formatter.format_dashboard(dashboard))
        self.pause()
    
    def export_csv(self):
        """Export laporan ke CSV."""
        self.clear_screen()
        self.draw_header("💾 EXPORT KE CSV")
        
        print("1. Produk Terlaris")
        print("2. Stok Produk")
        print("3. Transaksi Harian")
        print("0. Kembali")
        
        choice = input("\n👉 Pilih (0-3): ").strip()
        
        if choice == '1':
            produk_laris = self.report_generator.get_produk_terlaris(limit=100)
            self.csv_exporter.export_produk_terlaris(produk_laris)
        elif choice == '2':
            stok = self.report_generator.get_stok_summary()
            self.csv_exporter.export_stok_summary(stok)
        elif choice == '3':
            self.csv_exporter.export_transactions(self.db)
        else:
            return
        
        print("✅ File berhasil diekspor ke folder 'exports/'")
        self.pause()
    
    def cetak_ulang_resi(self):
        """Cetak ulang resi dari transaksi sebelumnya."""
        self.clear_screen()
        self.draw_header("🖨️  CETAK ULANG RESI")
        
        # Pilihan periode
        print("Pilih periode transaksi:")
        print("1. Hari Ini")
        print("2. Tanggal Tertentu")
        print("0. Kembali")
        
        periode_choice = input("\n👉 Pilih (0-2): ").strip()
        
        if periode_choice == '0':
            return
        
        transactions = []
        
        if periode_choice == '1':
            # Ambil transaksi hari ini
            from datetime import datetime
            today = datetime.now().strftime("%Y-%m-%d")
            transactions = self.db.get_transactions_by_date(today)
        elif periode_choice == '2':
            # Tanya user tanggal
            date_str = input("\nMasukkan tanggal (YYYY-MM-DD): ").strip()
            try:
                transactions = self.db.get_transactions_by_date(date_str)
            except Exception as e:
                print(f"❌ Error: {e}")
                self.pause()
                return
        else:
            print("❌ Pilihan tidak valid")
            self.pause()
            return
        
        if not transactions:
            print("⚠️  Tidak ada transaksi untuk periode yang dipilih")
            self.pause()
            return
        
        # Tampilkan list transaksi
        self.clear_screen()
        self.draw_header("📋 DAFTAR TRANSAKSI")
        
        print("No. | ID | Tanggal            | Total")
        print("-" * 60)
        
        for i, trans in enumerate(transactions, 1):
            trans_id = trans.get('id', 'N/A')
            tanggal = trans.get('tanggal', 'N/A')
            total = trans.get('total', 0)
            
            print(f"{i:>2}. | {trans_id:<3} | {str(tanggal):<18} | {format_rp(total)}")
        
        print("-" * 60)
        print(f"Total: {len(transactions)} transaksi")
        
        # Tanya user mana yang ingin dicetak
        pilih = self.get_safe_int("\n👉 Pilih nomor transaksi untuk dicetak (atau 0 untuk kembali): ", min_val=0)
        
        if pilih is None or pilih == 0:
            return
        
        if pilih < 1 or pilih > len(transactions):
            print("❌ Nomor tidak valid")
            self.pause()
            return
        
        selected_trans = transactions[pilih - 1]
        trans_id = selected_trans.get('id')
        
        if trans_id is None:
            print("❌ Data transaksi tidak valid")
            self.pause()
            return
        
        # Get full transaction data dengan items
        full_trans = self.db.get_transaction(trans_id)
        
        if full_trans is None:
            print(f"❌ Transaksi ID {trans_id} tidak ditemukan")
            self.pause()
            return
        
        # Reconstruct Transaction object dari database data
        try:
            from models import Transaction
            transaction = Transaction.from_dict(full_trans, self.db)
            
            # Tampilkan resi
            print("\n" + "=" * 70)
            print("📋 RESI TRANSAKSI (CETAK ULANG)")
            print("=" * 70)
            
            # Display receipt
            self.transaction_handler.receipt_manager.display_receipt(
                transaction,
                store_name=self.config.get_store_name(),
                store_address=self.config.get_store_address()
            )
            
            # Tanya user apakah ingin simpan file baru
            print("\n" + "-" * 70)
            simpan = input("💾 Simpan file resi baru? (y/n): ").strip().lower()
            if simpan == 'y':
                self.transaction_handler.receipt_manager.save_receipt(
                    transaction,
                    store_name=self.config.get_store_name(),
                    store_address=self.config.get_store_address()
                )
            
        except Exception as e:
            print(f"❌ Error saat cetak resi: {e}")
        
        self.pause()
    
    # ========================================================================
    # SETTINGS & UTILITY
    # ========================================================================
    
    def menu_settings(self):
        """Menu untuk settings dan utility."""
        while True:
            self.clear_screen()
            self.draw_header("⚙️ SETTINGS & UTILITY")
            
            stats = self.db.get_database_stats()
            print(f"📊 Database Stats:")
            print(f"   Produk: {stats['total_products']}")
            print(f"   Transaksi: {stats['total_transactions']}")
            print(f"   Items: {stats['total_items']}")
            print(f"   Location: {stats['db_path']}")
            
            print("\n1. 🔄 Reset Database (HATI-HATI!)")
            print("2. ℹ️  Tentang Sistem")
            print("0. ↩️  Kembali")
            
            choice = input("\n👉 Pilih menu (0-2): ").strip()
            
            if choice == '1':
                confirm = input("⚠️ Reset akan menghapus SEMUA data! Lanjut? (y/n): ").strip().lower()
                if confirm == 'y':
                    self.db.clear_database()
                    print("✅ Database berhasil direset")
            elif choice == '2':
                self.show_about()
            elif choice == '0':
                break
            else:
                print("❌ Pilihan tidak valid")
            
            self.pause()
    
    # ========================================================================
    # MENU - TELEGRAM BOT
    # ========================================================================
    
    def menu_telegram(self):
        """Menu untuk manage Telegram Bot."""
        if not TELEGRAM_AVAILABLE:
            self.clear_screen()
            print("\n❌ python-telegram-bot tidak terinstall!")
            print("\nInstall dengan command:")
            print("   pip install python-telegram-bot requests")
            self.pause()
            return
        
        while True:
            self.clear_screen()
            self.draw_header("🤖 TELEGRAM BOT MANAGEMENT")
            
            # Cek status bot
            if self.telegram_bot and self.telegram_bot.available:
                status = "✅ READY"
                bot_token = self.telegram_bot.config_manager.get_token()
                if bot_token:
                    bot_token = bot_token[:20] + "..."
                admin_id = self.telegram_bot.config_manager.config.get("admin_chat_id")
            else:
                status = "❌ NOT CONFIGURED"
                bot_token = "Not set"
                admin_id = "Not set"
            
            print(f"Status         : {status}")
            print(f"Bot Token      : {bot_token}")
            print(f"Admin Chat ID  : {admin_id}")
            print(f"Enabled        : {self.telegram_bot.config_manager.config.get('enabled', False) if self.telegram_bot else False}")
            print()
            
            print("1. 🚀 Jalankan Bot (Polling)")
            print("2. 📝 Setup Configuration")
            print("3. 🔔 Test Connection")
            print("4. 📋 Lihat Commands")
            print("5. 📊 Send Test Laporan")
            print("0. ↩️  Kembali ke Menu Utama")
            
            choice = input("\n👉 Pilih menu (0-5): ").strip()
            
            if choice == '1':
                self.telegram_start_bot()
            elif choice == '2':
                self.telegram_setup_config()
            elif choice == '3':
                self.telegram_test_connection()
            elif choice == '4':
                self.telegram_show_commands()
            elif choice == '5':
                self.telegram_send_test_report()
            elif choice == '0':
                break
            else:
                print("❌ Pilihan tidak valid")
                self.pause()
    
    def telegram_start_bot(self):
        """Jalankan Telegram Bot polling."""
        self.clear_screen()
        self.draw_header("🚀 JALANKAN TELEGRAM BOT")
        
        if not self.telegram_bot or not self.telegram_bot.available:
            print("❌ Bot belum di-configure")
            print("Silakan setup configuration terlebih dahulu (menu 2)")
            self.pause()
            return
        
        print("\n⏳ Bot sedang dimulai...")
        print("\n💡 Tips:")
        print("  - Bot akan berjalan di background")
        print("  - Tekan CTRL+C untuk menghentikan")
        print("  - Untuk mengirim command ke bot, gunakan Telegram dengan format /command")
        print()
        
        confirm = input("Lanjutkan? (y/n): ").strip().lower()
        
        if confirm == 'y':
            print("\n✅ Memulai bot...\n")
            self.telegram_bot.start()
    
    def telegram_setup_config(self):
        """Setup Telegram Bot configuration."""
        self.clear_screen()
        self.draw_header("📝 SETUP TELEGRAM BOT CONFIGURATION")
        
        if not self.telegram_bot:
            print("❌ Telegram bot tidak tersedia")
            self.pause()
            return
        
        print("\n📌 Petunjuk Setup:")
        print("  1. Buka Telegram dan cari @BotFather")
        print("  2. Kirim /newbot untuk membuat bot baru")
        print("  3. Ikuti instruksi, copy token yang diberikan")
        print("  4. Cari @userinfobot untuk mendapatkan Chat ID Anda")
        print()
        
        # Input bot token
        print("\n▶ Konfigurasi Bot Token:")
        token = input("  Masukkan Bot Token (dari BotFather): ").strip()
        if not token:
            print("❌ Token tidak boleh kosong")
            self.pause()
            return
        
        # Input admin chat ID
        print("\n▶ Konfigurasi Admin Chat ID:")
        try:
            admin_id = int(input("  Masukkan Admin Chat ID: ").strip())
        except ValueError:
            print("❌ Chat ID harus berupa angka")
            self.pause()
            return
        
        # Save config
        self.telegram_bot.config_manager.config["bot_token"] = token
        self.telegram_bot.config_manager.config["admin_chat_id"] = admin_id
        self.telegram_bot.config_manager.config["enabled"] = True
        self.telegram_bot.config_manager.config["allowed_chat_ids"] = [admin_id]
        self.telegram_bot.config_manager.save_config()
        
        # ⭐ PENTING: Reload telegram_bot object dengan config baru
        print("\n⏳ Memuat konfigurasi baru...")
        if TELEGRAM_AVAILABLE:
            try:
                self.telegram_bot = POSTelegramBot()
            except Exception as e:
                print(f"⚠️ Warning saat reload bot: {e}")
        
        print("\n✅ Konfigurasi berhasil disimpan!")
        print(f"   Bot Token: {token[:20]}...")
        print(f"   Admin ID: {admin_id}")
        print(f"   Status Bot: {'🟢 SIAP DIGUNAKAN' if self.telegram_bot and self.telegram_bot.available else '🔴 Belum siap'}")
        self.pause()
    
    def telegram_test_connection(self):
        """Test Telegram Bot connection."""
        self.clear_screen()
        self.draw_header("🔔 TEST TELEGRAM BOT CONNECTION")
        
        if not self.telegram_bot or not self.telegram_bot.available:
            print("❌ Bot belum di-configure")
            self.pause()
            return
        
        print("⏳ Testing connection...\n")
        
        try:
            import asyncio
            
            async def test_connection():
                admin_id = self.telegram_bot.config_manager.config.get("admin_chat_id")
                if not admin_id:
                    print("❌ Admin Chat ID belum dikonfigurasi")
                    return
                
                msg = (
                    "🤖 *TEST CONNECTION - POS TELEGRAM BOT*\n\n"
                    f"✅ Bot berhasil terhubung ke Telegram!\n"
                    f"Waktu: {datetime.now().strftime('%H:%M:%S')}"
                )
                
                try:
                    await self.telegram_bot.bot.send_message(
                        chat_id=admin_id,
                        text=msg,
                        parse_mode="Markdown"
                    )
                    print("✅ Pesan test berhasil dikirim ke Telegram!")
                except Exception as e:
                    print(f"❌ Error mengirim pesan: {e}")
            
            asyncio.run(test_connection())
        except Exception as e:
            print(f"❌ Error: {e}")
        
        self.pause()
    
    def telegram_show_commands(self):
        """Tampilkan semua commands yang tersedia."""
        self.clear_screen()
        self.draw_header("📋 TELEGRAM BOT COMMANDS")
        
        commands = [
            ("/laporan", "Laporan penjualan hari ini"),
            ("/stok", "Informasi stok produk"),
            ("/terlaris", "Produk paling laris (top 10)"),
            ("/dashboard", "Quick dashboard summary"),
            ("/ping", "Test bot connectivity"),
            ("/help", "Tampilkan bantuan commands"),
        ]
        
        print("\nCommands yang tersedia:\n")
        print("Command             | Deskripsi")
        print("-" * 70)
        
        for cmd, desc in commands:
            print(f"{cmd:<19} | {desc}")
        
        print("\n💡 Cara Penggunaan:")
        print("  1. Buka Telegram dan cari bot Anda")
        print("  2. Kirim salah satu command di atas (contoh: /laporan)")
        print("  3. Bot akan merespon dengan data real-time dari database POS")
        
        self.pause()
    
    def telegram_send_test_report(self):
        """Send test laporan ke Telegram."""
        self.clear_screen()
        self.draw_header("📊 SEND TEST LAPORAN")
        
        if not self.telegram_bot or not self.telegram_bot.available:
            print("❌ Bot belum di-configure")
            self.pause()
            return
        
        print("⏳ Sending test report...\n")
        
        try:
            import asyncio
            
            async def send_report():
                admin_id = self.telegram_bot.config_manager.config.get("admin_chat_id")
                if not admin_id:
                    print("❌ Admin Chat ID belum dikonfigurasi")
                    return
                
                # Generate laporan
                laporan = self.report_generator.get_laporan_harian()
                
                msg = (
                    f"📊 *TEST LAPORAN HARIAN*\n"
                    f"Tanggal: {laporan['tanggal']}\n\n"
                    f"💰 Total Penjualan: {format_rp(laporan['total_penjualan'])}\n"
                    f"📝 Total Transaksi: {laporan['total_transaksi']}\n"
                    f"📊 Rata-rata: {format_rp(int(laporan['rata_rata_transaksi']))}\n"
                )
                
                try:
                    await self.telegram_bot.bot.send_message(
                        chat_id=admin_id,
                        text=msg,
                        parse_mode="Markdown"
                    )
                    print("✅ Laporan test berhasil dikirim ke Telegram!")
                except Exception as e:
                    print(f"❌ Error mengirim laporan: {e}")
            
            asyncio.run(send_report())
        except Exception as e:
            print(f"❌ Error: {e}")
        
        self.pause()
    
    def show_about(self):
        """Tampilkan informasi tentang sistem."""
        self.clear_screen()
        print("""
╔════════════════════════════════════════════════════════════════════╗
║                   POINT OF SALE (POS) SYSTEM                       ║
║                      Version 1.0                                   ║
╠════════════════════════════════════════════════════════════════════╣
║                                                                    ║
║  Sistem Kasir modern dengan fitur lengkap:                        ║
║  - Manajemen produk dan stok                                      ║
║  - Transaksi penjualan real-time                                  ║
║  - Struk otomatis (print & simpan)                                ║
║  - Laporan penjualan & analisis                                   ║
║  - Export CSV untuk analisis lanjutan                             ║
║                                                                    ║
║  Database: SQLite (kasir_pos.db)                                  ║
║  Bahasa: Python 3.x                                               ║
║  Architecture: Modular, OOP, Maintainable                         ║
║                                                                    ║
║  Author: POS Development Team                                     ║
║  © 2026 - All Rights Reserved                                     ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝
        """)
    
    # ========================================================================
    # MAIN MENU & RUN
    # ========================================================================
    
    def show_main_menu(self):
        """Tampilkan main menu sesuai dengan user role."""
        while True:
            self.clear_screen()
            
            # Header dengan welcome
            print("""
╔════════════════════════════════════════════════════════════════════╗
║                                                                    ║
║                  🛒 SISTEM POS POINT OF SALE 🛒                  ║
║                      SELAMAT DATANG!                              ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝
            """)
            
            print(f"Toko: {self.config.get_store_name()}")
            print(f"User: {self.show_login_status()}")
            print(f"Waktu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            print("=" * 70)
            print("MENU UTAMA".center(70))
            print("=" * 70)
            
            print("\n1. 📦 Kelola Produk")
            print("2. 🛒 Transaksi Penjualan")
            print("3. 📊 Laporan & Analisis")
            
            # Role-based menu items
            if self.auth.require_admin():
                print("4. 🤖 Telegram Bot")
                print("5. ⚙️  Settings & Utility")
            
            print("0. 🚪 Keluar dari Sistem")
            
            choice = input("\n👉 Pilih menu (0-5): ").strip()
            
            if choice == '1':
                self.menu_produk()
            elif choice == '2':
                self.menu_transaksi()
            elif choice == '3':
                self.menu_laporan()
            elif choice == '4':
                if self.auth.require_admin():
                    self.menu_telegram()
                else:
                    print("❌ Hanya admin yang dapat mengakses menu Telegram")
                    self.pause()
            elif choice == '5':
                if self.auth.require_admin():
                    self.menu_settings()
                else:
                    print("❌ Hanya admin yang dapat mengakses menu Settings")
                    self.pause()
            elif choice == '0':
                self.exit_system()
                break
            else:
                print("❌ Pilihan tidak valid")
                self.pause()
    
    def exit_system(self):
        """Keluar dari sistem dengan pesan."""
        self.clear_screen()
        print("""
╔════════════════════════════════════════════════════════════════════╗
║                                                                    ║
║                   TERIMA KASIH TELAH MENGGUNAKAN                   ║
║                    POS SYSTEM POINT OF SALE                        ║
║                                                                    ║
║                     Sampai jumpa lagi! 👋                          ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝
        """)
        time.sleep(2)
    
    def run(self):
        """Jalankan POS System dengan login flow."""
        try:
            logger.info("=" * 70)
            logger.info("POS System started")
            logger.info("=" * 70)
            
            # Login flow dulu
            if not self.login_flow():
                logger.info("User cancelled login")
                return
            
            # Setelah login, tampilkan main menu
            self.show_main_menu()
            
        except KeyboardInterrupt:
            print("\n\n❌ Program dihentikan oleh user")
            logger.info("Program terminated by user (Ctrl+C)")
            self.exit_system()
        except Exception as e:
            print(f"\n❌ Error tidak terdupa: {e}")
            logger.error(f"Unexpected error: {e}", exc_info=True)
            import traceback
            traceback.print_exc()

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')  # Enable UTF-8 untuk Windows
    
    # Jalankan POS System
    pos_system = POSSystem()
    pos_system.run()
