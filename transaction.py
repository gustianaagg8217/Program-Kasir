# ============================================================================
# TRANSACTION.PY - Sistem Transaksi & Struk/Receipt Management
# ============================================================================
# Fungsi: Handle proses transaksi dari input item sampai generate struk
# Integrasi dengan database dan models
# ============================================================================

import os
from datetime import datetime
from typing import List, Optional, Dict

from database import DatabaseManager
from models import (
    Product, Transaction, TransactionItem, ProductManager,
    ValidationError, format_rp
)
from logger_config import get_logger, log_transaction_completed
from promotion_service import PromotionService

# Import accounting service
try:
    from accounting_service import AccountingService
    ACCOUNTING_AVAILABLE = True
except ImportError:
    ACCOUNTING_AVAILABLE = False
    AccountingService = None

logger = get_logger(__name__)

# ============================================================================
# TRANSACTION SERVICE - Main transaction processing logic
# ============================================================================

class TransactionService:
    """
    Service utama untuk mengelola proses transaksi dari awal sampai akhir.
    
    Workflow Transaksi:
    1. Buat transaksi baru (create_transaction)
    2. Scan/input kode produk dan qty (add_item)
    3. Konfirmasi pembayaran (set_payment)
    4. Simpan transaksi ke database (to_database)
    5. Generate & tampilkan struk (generate_receipt)
    
    Attributes:
        db (DatabaseManager): Database instance
        product_manager (ProductManager): Product manager instance
        current_transaction (Transaction): Transaksi aktif saat ini
        
    Methods:
        create_transaction(): Buat transaksi baru
        add_item_by_kode(): Add item menggunakan kode produk
        set_payment(): Set pembayaran dan hitung kembalian
        save_transaction(): Simpan ke database
        cancel_transaction(): Batalkan transaksi
    """
    
    def __init__(self, db: DatabaseManager):
        """
        Inisialisasi TransactionService.
        
        Args:
            db (DatabaseManager): Database instance
        """
        self.db = db
        self.product_manager = ProductManager(db)
        self.current_transaction: Optional[Transaction] = None
    
    # ========================================================================
    # TRANSACTION LIFECYCLE - Create, add, validate, save
    # ========================================================================
    
    def create_transaction(self) -> Transaction:
        """
        Buat transaksi baru dan set sebagai current_transaction.
        
        Returns:
            Transaction: Transaksi baru yang kosong
            
        Contoh:
            transaction = service.create_transaction()
            # transaction.items = [] (kosong)
            # transaction.total = 0
        """
        self.current_transaction = Transaction()
        print(f"✅ Transaksi baru dibuat pada {self.current_transaction.tanggal.strftime('%H:%M:%S')}")
        return self.current_transaction
    
    def add_item_by_kode(self, kode: str, qty: int) -> bool:
        """
        Tambah item ke transaksi aktif menggunakan kode produk.
        
        Process:
        1. Cek transaksi aktif ada atau tidak
        2. Lookup produk by kode
        3. Validasi stok cukup
        4. Buat TransactionItem
        5. Add ke transaksi
        6. Update total
        
        Args:
            kode (str): Kode produk
            qty (int): Jumlah item
            
        Returns:
            bool: True jika berhasil
            
        Raises:
            (handled internally, return False):
            - Transaksi belum dibuat
            - Produk tidak ditemukan
            - Stok tidak cukup
            - Input tidak valid
        """
        
        # Cek transaksi aktif
        if self.current_transaction is None:
            print("❌ Transaksi belum dibuat. Gunakan create_transaction() terlebih dahulu")
            return False
        
        try:
            # Validasi input qty
            from models import validate_qty
            qty = validate_qty(qty)
        except ValidationError as e:
            print(f"❌ Input error: {e}")
            return False
        
        # Cari produk by kode
        product = self.product_manager.get_product(kode)
        if product is None:
            print(f"❌ Produk dengan kode '{kode}' tidak ditemukan")
            return False
        
        # Cek stok
        if product.stok < qty:
            print(f"❌ Stok tidak cukup. Stok tersedia: {product.stok}, diminta: {qty}")
            return False
        
        # Buat transaction item
        item = TransactionItem(
            product_id=product.id,
            product_name=product.nama,
            qty=qty,
            harga_satuan=product.harga
        )
        
        # Apply promotion jika ada
        try:
            promo_service = PromotionService(self.db)
            active_promos = promo_service.get_applicable_promotions()
            
            # Check promotion menggunakan satuan produk yang sebenarnya (kg, pcs, dll)
            product_satuan = (product.satuan or 'pcs').lower()
            discount_info = promo_service.calculate_discount_for_quantity(qty, product_satuan, active_promos)
            
            if discount_info['applicable']:
                # Apply discount to item
                item.promotion_id = discount_info['promotion_id']
                item.promotion_name = discount_info['promotion_name']
                item.discount_percent = discount_info['discount_percent']
                item.discount_nominal = discount_info['discount_nominal']
                item.original_subtotal = item.subtotal
                
                # Calculate new subtotal with discount (dengan mempertimbangkan multiplier untuk kelipatan)
                multiplier = discount_info.get('multiplier', 1)
                
                if discount_info['discount_percent']:
                    discount_amount = int(item.subtotal * discount_info['discount_percent'] / 100)
                else:
                    discount_amount = discount_info['discount_nominal'] * multiplier
                
                item.subtotal = max(0, item.subtotal - discount_amount)
                
                print(f"🎯 Promosi Berlaku: {discount_info['promotion_name']}")
                if multiplier > 1:
                    print(f"   Kelipatan: {multiplier}x")
                print(f"   Diskon: {format_rp(discount_amount)}")
        except Exception as e:
            logger.warning(f"Error applying promotion: {e}")
            # Tetap lanjutkan transaksi jika promo error
        
        # Add ke transaksi
        try:
            self.current_transaction.add_item(item)
            print(f"✅ {product.nama} ({qty}x {format_rp(product.harga)}) ditambahkan")
            print(f"   Subtotal: {format_rp(item.subtotal)}")
            print(f"   Total transaksi: {format_rp(self.current_transaction.total)}")
            return True
        except Exception as e:
            print(f"❌ Error saat add item: {e}")
            return False
    
    def get_current_items(self) -> List[TransactionItem]:
        """
        Ambil list item dari transaksi aktif.
        
        Returns:
            List[TransactionItem]: List item dalam transaksi
            None: Jika tidak ada transaksi aktif
        """
        if self.current_transaction is None:
            return None
        return self.current_transaction.items
    
    def get_current_total(self) -> int:
        """
        Ambil total transaksi saat ini.
        
        Returns:
            int: Total dalam Rupiah (0 jika belum ada transaksi)
        """
        return self.current_transaction.total if self.current_transaction else 0
    
    def display_current_items(self):
        """
        Tampilkan daftar item dalam transaksi aktif dengan formatting rapi.
        """
        if self.current_transaction is None:
            print("❌ Transaksi belum dibuat")
            return
        
        if len(self.current_transaction.items) == 0:
            print("⚠️ Belum ada item dalam transaksi")
            return
        
        print("\n" + "=" * 70)
        print("ITEM DALAM TRANSAKSI:")
        print("=" * 70)
        
        for i, item in enumerate(self.current_transaction.items, 1):
            print(f"{i}. {item.display()}")
        
        print("-" * 70)
        print(f"Total: {format_rp(self.current_transaction.total)}")
        print("=" * 70 + "\n")
    
    def remove_item(self, index: int) -> bool:
        """
        Hapus item dari transaksi.
        
        Args:
            index (int): Index item (1-based untuk user-friendly)
            
        Returns:
            bool: True jika berhasil
        """
        if self.current_transaction is None:
            print("❌ Transaksi belum dibuat")
            return False
        
        # Convert dari 1-based ke 0-based index
        idx = index - 1
        
        try:
            self.current_transaction.remove_item(idx)
            print(f"✅ Item #{index} berhasil dihapus")
            print(f"   Total sekarang: {format_rp(self.current_transaction.total)}")
            return True
        except IndexError:
            print(f"❌ Item #{index} tidak ditemukan (item 1-{len(self.current_transaction.items)})")
            return False
    
    def set_payment(self, bayar: int, is_termin: bool = False) -> bool:
        """
        Set pembayaran dan hitung kembalian.
        
        Args:
            bayar (int): Jumlah uang pembayaran
            is_termin (bool): Jika True, bayar bisa kurang dari total (untuk DP)
            
        Returns:
            bool: True jika pembayaran valid
        """
        if self.current_transaction is None:
            print("❌ Transaksi belum dibuat")
            return False
        
        if len(self.current_transaction.items) == 0:
            print("❌ Transaksi kosong (tidak ada item)")
            return False
        
        try:
            self.current_transaction.set_bayar(bayar, is_termin=is_termin)
            print(f"✅ Pembayaran diterima")
            print(f"   Total        : {format_rp(self.current_transaction.total)}")
            
            # Tentukan label berdasarkan tipe pembayaran
            if is_termin:
                print(f"   DP (Down Payment): {format_rp(self.current_transaction.bayar)}")
                sisa_hutang = self.current_transaction.total - self.current_transaction.bayar
                print(f"   Sisa Hutang  : {format_rp(sisa_hutang)}")
            else:
                print(f"   Pembayaran   : {format_rp(self.current_transaction.bayar)}")
                print(f"   Kembalian    : {format_rp(self.current_transaction.kembalian)}")
            return True
        except ValidationError as e:
            print(f"❌ Error pembayaran: {e}")
            return False
    
    def save_transaction(self) -> Optional[int]:
        """
        Simpan transaksi ke database.
        
        Process:
        1. Validasi transaksi valid
        2. Kurangi stok setiap item
        3. Save transaction header ke database
        4. Save transaction items
        5. Return transaction ID
        
        Returns:
            int: Transaction ID jika berhasil
            None: Jika gagal
        """
        if self.current_transaction is None:
            print("❌ Transaksi belum dibuat")
            return None
        
        # Validasi transaksi
        if not self.current_transaction.is_valid():
            print("❌ Transaksi tidak valid")
            print(f"   - Items: {len(self.current_transaction.items)}")
            print(f"   - Total: {self.current_transaction.total}")
            print(f"   - Bayar: {self.current_transaction.bayar}")
            return None
        
        try:
            # 1. Kurangi stok untuk setiap item
            print("📦 Updating stok...")
            for item in self.current_transaction.items:
                success = self.db.reduce_stock(item.product_id, item.qty)
                if not success:
                    print("❌ Gagal update stok, transaksi dibatalkan")
                    return None
            
            # 2. Simpan transaction header dengan discount dan tax (terakumulasi)
            logger.info("Saving transaction to database...")
            # Untuk backward compatibility dengan database, gunakan discount_percent dari manual_discount_percent
            # dan discount_amount adalah total akumulasi
            trans_id = self.db.add_transaction(
                total=self.current_transaction.total,
                bayar=self.current_transaction.bayar,
                kembalian=self.current_transaction.kembalian,
                discount_percent=self.current_transaction.manual_discount_percent,
                discount_amount=self.current_transaction.discount_amount,  # Total diskon terakumulasi
                tax_percent=self.current_transaction.tax_percent,
                tax_amount=self.current_transaction.tax_amount,
                promotion_id=getattr(self.current_transaction, 'promotion_id', None),
                promotion_name=getattr(self.current_transaction, 'promotion_name', None)
            )
            
            if trans_id is None:
                logger.error("Failed to save transaction to database")
                return None
            
            # 3. Simpan transaction items dengan informasi promo
            for item in self.current_transaction.items:
                success = self.db.add_transaction_item(
                    transaction_id=trans_id,
                    product_id=item.product_id,
                    qty=item.qty,
                    harga_satuan=item.harga_satuan,
                    subtotal=item.subtotal,
                    promotion_id=getattr(item, 'promotion_id', None),
                    promotion_name=getattr(item, 'promotion_name', None),
                    discount_percent=getattr(item, 'discount_percent', 0),
                    discount_nominal=getattr(item, 'discount_nominal', 0)
                )
                if not success:
                    print(f"❌ Gagal menyimpan item, transaksi ID {trans_id}")
                    return None
            
            # Set ID pada transaksi
            self.current_transaction.id = trans_id
            print(f"✅ Transaksi berhasil disimpan (ID: {trans_id})")
            return trans_id
            
        except Exception as e:
            print(f"❌ Error saat save transaksi: {e}")
            return None
    
    def cancel_transaction(self):
        """
        Batalkan transaksi aktif (return ke kosong).
        
        Contoh:
            service.cancel_transaction()
            # current_transaction = None
        """
        if self.current_transaction is None:
            print("⚠️ Tidak ada transaksi aktif untuk dibatalkan")
            return
        
        items_count = len(self.current_transaction.items)
        total = self.current_transaction.total
        
        self.current_transaction = None
        print(f"❌ Transaksi dibatalkan ({items_count} item, total {format_rp(total)})")
    
    def get_current_transaction(self) -> Optional[Transaction]:
        """
        Ambil transaksi aktif saat ini.
        
        Returns:
            Transaction: Transaksi aktif
            None: Jika tidak ada transaksi
        """
        return self.current_transaction

# ============================================================================
# RECEIPT MANAGER - Generate dan simpan struk
# ============================================================================

class ReceiptManager:
    """
    Mengelola pembuatan, formatting, dan penyimpanan struk/receipt.
    
    Fitur:
    - Generate plain text receipt
    - Format rapi dengan tabel
    - Simpan ke file .txt
    - Custom receipt decorator (header, footer, dll)
    
    Attributes:
        receipt_dir (str): Directory untuk menyimpan file receipt
        
    Methods:
        generate_receipt(): Buat receipt object
        display_receipt(): Tampilkan ke console
        save_receipt(): Simpan ke file .txt
    """
    
    def __init__(self, receipt_dir: str = "receipts"):
        """
        Inisialisasi ReceiptManager.
        
        Args:
            receipt_dir (str): Directory untuk menyimpan receipts (default: "receipts")
        """
        self.receipt_dir = receipt_dir
        
        # Buat directory jika belum ada
        if not os.path.exists(receipt_dir):
            os.makedirs(receipt_dir)
            print(f"📁 Directory '{receipt_dir}' dibuat")
    
    def generate_receipt(self, transaction: Transaction, 
                        store_name: str = "TOKO POS",
                        store_address: str = None) -> str:
        """
        Generate formatted receipt string dari transaction.
        
        Args:
            transaction (Transaction): Transaction object
            store_name (str): Nama toko (default: "TOKO POS")
            store_address (str): Alamat toko (optional)
            
        Returns:
            str: Formatted receipt text
            
        Contoh output:
            ===========================================
            TOKO ACCESSORIES G-LIES
            Jl. Majalaya, Solokanjeruk, Bandung
            ===========================================
            Tanggal: 2026-03-29 14:30:45
            Invoice: #001234
            
            ITEM:
            Mie Goreng      2x Rp 15.000 = Rp 30.000
            Teh Botol       3x Rp 5.000  = Rp 15.000
            -----------------------------------------
            SUBTOTAL       : Rp 45.000
            DISKON (10%)   : -Rp 4.500
            PAJAK (10%)    : +Rp 4.050
            TOTAL          : Rp 44.550
            PEMBAYARAN     : Rp 50.000
            KEMBALIAN      : Rp 5.450
            ===========================================
            Terima kasih telah berbelanja!
            ===========================================
        """
        lines = []
        
        # Header
        lines.append("=" * 50)
        lines.append(store_name.center(50))
        if store_address:
            lines.append(store_address.center(50))
        lines.append("=" * 50)
        
        # Tanggal & Invoice
        lines.append(f"Tanggal: {transaction.tanggal.strftime('%Y-%m-%d %H:%M:%S')}")
        if transaction.id:
            lines.append(f"Invoice: #{transaction.id:06d}")
        lines.append("")
        
        # Items header
        lines.append("ITEM:")
        lines.append("-" * 50)
        
        # Items detail dengan promo breakdown
        total_promo_diskon = 0
        for item in transaction.items:
            lines.append(f"  {item.display()}")
            
            # Track total promo discount dari items
            if item.promotion_name:
                if item.discount_percent:
                    item_discount = int(item.original_subtotal * item.discount_percent / 100) if item.original_subtotal else 0
                else:
                    item_discount = item.discount_nominal or 0
                total_promo_diskon += item_discount
        
        # Total section
        lines.append("-" * 50)
        lines.append(f"SUBTOTAL       : {format_rp(transaction.subtotal):<20}")
        
        # Item-level promo diskon
        if total_promo_diskon > 0:
            lines.append(f"DISKON PROMOSI : -{format_rp(total_promo_diskon):<18}")
        
        # Diskon dari transaction-level (hasil apply_transaction_promotions)
        if transaction.discount_amount > 0:
            # Format: "DISKON (5%)" atau "DISKON" jika nominal tanpa persentase
            if transaction.discount_percent > 0:
                diskon_text = f"DISKON ({transaction.discount_percent}%)"
            else:
                diskon_text = "DISKON"
            lines.append(f"{diskon_text:<15}: -{format_rp(transaction.discount_amount):<18}")
        
        # Pajak
        if transaction.tax_amount > 0:
            pajak_text = f"PAJAK ({transaction.tax_percent}%)"
            lines.append(f"{pajak_text:<15}: +{format_rp(transaction.tax_amount):<18}")
        
        lines.append("-" * 50)
        lines.append(f"TOTAL          : {format_rp(transaction.total):<20}")
        lines.append(f"PEMBAYARAN     : {format_rp(transaction.bayar):<20}")
        lines.append(f"KEMBALIAN      : {format_rp(transaction.kembalian):<20}")
        lines.append("=" * 50)
        lines.append("Terima kasih telah berbelanja!".center(50))
        lines.append("=" * 50)
        
        return "\n".join(lines)
    
    def display_receipt(self, transaction: Transaction, 
                       store_name: str = "TOKO POS",
                       store_address: str = None):
        """
        Tampilkan receipt ke console/terminal.
        
        Args:
            transaction (Transaction): Transaction object
            store_name (str): Nama toko
            store_address (str): Alamat toko (optional)
        """
        receipt = self.generate_receipt(transaction, store_name, store_address)
        print("\n" + receipt + "\n")
    
    def save_receipt(self, transaction: Transaction, 
                    store_name: str = "TOKO POS",
                    store_address: str = None) -> Optional[str]:
        """
        Simpan receipt ke file .txt.
        
        Filename: receipts/receipt_20260329_143045_001234.txt
        
        Args:
            transaction (Transaction): Transaction object
            store_name (str): Nama toko
            store_address (str): Alamat toko (optional)
            
        Returns:
            str: Path file yang disimpan
            None: Jika gagal
        """
        try:
            # Generate receipt text
            receipt_text = self.generate_receipt(transaction, store_name, store_address)
            
            # Buat filename
            timestamp = transaction.tanggal.strftime("%Y%m%d_%H%M%S")
            invoice_num = f"{transaction.id:06d}" if transaction.id else "000000"
            filename = f"receipt_{timestamp}_{invoice_num}.txt"
            filepath = os.path.join(self.receipt_dir, filename)
            
            # Simpan ke file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(receipt_text)
            
            print(f"✅ Struk berhasil disimpan: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"❌ Error saat simpan struk: {e}")
            return None
    
    def get_receipt_path(self, transaction_id: int) -> str:
        """
        Get path untuk receipt file receipt berdasarkan transaction ID.
        Useful untuk retrieve receipt kemudian.
        
        Args:
            transaction_id (int): Transaction ID
            
        Returns:
            str: Receipt directory path
        """
        return self.receipt_dir

# ============================================================================
# TRANSACTION HANDLER - High-level wrapper untuk complete transaction flow
# ============================================================================

class TransactionHandler:
    """
    High-level handler yang mengkombinasikan TransactionService dan ReceiptManager.
    Digunakan di main.py untuk simplify transaction flow.
    
    Attributes:
        transaction_service (TransactionService): Service untuk transaksi
        receipt_manager (ReceiptManager): Manager untuk struk
        
    Methods:
        start_transaction(): Mulai transaksi baru
        process_item(): Add item
        complete_transaction(): Selesaikan transaksi
    """
    
    def __init__(self, db: DatabaseManager, receipt_dir: str = "receipts"):
        """
        Inisialisasi TransactionHandler.
        
        Args:
            db (DatabaseManager): Database instance
            receipt_dir (str): Directory untuk receipts
        """
        self.db = db
        self.transaction_service = TransactionService(db)
        self.receipt_manager = ReceiptManager(receipt_dir)
        
        # Initialize accounting service jika available
        if ACCOUNTING_AVAILABLE:
            self.accounting_service = AccountingService(db)
        else:
            self.accounting_service = None
            logger.warning("Accounting service not available - pembukuan feature disabled")
    
    def start_transaction(self) -> Transaction:
        """
        Mulai transaksi baru.
        
        Returns:
            Transaction: Transaksi baru
        """
        return self.transaction_service.create_transaction()
    
    def add_item(self, kode: str, qty: int) -> bool:
        """
        Add item ke transaksi.
        
        Args:
            kode (str): Kode produk
            qty (int): Qty
            
        Returns:
            bool: Success or not
        """
        return self.transaction_service.add_item_by_kode(kode, qty)
    
    def display_items(self):
        """Tampilkan item dalam transaksi."""
        self.transaction_service.display_current_items()
    
    def remove_item(self, index: int) -> bool:
        """Remove item dari transaksi."""
        return self.transaction_service.remove_item(index)
    
    def apply_transaction_promotions(self) -> dict:
        """
        Check dan apply promosi berdasarkan total transaksi.
        
        Fitur ini mengecek promosi yang berlaku berdasarkan total pembelian (harga),
        bukan berdasarkan qty/satuan individual item. Contoh: "Beli >= Rp 200.000 dapat diskon 5%"
        
        Method ini harus dipanggil sebelum checkout (sebelum complete_transaction).
        Diskon akan diterapkan otomatis ke transaction.discount_amount.
        
        Returns:
            dict: {
                'applied': bool,
                'promotion_id': int or None,
                'promotion_name': str,
                'discount_percent': int or None,
                'discount_amount': int,
                'total_before': int,
                'total_after': int
            }
        """
        trans = self.transaction_service.get_current_transaction()
        if trans is None:
            return {
                'applied': False,
                'promotion_id': None,
                'promotion_name': 'N/A',
                'discount_percent': None,
                'discount_amount': 0,
                'total_before': 0,
                'total_after': 0
            }
        
        try:
            # Get subtotal sebelum discount (reset discount dulu untuk hitung akurat)
            original_discount = trans.discount_amount
            trans.discount_amount = 0
            trans.calculate_total()
            subtotal = trans.subtotal
            
            # Check promosi berdasarkan total
            promo_service = PromotionService(self.db)
            active_promos = promo_service.get_applicable_promotions()
            discount_info = promo_service.calculate_discount_for_total(subtotal, active_promos)
            
            result = {
                'applied': False,
                'promotion_id': None,
                'promotion_name': '',
                'discount_percent': None,
                'discount_amount': 0,
                'total_before': subtotal,
                'total_after': subtotal
            }
            
            if discount_info['applicable']:
                # Calculate discount amount dengan mempertimbangkan multiplier (untuk kelipatan)
                multiplier = discount_info.get('multiplier', 1)
                
                if discount_info['discount_percent']:
                    discount_amount = int(subtotal * discount_info['discount_percent'] / 100)
                    discount_percent = discount_info['discount_percent']
                else:
                    discount_amount = discount_info['discount_nominal'] * multiplier
                    discount_percent = 0
                
                # Apply to transaction
                trans.set_promo_discount(discount_amount)  # Ini akan set promo_discount dan call calculate_total()
                trans.discount_percent = discount_percent  # Set persentase untuk display di receipt
                trans.discount_type = 'fixed'  # Fixed amount, not percentage
                trans.promotion_id = discount_info['promotion_id']
                trans.promotion_name = discount_info['promotion_name']
                
                result = {
                    'applied': True,
                    'promotion_id': discount_info['promotion_id'],
                    'promotion_name': discount_info['promotion_name'],
                    'discount_percent': discount_info['discount_percent'],
                    'discount_amount': discount_amount,
                    'multiplier': multiplier,
                    'total_before': subtotal,
                    'total_after': trans.total
                }
                
                logger.info(f"🎯 Transaction-wide promotion applied: {discount_info['promotion_name']}")
                logger.info(f"   Subtotal: Rp{subtotal:,}")
                logger.info(f"   Nilai Diskon (per unit): Rp{discount_info['discount_nominal']:,}") if discount_info['discount_nominal'] else None
                if multiplier > 1:
                    logger.info(f"   Kelipatan: {multiplier}x (Total Rp{discount_amount:,} = Rp{discount_info['discount_nominal']:,} x {multiplier})")
                else:
                    logger.info(f"   Diskon: Rp{discount_amount:,}")
                logger.info(f"   Total: Rp{trans.total:,}")
            else:
                # Restore original discount jika tidak ada promosi baru
                trans.discount_amount = original_discount
                trans.calculate_total()
                result['total_before'] = trans.subtotal
                result['total_after'] = trans.total
                result['multiplier'] = 1
            
            return result
            
        except Exception as e:
            logger.error(f"Error applying transaction promotions: {e}", exc_info=True)
            return {
                'applied': False,
                'promotion_id': None,
                'promotion_name': f'Error: {str(e)}',
                'discount_percent': None,
                'discount_amount': 0,
                'total_before': trans.subtotal if trans else 0,
                'total_after': trans.total if trans else 0
            }
    
    def complete_transaction(self, bayar: int, 
                            store_name: str = "TOKO POS",
                            store_address: str = None,
                            print_receipt: bool = False,
                            is_termin: bool = False) -> Optional[int]:
        """
        Selesaikan transaksi (set bayar, save ke DB).
        Receipt printing adalah optional dan bisa dilakukan terpisah dengan print_receipt().
        
        Args:
            bayar (int): Jumlah pembayaran
            store_name (str): Nama toko
            store_address (str): Alamat toko
            print_receipt (bool): Jika True, langsung display dan save receipt
            is_termin (bool): Jika True, ini adalah termin payment (bayar bisa kurang dari total)
            
        Returns:
            int: Transaction ID jika berhasil
            None: Jika gagal
        """
        try:
            # Set payment dengan is_termin flag
            if not self.transaction_service.set_payment(bayar, is_termin=is_termin):
                logger.error("Failed to set payment for transaction")
                return None
            
            # Save to database
            trans_id = self.transaction_service.save_transaction()
            if trans_id is None:
                logger.error("Failed to save transaction to database")
                return None
            
            # Get transaction details for logging
            transaction = self.transaction_service.get_current_transaction()
            total = transaction.total if transaction else 0
            items_count = transaction.get_item_count() if transaction else 0
            
            # Log transaction completion
            payment_type = "Termin" if is_termin else "Lunas"
            logger.info(f"Transaction completed ({payment_type}): ID={trans_id}, total=Rp{total:,}, items={items_count}, payment=Rp{bayar:,}")
            
            # Record income ke pembukuan (accounting)
            if ACCOUNTING_AVAILABLE and self.accounting_service:
                try:
                    if not is_termin:
                        # Only record income for lunas (not termin) transactions
                        self.accounting_service.record_income(
                            transaction_id=trans_id,
                            amount=total,
                            description="Penjualan"
                        )
                        logger.info(f"✅ Income recorded: trans_id={trans_id}, amount={total}, type=Penjualan")
                    elif is_termin and bayar > 0:
                        # For termin, record the payment made (not full total)
                        self.accounting_service.record_income(
                            transaction_id=trans_id,
                            amount=bayar,
                            description="Pembayaran Termin"
                        )
                        logger.info(f"✅ Termin payment recorded: trans_id={trans_id}, amount={bayar}, type=Pembayaran Termin")
                except Exception as e:
                    logger.error(f"❌ Error recording income: {e}", exc_info=True)
            else:
                logger.warning(f"⚠️ Accounting service not available (ACCOUNTING_AVAILABLE={ACCOUNTING_AVAILABLE}, service={self.accounting_service})")
            
            # Display receipt jika print_receipt=True
            if print_receipt:
                self.print_receipt(store_name, store_address)
            
            return trans_id
        except Exception as e:
            logger.error(f"Error completing transaction: {e}", exc_info=True)
            return None
    
    def print_receipt(self, store_name: str = "TOKO POS", store_address: str = None):
        """
        Display dan save receipt untuk transaksi yang sudah completed.
        Gunakan method ini untuk print receipt setelah transaksi selesai.
        
        Args:
            store_name (str): Nama toko
            store_address (str): Alamat toko (optional)
        """
        try:
            transaction = self.transaction_service.get_current_transaction()
            if transaction is None:
                print("❌ Tidak ada transaksi yang aktif")
                return
            
            # Display receipt
            self.receipt_manager.display_receipt(transaction, store_name, store_address)
            
            # Save receipt to file
            self.receipt_manager.save_receipt(transaction, store_name, store_address)
            
        except Exception as e:
            logger.error(f"Error printing receipt: {e}", exc_info=True)
            print(f"❌ Error saat cetak resi: {e}")
    
    def cancel_transaction(self):
        """Cancel transaksi aktif."""
        self.transaction_service.cancel_transaction()
    
    def get_transaction_summary(self) -> Optional[Dict]:
        """
        Ambil summary transaksi aktif.
        
        Returns:
            dict: {items_count, qty_total, total, bayar, kembalian}
            None: Jika tidak ada transaksi
        """
        trans = self.transaction_service.get_current_transaction()
        if trans is None:
            return None
        
        return {
            'items_count': trans.get_item_count(),
            'qty_total': trans.get_qty_total(),
            'total': trans.total,
            'bayar': trans.bayar,
            'kembalian': trans.kembalian,
            'status': 'VALID' if trans.is_valid() else 'INVALID'
        }
    
    def get_items(self) -> Optional[list]:
        """
        Ambil list items dari transaksi aktif dengan informasi promotional discount.
        
        Returns:
            list: List of items (dict format dengan promotional discount info)
            None: Jika tidak ada transaksi
        """
        trans = self.transaction_service.get_current_transaction()
        if trans is None:
            return None
        
        items = []
        for item in trans.items:
            # Hitung discount amount untuk item ini dengan safe null checking
            discount_amount = 0
            discount_text = ""
            
            item_discount_percent = item.discount_percent or 0
            item_discount_nominal = item.discount_nominal or 0
            item_promotion_name = item.promotion_name or ""
            item_original_subtotal = item.original_subtotal or item.subtotal
            
            if item_discount_percent > 0:
                discount_amount = int(item.harga_satuan * item.qty * item_discount_percent / 100)
                discount_text = f"{item_discount_percent}%"
            elif item_discount_nominal > 0:
                discount_amount = item_discount_nominal * item.qty
                discount_text = f"Rp {item_discount_nominal:,}/unit"
            
            # product_id adalah ID database, product_name sudah tersimpan
            items.append({
                'kode': str(item.product_id),  # Convert ID ke string untuk compatibility
                'nama': item.product_name,  # Gunakan product_name yang sudah tersimpan
                'qty': item.qty,
                'harga_satuan': item.harga_satuan,
                'subtotal': item.subtotal,
                'promotion_name': item_promotion_name,  # Nama promo jika ada
                'discount_amount': discount_amount,  # Jumlah diskon untuk item ini
                'discount_text': discount_text,  # Format diskon untuk display
                'original_subtotal': item_original_subtotal,  # Harga sebelum diskon
            })
        return items

# ============================================================================
# TESTING - Jalankan jika file dijalankan standalone
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("POS TRANSACTION SYSTEM - Testing")
    print("=" * 70)
    
    # Setup database
    db = DatabaseManager()
    
    # Clear existing data
    print("\n🔄 Clearing existing data...")
    db.clear_database()
    
    # Add sample products
    print("\n➕ Adding sample products...")
    db.add_product("PROD001", "Mie Goreng", 15000, 100)
    db.add_product("PROD002", "Teh Botol", 5000, 150)
    db.add_product("PROD003", "Roti Tawar", 20000, 50)
    
    # Create transaction service
    print("\n🛒 Testing TransactionService...")
    service = TransactionService(db)
    
    # Create transaction
    trans = service.create_transaction()
    
    # Add items
    service.add_item_by_kode("PROD001", 2)
    service.add_item_by_kode("PROD002", 3)
    service.add_item_by_kode("PROD003", 1)
    
    # Display items
    service.display_current_items()
    
    # Set payment
    service.set_payment(100000)
    
    # Save transaction
    trans_id = service.save_transaction()
    
    # Test ReceiptManager
    if trans_id:
        print("\n🧾 Testing ReceiptManager...")
        receipt_mgr = ReceiptManager()
        receipt_mgr.display_receipt(trans)
        receipt_mgr.save_receipt(trans)
    
    print("\n✅ Test selesai!")
