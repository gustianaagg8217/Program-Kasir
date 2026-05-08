# ============================================================================
# DATABASE.PY - SQLite Database Manager untuk POS System
# ============================================================================
# Fungsi: Mengelola semua operasi database (create, read, update, delete)
# Author: POS Team
# Version: 1.0
# ============================================================================

import sqlite3
import os
import hashlib
from datetime import datetime, timedelta
from contextlib import contextmanager
from logger_config import get_logger
from backup_manager import BackupManager

# Import secure password manager
try:
    from auth_security import PasswordManager
except ImportError:
    # Fallback if auth_security not available yet
    PasswordManager = None

logger = get_logger(__name__)

class DatabaseManager:
    """
    Kelola semua operasi database SQLite untuk sistem POS.
    
    Fitur:
    - Koneksi database otomatis
    - Create/Read/Update/Delete operasi
    - Transaction management
    - Context manager untuk safe connection handling
    
    Attributes:
        db_path (str): Path ke file database SQLite
        connection: SQLite connection object
    """
    
    def __init__(self, db_name: str = "kasir_pos.db", telegram_bot=None):
        """
        Inisialisasi DatabaseManager dan buat database jika belum ada.
        
        Args:
            db_name (str): Nama file database (default: kasir_pos.db)
            telegram_bot: Instance POSTelegramBot untuk mengirim notifikasi (optional)
        """
        # Tentukan path database di folder yang sama dengan script
        self.db_path = db_name
        self.telegram_bot = telegram_bot
        
        # Initialize backup manager
        self.backup_manager = BackupManager(backup_folder="backup", max_backups=7)
        
        # Buat database dan tabel jika belum ada
        self._init_database()
    
    # ========================================================================
    # KONEKSI DATABASE - Manage koneksi SQLite dengan context manager
    # ========================================================================
    
    @contextmanager
    def get_connection(self):
        """
        Context manager untuk koneksi database yang aman.
        
        Gunakan dengan 'with' statement untuk auto-commit dan close.
        Jika error terjadi, auto-rollback.
        
        Yield:
            sqlite3.Connection: Database connection object
            
        Contoh:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM products')
        """
        connection = None
        try:
            # Buka koneksi ke database
            connection = sqlite3.connect(self.db_path)
            connection.row_factory = sqlite3.Row  # Akses hasil query seperti dict
            yield connection
            # Auto-commit jika tidak ada error
            connection.commit()
        except Exception as e:
            # Rollback jika ada error
            if connection:
                connection.rollback()
            logger.error(f"Database error: {e}", exc_info=True)
            raise
        finally:
            # Tutup koneksi
            if connection:
                connection.close()
    
    # ========================================================================
    # PASSWORD HASHING - Secure password management dengan Bcrypt
    # ========================================================================
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password menggunakan Bcrypt (secure & salted).
        
        NOTE: Ini menggantikan old SHA256 hashing untuk security yang lebih baik.
        Backward compatibility: verify_password() masih support SHA256 hashes lama.
        
        Args:
            password (str): Password plain text
            
        Returns:
            str: Bcrypt hashed password
            
        Raises:
            ValueError: Jika password kosong atau bukan string
        """
        if PasswordManager:
            return PasswordManager.hash_password(password)
        else:
            # Fallback ke SHA256 jika bcrypt tidak tersedia
            logger.warning("PasswordManager not available, falling back to SHA256")
            return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """
        Verify password dengan hashnya (bcrypt atau legacy SHA256).
        
        Automatically support both:
        - New bcrypt hashes ($2b$12$...)
        - Legacy SHA256 hashes (backward compatibility)
        
        Args:
            password (str): Password plain text
            hashed_password (str): Password yang di-hash (bcrypt atau SHA256)
            
        Returns:
            bool: True jika cocok, False jika tidak
        """
        if PasswordManager:
            return PasswordManager.verify_password(password, hashed_password)
        else:
            # Fallback ke SHA256 jika bcrypt tidak tersedia
            logger.warning("PasswordManager not available, falling back to SHA256")
            return hashlib.sha256(password.encode()).hexdigest() == hashed_password
    
    # ========================================================================
    # INIT DATABASE - Buat struktur tabel jika belum ada
    # ========================================================================
    
    def _init_database(self):
        """
        Buat tabel database jika belum ada.
        Dijalankan otomatis saat __init__()
        
        Tabel yang dibuat:
        1. products - Daftar produk
        2. transactions - Header transaksi
        3. transaction_items - Item detail transaksi
        """
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # ================================================================
            # TABEL 1: PRODUCTS
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kode TEXT UNIQUE NOT NULL,
                    nama TEXT NOT NULL,
                    harga INTEGER NOT NULL,
                    stok INTEGER NOT NULL,
                    satuan TEXT DEFAULT 'pcs',
                    foto_path TEXT DEFAULT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Migration: Add missing columns if they don't exist
            try:
                cursor.execute("PRAGMA table_info(products)")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'foto_path' not in columns:
                    cursor.execute("ALTER TABLE products ADD COLUMN foto_path TEXT DEFAULT NULL")
                    logger.info("Added foto_path column to products table")
                if 'satuan' not in columns:
                    cursor.execute("ALTER TABLE products ADD COLUMN satuan TEXT DEFAULT 'pcs'")
                    logger.info("Added satuan column to products table")
            except Exception as e:
                logger.warning(f"Migration warning for products table: {e}")
            
            # ================================================================
            # TABEL 2: TRANSACTIONS - Header transaksi penjualan dengan discount/tax
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tanggal DATETIME DEFAULT CURRENT_TIMESTAMP,
                    total INTEGER NOT NULL,
                    bayar INTEGER NOT NULL,
                    kembalian INTEGER NOT NULL,
                    discount_percent REAL DEFAULT 0,
                    discount_amount INTEGER DEFAULT 0,
                    tax_percent REAL DEFAULT 0,
                    tax_amount INTEGER DEFAULT 0
                )
            """)
            
            # ================================================================
            # MIGRATION: Add discount/tax columns jika belum ada
            # ================================================================
            try:
                cursor.execute("PRAGMA table_info(transactions)")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'discount_percent' not in columns:
                    cursor.execute("ALTER TABLE transactions ADD COLUMN discount_percent REAL DEFAULT 0")
                if 'discount_amount' not in columns:
                    cursor.execute("ALTER TABLE transactions ADD COLUMN discount_amount INTEGER DEFAULT 0")
                if 'tax_percent' not in columns:
                    cursor.execute("ALTER TABLE transactions ADD COLUMN tax_percent REAL DEFAULT 0")
                if 'tax_amount' not in columns:
                    cursor.execute("ALTER TABLE transactions ADD COLUMN tax_amount INTEGER DEFAULT 0")
                if 'payment_type' not in columns:
                    cursor.execute("ALTER TABLE transactions ADD COLUMN payment_type TEXT DEFAULT 'lunas'")
                if 'payment_status' not in columns:
                    cursor.execute("ALTER TABLE transactions ADD COLUMN payment_status TEXT DEFAULT 'completed'")
                if 'due_date' not in columns:
                    cursor.execute("ALTER TABLE transactions ADD COLUMN due_date DATE DEFAULT NULL")
                if 'customer_name' not in columns:
                    cursor.execute("ALTER TABLE transactions ADD COLUMN customer_name TEXT DEFAULT NULL")
                if 'promotion_id' not in columns:
                    cursor.execute("ALTER TABLE transactions ADD COLUMN promotion_id INTEGER DEFAULT NULL")
                if 'promotion_name' not in columns:
                    cursor.execute("ALTER TABLE transactions ADD COLUMN promotion_name TEXT DEFAULT NULL")
                conn.commit()
                logger.info("Transaction table migration completed")
            except Exception as e:
                logger.warning(f"Migration warning: {e}")
            
            # ================================================================
            # TABEL 3: TRANSACTION_ITEMS - Detail item per transaksi
            # Foreign Key ke transactions.id dan products.id
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transaction_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    qty INTEGER NOT NULL,
                    harga_satuan INTEGER NOT NULL,
                    subtotal INTEGER NOT NULL,
                    FOREIGN KEY (transaction_id) REFERENCES transactions(id),
                    FOREIGN KEY (product_id) REFERENCES products(id)
                )
            """)
            
            # ================================================================
            # MIGRATION: Add promotion columns to transaction_items
            # ================================================================
            try:
                cursor.execute("PRAGMA table_info(transaction_items)")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'promotion_id' not in columns:
                    cursor.execute("ALTER TABLE transaction_items ADD COLUMN promotion_id INTEGER DEFAULT NULL")
                if 'promotion_name' not in columns:
                    cursor.execute("ALTER TABLE transaction_items ADD COLUMN promotion_name TEXT DEFAULT NULL")
                if 'discount_percent' not in columns:
                    cursor.execute("ALTER TABLE transaction_items ADD COLUMN discount_percent REAL DEFAULT 0")
                if 'discount_nominal' not in columns:
                    cursor.execute("ALTER TABLE transaction_items ADD COLUMN discount_nominal INTEGER DEFAULT 0")
                
                conn.commit()
                logger.info("Transaction items table migration completed (promotion columns added)")
            except Exception as e:
                logger.warning(f"Transaction items migration warning: {e}")
            
            # ================================================================
            # TABEL 4: USERS - User login dengan role-based access
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    hashed_password TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'cashier',
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # ================================================================
            # TABEL 4B: LOGIN_ATTEMPTS - Track login attempts untuk security
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS login_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    ip_address TEXT DEFAULT NULL,
                    user_agent TEXT DEFAULT NULL,
                    attempted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (username) REFERENCES users(username)
                )
            """)
            
            # Create index untuk faster queries
            try:
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_login_attempts_username 
                    ON login_attempts(username)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_login_attempts_timestamp 
                    ON login_attempts(attempted_at)
                """)
            except Exception as e:
                logger.warning(f"Index creation warning: {e}")
            
            # ================================================================
            # TABEL 5: STOCK_OPNAME - Riwayat stock count dan adjustment
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_opname (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    opname_date DATE NOT NULL,
                    product_id INTEGER NOT NULL,
                    stok_sistem INTEGER NOT NULL,
                    stok_fisik INTEGER NOT NULL,
                    selisih INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    catatan TEXT DEFAULT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products(id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # ================================================================
            # TABEL 6: INVOICES - Header invoice dari transaction
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_number TEXT UNIQUE NOT NULL,
                    total INTEGER NOT NULL,
                    bayar INTEGER NOT NULL,
                    kembalian INTEGER NOT NULL,
                    discount_percent REAL DEFAULT 0,
                    discount_amount INTEGER DEFAULT 0,
                    tax_percent REAL DEFAULT 0,
                    tax_amount INTEGER DEFAULT 0,
                    payment_type TEXT DEFAULT 'lunas',
                    payment_status TEXT DEFAULT 'completed',
                    due_date DATE DEFAULT NULL,
                    customer_name TEXT DEFAULT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # ================================================================
            # MIGRATION: Add termin columns ke invoices jika belum ada
            # ================================================================
            try:
                cursor.execute("PRAGMA table_info(invoices)")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'payment_type' not in columns:
                    cursor.execute("ALTER TABLE invoices ADD COLUMN payment_type TEXT DEFAULT 'lunas'")
                if 'payment_status' not in columns:
                    cursor.execute("ALTER TABLE invoices ADD COLUMN payment_status TEXT DEFAULT 'completed'")
                if 'due_date' not in columns:
                    cursor.execute("ALTER TABLE invoices ADD COLUMN due_date DATE DEFAULT NULL")
                if 'customer_name' not in columns:
                    cursor.execute("ALTER TABLE invoices ADD COLUMN customer_name TEXT DEFAULT NULL")
                if 'customer_phone' not in columns:
                    cursor.execute("ALTER TABLE invoices ADD COLUMN customer_phone TEXT DEFAULT NULL")
                if 'customer_email' not in columns:
                    cursor.execute("ALTER TABLE invoices ADD COLUMN customer_email TEXT DEFAULT NULL")
                if 'customer_address' not in columns:
                    cursor.execute("ALTER TABLE invoices ADD COLUMN customer_address TEXT DEFAULT NULL")
                logger.info("Invoice table migration completed")
            except Exception as e:
                logger.warning(f"Invoice migration warning: {e}")
            
            # ================================================================
            # TABEL 7: INVOICE_ITEMS - Detail item dalam invoice
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS invoice_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_id INTEGER NOT NULL,
                    nama TEXT NOT NULL,
                    qty INTEGER NOT NULL,
                    harga_satuan INTEGER NOT NULL,
                    subtotal INTEGER NOT NULL,
                    FOREIGN KEY (invoice_id) REFERENCES invoices(id)
                )
            """)
            
            # ================================================================
            # TABEL 8: TERMIN_PAYMENTS - Cicilan pembayaran untuk invoice termin
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS termin_payments (
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
            """)
            
            # Create indices untuk faster queries
            try:
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_termin_invoice_id 
                    ON termin_payments(invoice_id)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_termin_status 
                    ON termin_payments(status)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_termin_due_date 
                    ON termin_payments(due_date)
                """)
                logger.info("Termin payments table created successfully")
            except Exception as e:
                logger.warning(f"Termin table index creation warning: {e}")
            
            # Create indices untuk fast queries
            try:
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_invoices_number 
                    ON invoices(invoice_number)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_invoices_date 
                    ON invoices(created_at)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice_id 
                    ON invoice_items(invoice_id)
                """)
                logger.info("Invoice table indices created successfully")
            except Exception as e:
                logger.warning(f"Invoice index creation warning: {e}")
            
            # ================================================================
            # TABEL 9: CASHFLOW - Income dan Expense untuk Pembukuan
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cashflow (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
                    amount INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    related_transaction_id INTEGER DEFAULT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (related_transaction_id) REFERENCES transactions(id)
                )
            """)
            
            # Create indices untuk cashflow
            try:
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_cashflow_type 
                    ON cashflow(type)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_cashflow_date 
                    ON cashflow(created_at)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_cashflow_transaction 
                    ON cashflow(related_transaction_id)
                """)
                logger.info("Cashflow table indices created successfully")
            except Exception as e:
                logger.warning(f"Cashflow index creation warning: {e}")
            
            # ================================================================
            # TABEL 10: PROMOSI - Manajemen promosi dan diskon
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS promotions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nama_promosi TEXT NOT NULL,
                    deskripsi TEXT DEFAULT NULL,
                    tipe_diskon TEXT NOT NULL CHECK(tipe_diskon IN ('persentase', 'nominal')),
                    nilai_diskon INTEGER NOT NULL,
                    min_qty REAL NOT NULL,
                    satuan TEXT DEFAULT 'kg',
                    berlaku_kelipatan BOOLEAN DEFAULT 0,
                    tanggal_mulai DATE NOT NULL,
                    tanggal_selesai DATE NOT NULL,
                    status TEXT DEFAULT 'aktif' CHECK(status IN ('aktif', 'nonaktif')),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indices untuk promosi
            try:
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_promotion_status 
                    ON promotions(status)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_promotion_dates 
                    ON promotions(tanggal_mulai, tanggal_selesai)
                """)
                logger.info("Promotions table created successfully")
            except Exception as e:
                logger.warning(f"Promotions table index creation warning: {e}")
            
            # ================================================================
            # MIGRATION: Add berlaku_kelipatan column to promotions
            # ================================================================
            try:
                cursor.execute("PRAGMA table_info(promotions)")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'berlaku_kelipatan' not in columns:
                    cursor.execute("ALTER TABLE promotions ADD COLUMN berlaku_kelipatan BOOLEAN DEFAULT 0")
                    logger.info("Added berlaku_kelipatan column to promotions table")
            except Exception as e:
                logger.warning(f"Migration warning for promotions table: {e}")
            
            conn.commit()
            logger.info("Database tables initialized successfully")
    
    # ========================================================================
    # BACKUP OPERATIONS - Automatic backup management
    # ========================================================================
    
    def backup_database(self) -> bool:
        """
        Create automatic backup dari database file.
        
        Backup hanya dibuat jika belum ada backup untuk hari ini.
        Automatically cleanup old backups (keep hanya 7 backups).
        
        Returns:
            bool: True jika backup dibuat, False jika sudah ada untuk hari ini
        """
        try:
            return self.backup_manager.backup_database(self.db_path)
        except Exception as e:
            logger.error(f"Failed to create backup: {e}", exc_info=True)
            return False
    
    def get_backup_list(self) -> list:
        """Get list of all available backups."""
        try:
            return self.backup_manager.get_backup_list()
        except Exception as e:
            logger.error(f"Failed to get backup list: {e}", exc_info=True)
            return []
    
    def restore_backup(self, backup_filename: str) -> bool:
        """Restore database from backup file."""
        try:
            return self.backup_manager.restore_backup(backup_filename, self.db_path)
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}", exc_info=True)
            return False
    
    def get_backup_statistics(self) -> dict:
        """Get backup statistics."""
        try:
            return self.backup_manager.get_backup_statistics()
        except Exception as e:
            logger.error(f"Failed to get backup statistics: {e}", exc_info=True)
            return {}
    
    # ========================================================================
    # PRODUCT OPERATIONS - CRUD operasi untuk tabel products
    # ========================================================================
    
    def add_product(self, kode: str, nama: str, harga: int, stok: int, satuan: str = 'pcs', foto_path: str = None) -> bool:
        """
        Tambah produk baru ke database.
        
        Args:
            kode (str): Kode produk unik (contoh: 'PROD001')
            nama (str): Nama produk
            harga (int): Harga dalam Rupiah
            stok (int): Jumlah stok awal
            satuan (str): Satuan produk (contoh: 'pcs', 'Kg', 'L')
            foto_path (str, optional): Path file foto produk
            
        Returns:
            bool: True jika berhasil, False jika gagal
            
        Raises:
            sqlite3.IntegrityError: Jika kode produk sudah ada (duplicate)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                logger.debug(f"Adding product: kode={kode}, nama={nama}, harga={harga}, stok={stok}, satuan={satuan}, foto_path={foto_path}")
                cursor.execute("""
                    INSERT INTO products (kode, nama, harga, stok, satuan, foto_path)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (kode, nama, harga, stok, satuan, foto_path))
                conn.commit()
                logger.info(f"Product added: {kode} = {nama} ({satuan}) (foto: {foto_path})")
                return True
        except sqlite3.IntegrityError as e:
            logger.warning(f"Product code '{kode}' already exists: {e}")
            return False
        except Exception as e:
            logger.error(f"Error adding product: {e}", exc_info=True)
            return False
    
    def get_product_by_kode(self, kode: str) -> dict or None:
        """
        Ambil data produk berdasarkan kode.
        Kode di-uppercase dan di-strip untuk konsistensi.
        
        Args:
            kode (str): Kode produk
            
        Returns:
            dict: Data produk {id, kode, nama, harga, stok}
            None: Jika produk tidak ditemukan
            
        Contoh return:
            {'id': 1, 'kode': '0001', 'nama': 'Mie Goreng', 'harga': 15000, 'stok': 100}
        """
        try:
            # Normalize kode: strip whitespace
            kode = str(kode).strip()
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM products WHERE LOWER(TRIM(kode)) = LOWER(TRIM(?))", (kode,))
                result = cursor.fetchone()
                
                if result:
                    logger.debug(f"Product found by kode: {kode}")
                    return dict(result)
                else:
                    logger.debug(f"Product not found by kode: {kode}")
                    return None
        except Exception as e:
            logger.error(f"Error getting product by kode '{kode}': {e}", exc_info=True)
            return None
    
    def get_product_by_id(self, product_id: int) -> dict or None:
        """
        Ambil data produk berdasarkan ID.
        
        Args:
            product_id (int): ID produk
            
        Returns:
            dict: Data produk
            None: Jika tidak ditemukan
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
            result = cursor.fetchone()
            return dict(result) if result else None
    
    def get_product_by_nama(self, nama: str) -> dict or None:
        """
        Ambil data produk berdasarkan nama (case-insensitive).
        
        Args:
            nama (str): Nama produk
            
        Returns:
            dict: Data produk jika ditemukan
            None: Jika tidak ditemukan
        """
        try:
            nama = str(nama).strip()
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM products WHERE LOWER(TRIM(nama)) = LOWER(TRIM(?))", (nama,))
                result = cursor.fetchone()
                
                if result:
                    logger.debug(f"Product found by nama: {nama}")
                    return dict(result)
                else:
                    logger.debug(f"Product not found by nama: {nama}")
                    return None
        except Exception as e:
            logger.error(f"Error getting product by nama '{nama}': {e}", exc_info=True)
            return None
    
    def get_all_products(self) -> list:
        """
        Ambil semua daftar produk.
        
        Returns:
            list: List of dict berisi semua produk
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products ORDER BY kode")
            results = cursor.fetchall()
            return [dict(row) for row in results]
    
    def get_next_product_code(self) -> str:
        """
        Generate kode produk otomatis dengan format 4 digit (0001, 0002, 0003, dst).
        
        Returns:
            str: Kode produk berikutnya dengan format 0001, 0002, dll
            
        Contoh:
            Jika sudah ada produk: 0001, 0002, 0003
            Maka akan return: "0004"
            
            Jika belum ada produk sama sekali:
            Maka akan return: "0001"
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get all products ordered by ID (DESC to get latest)
                cursor.execute("SELECT kode FROM products ORDER BY id DESC")
                results = cursor.fetchall()
                
                # Find the highest numeric code
                max_code = 0
                for row in results:
                    kode = row['kode'].strip()
                    # Check if kode is all digits
                    if kode.isdigit():
                        code_num = int(kode)
                        if code_num > max_code:
                            max_code = code_num
                
                next_code = max_code + 1
                
                # Format dengan leading zeros (4 digit)
                formatted_code = str(next_code).zfill(4)
                logger.info(f"Next product code generated: {formatted_code}")
                return formatted_code
                
        except Exception as e:
            logger.error(f"Error generating next product code: {e}", exc_info=True)
            return "0001"
    
    def update_product(self, kode: str, nama: str = None, harga: int = None, stok: int = None, satuan: str = None, foto_path: str = None) -> bool:
        """
        Update data produk. Hanya field yang diberikan yang akan diupdate.
        
        Args:
            kode (str): Kode produk (identifier)
            nama (str): Nama produk baru (opsional)
            harga (int): Harga baru (opsional)
            stok (int): Stok baru (opsional)
            satuan (str): Satuan produk baru (opsional)
            foto_path (str): Path to product photo (opsional)
            
        Returns:
            bool: True jika berhasil
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Build dynamic UPDATE query
                fields = []
                values = []
                
                if nama is not None:
                    fields.append("nama = ?")
                    values.append(nama)
                if harga is not None:
                    fields.append("harga = ?")
                    values.append(harga)
                if stok is not None:
                    fields.append("stok = ?")
                    values.append(stok)
                if satuan is not None:
                    fields.append("satuan = ?")
                    values.append(satuan)
                if foto_path is not None:
                    fields.append("foto_path = ?")
                    values.append(foto_path)
                
                if not fields:
                    logger.warning("No fields to update in product")
                    return False
                
                update_query = f"UPDATE products SET {', '.join(fields)} WHERE kode = ?"
                values.append(kode)
                
                cursor.execute(update_query, values)
                if cursor.rowcount == 0:
                    logger.warning(f"Product with code '{kode}' not found for update")
                    return False
                
                conn.commit()
                logger.info(f"Product updated: {kode}")
                return True
        except Exception as e:
            logger.error(f"Error updating product: {e}", exc_info=True)
            return False
    
    def delete_product(self, kode: str) -> bool:
        """
        Hapus produk dari database.
        
        Args:
            kode (str): Kode produk
            
        Returns:
            bool: True jika berhasil
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM products WHERE kode = ?", (kode,))
                if cursor.rowcount == 0:
                    logger.warning(f"Product with code '{kode}' not found for deletion")
                    return False
                conn.commit()
                logger.warning(f"Product deleted: {kode}")
                return True
        except Exception as e:
            logger.error(f"Error deleting product: {e}", exc_info=True)
            return False
    
    def reduce_stock(self, product_id: int, qty: int) -> bool:
        """
        Kurangi stok produk saat transaksi.
        Sangat penting untuk menjaga akurasi stok.
        Jika stok turun di bawah 5 unit, kirim notifikasi ke Telegram.
        
        Args:
            product_id (int): ID produk
            qty (int): Jumlah yang dikurangi
            
        Returns:
            bool: True jika berhasil
        """
        try:
            # Cek stok saat ini
            product = self.get_product_by_id(product_id)
            if not product:
                logger.error(f"Product ID {product_id} not found for stock reduction")
                return False
            
            if product['stok'] < qty:
                logger.warning(f"Insufficient stock for product {product_id}: available={product['stok']}, requested={qty}")
                return False
            
            # Update stok
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE products
                    SET stok = stok - ?
                    WHERE id = ?
                """, (qty, product_id))
                conn.commit()
            
            remaining_stok = product['stok'] - qty
            logger.info(f"Stock reduced: product_id={product_id}, qty={qty}, remaining={remaining_stok}")
            
            # Kirim notifikasi Telegram jika stok < 5
            if remaining_stok < 5 and self.telegram_bot:
                try:
                    product_name = product.get('nama', 'Unknown Product')
                    self.telegram_bot.send_low_stock_alert_sync(product_name, remaining_stok)
                except Exception as e:
                    logger.warning(f"Failed to send low stock alert: {e}")
            
            return True
        except Exception as e:
            logger.error(f"Error updating stock: {e}", exc_info=True)
            return False
    
    # ========================================================================
    # TRANSACTION OPERATIONS - CRUD operasi untuk transaksi
    # ========================================================================
    
    def add_transaction(self, total: int, bayar: int, kembalian: int, 
                       discount_percent: float = 0, discount_amount: int = 0,
                       tax_percent: float = 0, tax_amount: int = 0,
                       promotion_id: int = None, promotion_name: str = None) -> int or None:
        """
        Tambah transaksi baru dengan discount, tax, dan promotion info support.
        
        Args:
            total (int): Total belanja (setelah discount/tax)
            bayar (int): Jumlah pembayaran
            kembalian (int): Kembalian
            discount_percent (float): Diskon dalam persen (default: 0)
            discount_amount (int): Diskon dalam rupiah (default: 0)
            tax_percent (float): Pajak dalam persen (default: 0)
            tax_amount (int): Pajak dalam rupiah (default: 0)
            promotion_id (int, optional): ID promosi yang diterapkan
            promotion_name (str, optional): Nama promosi yang diterapkan
            
        Returns:
            int: ID transaksi jika berhasil
            None: Jika gagal
        """
        try:
            from datetime import datetime
            # Use local time instead of database DEFAULT CURRENT_TIMESTAMP (which uses UTC)
            tanggal_sekarang = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO transactions 
                    (tanggal, total, bayar, kembalian, discount_percent, discount_amount, tax_percent, tax_amount, promotion_id, promotion_name)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (tanggal_sekarang, total, bayar, kembalian, discount_percent, discount_amount, tax_percent, tax_amount, promotion_id, promotion_name))
                transaction_id = cursor.lastrowid
                conn.commit()
                logger.info(f"Transaction created: ID={transaction_id}, total=Rp{total:,}, discount={discount_percent}% (Rp{discount_amount:,}), promo={promotion_name}, tax={tax_percent}% (Rp{tax_amount:,})")
                return transaction_id
        except Exception as e:
            logger.error(f"Error creating transaction: {e}", exc_info=True)
            return None
    
    def add_transaction_item(self, transaction_id: int, product_id: int, 
                            qty: int, harga_satuan: int, subtotal: int,
                            promotion_id: int = None, promotion_name: str = None,
                            discount_percent: float = 0, discount_nominal: int = 0) -> bool:
        """
        Tambah item ke transaksi dengan informasi promo.
        
        Args:
            transaction_id (int): ID transaksi
            product_id (int): ID produk
            qty (int): Jumlah
            harga_satuan (int): Harga per unit
            subtotal (int): Subtotal (qty * harga_satuan)
            promotion_id (int, optional): ID promosi yang diterapkan
            promotion_name (str, optional): Nama promosi
            discount_percent (float, optional): Diskon persentase
            discount_nominal (int, optional): Diskon nominal
            
        Returns:
            bool: True jika berhasil
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO transaction_items 
                    (transaction_id, product_id, qty, harga_satuan, subtotal, 
                     promotion_id, promotion_name, discount_percent, discount_nominal)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (transaction_id, product_id, qty, harga_satuan, subtotal,
                      promotion_id, promotion_name, discount_percent, discount_nominal))
                conn.commit()
                logger.debug(f"Transaction item added: trans_id={transaction_id}, product_id={product_id}, qty={qty}, promo={promotion_name}")
                return True
        except Exception as e:
            logger.error(f"Error adding transaction item: {e}", exc_info=True)
            return False
    
    def get_transaction(self, transaction_id: int) -> dict or None:
        """
        Ambil data transaksi beserta itemnya.
        
        Args:
            transaction_id (int): ID transaksi
            
        Returns:
            dict: {transaction_data, items: [list of items]}
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Ambil header transaksi
                cursor.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,))
                trans = cursor.fetchone()
                
                if not trans:
                    return None
                
                # Ambil items transaksi
                cursor.execute("""
                    SELECT ti.*, p.nama FROM transaction_items ti
                    JOIN products p ON ti.product_id = p.id
                    WHERE ti.transaction_id = ?
                """, (transaction_id,))
                items = cursor.fetchall()
                
                return {
                    'transaction': dict(trans),
                    'items': [dict(item) for item in items]
                }
        except Exception as e:
            logger.error(f"Error fetching transaction: {e}", exc_info=True)
            return None
    
    def get_all_transactions(self) -> list:
        """
        Ambil semua transaksi.
        
        Returns:
            list: List of dict berisi semua transaksi
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM transactions 
                ORDER BY tanggal DESC
            """)
            results = cursor.fetchall()
            return [dict(row) for row in results]
    
    def get_transactions_by_date(self, date_str: str) -> list:
        """
        Ambil transaksi berdasarkan tanggal tertentu.
        
        Args:
            date_str (str): Format: 'YYYY-MM-DD'
            
        Returns:
            list: List of dict transaksi pada tanggal tersebut
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM transactions
                WHERE DATE(tanggal) = ?
                ORDER BY tanggal DESC
            """, (date_str,))
            results = cursor.fetchall()
            return [dict(row) for row in results]
    
    # ========================================================================
    # LAPORAN OPERATIONS - Query untuk laporan/analytics
    # ========================================================================
    
    def get_total_penjualan_hari_ini(self) -> int:
        """
        Hitung total penjualan hari ini.
        
        Returns:
            int: Total penjualan dalam Rupiah
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COALESCE(SUM(total), 0) as total
                FROM transactions
                WHERE DATE(tanggal) = DATE('now')
            """)
            result = cursor.fetchone()
            return result['total'] if result else 0
    
    def get_total_transaksi_hari_ini(self) -> int:
        """
        Hitung jumlah transaksi hari ini.
        
        Returns:
            int: Jumlah transaksi
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM transactions
                WHERE DATE(tanggal) = DATE('now')
            """)
            result = cursor.fetchone()
            return result['count'] if result else 0
    
    def get_produk_paling_laris(self, limit: int = 5) -> list:
        """
        Ambil produk dengan penjualan terbanyak.
        
        Args:
            limit (int): Jumlah top produk (default: 5)
            
        Returns:
            list: List of dict {product_name, total_qty, total_revenue}
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    p.nama,
                    SUM(ti.qty) as total_qty,
                    SUM(ti.subtotal) as total_revenue
                FROM transaction_items ti
                JOIN products p ON ti.product_id = p.id
                GROUP BY ti.product_id
                ORDER BY total_qty DESC
                LIMIT ?
            """, (limit,))
            results = cursor.fetchall()
            return [dict(row) for row in results]
    
    def get_laporan_harian(self, date_str: str = None) -> dict:
        """
        Ambil laporan lengkap untuk satu hari.
        
        Args:
            date_str (str): Format 'YYYY-MM-DD' (default: hari ini)
            
        Returns:
            dict: {total_penjualan, total_transaksi, produk_laris, transactions}
        """
        if date_str is None:
            from datetime import datetime
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Total penjualan
            cursor.execute("""
                SELECT COALESCE(SUM(total), 0) as total
                FROM transactions
                WHERE DATE(tanggal) = ?
            """, (date_str,))
            total_penjualan = cursor.fetchone()['total']
            
            # Total transaksi
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM transactions
                WHERE DATE(tanggal) = ?
            """, (date_str,))
            total_transaksi = cursor.fetchone()['count']
            
            # Produk laris
            cursor.execute("""
                SELECT 
                    p.nama,
                    SUM(ti.qty) as total_qty,
                    SUM(ti.subtotal) as total_revenue
                FROM transaction_items ti
                JOIN products p ON ti.product_id = p.id
                JOIN transactions t ON ti.transaction_id = t.id
                WHERE DATE(t.tanggal) = ?
                GROUP BY ti.product_id
                ORDER BY total_qty DESC
                LIMIT 5
            """, (date_str,))
            produk_laris = [dict(row) for row in cursor.fetchall()]
            
            # Semua transaksi
            cursor.execute("""
                SELECT * FROM transactions
                WHERE DATE(tanggal) = ?
                ORDER BY tanggal
            """, (date_str,))
            transactions = [dict(row) for row in cursor.fetchall()]
            
            return {
                'tanggal': date_str,
                'total_penjualan': total_penjualan,
                'total_transaksi': total_transaksi,
                'produk_laris': produk_laris,
                'transactions': transactions
            }
    
    # ========================================================================
    # UTILITY OPERATIONS - Helper functions
    # ========================================================================
    
    def clear_database(self):
        """
        Hapus semua data dari database (WARNING: destructive operation).
        Gunakan hanya untuk testing/reset.
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM transaction_items")
                cursor.execute("DELETE FROM transactions")
                cursor.execute("DELETE FROM products")
                conn.commit()
                logger.warning("Database cleared - all data deleted")
        except Exception as e:
            logger.error(f"Error clearing database: {e}", exc_info=True)
    
    def get_database_stats(self) -> dict:
        """
        Ambil statistik database (jumlah produk, transaksi, dll).
        
        Returns:
            dict: {total_products, total_transactions, total_items}
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) as count FROM products")
            total_products = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM transactions")
            total_transactions = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM transaction_items")
            total_items = cursor.fetchone()['count']
            
            return {
                'total_products': total_products,
                'total_transactions': total_transactions,
                'total_items': total_items,
                'db_path': self.db_path
            }
    
    # ========================================================================
    # USER OPERATIONS - CRUD untuk user login dan role-based access
    # ========================================================================
    
    def create_user(self, username: str, password: str, role: str = "cashier") -> bool:
        """
        Buat user baru dengan password di-hash.
        
        Args:
            username (str): Username unik
            password (str): Password plain text (akan di-hash)
            role (str): Role user ('admin' atau 'cashier', default: 'cashier')
            
        Returns:
            bool: True jika berhasil, False jika gagal
        """
        try:
            hashed_pw = self.hash_password(password)
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (username, hashed_password, role)
                    VALUES (?, ?, ?)
                """, (username, hashed_pw, role))
                conn.commit()
                logger.info(f"User created: username={username}, role={role}")
                return True
        except sqlite3.IntegrityError:
            logger.warning(f"Username '{username}' already exists")
            return False
        except Exception as e:
            logger.error(f"Error creating user: {e}", exc_info=True)
            return False
    
    def get_user_by_username(self, username: str) -> dict or None:
        """
        Ambil data user berdasarkan username.
        
        Args:
            username (str): Username
            
        Returns:
            dict: Data user {id, username, role, is_active}
            None: Jika user tidak ditemukan
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, role, is_active 
                FROM users 
                WHERE username = ?
            """, (username,))
            result = cursor.fetchone()
            return dict(result) if result else None
    
    def verify_user_login(self, username: str, password: str) -> dict or None:
        """
        Verifikasi login user (check username + password).
        
        Args:
            username (str): Username
            password (str): Password plain text
            
        Returns:
            dict: Data user jika login berhasil {id, username, role}
            None: Jika login gagal
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, hashed_password, role, is_active 
                FROM users 
                WHERE username = ?
            """, (username,))
            result = cursor.fetchone()
            
            if result is None:
                return None
            
            user = dict(result)
            
            # Check if active
            if not user['is_active']:
                logger.warning(f"User '{username}' is inactive")
                return None
            
            # Verify password
            if self.verify_password(password, user['hashed_password']):
                logger.info(f"User login successful: {username}")
                return {'id': user['id'], 'username': user['username'], 'role': user['role']}
            else:
                logger.warning(f"Invalid password for user '{username}'")
                return None
    
    def user_exists(self) -> bool:
        """
        Check apakah ada user di database.
        
        Returns:
            bool: True jika ada, False jika belum ada
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM users")
            count = cursor.fetchone()['count']
            return count > 0
    
    def get_all_users(self) -> list:
        """
        Ambil semua user dari database.
        
        Returns:
            list: List berisi semua user
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, username, role, is_active, created_at 
                    FROM users 
                    ORDER BY created_at
                """)
                users = [dict(row) for row in cursor.fetchall()]
                return users
        except Exception as e:
            logger.error(f"Error getting all users: {e}", exc_info=True)
            return []
    
    def update_user(self, user_id: int, **kwargs) -> bool:
        """
        Update data user (role, password, atau status aktif).
        
        Args:
            user_id (int): ID user yang akan diupdate
            **kwargs: Field yang akan diupdate {role, password, is_active}
                     - role: 'admin' atau 'cashier'
                     - password: password baru (plain text, akan di-hash)
                     - is_active: True/False
            
        Returns:
            bool: True jika berhasil, False jika gagal
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Build update query dynamically
                update_parts = []
                update_values = []
                
                if 'role' in kwargs:
                    update_parts.append("role = ?")
                    update_values.append(kwargs['role'])
                
                if 'password' in kwargs:
                    hashed_pw = self.hash_password(kwargs['password'])
                    update_parts.append("hashed_password = ?")
                    update_values.append(hashed_pw)
                
                if 'is_active' in kwargs:
                    update_parts.append("is_active = ?")
                    update_values.append(kwargs['is_active'])
                
                if not update_parts:
                    logger.warning("No fields to update")
                    return False
                
                update_values.append(user_id)
                query = f"UPDATE users SET {', '.join(update_parts)} WHERE id = ?"
                
                cursor.execute(query, update_values)
                conn.commit()
                logger.info(f"User {user_id} updated: {kwargs}")
                return True
        except Exception as e:
            logger.error(f"Error updating user: {e}", exc_info=True)
            return False
    
    def delete_user(self, user_id: int) -> bool:
        """
        Hapus user dari database (fisik delete).
        
        Args:
            user_id (int): ID user yang akan dihapus
            
        Returns:
            bool: True jika berhasil, False jika gagal
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
                conn.commit()
                logger.info(f"User {user_id} deleted")
                return True
        except Exception as e:
            logger.error(f"Error deleting user: {e}", exc_info=True)
            return False
    
    def deactivate_user(self, user_id: int) -> bool:
        """
        Nonaktifkan user (soft delete - tidak menghapus data).
        Lebih aman daripada delete karena tetap menyimpan history.
        
        Args:
            user_id (int): ID user yang akan dinonaktifkan
            
        Returns:
            bool: True jika berhasil, False jika gagal
        """
        return self.update_user(user_id, is_active=False)
    
    def activate_user(self, user_id: int) -> bool:
        """
        Aktifkan kembali user yang telah dinonaktifkan.
        
        Args:
            user_id (int): ID user yang akan diaktifkan
            
        Returns:
            bool: True jika berhasil, False jika gagal
        """
        return self.update_user(user_id, is_active=True)
    
    # ========================================================================
    # LOGIN ATTEMPT TRACKING & RATE LIMITING
    # ========================================================================
    
    def record_login_attempt(self, username: str, success: bool, ip_address: str = None) -> dict:
        """
        Record login attempt ke database untuk audit trail dan rate limiting.
        
        Args:
            username (str): Username yang dicoba login
            success (bool): True jika login berhasil, False jika gagal
            ip_address (str): IP address dari login attempt (optional)
            
        Returns:
            dict: Info attempt yang direcord
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO login_attempts (username, success, ip_address, attempted_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (username, success, ip_address))
                
                attempt_id = cursor.lastrowid
                conn.commit()
                
                log_type = "SUCCESS" if success else "FAILED"
                logger.info(f"Login attempt recorded: {username} - {log_type} (ID: {attempt_id})")
                
                return {
                    'id': attempt_id,
                    'username': username,
                    'success': success,
                    'ip_address': ip_address,
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"Error recording login attempt: {e}", exc_info=True)
            return {}
    
    def get_failed_attempts_count(self, username: str, minutes: int = 15) -> int:
        """
        Get jumlah failed login attempts dalam periode tertentu.
        
        Args:
            username (str): Username
            minutes (int): Time window dalam menit (default: 15)
            
        Returns:
            int: Jumlah failed attempts
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Use SQLite datetime functions untuk proper comparison
                cursor.execute(f"""
                    SELECT COUNT(*) as count FROM login_attempts
                    WHERE username = ? AND success = 0 
                    AND attempted_at > datetime('now', '-{minutes} minutes')
                """, (username,))
                
                result = cursor.fetchone()
                count = result['count'] if result else 0
                return count
        except Exception as e:
            logger.error(f"Error counting failed attempts: {e}", exc_info=True)
            return 0
    
    def check_login_lockout(self, username: str, max_attempts: int = 5, lockout_minutes: int = 3) -> dict:
        """
        Check apakah account dikunci karena terlalu banyak failed attempts.
        
        Args:
            username (str): Username
            max_attempts (int): Maximum allowed failed attempts (default: 5)
            lockout_minutes (int): Lockout duration dalam menit (default: 3)
            
        Returns:
            dict: {'is_locked': bool, 'remaining_minutes': int, 'failed_count': int}
        """
        try:
            failed_count = self.get_failed_attempts_count(username, lockout_minutes)
            
            if failed_count >= max_attempts:
                # Get timestamp of first failed attempt in window
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Use SQLite datetime functions for proper comparison
                    cursor.execute(f"""
                        SELECT MIN(attempted_at) as first_attempt FROM login_attempts
                        WHERE username = ? AND success = 0 
                        AND attempted_at > datetime('now', '-{lockout_minutes} minutes')
                    """, (username,))
                    
                    result = cursor.fetchone()
                    if result and result['first_attempt']:
                        first_attempt = datetime.fromisoformat(result['first_attempt'])
                        lockout_until = first_attempt + timedelta(minutes=lockout_minutes)
                        remaining = lockout_until - datetime.now()
                        remaining_minutes = max(0, remaining.total_seconds() / 60)
                        
                        return {
                            'is_locked': True,
                            'remaining_minutes': int(remaining_minutes),
                            'failed_count': failed_count,
                            'max_attempts': max_attempts
                        }
            
            return {
                'is_locked': False,
                'remaining_minutes': 0,
                'failed_count': failed_count,
                'max_attempts': max_attempts
            }
        except Exception as e:
            logger.error(f"Error checking login lockout: {e}", exc_info=True)
            return {'is_locked': False, 'remaining_minutes': 0, 'failed_count': 0, 'max_attempts': max_attempts}
    
    def reset_login_attempts(self, username: str) -> bool:
        """
        Reset failed attempts counter untuk user (biasanya setelah successful login).
        
        Args:
            username (str): Username
            
        Returns:
            bool: True jika berhasil
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Mark old failed attempts as cleared (no data loss)
                # atau bisa delete, tapi lebih aman untuk audit trail
                cursor.execute("""
                    DELETE FROM login_attempts
                    WHERE username = ? AND success = 0 AND attempted_at < datetime('now', '-1 day')
                """, (username,))
                
                conn.commit()
                logger.info(f"Login attempts reset for user: {username}")
                return True
        except Exception as e:
            logger.error(f"Error resetting login attempts: {e}", exc_info=True)
            return False
    
    def get_login_history(self, username: str, limit: int = 10) -> list:
        """
        Get login attempt history untuk user.
        
        Args:
            username (str): Username
            limit (int): Maksimal records (default: 10)
            
        Returns:
            list: List of login attempts dengan details
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, username, success, ip_address, attempted_at
                    FROM login_attempts
                    WHERE username = ?
                    ORDER BY attempted_at DESC
                    LIMIT ?
                """, (username, limit))
                
                rows = cursor.fetchall()
                history = [dict(row) for row in rows]
                return history
        except Exception as e:
            logger.error(f"Error getting login history: {e}", exc_info=True)
            return []
    
    def get_security_summary(self, username: str) -> dict:
        """
        Get security summary untuk user (untuk monitoring purposes).
        
        Args:
            username (str): Username
            
        Returns:
            dict: Security metrics
        """
        try:
            lockout_status = self.check_login_lockout(username)
            history = self.get_login_history(username, limit=5)
            
            # Count successful logins dalam 24 jam
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Use SQLite datetime functions for proper comparison
                cursor.execute("""
                    SELECT COUNT(*) as count FROM login_attempts
                    WHERE username = ? AND success = 1 
                    AND attempted_at > datetime('now', '-24 hours')
                """, (username,))
                
                successful_24h = cursor.fetchone()['count']
            
            return {
                'username': username,
                'lockout_status': lockout_status,
                'recent_attempts': history,
                'successful_logins_24h': successful_24h,
                'last_login': history[0]['attempted_at'] if history else None
            }
        except Exception as e:
            logger.error(f"Error getting security summary: {e}", exc_info=True)
            return {}
    
    # ========================================================================
    # INVOICE OPERATIONS - Invoice management
    # ========================================================================
    
    def create_invoice(self, invoice_number: str, total: int, bayar: int, 
                      kembalian: int, discount_percent: float = 0, 
                      discount_amount: int = 0, tax_percent: float = 0, 
                      tax_amount: int = 0, payment_type: str = 'lunas') -> int or None:
        """
        Create invoice header in database.
        
        Args:
            invoice_number (str): Unique invoice number
            total (int): Total amount
            bayar (int): Amount paid
            kembalian (int): Change
            discount_percent (float): Discount percentage
            discount_amount (int): Discount amount
            tax_percent (float): Tax percentage
            tax_amount (int): Tax amount
            payment_type (str): Type of payment ('lunas' or 'termin')
            
        Returns:
            int: Invoice ID jika berhasil, None jika gagal
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO invoices 
                    (invoice_number, total, bayar, kembalian, discount_percent, 
                     discount_amount, tax_percent, tax_amount, payment_type, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (invoice_number, total, bayar, kembalian, discount_percent, 
                      discount_amount, tax_percent, tax_amount, payment_type))
                conn.commit()
                invoice_id = cursor.lastrowid
                logger.info(f"Invoice created: {invoice_number} (ID: {invoice_id}, Type: {payment_type})")
                return invoice_id
        except sqlite3.IntegrityError:
            logger.warning(f"Invoice number '{invoice_number}' already exists")
            return None
        except Exception as e:
            logger.error(f"Error creating invoice: {e}", exc_info=True)
            return None
    
    def add_invoice_item(self, invoice_id: int, nama: str, qty: int, 
                        harga_satuan: int, subtotal: int) -> bool:
        """
        Add item to invoice.
        
        Args:
            invoice_id (int): Invoice ID
            nama (str): Product name
            qty (int): Quantity
            harga_satuan (int): Price per unit
            subtotal (int): Subtotal (qty * harga_satuan)
            
        Returns:
            bool: True jika berhasil, False jika gagal
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO invoice_items 
                    (invoice_id, nama, qty, harga_satuan, subtotal)
                    VALUES (?, ?, ?, ?, ?)
                """, (invoice_id, nama, qty, harga_satuan, subtotal))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error adding invoice item: {e}", exc_info=True)
            return False
    
    def get_all_invoices(self, limit: int = 50, offset: int = 0) -> list:
        """
        Get semua invoices (most recent first).
        
        Args:
            limit (int): Max invoices to retrieve
            offset (int): Offset untuk pagination
            
        Returns:
            list: List of invoice data
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM invoices 
                    ORDER BY created_at DESC 
                    LIMIT ? OFFSET ?
                """, (limit, offset))
                invoices = [dict(row) for row in cursor.fetchall()]
                return invoices
        except Exception as e:
            logger.error(f"Error getting all invoices: {e}")
            return []
    
    def get_invoice_detail(self, invoice_id: int) -> dict or None:
        """
        Get invoice detail dengan items.
        
        Args:
            invoice_id (int): Invoice ID
            
        Returns:
            dict: Invoice detail {invoice, items}, atau None jika tidak ditemukan
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get invoice header
                cursor.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
                invoice_row = cursor.fetchone()
                
                if not invoice_row:
                    logger.warning(f"Invoice {invoice_id} not found")
                    return None
                
                invoice_data = dict(invoice_row)
                
                # Get invoice items
                cursor.execute("SELECT * FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
                items = [dict(row) for row in cursor.fetchall()]
                
                return {
                    'invoice': invoice_data,
                    'items': items
                }
        except Exception as e:
            logger.error(f"Error getting invoice detail {invoice_id}: {e}")
            return None
    
    def get_invoice_by_number(self, invoice_number: str) -> dict or None:
        """
        Get invoice by invoice number.
        
        Args:
            invoice_number (str): Invoice number
            
        Returns:
            dict: Invoice detail, atau None
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get invoice header
                cursor.execute("SELECT * FROM invoices WHERE invoice_number = ?", (invoice_number,))
                invoice_row = cursor.fetchone()
                
                if not invoice_row:
                    logger.warning(f"Invoice {invoice_number} not found")
                    return None
                
                invoice_data = dict(invoice_row)
                invoice_id = invoice_data['id']
                
                # Get invoice items
                cursor.execute("SELECT * FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
                items = [dict(row) for row in cursor.fetchall()]
                
                return {
                    'invoice': invoice_data,
                    'items': items
                }
        except Exception as e:
            logger.error(f"Error getting invoice by number {invoice_number}: {e}")
            return None
    
    def get_invoices_by_date(self, date_str: str) -> list:
        """
        Get invoices yang dibuat pada tanggal tertentu.
        
        Args:
            date_str (str): Format YYYY-MM-DD
            
        Returns:
            list: List of invoices
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT * FROM invoices 
                    WHERE DATE(created_at) = ?
                    ORDER BY created_at DESC
                """
                
                cursor.execute(query, (date_str,))
                invoices = [dict(row) for row in cursor.fetchall()]
                
                return invoices
        except Exception as e:
            logger.error(f"Error getting invoices by date {date_str}: {e}")
            return []
    
    def get_invoices_count(self) -> int:
        """
        Get total count of invoices.
        
        Returns:
            int: Total invoices count
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) as count FROM invoices")
                result = cursor.fetchone()
                return result['count'] if result else 0
        except Exception as e:
            logger.error(f"Error getting invoices count: {e}")
            return 0
    
    # ========================================================================
    # TERMIN PAYMENT OPERATIONS - Cicilan pembayaran untuk invoice termin
    # ========================================================================
    
    def add_termin_payment(self, invoice_id: int, payment_amount: int, 
                          payment_date: str, due_date: str, 
                          transaction_id: int = None, notes: str = None) -> int or None:
        """
        Tambah pembayaran termin untuk invoice.
        
        Args:
            invoice_id (int): ID invoice
            payment_amount (int): Jumlah pembayaran dalam Rp
            payment_date (str): Tanggal pembayaran (YYYY-MM-DD)
            due_date (str): Tanggal jatuh tempo (YYYY-MM-DD)
            transaction_id (int, optional): ID transaksi pembayaran
            notes (str, optional): Catatan pembayaran
            
        Returns:
            int: ID termin payment yang dibuat, None jika gagal
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO termin_payments 
                    (invoice_id, transaction_id, payment_amount, payment_date, due_date, status, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (invoice_id, transaction_id, payment_amount, payment_date, due_date, 'pending', notes))
                conn.commit()
                termin_id = cursor.lastrowid
                logger.info(f"Termin payment added: invoice_id={invoice_id}, amount={payment_amount}, termin_id={termin_id}")
                return termin_id
        except Exception as e:
            logger.error(f"Error adding termin payment: {e}", exc_info=True)
            return None
    
    def get_termin_payments_by_invoice(self, invoice_id: int) -> list:
        """
        Ambil semua cicilan pembayaran untuk invoice tertentu.
        
        Args:
            invoice_id (int): ID invoice
            
        Returns:
            list: List of termin payments
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM termin_payments
                    WHERE invoice_id = ?
                    ORDER BY due_date
                """, (invoice_id,))
                results = cursor.fetchall()
                return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error getting termin payments for invoice {invoice_id}: {e}")
            return []
    
    def update_termin_payment_status(self, termin_id: int, status: str, notes: str = None) -> bool:
        """
        Update status pembayaran termin (pending/completed/overdue).
        
        Args:
            termin_id (int): ID termin payment
            status (str): Status baru (pending/completed/overdue)
            notes (str, optional): Catatan update
            
        Returns:
            bool: True jika berhasil
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE termin_payments
                    SET status = ?, notes = ?
                    WHERE id = ?
                """, (status, notes, termin_id))
                conn.commit()
                logger.info(f"Termin payment status updated: termin_id={termin_id}, status={status}")
                return True
        except Exception as e:
            logger.error(f"Error updating termin payment status: {e}", exc_info=True)
            return False
    
    def get_unpaid_termin_invoices(self) -> list:
        """
        Ambil semua invoice termin yang belum lunas dengan info DP.
        
        Returns:
            list: List of unpaid termin invoices dengan sisa cicilan (total - DP)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        i.id,
                        i.invoice_number,
                        i.total,
                        i.customer_name,
                        i.due_date,
                        COALESCE(i.bayar, 0) as dp_amount,
                        COALESCE(SUM(tp.payment_amount), 0) as cicilan_terbayar,
                        (i.total - COALESCE(i.bayar, 0)) as total_cicilan,
                        ((i.total - COALESCE(i.bayar, 0)) - COALESCE(SUM(tp.payment_amount), 0)) as sisa_pembayaran
                    FROM invoices i
                    LEFT JOIN termin_payments tp ON i.id = tp.invoice_id 
                        AND tp.status = 'completed'
                    WHERE i.payment_type = 'termin' 
                        AND i.payment_status != 'completed'
                    GROUP BY i.id
                    HAVING sisa_pembayaran > 0
                    ORDER BY i.due_date
                """)
                results = cursor.fetchall()
                return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error getting unpaid termin invoices: {e}")
            return []
    
    def calculate_total_paid_termin(self, invoice_id: int) -> int:
        """
        Hitung total yang sudah dibayar untuk invoice termin (hanya completed payments).
        
        Args:
            invoice_id (int): ID invoice
            
        Returns:
            int: Total yang sudah dibayar (completed payments only)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COALESCE(SUM(payment_amount), 0) as total_paid
                    FROM termin_payments
                    WHERE invoice_id = ? AND status = 'completed'
                """, (invoice_id,))
                result = cursor.fetchone()
                return result['total_paid'] if result else 0
        except Exception as e:
            logger.error(f"Error calculating total paid for invoice {invoice_id}: {e}")
            return 0
    
    def get_overdue_termin_payments(self) -> list:
        """
        Ambil pembayaran termin yang jatuh tempo/overdue.
        
        Returns:
            list: List of overdue termin payments
        """
        try:
            from datetime import datetime, date
            today = date.today().isoformat()
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        tp.*,
                        i.invoice_number,
                        i.customer_name
                    FROM termin_payments tp
                    JOIN invoices i ON tp.invoice_id = i.id
                    WHERE tp.status IN ('pending')
                        AND tp.due_date < ?
                    ORDER BY tp.due_date
                """, (today,))
                results = cursor.fetchall()
                return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error getting overdue termin payments: {e}")
            return []
    
    def get_upcoming_termin_payments(self, days_ahead: int = 7) -> list:
        """
        Ambil pembayaran termin yang akan jatuh tempo dalam N hari ke depan.
        
        Args:
            days_ahead (int): Jumlah hari ke depan untuk pengecekan (default: 7)
        
        Returns:
            list: List of upcoming termin payments
        """
        try:
            from datetime import datetime, date, timedelta
            today = date.today().isoformat()
            upcoming_date = (date.today() + timedelta(days=days_ahead)).isoformat()
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        tp.*,
                        i.invoice_number,
                        i.customer_name
                    FROM termin_payments tp
                    JOIN invoices i ON tp.invoice_id = i.id
                    WHERE tp.status IN ('pending')
                        AND tp.due_date >= ?
                        AND tp.due_date <= ?
                    ORDER BY tp.due_date
                """, (today, upcoming_date))
                results = cursor.fetchall()
                return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error getting upcoming termin payments: {e}")
            return []
    
    def get_all_pending_termin_payments(self) -> list:
        """
        Ambil SEMUA pembayaran termin yang masih pending (overdue + upcoming).
        Untuk konsistensi display di laporan dan detail page.
        
        Returns:
            list: List of all pending termin payments
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        tp.*,
                        i.invoice_number,
                        i.customer_name,
                        i.total as invoice_total,
                        i.bayar as dp_amount
                    FROM termin_payments tp
                    JOIN invoices i ON tp.invoice_id = i.id
                    WHERE tp.status IN ('pending')
                    ORDER BY tp.due_date
                """)
                results = cursor.fetchall()
                return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error getting all pending termin payments: {e}")
            return []
    
    # ========================================================================
    # CASHFLOW OPERATIONS - Income dan Expense untuk Pembukuan
    # ========================================================================
    
    def add_cashflow(self, cf_type: str, amount: int, description: str,
                    related_transaction_id: int = None) -> int:
        """
        Tambah entry cashflow (income atau expense).
        
        Args:
            cf_type (str): 'income' atau 'expense'
            amount (int): Jumlah dalam Rupiah
            description (str): Deskripsi
            related_transaction_id (int): ID transaksi terkait (optional)
            
        Returns:
            int: Cashflow ID jika berhasil
            None: Jika gagal
        """
        if cf_type not in ['income', 'expense']:
            logger.error(f"Invalid cashflow type: {cf_type}")
            return None
        
        if amount <= 0:
            logger.error(f"Invalid amount: {amount}")
            return None
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO cashflow (type, amount, description, related_transaction_id)
                    VALUES (?, ?, ?, ?)
                """, (cf_type, amount, description, related_transaction_id))
                cf_id = cursor.lastrowid
                conn.commit()
                logger.info(f"Cashflow added: type={cf_type}, amount={amount}, id={cf_id}")
                return cf_id
        except Exception as e:
            logger.error(f"Error adding cashflow: {e}", exc_info=True)
            return None
    
    def get_total_cashflow(self, cf_type: str, start_date = None, end_date = None) -> int:
        """
        Get total income atau expense untuk range tanggal.
        
        Args:
            cf_type (str): 'income' atau 'expense'
            start_date: Start date (format: date object atau YYYY-MM-DD string)
            end_date: End date (format: date object atau YYYY-MM-DD string)
            
        Returns:
            int: Total amount dalam Rupiah
        """
        from datetime import date
        
        # Default date range: current month
        if start_date is None:
            today = date.today()
            start_date = date(today.year, today.month, 1)
        
        if end_date is None:
            end_date = date.today()
        
        # Convert to string if date object
        if hasattr(start_date, 'isoformat'):
            start_date = start_date.isoformat()
        if hasattr(end_date, 'isoformat'):
            end_date = end_date.isoformat()
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0) as total
                    FROM cashflow
                    WHERE type = ?
                        AND DATE(created_at) >= ?
                        AND DATE(created_at) <= ?
                """, (cf_type, start_date, end_date))
                
                result = cursor.fetchone()
                return result['total'] if result else 0
        except Exception as e:
            logger.error(f"Error getting total cashflow: {e}", exc_info=True)
            return 0
    
    def get_cashflow_history(self, limit: int = 100, start_date = None, end_date = None) -> list:
        """
        Get history of cashflow entries.
        
        Args:
            limit (int): Maximum entries to retrieve
            start_date: Start date filter (optional)
            end_date: End date filter (optional)
            
        Returns:
            list: List of cashflow entries as dict
        """
        from datetime import date
        
        # Default date range: last 1 year
        if end_date is None:
            end_date = date.today()
        
        if start_date is None:
            from datetime import timedelta
            start_date = end_date - timedelta(days=365)
        
        # Convert to string if date object
        if hasattr(start_date, 'isoformat'):
            start_date = start_date.isoformat()
        if hasattr(end_date, 'isoformat'):
            end_date = end_date.isoformat()
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, type, amount, description, related_transaction_id, created_at
                    FROM cashflow
                    WHERE DATE(created_at) >= ?
                        AND DATE(created_at) <= ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (start_date, end_date, limit))
                
                results = cursor.fetchall()
                return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error getting cashflow history: {e}", exc_info=True)
            return []
    
    def delete_cashflow(self, cashflow_id: int) -> bool:
        """
        Delete cashflow entry (untuk undo/koreksi).
        
        Args:
            cashflow_id (int): ID cashflow yang akan dihapus
            
        Returns:
            bool: True jika berhasil
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM cashflow WHERE id = ?", (cashflow_id,))
                conn.commit()
                if cursor.rowcount > 0:
                    logger.info(f"Cashflow entry {cashflow_id} deleted")
                    return True
                return False
        except Exception as e:
            logger.error(f"Error deleting cashflow: {e}", exc_info=True)
            return False
    
    def get_daily_cashflow_stats(self, num_days: int = 7) -> list:
        """
        Get daily cashflow stats untuk last n days.
        
        Args:
            num_days (int): Number of days to retrieve
            
        Returns:
            list: List of daily stats with format:
                [
                    {
                        'date': YYYY-MM-DD,
                        'total_income': int,
                        'total_expense': int,
                        'profit': int
                    },
                    ...
                ]
        """
        from datetime import date, timedelta
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        DATE(created_at) as date,
                        COALESCE(SUM(CASE WHEN type='income' THEN amount ELSE 0 END), 0) as total_income,
                        COALESCE(SUM(CASE WHEN type='expense' THEN amount ELSE 0 END), 0) as total_expense
                    FROM cashflow
                    WHERE DATE(created_at) >= DATE('now', '-' || ? || ' days')
                    GROUP BY DATE(created_at)
                    ORDER BY date DESC
                """, (num_days,))
                
                results = cursor.fetchall()
                daily_stats = []
                for row in results:
                    data = dict(row)
                    data['profit'] = data['total_income'] - data['total_expense']
                    daily_stats.append(data)
                
                return daily_stats
        except Exception as e:
            logger.error(f"Error getting daily cashflow stats: {e}", exc_info=True)
            return []
    
    def get_cashflow_stats_for_range(self, start_date, end_date) -> list:
        """
        Get daily cashflow stats untuk range tanggal tertentu.
        
        Args:
            start_date: Start date (date object atau string YYYY-MM-DD)
            end_date: End date (date object atau string YYYY-MM-DD)
            
        Returns:
            list: List of daily stats
        """
        # Convert to string if date object
        if hasattr(start_date, 'isoformat'):
            start_date = start_date.isoformat()
        if hasattr(end_date, 'isoformat'):
            end_date = end_date.isoformat()
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        DATE(created_at) as date,
                        COALESCE(SUM(CASE WHEN type='income' THEN amount ELSE 0 END), 0) as total_income,
                        COALESCE(SUM(CASE WHEN type='expense' THEN amount ELSE 0 END), 0) as total_expense
                    FROM cashflow
                    WHERE DATE(created_at) >= ?
                        AND DATE(created_at) <= ?
                    GROUP BY DATE(created_at)
                    ORDER BY date DESC
                """, (start_date, end_date))
                
                results = cursor.fetchall()
                daily_stats = []
                for row in results:
                    data = dict(row)
                    data['profit'] = data['total_income'] - data['total_expense']
                    daily_stats.append(data)
                
                return daily_stats
        except Exception as e:
            logger.error(f"Error getting cashflow stats for range: {e}", exc_info=True)
            return []
    
    # ========================================================================
    # PROMOTION OPERATIONS - Manajemen promosi dan diskon
    # ========================================================================
    
    def add_promotion(self, nama_promosi: str, tipe_diskon: str, nilai_diskon: int, 
                     min_qty: float, satuan: str, tanggal_mulai: str, tanggal_selesai: str, 
                     deskripsi: str = None, berlaku_kelipatan: bool = False) -> tuple:
        """
        Tambah promosi baru.
        
        Args:
            nama_promosi: Nama promosi
            tipe_diskon: 'persentase' atau 'nominal'
            nilai_diskon: Nilai diskon (% atau Rp)
            min_qty: Minimum quantity untuk trigger promosi
            satuan: Satuan (kg, pcs, dll)
            tanggal_mulai: Tanggal mulai (YYYY-MM-DD)
            tanggal_selesai: Tanggal selesai (YYYY-MM-DD)
            deskripsi: Deskripsi promosi (optional)
            berlaku_kelipatan: Apakah diskon berlaku per kelipatan min_qty (default False)
            
        Returns:
            tuple: (success, message, promotion_id)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO promotions 
                    (nama_promosi, tipe_diskon, nilai_diskon, min_qty, satuan, 
                     tanggal_mulai, tanggal_selesai, deskripsi, berlaku_kelipatan, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'aktif')
                """, (nama_promosi, tipe_diskon, nilai_diskon, min_qty, satuan, 
                      tanggal_mulai, tanggal_selesai, deskripsi, berlaku_kelipatan))
                
                promotion_id = cursor.lastrowid
                logger.info(f"Promotion added: {nama_promosi} (ID: {promotion_id})")
                return True, "Promosi berhasil ditambahkan", promotion_id
        except Exception as e:
            logger.error(f"Error adding promotion: {e}", exc_info=True)
            return False, f"Error: {str(e)}", None
    
    def get_all_promotions(self, status: str = None) -> list:
        """
        Get semua promosi.
        
        Args:
            status: Filter by status ('aktif', 'nonaktif', atau None untuk semua)
            
        Returns:
            list: List of promotions
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if status:
                    cursor.execute("SELECT * FROM promotions WHERE status = ? ORDER BY id DESC", (status,))
                else:
                    cursor.execute("SELECT * FROM promotions ORDER BY id DESC")
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting promotions: {e}", exc_info=True)
            return []
    
    def get_active_promotions(self, current_date: str = None) -> list:
        """
        Get promosi yang aktif berdasarkan tanggal.
        
        Args:
            current_date: Current date (YYYY-MM-DD), default ke hari ini
            
        Returns:
            list: List of active promotions
        """
        if not current_date:
            current_date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM promotions 
                    WHERE status = 'aktif'
                      AND tanggal_mulai <= ?
                      AND tanggal_selesai >= ?
                    ORDER BY id ASC
                """, (current_date, current_date))
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting active promotions: {e}", exc_info=True)
            return []
    
    def update_promotion(self, promotion_id: int, **kwargs) -> tuple:
        """
        Update promosi.
        
        Args:
            promotion_id: ID promosi
            **kwargs: Field yang akan diupdate (nama_promosi, nilai_diskon, berlaku_kelipatan, dll)
            
        Returns:
            tuple: (success, message)
        """
        allowed_fields = ['nama_promosi', 'tipe_diskon', 'nilai_diskon', 'min_qty', 
                         'satuan', 'tanggal_mulai', 'tanggal_selesai', 'deskripsi', 'status', 'berlaku_kelipatan']
        
        update_fields = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not update_fields:
            return False, "Tidak ada field untuk diupdate"
        
        update_fields['updated_at'] = datetime.now().isoformat()
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                set_clause = ", ".join([f"{k} = ?" for k in update_fields.keys()])
                values = list(update_fields.values()) + [promotion_id]
                
                cursor.execute(f"UPDATE promotions SET {set_clause} WHERE id = ?", values)
                logger.info(f"Promotion updated: ID {promotion_id}")
                return True, "Promosi berhasil diupdate"
        except Exception as e:
            logger.error(f"Error updating promotion: {e}", exc_info=True)
            return False, f"Error: {str(e)}"
    
    def delete_promotion(self, promotion_id: int) -> tuple:
        """
        Delete promosi.
        
        Args:
            promotion_id: ID promosi
            
        Returns:
            tuple: (success, message)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM promotions WHERE id = ?", (promotion_id,))
                logger.info(f"Promotion deleted: ID {promotion_id}")
                return True, "Promosi berhasil dihapus"
        except Exception as e:
            logger.error(f"Error deleting promotion: {e}", exc_info=True)
            return False, f"Error: {str(e)}"
    
    def get_promotion_by_id(self, promotion_id: int) -> dict:
        """Get promosi berdasarkan ID."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM promotions WHERE id = ?", (promotion_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting promotion: {e}", exc_info=True)
            return None


# ============================================================================
# TESTING - Jalankan jika file dijalankan standalone
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("POS DATABASE SYSTEM - Testing")
    print("=" * 70)
    
    # Inisialisasi database
    db = DatabaseManager()
    print("\n📊 Database Stats:")
    print(db.get_database_stats())
