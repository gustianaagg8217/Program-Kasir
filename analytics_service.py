# ============================================================================
# ANALYTICS_SERVICE.PY - Business Intelligence & Data Analytics
# ============================================================================
# Fungsi: Provide actionable business insights from transaction data
# Fitur: Trends, forecasts, peak hours, product performance, comparisons
# ============================================================================

from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import json

from logger_config import get_logger

logger = get_logger(__name__)


# ============================================================================
# ENUMS & DATA MODELS
# ============================================================================

class PeriodType(Enum):
    """Analysis period types"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


@dataclass
class SalesTrend:
    """Sales trend data"""
    period: str
    total_sales: float
    transaction_count: int
    avg_transaction: float
    growth_percentage: float  # vs previous period
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class ProductPerformance:
    """Product performance metrics"""
    product_id: int
    product_name: str
    units_sold: int
    total_revenue: float
    avg_price: float
    rank: int = 0
    trend: str = "stable"  # up, down, stable
    revenue_percentage: float = 0.0  # % of total


@dataclass
class PeakHourData:
    """Peak sales hour analysis"""
    hour: int
    transactions: int
    total_sales: float
    avg_transaction: float


@dataclass
class CustomerInsight:
    """Customer behavior insight"""
    metric_name: str
    value: float
    comparison: float = 0.0  # vs previous period
    change_percentage: float = 0.0


# ============================================================================
# ANALYTICS SERVICE
# ============================================================================

class AnalyticsService:
    """
    Service for business analytics and reporting
    
    Features:
    - Sales trends & forecasting
    - Product performance ranking
    - Peak sales hour analysis
    - Customer behavior analytics
    - Period-over-period comparison
    - JSON API-ready data formatting
    """
    
    def __init__(self, db_manager):
        """
        Initialize analytics service
        
        Args:
            db_manager: DatabaseManager instance
        """
        self.db = db_manager
        logger.info("✅ AnalyticsService initialized")
    
    # ========================================================================
    # SALES TRENDS
    # ========================================================================
    
    def get_sales_trend(self, period_type: PeriodType = PeriodType.DAILY, 
                        periods: int = 7) -> List[SalesTrend]:
        """
        Get sales trend for specified periods
        
        Args:
            period_type: daily/weekly/monthly/yearly
            periods: Number of periods to fetch
        
        Returns:
            List of SalesTrend objects
        
        Example:
            trends = service.get_sales_trend(PeriodType.DAILY, 7)
            # Returns last 7 days of sales data with growth %
        """
        try:
            trends = []
            now = datetime.now()
            
            for i in range(periods, 0, -1):
                # Calculate period dates
                if period_type == PeriodType.DAILY:
                    start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0)
                    end = start + timedelta(days=1)
                    period_str = start.strftime('%Y-%m-%d')
                elif period_type == PeriodType.WEEKLY:
                    start = now - timedelta(days=now.weekday() + 7*i)
                    end = start + timedelta(days=7)
                    period_str = f"Week {start.strftime('%Y-%W')}"
                elif period_type == PeriodType.MONTHLY:
                    month = (now.month - i) % 12 or 12
                    year = now.year - (i // 12) if i > now.month else now.year
                    start = datetime(year, month, 1)
                    if month == 12:
                        end = datetime(year + 1, 1, 1)
                    else:
                        end = datetime(year, month + 1, 1)
                    period_str = start.strftime('%Y-%m')
                else:  # YEARLY
                    year = now.year - i
                    start = datetime(year, 1, 1)
                    end = datetime(year + 1, 1, 1)
                    period_str = str(year)
                
                # Get data for period
                data = self.db.get_sales_for_period(start.isoformat(), end.isoformat())
                
                total_sales = data.get('total', 0) if data else 0
                transaction_count = data.get('count', 0) if data else 0
                avg_transaction = total_sales / transaction_count if transaction_count > 0 else 0
                
                # Calculate growth vs previous period
                prev_data = self.db.get_sales_for_period(
                    (start - (end - start)).isoformat(),
                    start.isoformat()
                )
                prev_total = prev_data.get('total', 0) if prev_data else 0
                
                growth = ((total_sales - prev_total) / prev_total * 100) if prev_total > 0 else 0
                
                trend = SalesTrend(
                    period=period_str,
                    total_sales=total_sales,
                    transaction_count=transaction_count,
                    avg_transaction=avg_transaction,
                    growth_percentage=round(growth, 2)
                )
                trends.append(trend)
            
            logger.info(f"✅ Sales trend calculated: {len(trends)} periods")
            return trends
            
        except Exception as e:
            logger.error(f"Error calculating sales trend: {e}")
            return []
    
    def get_sales_trend_json(self, period_type: PeriodType = PeriodType.DAILY, 
                            periods: int = 7) -> Dict:
        """Get sales trend as JSON (API-ready)"""
        try:
            trends = self.get_sales_trend(period_type, periods)
            return {
                'period_type': period_type.value,
                'data': [
                    {
                        'period': t.period,
                        'total_sales': t.total_sales,
                        'transaction_count': t.transaction_count,
                        'avg_transaction': round(t.avg_transaction, 2),
                        'growth_percentage': t.growth_percentage
                    }
                    for t in trends
                ],
                'summary': {
                    'total_periods': len(trends),
                    'total_sales': sum(t.total_sales for t in trends),
                    'avg_growth': round(sum(t.growth_percentage for t in trends) / len(trends), 2) if trends else 0
                }
            }
        except Exception as e:
            logger.error(f"Error formatting trend JSON: {e}")
            return {}
    
    # ========================================================================
    # PRODUCT PERFORMANCE
    # ========================================================================
    
    def get_top_products(self, limit: int = 10, start_date: str = None, 
                        end_date: str = None) -> List[ProductPerformance]:
        """
        Get top-selling products
        
        Args:
            limit: Number of products
            start_date: Optional filter (YYYY-MM-DD)
            end_date: Optional filter (YYYY-MM-DD)
        
        Returns:
            Sorted list of ProductPerformance objects
        """
        try:
            # Get total revenue for percentage calculation
            total_data = self.db.get_sales_for_period(start_date, end_date)
            total_revenue = total_data.get('total', 0) if total_data else 0
            
            # Get products
            products = self.db.get_produk_terlaris(limit, start_date, end_date)
            
            performances = []
            for idx, p in enumerate(products, 1):
                perf = ProductPerformance(
                    product_id=p.get('id'),
                    product_name=p.get('nama'),
                    units_sold=p.get('total_qty', 0),
                    total_revenue=p.get('total_revenue', 0),
                    avg_price=p.get('total_revenue', 0) / p.get('total_qty', 1) if p.get('total_qty', 0) > 0 else 0,
                    rank=idx,
                    revenue_percentage=(p.get('total_revenue', 0) / total_revenue * 100) if total_revenue > 0 else 0
                )
                performances.append(perf)
            
            logger.info(f"✅ Top products calculated: {len(performances)} items")
            return performances
            
        except Exception as e:
            logger.error(f"Error getting top products: {e}")
            return []
    
    def get_top_products_json(self, limit: int = 10) -> Dict:
        """Get top products as JSON (API-ready)"""
        try:
            products = self.get_top_products(limit)
            return {
                'top_products': [
                    {
                        'rank': p.rank,
                        'product_id': p.product_id,
                        'product_name': p.product_name,
                        'units_sold': p.units_sold,
                        'total_revenue': p.total_revenue,
                        'avg_price': round(p.avg_price, 2),
                        'revenue_percentage': round(p.revenue_percentage, 2)
                    }
                    for p in products
                ],
                'total_revenue': sum(p.total_revenue for p in products)
            }
        except Exception as e:
            logger.error(f"Error formatting products JSON: {e}")
            return {}
    
    # ========================================================================
    # PEAK HOURS ANALYSIS
    # ========================================================================
    
    def get_peak_hours(self, date: str = None) -> List[PeakHourData]:
        """
        Analyze peak sales hours
        
        Args:
            date: Optional specific date (YYYY-MM-DD), defaults to today
        
        Returns:
            List of PeakHourData sorted by sales volume
        """
        try:
            peak_data = self.db.get_peak_hours(date)
            
            peak_hours = []
            for hour_data in peak_data:
                hour = hour_data.get('hour')
                transactions = hour_data.get('transaction_count', 0)
                total = hour_data.get('total_sales', 0)
                avg_trans = total / transactions if transactions > 0 else 0
                
                peak = PeakHourData(
                    hour=hour,
                    transactions=transactions,
                    total_sales=total,
                    avg_transaction=avg_trans
                )
                peak_hours.append(peak)
            
            # Sort by total sales
            peak_hours.sort(key=lambda x: x.total_sales, reverse=True)
            
            logger.info(f"✅ Peak hours calculated: {len(peak_hours)} hours")
            return peak_hours
            
        except Exception as e:
            logger.error(f"Error calculating peak hours: {e}")
            return []
    
    def get_peak_hours_json(self, date: str = None) -> Dict:
        """Get peak hours as JSON"""
        try:
            peak_hours = self.get_peak_hours(date)
            
            # Find peak hour
            if peak_hours:
                top_hour = peak_hours[0]
                peak_label = f"{top_hour.hour:02d}:00 - {top_hour.hour:02d}:59"
            else:
                peak_label = "N/A"
            
            return {
                'date': date or datetime.now().strftime('%Y-%m-%d'),
                'peak_hour': peak_label,
                'hourly_data': [
                    {
                        'hour': f"{p.hour:02d}:00",
                        'transactions': p.transactions,
                        'total_sales': p.total_sales,
                        'avg_transaction': round(p.avg_transaction, 2)
                    }
                    for p in peak_hours
                ]
            }
        except Exception as e:
            logger.error(f"Error formatting peak hours JSON: {e}")
            return {}
    
    # ========================================================================
    # CUSTOMER INSIGHTS
    # ========================================================================
    
    def get_customer_metrics(self) -> Dict[str, CustomerInsight]:
        """
        Get customer behavior metrics
        
        Returns:
            {
                'avg_transaction_value': {...},
                'transactions_per_day': {...},
                'avg_items_per_transaction': {...},
                'customer_retention': {...}
            }
        """
        try:
            metrics = {}
            
            # Average transaction value
            today_data = self.db.get_sales_for_period(
                datetime.now().replace(hour=0, minute=0, second=0).isoformat(),
                datetime.now().isoformat()
            )
            yesterday_data = self.db.get_sales_for_period(
                (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0).isoformat(),
                (datetime.now() - timedelta(days=1)).replace(hour=23, minute=59, second=59).isoformat()
            )
            
            today_avg = today_data.get('avg', 0) if today_data else 0
            yesterday_avg = yesterday_data.get('avg', 0) if yesterday_data else 0
            change = ((today_avg - yesterday_avg) / yesterday_avg * 100) if yesterday_avg > 0 else 0
            
            metrics['avg_transaction_value'] = CustomerInsight(
                metric_name='Average Transaction Value',
                value=today_avg,
                comparison=yesterday_avg,
                change_percentage=round(change, 2)
            )
            
            # Transactions per day
            trans_today = today_data.get('count', 0) if today_data else 0
            trans_yesterday = yesterday_data.get('count', 0) if yesterday_data else 0
            change = ((trans_today - trans_yesterday) / trans_yesterday * 100) if trans_yesterday > 0 else 0
            
            metrics['daily_transactions'] = CustomerInsight(
                metric_name='Daily Transactions',
                value=trans_today,
                comparison=trans_yesterday,
                change_percentage=round(change, 2)
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting customer metrics: {e}")
            return {}
    
    # ========================================================================
    # COMPARATIVE ANALYTICS
    # ========================================================================
    
    def compare_periods(self, period1_start: str, period1_end: str,
                       period2_start: str, period2_end: str) -> Dict:
        """
        Compare two periods (e.g., last month vs this month)
        
        Returns:
            {
                'period1': {...sales data...},
                'period2': {...sales data...},
                'comparison': {...metrics...}
            }
        """
        try:
            data1 = self.db.get_sales_for_period(period1_start, period1_end)
            data2 = self.db.get_sales_for_period(period2_start, period2_end)
            
            if not data1 or not data2:
                return {}
            
            sales_growth = ((data2.get('total', 0) - data1.get('total', 0)) / data1.get('total', 1) * 100)
            trans_growth = ((data2.get('count', 0) - data1.get('count', 0)) / data1.get('count', 1) * 100)
            avg_growth = ((data2.get('avg', 0) - data1.get('avg', 0)) / data1.get('avg', 1) * 100)
            
            return {
                'period1': {
                    'start_date': period1_start,
                    'end_date': period1_end,
                    'total_sales': data1.get('total', 0),
                    'transactions': data1.get('count', 0),
                    'avg_transaction': round(data1.get('avg', 0), 2)
                },
                'period2': {
                    'start_date': period2_start,
                    'end_date': period2_end,
                    'total_sales': data2.get('total', 0),
                    'transactions': data2.get('count', 0),
                    'avg_transaction': round(data2.get('avg', 0), 2)
                },
                'comparison': {
                    'sales_growth_percentage': round(sales_growth, 2),
                    'transaction_growth_percentage': round(trans_growth, 2),
                    'avg_transaction_growth_percentage': round(avg_growth, 2)
                }
            }
            
        except Exception as e:
            logger.error(f"Error comparing periods: {e}")
            return {}
    
    # ========================================================================
    # DASHBOARD SUMMARY (Unified API)
    # ========================================================================
    
    def get_analytics_dashboard(self) -> Dict:
        """
        Get complete analytics dashboard (all metrics in one call)
        
        Returns:
            Complete dashboard with all analytics
        """
        try:
            today = datetime.now()
            yesterday = today - timedelta(days=1)
            last_month = today - timedelta(days=30)
            
            return {
                'timestamp': today.isoformat(),
                'trends': self.get_sales_trend_json(PeriodType.DAILY, 7),
                'top_products': self.get_top_products_json(10),
                'peak_hours': self.get_peak_hours_json(),
                'customer_metrics': {
                    k: asdict(v) for k, v in self.get_customer_metrics().items()
                },
                'month_comparison': self.compare_periods(
                    (today - timedelta(days=60)).strftime('%Y-%m-%d'),
                    (today - timedelta(days=30)).strftime('%Y-%m-%d'),
                    (today - timedelta(days=30)).strftime('%Y-%m-%d'),
                    today.strftime('%Y-%m-%d')
                )
            }
            
        except Exception as e:
            logger.error(f"Error generating dashboard: {e}")
            return {}


if __name__ == "__main__":
    logger.info("Analytics Service module loaded")
