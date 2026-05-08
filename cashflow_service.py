# ============================================================================
# CASHFLOW_SERVICE.PY - Cashflow Management Service
# ============================================================================
# Fungsi: Mengelola income dan expense cashflow untuk pembukuan
# Fitur: Add income, add expense, tracking cashflow
# ============================================================================

from datetime import datetime, date
from typing import List, Optional, Dict, Tuple
from database import DatabaseManager
from logger_config import get_logger

logger = get_logger(__name__)

# ============================================================================
# CASHFLOW SERVICE - Manage income dan expense
# ============================================================================

class CashflowService:
    """
    Service untuk mengelola cashflow (income dan expense).
    
    Fitur:
    - Track income dari penjualan (otomatis dari transaksi)
    - Track expense manual
    - Get total income, expense, profit
    - Get cashflow history
    
    Attributes:
        db (DatabaseManager): Database instance
    """
    
    def __init__(self, db: DatabaseManager):
        """
        Inisialisasi CashflowService.
        
        Args:
            db (DatabaseManager): Database instance
        """
        self.db = db
    
    # ========================================================================
    # ADD INCOME - Record income (penjualan/transaksi)
    # ========================================================================
    
    def add_income(self, amount: int, description: str = "Penjualan", 
                  related_transaction_id: Optional[int] = None) -> Optional[int]:
        """
        Tambah income (penjualan/revenue).
        
        Args:
            amount (int): Jumlah income dalam Rupiah
            description (str): Deskripsi income
            related_transaction_id (int): ID transaksi terkait (optional)
            
        Returns:
            int: Cashflow ID jika berhasil
            None: Jika gagal
            
        Contoh:
            service = CashflowService(db)
            cf_id = service.add_income(500000, "Penjualan")
        """
        if amount <= 0:
            logger.warning(f"Invalid income amount: {amount}")
            return None
        
        try:
            cf_id = self.db.add_cashflow(
                cf_type="income",
                amount=amount,
                description=description,
                related_transaction_id=related_transaction_id
            )
            
            if cf_id:
                logger.info(f"Income recorded: Rp{amount:,} - {description}")
            return cf_id
            
        except Exception as e:
            logger.error(f"Error adding income: {e}", exc_info=True)
            return None
    
    # ========================================================================
    # ADD EXPENSE - Record expense (pengeluaran)
    # ========================================================================
    
    def add_expense(self, amount: int, description: str) -> Optional[int]:
        """
        Tambah expense (pengeluaran/biaya operasional).
        
        Args:
            amount (int): Jumlah expense dalam Rupiah
            description (str): Deskripsi expense
            
        Returns:
            int: Cashflow ID jika berhasil
            None: Jika gagal
            
        Contoh:
            service = CashflowService(db)
            cf_id = service.add_expense(50000, "Pembelian plastik")
        """
        if amount <= 0:
            logger.warning(f"Invalid expense amount: {amount}")
            return None
        
        if not description or len(description.strip()) == 0:
            logger.warning("Expense description cannot be empty")
            return None
        
        try:
            cf_id = self.db.add_cashflow(
                cf_type="expense",
                amount=amount,
                description=description
            )
            
            if cf_id:
                logger.info(f"Expense recorded: Rp{amount:,} - {description}")
            return cf_id
            
        except Exception as e:
            logger.error(f"Error adding expense: {e}", exc_info=True)
            return None
    
    # ========================================================================
    # GET CASHFLOW SUMMARY - Total income, expense, profit
    # ========================================================================
    
    def get_cashflow_summary(self, start_date: Optional[date] = None, 
                            end_date: Optional[date] = None) -> Dict[str, int]:
        """
        Dapatkan summary cashflow untuk periode tertentu.
        
        Args:
            start_date (date): Tanggal mulai (optional, default: start of month)
            end_date (date): Tanggal akhir (optional, default: today)
            
        Returns:
            dict: {
                'total_income': int,
                'total_expense': int,
                'profit': int
            }
            
        Contoh:
            summary = service.get_cashflow_summary()
            print(f"Income: Rp{summary['total_income']:,}")
            print(f"Expense: Rp{summary['total_expense']:,}")
            print(f"Profit: Rp{summary['profit']:,}")
        """
        try:
            # Default date range: current month
            if start_date is None:
                today = date.today()
                start_date = date(today.year, today.month, 1)
            
            if end_date is None:
                end_date = date.today()
            
            # Get data from database
            total_income = self.db.get_total_cashflow(
                cf_type="income",
                start_date=start_date,
                end_date=end_date
            )
            
            total_expense = self.db.get_total_cashflow(
                cf_type="expense",
                start_date=start_date,
                end_date=end_date
            )
            
            profit = total_income - total_expense
            
            return {
                'total_income': total_income,
                'total_expense': total_expense,
                'profit': profit
            }
            
        except Exception as e:
            logger.error(f"Error getting cashflow summary: {e}", exc_info=True)
            return {
                'total_income': 0,
                'total_expense': 0,
                'profit': 0
            }
    
    # ========================================================================
    # GET DAILY CASHFLOW - Get cashflow for specific day
    # ========================================================================
    
    def get_daily_cashflow(self, target_date: Optional[date] = None) -> Dict[str, int]:
        """
        Dapatkan cashflow untuk satu hari tertentu.
        
        Args:
            target_date (date): Tanggal target (default: hari ini)
            
        Returns:
            dict: {
                'total_income': int,
                'total_expense': int,
                'profit': int
            }
        """
        if target_date is None:
            target_date = date.today()
        
        return self.get_cashflow_summary(start_date=target_date, end_date=target_date)
    
    # ========================================================================
    # GET CASHFLOW HISTORY - List cashflow entries
    # ========================================================================
    
    def get_cashflow_history(self, limit: int = 100, 
                            start_date: Optional[date] = None,
                            end_date: Optional[date] = None) -> List[Dict]:
        """
        Dapatkan history/list cashflow entries.
        
        Args:
            limit (int): Jumlah entries yang diambil (default: 100)
            start_date (date): Tanggal mulai filter (optional)
            end_date (date): Tanggal akhir filter (optional)
            
        Returns:
            list: List of cashflow entries dengan format:
                [
                    {
                        'id': int,
                        'type': str (income/expense),
                        'amount': int,
                        'description': str,
                        'created_at': str,
                        'related_transaction_id': int or None
                    },
                    ...
                ]
        """
        try:
            return self.db.get_cashflow_history(
                limit=limit,
                start_date=start_date,
                end_date=end_date
            )
        except Exception as e:
            logger.error(f"Error getting cashflow history: {e}", exc_info=True)
            return []
    
    # ========================================================================
    # DELETE CASHFLOW ENTRY - Remove cashflow entry (undo)
    # ========================================================================
    
    def delete_cashflow(self, cashflow_id: int) -> bool:
        """
        Hapus entry cashflow (untuk undo/koreksi).
        
        Args:
            cashflow_id (int): ID cashflow yang akan dihapus
            
        Returns:
            bool: True jika berhasil
        """
        try:
            result = self.db.delete_cashflow(cashflow_id)
            if result:
                logger.info(f"Cashflow entry {cashflow_id} deleted")
            return result
        except Exception as e:
            logger.error(f"Error deleting cashflow: {e}", exc_info=True)
            return False
    
    # ========================================================================
    # GET DAILY STATS - Cashflow stats untuk setiap hari
    # ========================================================================
    
    def get_daily_stats(self, num_days: int = 7) -> List[Dict]:
        """
        Dapatkan statistics cashflow per hari untuk n hari terakhir.
        Berguna untuk visualisasi dashboard/chart.
        
        Args:
            num_days (int): Jumlah hari yang diambil (default: 7)
            
        Returns:
            list: List of daily stats:
                [
                    {
                        'date': str (YYYY-MM-DD),
                        'total_income': int,
                        'total_expense': int,
                        'profit': int
                    },
                    ...
                ]
        """
        try:
            return self.db.get_daily_cashflow_stats(num_days)
        except Exception as e:
            logger.error(f"Error getting daily stats: {e}", exc_info=True)
            return []
