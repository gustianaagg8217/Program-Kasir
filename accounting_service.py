# ============================================================================
# ACCOUNTING_SERVICE.PY - Accounting/Bookkeeping Service
# ============================================================================
# Fungsi: High-level service untuk pembukuan/accounting
# Fitur: Record income dari transaksi, manage expenses, reporting
# ============================================================================

from datetime import datetime, date
from typing import Optional, Dict, List
from cashflow_service import CashflowService
from database import DatabaseManager
from logger_config import get_logger

logger = get_logger(__name__)

# ============================================================================
# ACCOUNTING SERVICE - High-level accounting operations
# ============================================================================

class AccountingService:
    """
    High-level service untuk manage pembukuan/accounting system.
    
    Fitur:
    - Automatic income recording dari transaksi
    - Manual expense input
    - Profit calculation
    - Reporting dan summary
    
    Attributes:
        db (DatabaseManager): Database instance
        cashflow_service (CashflowService): Cashflow service instance
    """
    
    def __init__(self, db: DatabaseManager):
        """
        Inisialisasi AccountingService.
        
        Args:
            db (DatabaseManager): Database instance
        """
        self.db = db
        self.cashflow_service = CashflowService(db)
    
    # ========================================================================
    # RECORD INCOME - Automatically record income dari transaksi
    # ========================================================================
    
    def record_income(self, transaction_id: int, amount: int,
                     description: str = "Penjualan") -> Optional[int]:
        """
        Record income dari transaksi yang berhasil.
        
        Ini adalah wrapper untuk menambah income dan link ke transaction.
        
        Args:
            transaction_id (int): ID transaksi terkait
            amount (int): Jumlah income/penjualan
            description (str): Deskripsi (default: "Penjualan")
            
        Returns:
            int: Cashflow ID jika berhasil
            None: Jika gagal
            
        Contoh:
            service = AccountingService(db)
            cf_id = service.record_income(123, 500000)
        """
        try:
            cf_id = self.cashflow_service.add_income(
                amount=amount,
                description=description,
                related_transaction_id=transaction_id
            )
            
            if cf_id:
                logger.info(f"Income recorded for transaction {transaction_id}: Rp{amount:,}")
            
            return cf_id
            
        except Exception as e:
            logger.error(f"Error recording income: {e}", exc_info=True)
            return None
    
    # ========================================================================
    # RECORD EXPENSE - Record expense/pengeluaran operasional
    # ========================================================================
    
    def record_expense(self, amount: int, description: str) -> Optional[int]:
        """
        Record expense/pengeluaran operasional.
        
        Args:
            amount (int): Jumlah expense dalam Rupiah
            description (str): Deskripsi expense (e.g., "Pembelian plastik")
            
        Returns:
            int: Cashflow ID jika berhasil
            None: Jika gagal
            
        Contoh:
            service = AccountingService(db)
            cf_id = service.record_expense(50000, "Pembelian plastik kemasan")
        """
        if not description or len(description.strip()) == 0:
            logger.warning("Expense description is required")
            return None
        
        try:
            cf_id = self.cashflow_service.add_expense(amount, description)
            
            if cf_id:
                logger.info(f"Expense recorded: Rp{amount:,} - {description}")
            
            return cf_id
            
        except Exception as e:
            logger.error(f"Error recording expense: {e}", exc_info=True)
            return None
    
    # ========================================================================
    # GET PROFIT - Calculate profit/rugi
    # ========================================================================
    
    def get_profit(self, start_date: Optional[date] = None, 
                  end_date: Optional[date] = None) -> int:
        """
        Hitung profit/rugi untuk periode tertentu.
        Profit = Total Income - Total Expense
        
        Args:
            start_date (date): Tanggal mulai (optional)
            end_date (date): Tanggal akhir (optional)
            
        Returns:
            int: Profit dalam Rupiah (bisa negatif untuk rugi)
            
        Contoh:
            service = AccountingService(db)
            profit = service.get_profit()
            if profit > 0:
                print(f"Keuntungan: Rp{profit:,}")
            else:
                print(f"Kerugian: Rp{abs(profit):,}")
        """
        summary = self.cashflow_service.get_cashflow_summary(start_date, end_date)
        return summary['profit']
    
    # ========================================================================
    # GET ACCOUNTING REPORT - Get complete accounting report
    # ========================================================================
    
    def get_accounting_report(self, start_date: Optional[date] = None,
                             end_date: Optional[date] = None) -> Dict:
        """
        Get complete accounting report untuk periode tertentu.
        
        Args:
            start_date (date): Tanggal mulai
            end_date (date): Tanggal akhir
            
        Returns:
            dict: {
                'period': {
                    'start_date': str,
                    'end_date': str
                },
                'summary': {
                    'total_income': int,
                    'total_expense': int,
                    'profit': int
                },
                'details': [
                    {
                        'date': str,
                        'total_income': int,
                        'total_expense': int,
                        'profit': int
                    },
                    ...
                ]
            }
        """
        try:
            if start_date is None:
                today = date.today()
                start_date = date(today.year, today.month, 1)
            
            if end_date is None:
                end_date = date.today()
            
            # Get summary
            summary = self.cashflow_service.get_cashflow_summary(start_date, end_date)
            
            # Get daily details
            daily_stats = self._get_daily_stats_for_range(start_date, end_date)
            
            return {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'summary': summary,
                'details': daily_stats
            }
            
        except Exception as e:
            logger.error(f"Error generating accounting report: {e}", exc_info=True)
            return {
                'period': {},
                'summary': {'total_income': 0, 'total_expense': 0, 'profit': 0},
                'details': []
            }
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _get_daily_stats_for_range(self, start_date: date, end_date: date) -> List[Dict]:
        """
        Get daily statistics untuk range tanggal tertentu.
        
        Args:
            start_date (date): Tanggal mulai
            end_date (date): Tanggal akhir
            
        Returns:
            list: List of daily stats
        """
        try:
            return self.db.get_cashflow_stats_for_range(start_date, end_date)
        except Exception as e:
            logger.error(f"Error getting daily stats: {e}", exc_info=True)
            return []
    
    # ========================================================================
    # GET CASHFLOW HISTORY - Get list of all cashflow entries
    # ========================================================================
    
    def get_history(self, limit: int = 100,
                   start_date: Optional[date] = None,
                   end_date: Optional[date] = None) -> List[Dict]:
        """
        Get history of all cashflow entries.
        
        Args:
            limit (int): Maximum entries to retrieve
            start_date (date): Filter start date (optional)
            end_date (date): Filter end date (optional)
            
        Returns:
            list: List of cashflow entries
        """
        return self.cashflow_service.get_cashflow_history(limit, start_date, end_date)
    
    # ========================================================================
    # DELETE ENTRY - Delete/undo cashflow entry
    # ========================================================================
    
    def delete_entry(self, cashflow_id: int) -> bool:
        """
        Delete/undo a cashflow entry.
        
        Args:
            cashflow_id (int): ID of cashflow entry to delete
            
        Returns:
            bool: True if successful
        """
        return self.cashflow_service.delete_cashflow(cashflow_id)
