# ============================================================================
# ANALYTICS_SERVICE.PY - Advanced Analytics & Reporting Service
# ============================================================================
# Fungsi: Provide business intelligence dan data analytics
# Sales trends, peak hours, customer analysis, growth metrics, forecasting
# ============================================================================

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from ..core import (
    SalesTrendData, DailySalesReport, ProductSalesReport,
    ServiceError, ValidationError
)
from ..repository import RepositoryFactory
from .base_service import BaseService
from logger_config import get_logger

logger = get_logger(__name__)


class AnalyticsService(BaseService):
    """
    Advanced analytics and business intelligence service.
    
    Fitur:
    - Sales trend analysis
    - Peak hours/days detection
    - Product performance ranking
    - Customer analytics
    - Growth percentage calculation
    - Period comparison
    - Forecasting (simple)
    - JSON-ready export for dashboards
    
    Methods:
        get_sales_trend(): Get sales trend for period
        get_peak_hours(): Get peak sales hours
        get_top_products(): Get top selling products
        get_growth_metrics(): Calculate growth % vs previous period
        get_period_comparison(): Compare two periods
        get_customer_analytics(): Analyze customer behavior
        get_revenue_forecast(): Forecast revenue
        export_analytics_json(): Export all analytics as JSON
    """
    
    def __init__(self, repository_factory: RepositoryFactory):
        """Initialize AnalyticsService."""
        super().__init__(repository_factory)
        self.transaction_repo = self.repositories.get('transaction')
        self.product_repo = self.repositories.get('product')
    
    def validate(self) -> bool:
        """Validate AnalyticsService initialization."""
        try:
            if not self.transaction_repo or not self.product_repo:
                raise ServiceError("Transaction or Product repository not available")
            
            self._log_info("AnalyticsService initialized")
            return True
        except Exception as e:
            self._log_error("AnalyticsService initialization failed", e)
            return False
    
    def get_sales_trend(
        self,
        period: str = "daily",
        start_date: datetime = None,
        end_date: datetime = None
    ) -> SalesTrendData:
        """
        Get sales trend for specified period.
        
        Args:
            period (str): "daily", "weekly", or "monthly"
            start_date (datetime): Start of period
            end_date (datetime): End of period
            
        Returns:
            SalesTrendData: Trend data with comparisons
        """
        try:
            # Default to last 30 days
            if not end_date:
                end_date = datetime.now()
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            # Get transactions in period
            transactions = self.transaction_repo.get_by_date_range(start_date, end_date)
            
            if not transactions:
                raise ValidationError("Tidak ada data penjualan untuk periode ini", "period")
            
            # Calculate metrics
            total_revenue = sum(t.total for t in transactions)
            total_transactions = len(transactions)
            avg_transaction_value = total_revenue // max(total_transactions, 1)
            
            # Get previous period data for comparison
            period_delta = self._get_period_delta(period)
            prev_start = start_date - period_delta
            prev_end = start_date
            prev_transactions = self.transaction_repo.get_by_date_range(prev_start, prev_end)
            prev_revenue = sum(t.total for t in prev_transactions)
            
            # Calculate growth %
            growth_percent = 0.0
            if prev_revenue > 0:
                growth_percent = ((total_revenue - prev_revenue) / prev_revenue) * 100
            
            # Find peak hour
            peak_hour = self._get_peak_hour(transactions)
            
            # Find peak day
            peak_day = self._get_peak_day(transactions)
            
            # Payment methods breakdown
            payment_breakdown = self._get_payment_breakdown(transactions)
            
            # Top products
            top_products = self._get_top_products(transactions, limit=5)
            
            return SalesTrendData(
                period=period,
                start_date=start_date,
                end_date=end_date,
                total_revenue=total_revenue,
                total_transactions=total_transactions,
                avg_transaction_value=avg_transaction_value,
                growth_percent=growth_percent,
                peak_hour=peak_hour,
                peak_day=peak_day,
                payment_methods=payment_breakdown,
                top_products=top_products
            )
            
        except Exception as e:
            self._log_error(f"Error calculating sales trend: {e}", e)
            raise ServiceError(f"Gagal menghitung trend penjualan: {str(e)}")
    
    def get_peak_hours(self, start_date: datetime = None, end_date: datetime = None) -> Dict:
        """
        Analyze peak sales hours.
        
        Args:
            start_date (datetime): Start date
            end_date (datetime): End date
            
        Returns:
            dict: Hour-by-hour breakdown
        """
        try:
            if not end_date:
                end_date = datetime.now()
            if not start_date:
                start_date = end_date - timedelta(days=7)
            
            transactions = self.transaction_repo.get_by_date_range(start_date, end_date)
            
            hourly_sales = defaultdict(lambda: {'total': 0, 'count': 0})
            
            for trans in transactions:
                hour = trans.tanggal.hour if hasattr(trans.tanggal, 'hour') else 0
                hourly_sales[hour]['total'] += trans.total
                hourly_sales[hour]['count'] += 1
            
            # Sort by revenue
            sorted_hours = sorted(
                hourly_sales.items(),
                key=lambda x: x[1]['total'],
                reverse=True
            )
            
            result = {}
            for hour, data in sorted_hours:
                result[f"{hour:02d}:00"] = {
                    'total_revenue': data['total'],
                    'transaction_count': data['count'],
                    'avg_transaction': data['total'] // max(data['count'], 1)
                }
            
            return result
            
        except Exception as e:
            self._log_error("Error analyzing peak hours", e)
            return {}
    
    def get_top_products(
        self,
        limit: int = 10,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> List[ProductSalesReport]:
        """
        Get top selling products by revenue.
        
        Args:
            limit (int): Number of products to return
            start_date (datetime): Start date
            end_date (datetime): End date
            
        Returns:
            List[ProductSalesReport]: Top products
        """
        try:
            if not end_date:
                end_date = datetime.now()
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            transactions = self.transaction_repo.get_by_date_range(start_date, end_date)
            
            # Aggregate product data
            product_stats = defaultdict(lambda: {
                'name': '',
                'code': '',
                'qty_sold': 0,
                'revenue': 0,
                'transaction_count': 0
            })
            
            for trans in transactions:
                for item in trans.items:
                    product_id = item.product_id
                    product_stats[product_id]['name'] = item.product_name
                    product_stats[product_id]['code'] = item.product_code
                    product_stats[product_id]['qty_sold'] += item.qty
                    product_stats[product_id]['revenue'] += item.subtotal
                    product_stats[product_id]['transaction_count'] += 1
            
            # Convert to reports and sort
            reports = []
            for product_id, stats in product_stats.items():
                report = ProductSalesReport(
                    product_id=product_id,
                    product_name=stats['name'],
                    product_code=stats['code'],
                    total_qty_sold=stats['qty_sold'],
                    total_revenue=stats['revenue'],
                    total_transactions=stats['transaction_count'],
                    avg_qty_per_transaction=stats['qty_sold'] / max(stats['transaction_count'], 1)
                )
                reports.append(report)
            
            # Sort by revenue descending
            reports.sort(key=lambda r: r.total_revenue, reverse=True)
            
            return reports[:limit]
            
        except Exception as e:
            self._log_error("Error getting top products", e)
            return []
    
    def get_growth_metrics(
        self,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> Dict:
        """
        Calculate growth metrics vs previous period.
        
        Args:
            start_date (datetime): Period start
            end_date (datetime): Period end
            
        Returns:
            dict: Growth metrics
        """
        try:
            if not end_date:
                end_date = datetime.now()
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            # Current period
            current_trans = self.transaction_repo.get_by_date_range(start_date, end_date)
            current_revenue = sum(t.total for t in current_trans)
            current_count = len(current_trans)
            
            # Previous period (same length)
            period_length = (end_date - start_date).days
            prev_start = start_date - timedelta(days=period_length)
            prev_end = start_date
            prev_trans = self.transaction_repo.get_by_date_range(prev_start, prev_end)
            prev_revenue = sum(t.total for t in prev_trans)
            prev_count = len(prev_trans)
            
            # Calculate growth %
            revenue_growth = 0.0
            if prev_revenue > 0:
                revenue_growth = ((current_revenue - prev_revenue) / prev_revenue) * 100
            
            transaction_growth = 0.0
            if prev_count > 0:
                transaction_growth = ((current_count - prev_count) / prev_count) * 100
            
            return {
                'period_days': period_length,
                'current_period': {
                    'revenue': current_revenue,
                    'transactions': current_count,
                    'avg_transaction': current_revenue // max(current_count, 1)
                },
                'previous_period': {
                    'revenue': prev_revenue,
                    'transactions': prev_count,
                    'avg_transaction': prev_revenue // max(prev_count, 1)
                },
                'growth': {
                    'revenue_percent': round(revenue_growth, 2),
                    'transaction_percent': round(transaction_growth, 2),
                    'revenue_increase': current_revenue - prev_revenue,
                    'transaction_increase': current_count - prev_count
                }
            }
            
        except Exception as e:
            self._log_error("Error calculating growth metrics", e)
            return {}
    
    def get_daily_sales_report(self, date: datetime = None) -> DailySalesReport:
        """
        Get daily sales summary.
        
        Args:
            date (datetime): Date to report on
            
        Returns:
            DailySalesReport: Daily summary
        """
        try:
            if not date:
                date = datetime.now()
            
            # Get all transactions for this date
            start = datetime(date.year, date.month, date.day, 0, 0, 0)
            end = start + timedelta(days=1)
            
            transactions = self.transaction_repo.get_by_date_range(start, end)
            
            total_penjualan = sum(t.total for t in transactions)
            total_pajak = sum(t.total_pajak for t in transactions)
            total_diskon = sum(getattr(t, 'total_diskon', 0) for t in transactions)
            total_item = sum(len(t.items) for t in transactions)
            
            # Payment breakdown
            payment_breakdown = self._get_payment_breakdown(transactions)
            
            return DailySalesReport(
                tanggal=date,
                total_transaksi=len(transactions),
                total_item=total_item,
                total_penjualan=total_penjualan,
                total_pajak=total_pajak,
                total_diskon=total_diskon,
                payment_breakdown=payment_breakdown
            )
            
        except Exception as e:
            self._log_error(f"Error generating daily report: {e}", e)
            raise ServiceError(f"Gagal membuat laporan harian: {str(e)}")
    
    def export_analytics_json(
        self,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> Dict:
        """
        Export comprehensive analytics as JSON (for API/Dashboard).
        
        Args:
            start_date (datetime): Start date
            end_date (datetime): End date
            
        Returns:
            dict: Complete analytics data
        """
        try:
            if not end_date:
                end_date = datetime.now()
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            analytics = {
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'summary': self.get_growth_metrics(start_date, end_date),
                'daily': self.get_daily_sales_report().to_dict() if hasattr(self.get_daily_sales_report(), 'to_dict') else {},
                'trend': self._trend_to_dict(self.get_sales_trend('daily', start_date, end_date)),
                'peak_hours': self.get_peak_hours(start_date, end_date),
                'top_products': [
                    {
                        'id': p.product_id,
                        'name': p.product_name,
                        'code': p.product_code,
                        'qty_sold': p.total_qty_sold,
                        'revenue': p.total_revenue,
                        'transactions': p.total_transactions,
                        'avg_qty': round(p.avg_qty_per_transaction, 2)
                    }
                    for p in self.get_top_products(start_date=start_date, end_date=end_date)
                ]
            }
            
            return analytics
            
        except Exception as e:
            self._log_error("Error exporting analytics", e)
            return {}
    
    # ========== HELPER METHODS ==========
    
    def _get_period_delta(self, period: str) -> timedelta:
        """Get timedelta for period."""
        if period == "daily":
            return timedelta(days=1)
        elif period == "weekly":
            return timedelta(weeks=1)
        elif period == "monthly":
            return timedelta(days=30)
        return timedelta(days=1)
    
    def _get_peak_hour(self, transactions) -> Optional[int]:
        """Find peak sales hour."""
        if not transactions:
            return None
        
        hourly = defaultdict(int)
        for trans in transactions:
            if hasattr(trans.tanggal, 'hour'):
                hourly[trans.tanggal.hour] += trans.total
        
        if hourly:
            return max(hourly, key=hourly.get)
        return None
    
    def _get_peak_day(self, transactions) -> Optional[str]:
        """Find peak sales day."""
        if not transactions:
            return None
        
        daily = defaultdict(int)
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        for trans in transactions:
            day_num = trans.tanggal.weekday() if hasattr(trans.tanggal, 'weekday') else 0
            daily[days[day_num]] += trans.total
        
        if daily:
            return max(daily, key=daily.get)
        return None
    
    def _get_payment_breakdown(self, transactions) -> Dict[str, int]:
        """Get sales breakdown by payment method."""
        breakdown = defaultdict(int)
        for trans in transactions:
            method = getattr(trans, 'payment_method', 'cash')
            breakdown[method] += trans.total
        return dict(breakdown)
    
    def _get_top_products(self, transactions, limit=5):
        """Helper to get top products from transactions."""
        product_revenue = defaultdict(int)
        
        for trans in transactions:
            for item in trans.items:
                product_revenue[item.product_name] += item.subtotal
        
        sorted_products = sorted(
            product_revenue.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [
            {'name': name, 'revenue': revenue}
            for name, revenue in sorted_products[:limit]
        ]
    
    def _trend_to_dict(self, trend: SalesTrendData) -> Dict:
        """Convert SalesTrendData to dict."""
        return {
            'period': trend.period,
            'total_revenue': trend.total_revenue,
            'total_transactions': trend.total_transactions,
            'avg_transaction_value': trend.avg_transaction_value,
            'growth_percent': round(trend.growth_percent, 2),
            'peak_hour': trend.peak_hour,
            'peak_day': trend.peak_day,
            'payment_methods': trend.payment_methods,
            'top_products': trend.top_products
        }
