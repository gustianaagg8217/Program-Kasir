# ============================================================================
# PAYMENT_REPOSITORY.PY - Payment Data Access Layer (Repository Layer)
# ============================================================================
# Fungsi: Handle all payment database operations
# CRUD operations untuk Payment records
# ============================================================================

from typing import List, Optional
from datetime import datetime

from ..core import Payment
from .base_repository import BaseRepository
from logger_config import get_logger

logger = get_logger(__name__)


class PaymentRepository(BaseRepository):
    """
    Repository untuk Payment data access.
    
    Handles:
    - Create payment records
    - Retrieve payment by ID or transaction ID
    - Update payment status
    - Payment history queries
    """
    
    def create(self, **kwargs) -> Payment:
        """Create new payment record."""
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO payments (
                        transaction_id, method, amount, reference_id,
                        status, timestamp, verified_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    kwargs.get('transaction_id'),
                    kwargs.get('method'),
                    kwargs.get('amount'),
                    kwargs.get('reference_id', ''),
                    kwargs.get('status', 'pending'),
                    kwargs.get('timestamp', datetime.now()),
                    kwargs.get('verified_by', '')
                ))
                
                payment_id = cursor.lastrowid
                
                logger.info(f"Payment created: ID {payment_id}")
                
                return self.get_by_id(payment_id)
                
        except Exception as e:
            logger.error(f"Error creating payment: {e}", exc_info=e)
            raise
    
    def get_by_id(self, payment_id: int) -> Optional[Payment]:
        """Get payment by ID."""
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM payments WHERE id = ?
                """, (payment_id,))
                
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_payment(row)
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting payment {payment_id}: {e}", exc_info=e)
            raise
    
    def get_by_transaction(self, transaction_id: int) -> List[Payment]:
        """Get all payments for a transaction."""
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM payments 
                    WHERE transaction_id = ?
                    ORDER BY timestamp DESC
                """, (transaction_id,))
                
                payments = []
                for row in cursor.fetchall():
                    payments.append(self._row_to_payment(row))
                
                return payments
                
        except Exception as e:
            logger.error(f"Error getting payments for transaction {transaction_id}: {e}", exc_info=e)
            raise
    
    def update(self, payment_id: int, **kwargs) -> bool:
        """Update payment record."""
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()
                
                # Build update query dynamically
                updates = []
                params = []
                
                for key, value in kwargs.items():
                    if key in ['method', 'amount', 'reference_id', 'status', 'verified_by']:
                        updates.append(f"{key} = ?")
                        params.append(value)
                
                if not updates:
                    return False
                
                params.append(payment_id)
                
                cursor.execute(f"""
                    UPDATE payments SET {', '.join(updates)}
                    WHERE id = ?
                """, params)
                
                logger.info(f"Payment {payment_id} updated")
                return True
                
        except Exception as e:
            logger.error(f"Error updating payment {payment_id}: {e}", exc_info=e)
            raise
    
    def delete(self, payment_id: int) -> bool:
        """Delete payment record (soft delete recommended)."""
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()
                
                # Soft delete - mark as cancelled instead of hard delete
                cursor.execute("""
                    UPDATE payments SET status = 'cancelled'
                    WHERE id = ?
                """, (payment_id,))
                
                logger.warning(f"Payment {payment_id} marked as cancelled")
                return True
                
        except Exception as e:
            logger.error(f"Error deleting payment {payment_id}: {e}", exc_info=e)
            raise
    
    def get_by_status(self, status: str) -> List[Payment]:
        """Get payments by status."""
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM payments
                    WHERE status = ?
                    ORDER BY timestamp DESC
                """, (status,))
                
                payments = []
                for row in cursor.fetchall():
                    payments.append(self._row_to_payment(row))
                
                return payments
                
        except Exception as e:
            logger.error(f"Error getting payments by status {status}: {e}", exc_info=e)
            raise
    
    def get_by_method(self, method: str) -> List[Payment]:
        """Get payments by method."""
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM payments
                    WHERE method = ?
                    ORDER BY timestamp DESC
                """, (method,))
                
                payments = []
                for row in cursor.fetchall():
                    payments.append(self._row_to_payment(row))
                
                return payments
                
        except Exception as e:
            logger.error(f"Error getting payments by method {method}: {e}", exc_info=e)
            raise
    
    def get_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Payment]:
        """Get payments within date range."""
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM payments
                    WHERE timestamp BETWEEN ? AND ?
                    ORDER BY timestamp DESC
                """, (start_date, end_date))
                
                payments = []
                for row in cursor.fetchall():
                    payments.append(self._row_to_payment(row))
                
                return payments
                
        except Exception as e:
            logger.error(f"Error getting payments for date range: {e}", exc_info=e)
            raise
    
    def get_all(self, limit: int = 100, offset: int = 0) -> List[Payment]:
        """Get all payments with pagination."""
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM payments
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))
                
                payments = []
                for row in cursor.fetchall():
                    payments.append(self._row_to_payment(row))
                
                return payments
                
        except Exception as e:
            logger.error(f"Error getting all payments: {e}", exc_info=e)
            raise
    
    @staticmethod
    def _row_to_payment(row) -> Payment:
        """Convert database row to Payment object."""
        return Payment(
            id=row['id'] if 'id' in row.keys() else None,
            transaction_id=row['transaction_id'] if 'transaction_id' in row.keys() else None,
            method=row['method'] if 'method' in row.keys() else 'cash',
            amount=row['amount'] if 'amount' in row.keys() else 0,
            reference_id=row['reference_id'] if 'reference_id' in row.keys() else '',
            status=row['status'] if 'status' in row.keys() else 'pending',
            timestamp=row['timestamp'] if 'timestamp' in row.keys() else datetime.now(),
            verified_by=row['verified_by'] if 'verified_by' in row.keys() else ''
        )
