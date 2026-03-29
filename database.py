# ============================================================================
# DATABASE.PY - SQLite Database Manager untuk POS System
# ============================================================================
# Fungsi: Mengelola semua operasi database (create, read, update, delete)
# Author: POS Team
# Version: 1.0
# ============================================================================

import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

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
    
    def __init__(self, db_name: str = "kasir_pos.db"):
        """
        Inisialisasi DatabaseManager dan buat database jika belum ada.
        
        Args:
            db_name (str): Nama file database (default: kasir_pos.db)
        """
        # Tentukan path database di folder yang sama dengan script
        self.db_path = db_name
        
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
            print(f"❌ Database Error: {e}")
            raise
        finally:
            # Tutup koneksi
            if connection:
                connection.close()
    
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
            # TABEL 2: TRANSACTIONS - Header transaksi penjualan
            # ================================================================
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tanggal DATETIME DEFAULT CURRENT_TIMESTAMP,
                    total INTEGER NOT NULL,
                    bayar INTEGER NOT NULL,
                    kembalian INTEGER NOT NULL
                )
            """)
            
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
            
            conn.commit()
            print("✅ Database tabel berhasil diinisialisasi")
    
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
                print(f"✅ Produk '{nama}' berhasil ditambahkan")
                return True
        except sqlite3.IntegrityError:
            print(f"❌ Kode produk '{kode}' sudah ada. Gunakan kode yang berbeda.")
            return False
        except Exception as e:
            print(f"❌ Error saat menambah produk: {e}")
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
                    print("⚠️ Tidak ada field yang diupdate")
                    return False
                
                update_query = f"UPDATE products SET {', '.join(fields)} WHERE kode = ?"
                values.append(kode)
                
                cursor.execute(update_query, values)
                if cursor.rowcount == 0:
                    print(f"❌ Produk dengan kode '{kode}' tidak ditemukan")
                    return False
                
                conn.commit()
                print(f"✅ Produk '{kode}' berhasil diupdate")
                return True
        except Exception as e:
            print(f"❌ Error saat update produk: {e}")
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
                    print(f"❌ Produk '{kode}' tidak ditemukan")
                    return False
                conn.commit()
                print(f"✅ Produk '{kode}' berhasil dihapus")
                return True
        except Exception as e:
            print(f"❌ Error saat hapus produk: {e}")
            return False
    
    def reduce_stock(self, product_id: int, qty: int) -> bool:
        """
        Kurangi stok produk saat transaksi.
        Sangat penting untuk menjaga akurasi stok.
        
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
                print(f"❌ Produk ID {product_id} tidak ditemukan")
                return False
            
            if product['stok'] < qty:
                print(f"❌ Stok tidak cukup (stok: {product['stok']}, diminta: {qty})")
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
            
            return True
        except Exception as e:
            print(f"❌ Error saat update stok: {e}")
            return False
    
    # ========================================================================
    # TRANSACTION OPERATIONS - CRUD operasi untuk transaksi
    # ========================================================================
    
    def add_transaction(self, total: int, bayar: int, kembalian: int) -> int or None:
        """
        Tambah transaksi baru.
        
        Args:
            total (int): Total belanja
            bayar (int): Jumlah pembayaran
            kembalian (int): Kembalian
            
        Returns:
            int: ID transaksi jika berhasil
            None: Jika gagal
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO transactions (total, bayar, kembalian)
                    VALUES (?, ?, ?)
                """, (total, bayar, kembalian))
                transaction_id = cursor.lastrowid
                conn.commit()
                return transaction_id
        except Exception as e:
            print(f"❌ Error saat menambah transaksi: {e}")
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
                return True
        except Exception as e:
            print(f"❌ Error saat menambah item transaksi: {e}")
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
            print(f"❌ Error saat ambil transaksi: {e}")
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
                print("⚠️ Database berhasil dikosongkan")
        except Exception as e:
            print(f"❌ Error saat clear database: {e}")
    
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
