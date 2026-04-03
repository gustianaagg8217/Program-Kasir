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
from datetime import datetime
from contextlib import contextmanager
from logger_config import get_logger
from backup_manager import BackupManager

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
    # PASSWORD HASHING - Secure password management dengan hashlib
    # ========================================================================
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password menggunakan SHA256.
        
        Args:
            password (str): Password plain text
            
        Returns:
            str: Hashed password
        """
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """
        Verifikasi password dengan hash.
        
        Args:
            password (str): Password plain text
            hashed_password (str): Password yang di-hash
            
        Returns:
            bool: True jika cocok, False jika tidak
        """
        return DatabaseManager.hash_password(password) == hashed_password
    
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
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
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
    
    def add_product(self, kode: str, nama: str, harga: int, stok: int) -> bool:
        """
        Tambah produk baru ke database.
        
        Args:
            kode (str): Kode produk unik (contoh: 'PROD001')
            nama (str): Nama produk
            harga (int): Harga dalam Rupiah
            stok (int): Jumlah stok awal
            
        Returns:
            bool: True jika berhasil, False jika gagal
            
        Raises:
            sqlite3.IntegrityError: Jika kode produk sudah ada (duplicate)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO products (kode, nama, harga, stok)
                    VALUES (?, ?, ?, ?)
                """, (kode, nama, harga, stok))
                conn.commit()
                logger.info(f"Product added: {kode} = {nama}")
                return True
        except sqlite3.IntegrityError:
            logger.warning(f"Product code '{kode}' already exists")
            return False
        except Exception as e:
            logger.error(f"Error adding product: {e}", exc_info=True)
            return False
    
    def get_product_by_kode(self, kode: str) -> dict or None:
        """
        Ambil data produk berdasarkan kode.
        
        Args:
            kode (str): Kode produk
            
        Returns:
            dict: Data produk {id, kode, nama, harga, stok}
            None: Jika produk tidak ditemukan
            
        Contoh return:
            {'id': 1, 'kode': 'PROD001', 'nama': 'Mie Goreng', 'harga': 15000, 'stok': 100}
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products WHERE kode = ?", (kode,))
            result = cursor.fetchone()
            return dict(result) if result else None
    
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
    
    def update_product(self, kode: str, nama: str = None, harga: int = None, stok: int = None) -> bool:
        """
        Update data produk. Hanya field yang diberikan yang akan diupdate.
        
        Args:
            kode (str): Kode produk (identifier)
            nama (str): Nama produk baru (opsional)
            harga (int): Harga baru (opsional)
            stok (int): Stok baru (opsional)
            
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
                       tax_percent: float = 0, tax_amount: int = 0) -> int or None:
        """
        Tambah transaksi baru dengan discount dan tax support.
        
        Args:
            total (int): Total belanja (setelah discount/tax)
            bayar (int): Jumlah pembayaran
            kembalian (int): Kembalian
            discount_percent (float): Diskon dalam persen (default: 0)
            discount_amount (int): Diskon dalam rupiah (default: 0)
            tax_percent (float): Pajak dalam persen (default: 0)
            tax_amount (int): Pajak dalam rupiah (default: 0)
            
        Returns:
            int: ID transaksi jika berhasil
            None: Jika gagal
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO transactions 
                    (total, bayar, kembalian, discount_percent, discount_amount, tax_percent, tax_amount)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (total, bayar, kembalian, discount_percent, discount_amount, tax_percent, tax_amount))
                transaction_id = cursor.lastrowid
                conn.commit()
                logger.info(f"Transaction created: ID={transaction_id}, total=Rp{total:,}, discount={discount_percent}% (Rp{discount_amount:,}), tax={tax_percent}% (Rp{tax_amount:,})")
                return transaction_id
        except Exception as e:
            logger.error(f"Error creating transaction: {e}", exc_info=True)
            return None
    
    def add_transaction_item(self, transaction_id: int, product_id: int, 
                            qty: int, harga_satuan: int, subtotal: int) -> bool:
        """
        Tambah item ke transaksi.
        
        Args:
            transaction_id (int): ID transaksi
            product_id (int): ID produk
            qty (int): Jumlah
            harga_satuan (int): Harga per unit
            subtotal (int): Subtotal (qty * harga_satuan)
            
        Returns:
            bool: True jika berhasil
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO transaction_items 
                    (transaction_id, product_id, qty, harga_satuan, subtotal)
                    VALUES (?, ?, ?, ?, ?)
                """, (transaction_id, product_id, qty, harga_satuan, subtotal))
                conn.commit()
                logger.debug(f"Transaction item added: trans_id={transaction_id}, product_id={product_id}, qty={qty}")
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
