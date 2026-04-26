# ============================================================================
# TRANSACTION_REPOSITORY.PY - Database Access Layer untuk Transactions
# ============================================================================
# Fungsi: CRUD operations untuk transaction data
# Responsibilitas: Direct database access ONLY, no business logic
# ============================================================================

from typing import List, Optional, Dict, Any
from datetime import datetime
from database import DatabaseManager
from logger_config import get_logger
from app.utils.error_handler import DatabaseError

logger = get_logger(__name__)


class Transaction:
    """Data model untuk Transaction."""
    def __init__(self, id: int, tanggal: str, user_id: int, username: str, total_items: int,
                 subtotal: int, discount: int, tax: int, total: int, metode_bayar: str,
                 status: str = "completed", catatan: str = ""):
        self.id = id
        self.tanggal = tanggal
        self.user_id = user_id
        self.username = username
        self.total_items = total_items
        self.subtotal = subtotal
        self.discount = discount
        self.tax = tax
        self.total = total
        self.metode_bayar = metode_bayar  # 'cash', 'transfer', 'card'
        self.status = status  # 'completed', 'refunded', 'cancelled'
        self.catatan = catatan
    
    def __repr__(self):
        return f"Transaction(id={self.id}, tanggal={self.tanggal}, total={self.total})"


class TransactionRepository:
    """Repository untuk transaction data access."""
    
    def __init__(self, db: DatabaseManager):
        """
        Init dengan DatabaseManager instance.
        
        Args:
            db: DatabaseManager instance
        """
        self.db = db
    
    def create(self, user_id: int, username: str, total_items: int, subtotal: int,
               discount: int, tax: int, total: int, metode_bayar: str, catatan: str = "") -> Transaction:
        """
        Create transaction baru.
        
        Args:
            user_id: User ID yang melakukan transaksi
            username: Username
            total_items: Jumlah item
            subtotal: Subtotal sebelum tax/discount
            discount: Discount amount
            tax: Tax amount
            total: Total amount
            metode_bayar: Metode pembayaran
            catatan: Catatan transaksi
            
        Returns:
            Transaction object
        """
        try:
            tanggal = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO transactions 
                    (tanggal, user_id, username, total_items, subtotal, discount, tax, total, metode_bayar, status, catatan)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed', ?)
                """, (tanggal, user_id, username, total_items, subtotal, discount, tax, total, metode_bayar, catatan))
                conn.commit()
                
                trans_id = cursor.lastrowid
                logger.info(f"Transaction created: ID={trans_id}, total={total}, items={total_items}")
                
                return Transaction(trans_id, tanggal, user_id, username, total_items,
                                 subtotal, discount, tax, total, metode_bayar, "completed", catatan)
        except Exception as e:
            logger.error(f"Error creating transaction: {e}")
            raise DatabaseError(str(e), "Gagal menyimpan transaksi")
    
    def get_by_id(self, trans_id: int) -> Optional[Transaction]:
        """Get transaction berdasarkan ID."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, tanggal, user_id, username, total_items, subtotal, 
                           discount, tax, total, metode_bayar, status, catatan
                    FROM transactions WHERE id = ?
                """, (trans_id,))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                return self._map_to_transaction(row)
        except Exception as e:
            logger.error(f"Error getting transaction: {e}")
            return None
    
    def list_by_date_range(self, start_date: str, end_date: str) -> List[Transaction]:
        """
        Get transactions dalam range tanggal (untuk laporan).
        
        Args:
            start_date: Format 'YYYY-MM-DD'
            end_date: Format 'YYYY-MM-DD'
            
        Returns:
            List of transactions
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, tanggal, user_id, username, total_items, subtotal, 
                           discount, tax, total, metode_bayar, status, catatan
                    FROM transactions
                    WHERE DATE(tanggal) BETWEEN ? AND ?
                    ORDER BY tanggal DESC
                """, (start_date, end_date))
                
                rows = cursor.fetchall()
                return [self._map_to_transaction(row) for row in rows]
        except Exception as e:
            logger.error(f"Error listing transactions: {e}")
            return []
    
    def list_by_user(self, user_id: int, limit: int = 50) -> List[Transaction]:
        """Get transactions for specific user."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, tanggal, user_id, username, total_items, subtotal, 
                           discount, tax, total, metode_bayar, status, catatan
                    FROM transactions
                    WHERE user_id = ?
                    ORDER BY tanggal DESC
                    LIMIT ?
                """, (user_id, limit))
                
                rows = cursor.fetchall()
                return [self._map_to_transaction(row) for row in rows]
        except Exception as e:
            logger.error(f"Error listing user transactions: {e}")
            return []
    
    def list_all(self, limit: int = 100, offset: int = 0) -> List[Transaction]:
        """Get semua transactions dengan pagination."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, tanggal, user_id, username, total_items, subtotal, 
                           discount, tax, total, metode_bayar, status, catatan
                    FROM transactions
                    ORDER BY tanggal DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))
                
                rows = cursor.fetchall()
                return [self._map_to_transaction(row) for row in rows]
        except Exception as e:
            logger.error(f"Error listing transactions: {e}")
            return []
    
    def update_status(self, trans_id: int, status: str) -> bool:
        """Update transaction status (e.g., refunded, cancelled)."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE transactions SET status = ? WHERE id = ?
                """, (status, trans_id))
                conn.commit()
                
                logger.info(f"Transaction status updated: ID={trans_id}, status={status}")
                return True
        except Exception as e:
            logger.error(f"Error updating transaction: {e}")
            return False
    
    def get_summary(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Get transaction summary untuk periode (untuk laporan).
        
        Args:
            start_date: Format 'YYYY-MM-DD'
            end_date: Format 'YYYY-MM-DD'
            
        Returns:
            Dictionary dengan summary data
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_transactions,
                        SUM(total_items) as total_items,
                        SUM(subtotal) as total_subtotal,
                        SUM(discount) as total_discount,
                        SUM(tax) as total_tax,
                        SUM(total) as total_revenue
                    FROM transactions
                    WHERE DATE(tanggal) BETWEEN ? AND ?
                """, (start_date, end_date))
                
                row = cursor.fetchone()
                return {
                    'total_transactions': row[0] or 0,
                    'total_items': row[1] or 0,
                    'subtotal': row[2] or 0,
                    'discount': row[3] or 0,
                    'tax': row[4] or 0,
                    'revenue': row[5] or 0
                }
        except Exception as e:
            logger.error(f"Error getting transaction summary: {e}")
            return {}
    
    @staticmethod
    def _map_to_transaction(row: tuple) -> Transaction:
        """Map database row ke Transaction object."""
        return Transaction(
            id=row[0],
            tanggal=row[1],
            user_id=row[2],
            username=row[3],
            total_items=row[4],
            subtotal=row[5],
            discount=row[6],
            tax=row[7],
            total=row[8],
            metode_bayar=row[9],
            status=row[10],
            catatan=row[11]
        )
