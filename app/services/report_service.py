# ============================================================================
# REPORT_SERVICE.PY - Background Report Generation Service
# ============================================================================
# Fungsi: Generate reports dalam background tanpa blocking UI
# Responsibilitas: Report generation, export, scheduling
# ============================================================================

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from app.services.transaction_service import TransactionService
from app.services.product_service import ProductService
from app.utils.async_manager import AsyncManager, get_async_manager
from app.utils.print_manager import PrintManager, get_print_manager
from app.utils.error_handler import DatabaseError
from logger_config import get_logger

logger = get_logger(__name__)


class ReportService:
    """
    Service untuk generate reports dalam background.
    
    Support:
    - Daily/weekly/monthly reports
    - Sales analysis
    - Inventory reports
    - User performance reports
    """
    
    def __init__(
        self,
        trans_service: TransactionService,
        product_service: ProductService,
        async_manager: AsyncManager = None
    ):
        """
        Init ReportService.
        
        Args:
            trans_service: TransactionService instance
            product_service: ProductService instance
            async_manager: AsyncManager instance (optional)
        """
        self.trans_service = trans_service
        self.product_service = product_service
        self.async_manager = async_manager or get_async_manager()
        self.print_manager = get_print_manager()
        logger.info("ReportService initialized")
    
    def generate_daily_report(
        self,
        date: str = None,
        callback: callable = None,
        error_callback: callable = None
    ) -> str:
        """
        Generate daily sales report dalam background.
        
        Args:
            date: Date dalam format 'YYYY-MM-DD' (default: hari ini)
            callback: Success callback function
            error_callback: Error callback function
            
        Returns:
            Task ID untuk monitor progress
        """
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        def generate():
            logger.info(f"Generating daily report untuk {date}")
            
            summary = self.trans_service.get_daily_summary(date)
            revenue_by_method = self.trans_service.get_revenue_by_payment_method(date, date)
            avg_trans = self.trans_service.calculate_avg_transaction(date, date)
            
            report = {
                'report_type': 'daily',
                'date': date,
                'timestamp': datetime.now().isoformat(),
                'summary': summary,
                'revenue_by_method': revenue_by_method,
                'avg_transaction': avg_trans,
                'status': 'completed'
            }
            
            logger.info(f"Daily report generated: {date}")
            return report
        
        task_id = f"daily_report_{date.replace('-', '')}"
        task = self.async_manager.submit_task(
            task_id=task_id,
            name=f"Daily Report {date}",
            func=generate,
            callback=callback,
            error_callback=error_callback
        )
        
        return task_id
    
    def generate_weekly_report(
        self,
        end_date: str = None,
        callback: callable = None
    ) -> str:
        """
        Generate weekly sales report.
        
        Args:
            end_date: End date (default: hari ini)
            callback: Success callback function
            
        Returns:
            Task ID
        """
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=7)).strftime('%Y-%m-%d')
        
        def generate():
            logger.info(f"Generating weekly report: {start_date} to {end_date}")
            
            transactions = self.trans_service.get_transactions_by_date(start_date, end_date)
            summary = self.trans_service.get_period_summary(start_date, end_date)
            revenue_by_method = self.trans_service.get_revenue_by_payment_method(start_date, end_date)
            
            # Daily breakdown
            daily_breakdown = {}
            for day_offset in range(7):
                day = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=6-day_offset)).strftime('%Y-%m-%d')
                daily = self.trans_service.get_daily_summary(day)
                daily_breakdown[day] = daily
            
            report = {
                'report_type': 'weekly',
                'period': f"{start_date} to {end_date}",
                'timestamp': datetime.now().isoformat(),
                'summary': summary,
                'revenue_by_method': revenue_by_method,
                'daily_breakdown': daily_breakdown,
                'transaction_count': len(transactions),
                'status': 'completed'
            }
            
            logger.info(f"Weekly report generated: {start_date} to {end_date}")
            return report
        
        task_id = f"weekly_report_{end_date.replace('-', '')}"
        task = self.async_manager.submit_task(
            task_id=task_id,
            name=f"Weekly Report ({start_date} to {end_date})",
            func=generate,
            callback=callback
        )
        
        return task_id
    
    def generate_monthly_report(
        self,
        year_month: str = None,
        callback: callable = None
    ) -> str:
        """
        Generate monthly sales report.
        
        Args:
            year_month: Year-month dalam format 'YYYY-MM' (default: bulan ini)
            callback: Success callback function
            
        Returns:
            Task ID
        """
        if not year_month:
            year_month = datetime.now().strftime('%Y-%m')
        
        start_date = f"{year_month}-01"
        year, month = map(int, year_month.split('-'))
        if month == 12:
            next_date = datetime(year + 1, 1, 1)
        else:
            next_date = datetime(year, month + 1, 1)
        end_date = (next_date - timedelta(days=1)).strftime('%Y-%m-%d')
        
        def generate():
            logger.info(f"Generating monthly report: {year_month}")
            
            transactions = self.trans_service.get_transactions_by_date(start_date, end_date)
            summary = self.trans_service.get_period_summary(start_date, end_date)
            revenue_by_method = self.trans_service.get_revenue_by_payment_method(start_date, end_date)
            
            # Weekly breakdown
            weekly_breakdown = {}
            current = datetime.strptime(start_date, '%Y-%m-%d')
            while current <= datetime.strptime(end_date, '%Y-%m-%d'):
                week_start = current.strftime('%Y-%m-%d')
                week_end = (current + timedelta(days=6)).strftime('%Y-%m-%d')
                if datetime.strptime(week_end, '%Y-%m-%d') > datetime.strptime(end_date, '%Y-%m-%d'):
                    week_end = end_date
                
                week_summary = self.trans_service.get_period_summary(week_start, week_end)
                weekly_breakdown[week_start] = week_summary
                
                current += timedelta(days=7)
            
            report = {
                'report_type': 'monthly',
                'period': year_month,
                'timestamp': datetime.now().isoformat(),
                'summary': summary,
                'revenue_by_method': revenue_by_method,
                'weekly_breakdown': weekly_breakdown,
                'transaction_count': len(transactions),
                'status': 'completed'
            }
            
            logger.info(f"Monthly report generated: {year_month}")
            return report
        
        task_id = f"monthly_report_{year_month.replace('-', '')}"
        task = self.async_manager.submit_task(
            task_id=task_id,
            name=f"Monthly Report ({year_month})",
            func=generate,
            callback=callback
        )
        
        return task_id
    
    def generate_inventory_report(
        self,
        callback: callable = None
    ) -> str:
        """
        Generate inventory status report.
        
        Returns:
            Task ID
        """
        def generate():
            logger.info("Generating inventory report")
            
            all_products = self.product_service.list_products(limit=999)
            total_value = self.product_service.get_total_inventory_value()
            
            low_stock = self.product_service.get_low_stock_products(threshold=10)
            
            inventory_list = []
            for product in all_products:
                inventory_list.append({
                    'kode': product.kode,
                    'nama': product.nama,
                    'qty': product.qty,
                    'harga': product.harga,
                    'total_value': product.qty * product.harga,
                    'satuan': product.satuan,
                    'status': 'low' if product.id in [p.id for p in low_stock] else 'ok'
                })
            
            # Sort by total value descending
            inventory_list.sort(key=lambda x: x['total_value'], reverse=True)
            
            report = {
                'report_type': 'inventory',
                'timestamp': datetime.now().isoformat(),
                'total_products': len(all_products),
                'total_inventory_value': total_value,
                'low_stock_count': len(low_stock),
                'inventory_list': inventory_list,
                'low_stock_items': [
                    {
                        'kode': p.kode,
                        'nama': p.nama,
                        'qty': p.qty,
                        'harga': p.harga
                    } for p in low_stock
                ],
                'status': 'completed'
            }
            
            logger.info("Inventory report generated")
            return report
        
        task_id = f"inventory_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        task = self.async_manager.submit_task(
            task_id=task_id,
            name="Inventory Report",
            func=generate,
            callback=callback
        )
        
        return task_id
    
    def get_report(self, task_id: str, timeout: float = None) -> Optional[Dict[str, Any]]:
        """
        Get report result.
        
        Args:
            task_id: Task ID dari generate function
            timeout: Timeout dalam seconds
            
        Returns:
            Report dictionary atau None jika belum selesai
        """
        try:
            return self.async_manager.get_task_result(task_id, timeout=timeout)
        except Exception as e:
            logger.error(f"Error getting report {task_id}: {e}")
            return None
    
    def export_report_as_text(
        self,
        report: Dict[str, Any],
        output_file: str = None
    ) -> str:
        """
        Export report ke text file.
        
        Args:
            report: Report dictionary
            output_file: Output file path
            
        Returns:
            File path
        """
        try:
            if not output_file:
                output_file = f"reports/report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            
            from pathlib import Path
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            
            # Format report sebagai text
            content = f"""
REPORT: {report.get('report_type', 'unknown').upper()}
Date: {report.get('timestamp', 'N/A')}
Period: {report.get('period', report.get('date', 'N/A'))}

{str(report)}
"""
            
            Path(output_file).write_text(content)
            logger.info(f"Report exported: {output_file}")
            return output_file
        
        except Exception as e:
            logger.error(f"Error exporting report: {e}")
            return None
    
    def get_all_reports(self) -> List[Dict]:
        """Get semua report tasks dengan status."""
        tasks = self.async_manager.get_all_tasks()
        reports = []
        
        for task in tasks:
            if 'report' in task.name.lower():
                reports.append(task.to_dict())
        
        return reports
