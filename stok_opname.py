# ============================================================================
# STOK_OPNAME.PY - Inventory Count / Stock Opname Management
# ============================================================================
# Fungsi: Mengelola proses stok opname (physical inventory count)
# Fitur: Create session, input physical stock, compare with system, generate report
# ============================================================================

import sqlite3
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
from database import DatabaseManager
from logger_config import get_logger

logger = get_logger(__name__)

# ============================================================================
# DATACLASS - Stok Opname Models
# ============================================================================

@dataclass
class StokOpnameSession:
    """Model untuk stok opname session."""
    id: int
    tanggal: str
    keterangan: str
    status: str  # 'active', 'completed', 'cancelled'
    created_at: str
    created_by: str
    completed_at: Optional[str] = None

@dataclass
class StokOpnameItem:
    """Model untuk item dalam stok opname."""
    id: int
    session_id: int
    product_id: int
    kode_produk: str
    nama_produk: str
    stok_sistem: int
    stok_fisik: int
    selisih: int
    status: str  # 'pending', 'counted', 'verified'
    catatan: str
    satuan: str

@dataclass
class StokOpnameReport:
    """Model untuk laporan stok opname."""
    session_id: int
    tanggal: str
    total_items: int
    items_counted: int
    total_selisih: int
    total_selisih_qty: int
    items_details: List[Dict]

# ============================================================================
# STOK OPNAME SERVICE - Business logic untuk stok opname
# ============================================================================

class StokOpnameService:
    """Service untuk mengelola proses stok opname."""
    
    def __init__(self, db: DatabaseManager):
        """
        Inisialisasi StokOpnameService.
        
        Args:
            db (DatabaseManager): Database manager instance
        """
        self.db = db
        self._init_stok_opname_tables()
    
    def _init_stok_opname_tables(self):
        """Buat tabel stok opname jika belum ada."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabel: stok_opname_sessions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stok_opname_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tanggal DATE NOT NULL,
                    keterangan TEXT,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT NOT NULL,
                    completed_at TIMESTAMP
                )
            """)
            
            # Tabel: stok_opname_items
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stok_opname_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    stok_sistem INTEGER NOT NULL,
                    stok_fisik INTEGER DEFAULT 0,
                    selisih INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    catatan TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES stok_opname_sessions(id),
                    FOREIGN KEY (product_id) REFERENCES products(id)
                )
            """)
            
            logger.info("Stok opname tables initialized")
    
    # ====================================================================
    # SESSION MANAGEMENT
    # ====================================================================
    
    def create_session(self, tanggal: str, keterangan: str, created_by: str) -> int:
        """
        Buat session stok opname baru.
        
        Args:
            tanggal (str): Tanggal opname (format: YYYY-MM-DD)
            keterangan (str): Keterangan atau catatan session
            created_by (str): Username yang membuat session
            
        Returns:
            int: ID session yang baru dibuat
            
        Raises:
            Exception: Jika gagal membuat session
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Ambil semua produk untuk diinisialisasi di session ini
                cursor.execute("SELECT id FROM products")
                products = cursor.fetchall()
                
                # Insert session
                cursor.execute("""
                    INSERT INTO stok_opname_sessions 
                    (tanggal, keterangan, status, created_by)
                    VALUES (?, ?, 'active', ?)
                """, (tanggal, keterangan, created_by))
                
                session_id = cursor.lastrowid
                
                # Insert semua produk sebagai items dengan stok_sistem
                for product in products:
                    product_id = product[0]
                    
                    # Ambil data produk
                    cursor.execute("""
                        SELECT id, stok FROM products WHERE id = ?
                    """, (product_id,))
                    prod = cursor.fetchone()
                    
                    if prod:
                        stok_sistem = prod[1]
                        
                        cursor.execute("""
                            INSERT INTO stok_opname_items
                            (session_id, product_id, stok_sistem, selisih, status)
                            VALUES (?, ?, ?, 0, 'pending')
                        """, (session_id, product_id, stok_sistem))
                
                logger.info(f"Stok opname session created: ID={session_id}, by={created_by}")
                return session_id
                
        except Exception as e:
            logger.error(f"Error creating stok opname session: {e}", exc_info=True)
            raise
    
    def get_session(self, session_id: int) -> Optional[StokOpnameSession]:
        """
        Ambil detail session berdasarkan ID.
        
        Args:
            session_id (int): ID session
            
        Returns:
            StokOpnameSession atau None jika tidak ditemukan
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, tanggal, keterangan, status, created_at, created_by, completed_at
                    FROM stok_opname_sessions
                    WHERE id = ?
                """, (session_id,))
                
                row = cursor.fetchone()
                if row:
                    return StokOpnameSession(*row)
                return None
                
        except Exception as e:
            logger.error(f"Error getting stok opname session: {e}", exc_info=True)
            raise
    
    def list_sessions(self, limit: int = 50) -> List[StokOpnameSession]:
        """
        Ambil daftar session stok opname (terbaru terlebih dahulu).
        
        Args:
            limit (int): Jumlah maksimal hasil
            
        Returns:
            List[StokOpnameSession]: Daftar session
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, tanggal, keterangan, status, created_at, created_by, completed_at
                    FROM stok_opname_sessions
                    ORDER BY tanggal DESC, created_at DESC
                    LIMIT ?
                """, (limit,))
                
                sessions = []
                for row in cursor.fetchall():
                    sessions.append(StokOpnameSession(*row))
                return sessions
                
        except Exception as e:
            logger.error(f"Error listing stok opname sessions: {e}", exc_info=True)
            raise
    
    # ====================================================================
    # ITEM MANAGEMENT - Update stok fisik dan catatan
    # ====================================================================
    
    def update_item(self, item_id: int, stok_fisik: int, catatan: str = "", status: str = "counted") -> bool:
        """
        Update stok fisik untuk item dalam session.
        
        Args:
            item_id (int): ID item
            stok_fisik (int): Stok fisik yang dihitung
            catatan (str): Catatan tambahan
            status (str): Status item (counted, verified, dll)
            
        Returns:
            bool: True jika berhasil
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Ambil stok_sistem untuk hitung selisih
                cursor.execute("""
                    SELECT stok_sistem FROM stok_opname_items WHERE id = ?
                """, (item_id,))
                
                row = cursor.fetchone()
                if not row:
                    logger.warning(f"Item not found: {item_id}")
                    return False
                
                stok_sistem = row[0]
                selisih = stok_fisik - stok_sistem
                
                # Update item
                cursor.execute("""
                    UPDATE stok_opname_items
                    SET stok_fisik = ?, selisih = ?, catatan = ?, status = ?
                    WHERE id = ?
                """, (stok_fisik, selisih, catatan, status, item_id))
                
                logger.info(f"Stok opname item updated: ID={item_id}, fisik={stok_fisik}, selisih={selisih}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating stok opname item: {e}", exc_info=True)
            raise
    
    def get_item(self, item_id: int) -> Optional[StokOpnameItem]:
        """
        Ambil detail item dari stok opname.
        
        Args:
            item_id (int): ID item
            
        Returns:
            StokOpnameItem atau None
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        soi.id, soi.session_id, soi.product_id, 
                        p.kode, p.nama, 
                        soi.stok_sistem, soi.stok_fisik, soi.selisih,
                        soi.status, soi.catatan, p.satuan
                    FROM stok_opname_items soi
                    JOIN products p ON soi.product_id = p.id
                    WHERE soi.id = ?
                """, (item_id,))
                
                row = cursor.fetchone()
                if row:
                    return StokOpnameItem(*row)
                return None
                
        except Exception as e:
            logger.error(f"Error getting stok opname item: {e}", exc_info=True)
            raise
    
    def get_session_items(self, session_id: int, status_filter: str = None) -> List[StokOpnameItem]:
        """
        Ambil semua item dalam session.
        
        Args:
            session_id (int): ID session
            status_filter (str): Filter berdasarkan status (optional)
            
        Returns:
            List[StokOpnameItem]: Daftar item
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                if status_filter:
                    cursor.execute("""
                        SELECT 
                            soi.id, soi.session_id, soi.product_id, 
                            p.kode, p.nama, 
                            soi.stok_sistem, soi.stok_fisik, soi.selisih,
                            soi.status, soi.catatan, p.satuan
                        FROM stok_opname_items soi
                        JOIN products p ON soi.product_id = p.id
                        WHERE soi.session_id = ? AND soi.status = ?
                        ORDER BY p.kode
                    """, (session_id, status_filter))
                else:
                    cursor.execute("""
                        SELECT 
                            soi.id, soi.session_id, soi.product_id, 
                            p.kode, p.nama, 
                            soi.stok_sistem, soi.stok_fisik, soi.selisih,
                            soi.status, soi.catatan, p.satuan
                        FROM stok_opname_items soi
                        JOIN products p ON soi.product_id = p.id
                        WHERE soi.session_id = ?
                        ORDER BY p.kode
                    """, (session_id,))
                
                items = []
                for row in cursor.fetchall():
                    items.append(StokOpnameItem(*row))
                return items
                
        except Exception as e:
            logger.error(f"Error getting stok opname items: {e}", exc_info=True)
            raise
    
    # ====================================================================
    # COMPLETE SESSION - Update stok produk dan tutup session
    # ====================================================================
    
    def complete_session(self, session_id: int) -> bool:
        """
        Selesaikan session stok opname dan update stok produk berdasarkan stok fisik.
        
        Args:
            session_id (int): ID session
            
        Returns:
            bool: True jika berhasil
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Ambil semua items yang sudah dicounted
                cursor.execute("""
                    SELECT product_id, stok_fisik
                    FROM stok_opname_items
                    WHERE session_id = ? AND status != 'pending'
                """, (session_id,))
                
                items = cursor.fetchall()
                
                # Update stok produk
                for product_id, stok_fisik in items:
                    cursor.execute("""
                        UPDATE products
                        SET stok = ?
                        WHERE id = ?
                    """, (stok_fisik, product_id))
                
                # Update session status
                cursor.execute("""
                    UPDATE stok_opname_sessions
                    SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (session_id,))
                
                logger.info(f"Stok opname session completed: ID={session_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error completing stok opname session: {e}", exc_info=True)
            raise
    
    def cancel_session(self, session_id: int) -> bool:
        """
        Batalkan session stok opname.
        
        Args:
            session_id (int): ID session
            
        Returns:
            bool: True jika berhasil
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE stok_opname_sessions
                    SET status = 'cancelled'
                    WHERE id = ?
                """, (session_id,))
                
                logger.info(f"Stok opname session cancelled: ID={session_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error cancelling stok opname session: {e}", exc_info=True)
            raise
    
    # ====================================================================
    # REPORT GENERATION
    # ====================================================================
    
    def get_session_report(self, session_id: int) -> Optional[StokOpnameReport]:
        """
        Generate laporan untuk session stok opname.
        
        Args:
            session_id (int): ID session
            
        Returns:
            StokOpnameReport atau None
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Ambil session info
                cursor.execute("""
                    SELECT tanggal FROM stok_opname_sessions WHERE id = ?
                """, (session_id,))
                
                session = cursor.fetchone()
                if not session:
                    return None
                
                tanggal = session[0]
                
                # Hitung statistik
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_items,
                        SUM(CASE WHEN status != 'pending' THEN 1 ELSE 0 END) as items_counted,
                        COUNT(DISTINCT CASE WHEN selisih != 0 THEN id END) as items_with_diff,
                        SUM(ABS(selisih)) as total_qty_diff
                    FROM stok_opname_items
                    WHERE session_id = ?
                """, (session_id,))
                
                stats = cursor.fetchone()
                
                # Ambil detail items
                items = self.get_session_items(session_id)
                items_details = []
                
                for item in items:
                    items_details.append({
                        'kode': item.kode_produk,
                        'nama': item.nama_produk,
                        'satuan': item.satuan,
                        'stok_sistem': item.stok_sistem,
                        'stok_fisik': item.stok_fisik,
                        'selisih': item.selisih,
                        'status': item.status,
                        'catatan': item.catatan
                    })
                
                return StokOpnameReport(
                    session_id=session_id,
                    tanggal=tanggal,
                    total_items=stats[0] or 0,
                    items_counted=stats[1] or 0,
                    total_selisih=stats[2] or 0,
                    total_selisih_qty=stats[3] or 0,
                    items_details=items_details
                )
                
        except Exception as e:
            logger.error(f"Error generating stok opname report: {e}", exc_info=True)
            raise
    
    def get_items_with_differences(self, session_id: int) -> List[StokOpnameItem]:
        """
        Ambil item yang memiliki selisih stok.
        
        Args:
            session_id (int): ID session
            
        Returns:
            List[StokOpnameItem]: Item dengan selisih
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        soi.id, soi.session_id, soi.product_id, 
                        p.kode, p.nama, 
                        soi.stok_sistem, soi.stok_fisik, soi.selisih,
                        soi.status, soi.catatan, p.satuan
                    FROM stok_opname_items soi
                    JOIN products p ON soi.product_id = p.id
                    WHERE soi.session_id = ? AND soi.selisih != 0
                    ORDER BY ABS(soi.selisih) DESC
                """, (session_id,))
                
                items = []
                for row in cursor.fetchall():
                    items.append(StokOpnameItem(*row))
                return items
                
        except Exception as e:
            logger.error(f"Error getting items with differences: {e}", exc_info=True)
            raise
