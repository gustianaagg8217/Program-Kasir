# ============================================================================
# TRANSACTION_REPOSITORY.PY - Transaction Data Access Layer
# ============================================================================
# Fungsi: Handle semua DB operations untuk Transaction entity
# ============================================================================

from typing import List, Optional
from datetime import datetime, date

from ..core import Transaction, TransactionItem, DatabaseError
from .base_repository import CacheableRepository


class TransactionRepository(CacheableRepository):
    """
    Repository untuk Transaction CRUD operations.
    
    Methods:
        create(transaction, items): Create transaction with items
        get_by_id(transaction_id): Get transaction with items
        list_all(): List all transactions
        list_by_date(date): List transactions for a specific date
        update(transaction_id, ...): Update transaction
        delete(transaction_id): Delete transaction (soft delete)
    """
    
    def create(self, transaction: Transaction) -> int:
        """
        Create transaction dengan items.
        
        Args:
            transaction (Transaction): Transaction object to save
            
        Returns:
            int: Transaction ID
            
        Raises:
            DatabaseError: If creation fails
        """
        with self.get_db() as conn:
            cursor = conn.cursor()
            try:
                # Insert main transaction
                cursor.execute("""
                    INSERT INTO transactions 
                    (tanggal, payment_method, total_sebelum_pajak, total_pajak, total, 
                     uang_diterima, kembalian, catatan, cashier_id, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    transaction.tanggal,
                    transaction.payment_method,
                    transaction.total_sebelum_pajak,
                    transaction.total_pajak,
                    transaction.total,
                    transaction.uang_diterima,
                    transaction.kembalian,
                    transaction.catatan,
                    transaction.cashier_id,
                    transaction.status,
                    datetime.now()
                ))
                
                transaction_id = cursor.lastrowid
                
                # Insert transaction items
                for item in transaction.items:
                    cursor.execute("""
                        INSERT INTO transaction_items 
                        (transaction_id, product_id, product_code, product_name, 
                         qty, harga_satuan, discount_pct, tax_pct, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        transaction_id,
                        item.product_id,
                        item.product_code,
                        item.product_name,
                        item.qty,
                        item.harga_satuan,
                        item.discount_pct,
                        item.tax_pct,
                        datetime.now()
                    ))
                
                # Invalidate cache
                self._invalidate_cache("transactions")
                
                return transaction_id
            
            except Exception as e:
                raise DatabaseError(f"Gagal create transaction: {str(e)}", "create")
    
    def read(self, transaction_id: int) -> Optional[Transaction]:
        """Get transaction by ID."""
        return self.get_by_id(transaction_id)
    
    def get_by_id(self, transaction_id: int) -> Optional[Transaction]:
        """
        Get transaction by ID dengan items.
        
        Args:
            transaction_id (int): Transaction ID
            
        Returns:
            Transaction: Transaction object or None
        """
        with self.get_db() as conn:
            cursor = conn.cursor()
            
            # Get main transaction
            cursor.execute("""
                SELECT id, tanggal, payment_method, total_sebelum_pajak, total_pajak, total,
                       uang_diterima, kembalian, catatan, cashier_id, status, created_at
                FROM transactions WHERE id = ?
            """, (transaction_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            transaction = self._map_row_to_transaction(row)
            
            # Get items
            cursor.execute("""
                SELECT product_id, product_code, product_name, qty, harga_satuan, 
                       discount_pct, tax_pct
                FROM transaction_items WHERE transaction_id = ?
            """, (transaction_id,))
            
            items_row = cursor.fetchall()
            transaction.items = [self._map_row_to_transaction_item(item_row) for item_row in items_row]
            
            return transaction
    
    def list_all(self, limit: int = 1000, offset: int = 0) -> List[Transaction]:
        """
        List all transactions (without items for performance).
        
        Args:
            limit (int): Limit results
            offset (int): Pagination offset
            
        Returns:
            List[Transaction]: List of transactions
        """
        cache_key = f"transactions_all_{limit}_{offset}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached
        
        with self.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, tanggal, payment_method, total_sebelum_pajak, total_pajak, total,
                       uang_diterima, kembalian, catatan, cashier_id, status, created_at
                FROM transactions ORDER BY tanggal DESC LIMIT ? OFFSET ?
            """, (limit, offset))
            
            rows = cursor.fetchall()
            transactions = [self._map_row_to_transaction(row) for row in rows]
            
            # Note: items not loaded for performance in list view
            # Use get_by_id() to load full transaction details
            
            self._set_cache(cache_key, transactions)
            return transactions
    
    def list_by_date(self, target_date: date) -> List[Transaction]:
        """
        List transactions for specific date.
        
        Args:
            target_date (date): Date to filter
            
        Returns:
            List[Transaction]: Transactions on that date
        """
        with self.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, tanggal, payment_method, total_sebelum_pajak, total_pajak, total,
                       uang_diterima, kembalian, catatan, cashier_id, status, created_at
                FROM transactions 
                WHERE DATE(tanggal) = DATE(?)
                ORDER BY tanggal DESC
            """, (target_date,))
            
            rows = cursor.fetchall()
            return [self._map_row_to_transaction(row) for row in rows]
    
    def list_by_date_range(self, start_date: date, end_date: date) -> List[Transaction]:
        """
        List transactions within date range.
        
        Args:
            start_date (date): Start date
            end_date (date): End date
            
        Returns:
            List[Transaction]: Transactions in range
        """
        with self.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, tanggal, payment_method, total_sebelum_pajak, total_pajak, total,
                       uang_diterima, kembalian, catatan, cashier_id, status, created_at
                FROM transactions 
                WHERE DATE(tanggal) >= DATE(?) AND DATE(tanggal) <= DATE(?)
                ORDER BY tanggal DESC
            """, (start_date, end_date))
            
            rows = cursor.fetchall()
            return [self._map_row_to_transaction(row) for row in rows]
    
    def update(self, transaction_id: int, **kwargs) -> bool:
        """
        Update transaction (usually just status/notes).
        
        Args:
            transaction_id (int): Transaction ID
            **kwargs: Fields to update
            
        Returns:
            bool: True if updated
        """
        allowed_fields = {'status', 'catatan'}
        fields_to_update = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not fields_to_update:
            return False
        
        set_clause = ', '.join([f"{k} = ?" for k in fields_to_update.keys()])
        values = list(fields_to_update.values()) + [transaction_id]
        
        with self.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE transactions SET {set_clause} WHERE id = ?", values)
            
            self._invalidate_cache("transactions")
            return cursor.rowcount > 0
    
    def delete(self, transaction_id: int) -> bool:
        """
        Soft delete transaction (mark as cancelled).
        
        Args:
            transaction_id (int): Transaction ID
            
        Returns:
            bool: True if deleted
        """
        return self.update(transaction_id, status='cancelled')
    
    def count_by_date(self, target_date: date) -> int:
        """Count transactions on a specific date."""
        with self.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as count FROM transactions WHERE DATE(tanggal) = DATE(?)
            """, (target_date,))
            
            row = cursor.fetchone()
            return row['count'] if row else 0
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    @staticmethod
    def _map_row_to_transaction(row) -> Transaction:
        """Convert database row to Transaction object."""
        if row is None:
            return None
        
        return Transaction(
            id=row['id'],
            tanggal=row['tanggal'],
            items=[],  # Load separately with get_by_id
            payment_method=row['payment_method'],
            total_sebelum_pajak=row['total_sebelum_pajak'],
            total_pajak=row['total_pajak'],
            total=row['total'],
            uang_diterima=row['uang_diterima'],
            kembalian=row['kembalian'],
            catatan=row['catatan'],
            cashier_id=row['cashier_id'],
            status=row['status']
        )
    
    @staticmethod
    def _map_row_to_transaction_item(row) -> TransactionItem:
        """Convert database row to TransactionItem object."""
        if row is None:
            return None
        
        return TransactionItem(
            product_id=row['product_id'],
            product_code=row['product_code'],
            product_name=row['product_name'],
            qty=row['qty'],
            harga_satuan=row['harga_satuan'],
            discount_pct=row['discount_pct'],
            tax_pct=row['tax_pct']
        )
