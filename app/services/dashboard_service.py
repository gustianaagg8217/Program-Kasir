# ============================================================================
# DASHBOARD_SERVICE.PY - Real-time Dashboard Data Aggregation
# ============================================================================
# Fungsi: Aggregate dashboard data dari multiple services
# Responsibilitas: Data collection, caching, metrics calculation
# ============================================================================

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from app.services.transaction_service import TransactionService
from app.services.product_service import ProductService
from app.ai.smart_restock import SmartRestock
from app.utils.async_manager import AsyncManager, get_async_manager
from app.utils.error_handler import DatabaseError
from logger_config import get_logger

logger = get_logger(__name__)


class DashboardMetrics:
    """Container untuk dashboard metrics."""
    
    def __init__(self):
        self.today_revenue = 0
        self.today_transactions = 0
        self.today_items_sold = 0
        self.avg_transaction_today = 0
        
        self.week_revenue = 0
        self.week_transactions = 0
        self.week_avg_daily = 0
        
        self.month_revenue = 0
        self.month_transactions = 0
        self.month_avg_daily = 0
        
        self.inventory_value = 0
        self.total_products = 0
        self.low_stock_count = 0
        
        self.top_products = []
        self.revenue_by_method = {}
        
        self.last_updated = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'today': {
                'revenue': self.today_revenue,
                'transactions': self.today_transactions,
                'items_sold': self.today_items_sold,
                'avg_transaction': self.avg_transaction_today
            },
            'week': {
                'revenue': self.week_revenue,
                'transactions': self.week_transactions,
                'avg_daily': self.week_avg_daily
            },
            'month': {
                'revenue': self.month_revenue,
                'transactions': self.month_transactions,
                'avg_daily': self.month_avg_daily
            },
            'inventory': {
                'total_value': self.inventory_value,
                'total_products': self.total_products,
                'low_stock': self.low_stock_count
            },
            'sales': {
                'top_products': self.top_products,
                'revenue_by_method': self.revenue_by_method
            },
            'last_updated': self.last_updated
        }


class DashboardService:
    """
    Service untuk real-time dashboard data aggregation.
    
    Provide:
    - Today's KPIs (revenue, transactions, items)
    - Weekly/monthly trends
    - Inventory status
    - Top products
    - Revenue breakdown
    - Performance metrics
    """
    
    def __init__(
        self,
        trans_service: TransactionService,
        product_service: ProductService,
        restock_service: SmartRestock,
        async_manager: AsyncManager = None
    ):
        """
        Init DashboardService.
        
        Args:
            trans_service: TransactionService instance
            product_service: ProductService instance
            restock_service: SmartRestock instance
            async_manager: AsyncManager instance (optional)
        """
        self.trans_service = trans_service
        self.product_service = product_service
        self.restock_service = restock_service
        self.async_manager = async_manager or get_async_manager()
        self.metrics_cache = None
        self.cache_timestamp = None
        self.cache_ttl = 60  # Cache untuk 60 seconds
        logger.info("DashboardService initialized")
    
    def get_dashboard_data(
        self,
        use_cache: bool = True,
        callback: callable = None
    ) -> str:
        """
        Get dashboard data dalam background.
        
        Args:
            use_cache: Use cached data jika available
            callback: Callback function pada completion
            
        Returns:
            Task ID
        """
        def aggregate():
            logger.info("Aggregating dashboard data")
            
            metrics = DashboardMetrics()
            
            # Today's metrics
            today_summary = self.trans_service.get_daily_summary()
            metrics.today_revenue = today_summary.get('revenue', 0)
            metrics.today_transactions = today_summary.get('total_transactions', 0)
            metrics.today_items_sold = today_summary.get('total_items', 0)
            metrics.avg_transaction_today = self.trans_service.calculate_avg_transaction(
                datetime.now().strftime('%Y-%m-%d'),
                datetime.now().strftime('%Y-%m-%d')
            ).get('avg_value', 0)
            
            # Weekly metrics
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            week_summary = self.trans_service.get_period_summary(start_date, end_date)
            metrics.week_revenue = week_summary.get('revenue', 0)
            metrics.week_transactions = week_summary.get('total_transactions', 1)
            metrics.week_avg_daily = metrics.week_revenue // 7 if metrics.week_revenue > 0 else 0
            
            # Monthly metrics
            start_month = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            month_summary = self.trans_service.get_period_summary(start_month, end_date)
            metrics.month_revenue = month_summary.get('revenue', 0)
            metrics.month_transactions = month_summary.get('total_transactions', 1)
            metrics.month_avg_daily = metrics.month_revenue // 30 if metrics.month_revenue > 0 else 0
            
            # Inventory metrics
            metrics.inventory_value = self.product_service.get_total_inventory_value()
            all_products = self.product_service.list_products(limit=999)
            metrics.total_products = len(all_products)
            low_stock = self.product_service.get_low_stock_products(threshold=10)
            metrics.low_stock_count = len(low_stock)
            
            # Top products (by quantity sold)
            # TODO: Implement actual top products tracking
            # For now, return all products sorted by value
            top_products = sorted(
                [
                    {
                        'kode': p.kode,
                        'nama': p.nama,
                        'qty': p.qty,
                        'harga': p.harga,
                        'total_value': p.qty * p.harga
                    } for p in all_products
                ],
                key=lambda x: x['total_value'],
                reverse=True
            )[:10]
            metrics.top_products = top_products
            
            # Revenue by payment method
            metrics.revenue_by_method = self.trans_service.get_revenue_by_payment_method(
                datetime.now().strftime('%Y-%m-%d'),
                datetime.now().strftime('%Y-%m-%d')
            )
            
            metrics.last_updated = datetime.now().isoformat()
            
            # Cache results
            self.metrics_cache = metrics
            self.cache_timestamp = datetime.now()
            
            logger.info("Dashboard data aggregated successfully")
            return metrics.to_dict()
        
        # Check cache
        if use_cache and self.metrics_cache and self.cache_timestamp:
            age = (datetime.now() - self.cache_timestamp).total_seconds()
            if age < self.cache_ttl:
                logger.info(f"Using cached dashboard data (age={age}s)")
                if callback:
                    callback(self.metrics_cache.to_dict())
                return None
        
        task_id = f"dashboard_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        task = self.async_manager.submit_task(
            task_id=task_id,
            name="Dashboard Metrics",
            func=aggregate,
            callback=callback
        )
        
        return task_id
    
    def get_cached_metrics(self) -> Optional[Dict[str, Any]]:
        """Get cached metrics jika available."""
        if self.metrics_cache:
            return self.metrics_cache.to_dict()
        return None
    
    def get_daily_comparison(
        self,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get daily comparison untuk trend analysis.
        
        Args:
            days: Number of days to compare
            
        Returns:
            Comparison data dictionary
        """
        try:
            comparison = []
            
            for i in range(days, 0, -1):
                date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
                daily = self.trans_service.get_daily_summary(date)
                comparison.append({
                    'date': date,
                    'revenue': daily.get('revenue', 0),
                    'transactions': daily.get('total_transactions', 0),
                    'items': daily.get('total_items', 0)
                })
            
            return {
                'period': f"Last {days} days",
                'data': comparison,
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error getting daily comparison: {e}")
            return {'error': str(e)}
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get overall performance metrics.
        
        Returns:
            Performance metrics
        """
        try:
            today_summary = self.trans_service.get_daily_summary()
            week_summary = self.trans_service.get_period_summary(
                (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
                datetime.now().strftime('%Y-%m-%d')
            )
            month_summary = self.trans_service.get_period_summary(
                (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
                datetime.now().strftime('%Y-%m-%d')
            )
            
            # Calculate growth rates
            week_avg_daily = week_summary.get('revenue', 0) / 7 if week_summary.get('revenue', 0) > 0 else 0
            today_revenue = today_summary.get('revenue', 0)
            today_vs_week_avg = ((today_revenue - week_avg_daily) / week_avg_daily * 100) if week_avg_daily > 0 else 0
            
            month_avg_daily = month_summary.get('revenue', 0) / 30 if month_summary.get('revenue', 0) > 0 else 0
            month_vs_week_avg = ((week_summary.get('revenue', 0) / 7 - month_avg_daily) / month_avg_daily * 100) if month_avg_daily > 0 else 0
            
            return {
                'today': {
                    'revenue': today_revenue,
                    'transactions': today_summary.get('total_transactions', 0),
                    'vs_weekly_avg': f"{today_vs_week_avg:+.1f}%"
                },
                'week': {
                    'revenue': week_summary.get('revenue', 0),
                    'avg_daily': week_avg_daily,
                    'transactions': week_summary.get('total_transactions', 0)
                },
                'month': {
                    'revenue': month_summary.get('revenue', 0),
                    'avg_daily': month_avg_daily,
                    'vs_week_avg': f"{month_vs_week_avg:+.1f}%",
                    'transactions': month_summary.get('total_transactions', 0)
                },
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {'error': str(e)}
    
    def get_health_check(self) -> Dict[str, Any]:
        """
        Get system health check.
        
        Returns:
            Health status
        """
        try:
            health = {
                'status': 'healthy',
                'checks': {},
                'timestamp': datetime.now().isoformat()
            }
            
            # Check database connectivity
            try:
                self.trans_service.get_today_transactions()
                health['checks']['database'] = 'ok'
            except Exception as e:
                health['checks']['database'] = f'error: {e}'
                health['status'] = 'degraded'
            
            # Check inventory
            try:
                all_products = self.product_service.list_products(limit=1)
                health['checks']['inventory'] = 'ok'
            except Exception as e:
                health['checks']['inventory'] = f'error: {e}'
                health['status'] = 'degraded'
            
            # Check restock recommendations
            try:
                recs = self.restock_service.get_restock_recommendations()
                health['checks']['ai_restock'] = 'ok'
            except Exception as e:
                health['checks']['ai_restock'] = f'error: {e}'
            
            return health
        
        except Exception as e:
            logger.error(f"Error checking health: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def clear_cache(self):
        """Clear metrics cache."""
        self.metrics_cache = None
        self.cache_timestamp = None
        logger.info("Dashboard cache cleared")
