# ============================================================================
# TRANSACTION_SERVICE.PY - Business Logic Layer untuk Transactions
# ============================================================================
# Fungsi: Handle transaction management, refunds, reporting
# Responsibilitas: NO direct database access (gunakan repository)
# ============================================================================

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from app.repositories.transaction_repository import TransactionRepository, Transaction
from app.repositories.product_repository import ProductRepository
from app.services.product_service import ProductService
from app.utils.error_handler import ValidationError as ServiceValidationError, DatabaseError
from logger_config import get_logger

logger = get_logger(__name__)


class TransactionService:
    """Service layer untuk transaction management."""
    
    def __init__(self, trans_repo: TransactionRepository, product_service: ProductService):
        """
        Init dengan repositories & services.
        
        Args:
            trans_repo: TransactionRepository instance
            product_service: ProductService instance
        """
        self.trans_repo = trans_repo
        self.product_service = product_service
    
    def create_transaction(
        self,
        user_id: int,
        username: str,
        total_items: int,
        subtotal: int,
        discount: int,
        tax: int,
        total: int,
        metode_bayar: str,
        catatan: str = ""
    ) -> Transaction:
        """
        Create transaction baru dengan validasi.
        
        Args:
            user_id: User yang melakukan transaksi
            username: Username
            total_items: Jumlah item
            subtotal: Subtotal
            discount: Discount amount
            tax: Tax amount
            total: Total harga
            metode_bayar: Metode bayar (cash, transfer, card)
            catatan: Catatan
            
        Returns:
            Transaction object
            
        Raises:
            ServiceValidationError: Jika validasi gagal
        """
        try:
            # Validasi
            if total_items <= 0:
                raise ServiceValidationError("Total items harus > 0")
            
            if total <= 0:
                raise ServiceValidationError("Total harga harus > 0")
            
            valid_methods = ['cash', 'transfer', 'card', 'check']
            if metode_bayar.lower() not in valid_methods:
                raise ServiceValidationError(f"Metode bayar harus: {', '.join(valid_methods)}")
            
            # Validasi calculation
            calculated_total = subtotal - discount + tax
            if calculated_total != total:
                logger.warning(f"Amount mismatch: calculated={calculated_total}, provided={total}")
                # Some tolerance for rounding
                if abs(calculated_total - total) > 1000:  # 1000 rupiah tolerance
                    raise ServiceValidationError("Perhitungan total tidak sesuai")
            
            # Create transaction
            trans = self.trans_repo.create(
                user_id, username, total_items, subtotal, discount, tax, total, metode_bayar, catatan
            )
            
            logger.info(f"Transaction completed: ID={trans.id}, total={total}, items={total_items}")
            return trans
        
        except ServiceValidationError:
            raise
        except Exception as e:
            logger.error(f"Error creating transaction: {e}")
            raise DatabaseError(str(e), "Gagal menyimpan transaksi")
    
    def get_transaction(self, trans_id: int) -> Optional[Transaction]:
        """Get transaction by ID."""
        trans = self.trans_repo.get_by_id(trans_id)
        if trans:
            logger.info(f"Transaction fetched: ID={trans_id}")
        return trans
    
    def get_transactions_by_date(self, start_date: str, end_date: str) -> List[Transaction]:
        """
        Get transactions dalam range tanggal.
        
        Args:
            start_date: 'YYYY-MM-DD'
            end_date: 'YYYY-MM-DD'
            
        Returns:
            List of transactions
        """
        return self.trans_repo.list_by_date_range(start_date, end_date)
    
    def get_today_transactions(self) -> List[Transaction]:
        """Get transactions for today."""
        today = datetime.now().strftime('%Y-%m-%d')
        return self.trans_repo.list_by_date_range(today, today)
    
    def get_week_transactions(self) -> List[Transaction]:
        """Get transactions untuk 7 hari terakhir."""
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        return self.trans_repo.list_by_date_range(start_date, end_date)
    
    def get_month_transactions(self) -> List[Transaction]:
        """Get transactions untuk 30 hari terakhir."""
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        return self.trans_repo.list_by_date_range(start_date, end_date)
    
    def get_user_transactions(self, user_id: int) -> List[Transaction]:
        """Get transactions untuk specific user."""
        return self.trans_repo.list_by_user(user_id)
    
    def get_daily_summary(self, date: str = None) -> Dict[str, Any]:
        """
        Get daily transaction summary.
        
        Args:
            date: Date dalam format 'YYYY-MM-DD' (default: hari ini)
            
        Returns:
            Summary dictionary
        """
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        summary = self.trans_repo.get_summary(date, date)
        summary['date'] = date
        return summary
    
    def get_period_summary(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get transaction summary untuk period."""
        summary = self.trans_repo.get_summary(start_date, end_date)
        summary['period'] = f"{start_date} to {end_date}"
        return summary
    
    def get_revenue_by_payment_method(self, start_date: str, end_date: str) -> Dict[str, int]:
        """
        Get revenue breakdown by payment method.
        
        Args:
            start_date: 'YYYY-MM-DD'
            end_date: 'YYYY-MM-DD'
            
        Returns:
            Dictionary dengan revenue per metode
        """
        try:
            transactions = self.trans_repo.list_by_date_range(start_date, end_date)
            
            revenue_by_method = {}
            for trans in transactions:
                method = trans.metode_bayar
                if method not in revenue_by_method:
                    revenue_by_method[method] = 0
                revenue_by_method[method] += trans.total
            
            return revenue_by_method
        except Exception as e:
            logger.error(f"Error getting revenue by payment method: {e}")
            return {}
    
    def calculate_avg_transaction(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Calculate average transaction value untuk period."""
        try:
            summary = self.trans_repo.get_summary(start_date, end_date)
            
            if summary['total_transactions'] == 0:
                return {'avg_value': 0, 'avg_items': 0}
            
            return {
                'avg_value': summary['revenue'] // summary['total_transactions'],
                'avg_items': summary['total_items'] // summary['total_transactions'],
                'total_transactions': summary['total_transactions']
            }
        except Exception as e:
            logger.error(f"Error calculating average transaction: {e}")
            return {}
    
    def refund_transaction(self, trans_id: int) -> bool:
        """
        Refund transaction (revert stock changes).
        
        Args:
            trans_id: Transaction ID
            
        Returns:
            True jika berhasil
        """
        try:
            trans = self.trans_repo.get_by_id(trans_id)
            if not trans:
                raise ServiceValidationError(f"Transaksi {trans_id} tidak ditemukan")
            
            if trans.status == 'refunded':
                raise ServiceValidationError("Transaksi sudah di-refund sebelumnya")
            
            # Update status
            result = self.trans_repo.update_status(trans_id, 'refunded')
            if result:
                logger.info(f"Transaction refunded: ID={trans_id}")
            
            return result
        
        except ServiceValidationError:
            raise
        except Exception as e:
            logger.error(f"Error refunding transaction: {e}")
            raise DatabaseError(str(e), "Gagal refund transaksi")
