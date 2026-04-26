# ============================================================================
# GUI SERVICES INTEGRATION MODULE
# ============================================================================
# Tujuan: Initialize dan manage semua Phase 4-5 services untuk GUI
# Status: Phase 5 Integration ✅
# ============================================================================

import sys
from typing import Optional, Dict, Callable, Any
from logging import Logger

from app.repositories.product_repository import ProductRepository
from app.repositories.user_repository import UserRepository
from app.repositories.transaction_repository import TransactionRepository

from app.services.product_service import ProductService
from app.services.user_service import UserService
from app.services.transaction_service import TransactionService
from app.services.report_service import ReportService
from app.services.dashboard_service import DashboardService

from app.ai.smart_restock import SmartRestock
from app.utils.async_manager import get_async_manager, AsyncManager
from app.utils.session_manager import get_session_manager, SessionManager
from app.utils.print_manager import get_print_manager, PrintManager
from app.utils.error_handler import get_error_handler, ErrorHandler
from app.utils.password_manager import PasswordManager

from database import DatabaseManager
from logger_config import get_logger

logger = get_logger(__name__)


class GUIServicesManager:
    """
    Centralized manager untuk semua Phase 4-5 services.
    
    Handles:
    - Service initialization
    - Session management
    - Error handling
    - Async operations
    - Printing
    
    Gunakan:
        manager = GUIServicesManager(db_manager)
        manager.init_services()
        
        # Access services
        manager.product_service
        manager.transaction_service
        manager.session_manager
        etc.
    """
    
    def __init__(self, db_manager: DatabaseManager, logger_instance: Optional[Logger] = None):
        """
        Initialize GUI Services Manager.
        
        Args:
            db_manager: DatabaseManager instance
            logger_instance: Optional logger instance
        """
        self.db_manager = db_manager
        self.logger = logger_instance or logger
        
        # Services (akan diinit di init_services)
        self.product_service: Optional[ProductService] = None
        self.user_service: Optional[UserService] = None
        self.transaction_service: Optional[TransactionService] = None
        self.report_service: Optional[ReportService] = None
        self.dashboard_service: Optional[DashboardService] = None
        self.restock_service: Optional[SmartRestock] = None
        
        # Utilities
        self.async_manager: Optional[AsyncManager] = None
        self.session_manager: Optional[SessionManager] = None
        self.print_manager: Optional[PrintManager] = None
        self.error_handler: Optional[ErrorHandler] = None
        self.password_manager: Optional[PasswordManager] = None
        
        self.logger.info("GUIServicesManager initialized")
    
    def init_services(self, max_workers: int = 5, timeout_minutes: int = 30) -> bool:
        """
        Initialize semua services.
        
        Args:
            max_workers: Max threads untuk AsyncManager
            timeout_minutes: Session timeout dalam minutes
        
        Returns:
            bool: True jika berhasil, False jika error
        """
        try:
            self.logger.info("Initializing all services...")
            
            # 1. Initialize repositories
            self.logger.debug("Initializing repositories...")
            product_repo = ProductRepository(self.db_manager)
            user_repo = UserRepository(self.db_manager)
            trans_repo = TransactionRepository(self.db_manager)
            
            # 2. Initialize services
            self.logger.debug("Initializing services...")
            self.product_service = ProductService(product_repo)
            self.user_service = UserService(user_repo)
            self.transaction_service = TransactionService(trans_repo, self.product_service)
            self.restock_service = SmartRestock(self.product_service)
            
            # 3. Initialize async manager
            self.logger.debug("Initializing AsyncManager...")
            self.async_manager = get_async_manager(max_workers=max_workers)
            
            # 4. Initialize reporting & dashboard (depends on async)
            self.logger.debug("Initializing ReportService and DashboardService...")
            self.report_service = ReportService(
                self.transaction_service,
                self.product_service,
                self.async_manager
            )
            self.dashboard_service = DashboardService(
                self.transaction_service,
                self.product_service,
                self.restock_service,
                self.async_manager
            )
            
            # 5. Initialize utilities
            self.logger.debug("Initializing utilities...")
            self.session_manager = get_session_manager(timeout_minutes=timeout_minutes)
            self.print_manager = get_print_manager()
            self.error_handler = get_error_handler()
            self.password_manager = PasswordManager()
            
            self.logger.info("✅ All services initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize services: {e}", exc_info=True)
            return False
    
    def create_user_session(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Create session untuk user setelah login.
        
        Args:
            username: Username user
        
        Returns:
            Dict dengan user info, atau None jika gagal
        """
        try:
            user = self.user_service.get_user_by_username(username)
            if user:
                session_info = self.session_manager.create_session(user)
                self.logger.info(f"✅ Session created for {username}")
                return session_info.to_dict()
            else:
                self.logger.warning(f"User not found: {username}")
                return None
        except Exception as e:
            self.logger.error(f"Failed to create session: {e}")
            return None
    
    def destroy_user_session(self) -> bool:
        """
        Destroy current user session.
        
        Returns:
            bool: True jika berhasil
        """
        try:
            self.session_manager.destroy_session()
            self.logger.info("✅ Session destroyed")
            return True
        except Exception as e:
            self.logger.error(f"Failed to destroy session: {e}")
            return False
    
    def check_permission(self, permission: str) -> bool:
        """
        Check if current user has permission.
        
        Args:
            permission: Permission name
        
        Returns:
            bool: True jika user punya permission
        """
        try:
            return self.session_manager.has_permission(permission)
        except Exception as e:
            self.logger.error(f"Permission check failed: {e}")
            return False
    
    def require_permission(self, permission: str) -> bool:
        """
        Require permission, raise error jika tidak punya.
        
        Args:
            permission: Permission name
        
        Returns:
            bool: True jika punya permission
        
        Raises:
            PermissionError: Jika tidak punya permission
        """
        try:
            self.session_manager.require_permission(permission)
            return True
        except Exception as e:
            self.logger.warning(f"Permission denied: {permission}")
            raise
    
    def is_admin(self) -> bool:
        """Check if current user is admin."""
        return self.session_manager.is_admin()
    
    def is_cashier(self) -> bool:
        """Check if current user is cashier."""
        return self.session_manager.is_cashier()
    
    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated."""
        return self.session_manager.is_authenticated()
    
    def submit_background_task(
        self,
        task_id: str,
        task_name: str,
        func: Callable,
        args: tuple = (),
        on_success: Optional[Callable] = None,
        on_error: Optional[Callable] = None
    ) -> str:
        """
        Submit background task (non-blocking operation).
        
        Args:
            task_id: Unique task ID
            task_name: Readable task name
            func: Function to execute
            args: Function arguments
            on_success: Callback on success
            on_error: Callback on error
        
        Returns:
            str: Task ID
        """
        return self.async_manager.submit_task(
            task_id=task_id,
            name=task_name,
            func=func,
            args=args,
            on_success=on_success,
            on_error=on_error
        )
    
    def get_task_result(self, task_id: str) -> Any:
        """Get result dari completed task."""
        return self.async_manager.get_task_result(task_id)
    
    def get_task_status(self, task_id: str) -> Optional[str]:
        """Get status dari task."""
        task = self.async_manager.get_task(task_id)
        return task.status if task else None
    
    def shutdown(self) -> None:
        """Shutdown semua services gracefully."""
        try:
            self.logger.info("Shutting down services...")
            
            # Destroy session
            if self.session_manager and self.session_manager.is_authenticated():
                self.destroy_user_session()
            
            # Shutdown async manager
            if self.async_manager:
                self.async_manager.shutdown()
            
            self.logger.info("✅ All services shut down successfully")
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
    
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Get current logged-in user info."""
        try:
            return self.session_manager.get_current_user()
        except Exception as e:
            self.logger.error(f"Failed to get current user: {e}")
            return None
    
    def get_dashboard_metrics(self, callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Get dashboard metrics.
        
        Args:
            callback: Optional callback when metrics ready
        
        Returns:
            Dict dengan metrics
        """
        try:
            cached = self.dashboard_service.get_cached_metrics()
            if cached:
                self.logger.debug("Using cached dashboard metrics")
                return cached
            
            # Get fresh metrics (async)
            if callback:
                self.dashboard_service.get_dashboard_data(callback=callback)
                return {"status": "loading"}
            else:
                return self.dashboard_service.get_dashboard_data()
        except Exception as e:
            self.logger.error(f"Failed to get dashboard metrics: {e}")
            return {}
    
    def generate_report(self, report_type: str, callback: Optional[Callable] = None) -> str:
        """
        Generate report (background operation).
        
        Args:
            report_type: 'daily', 'weekly', atau 'monthly'
            callback: Optional callback when report ready
        
        Returns:
            str: Task ID
        """
        try:
            if report_type == 'daily':
                task_id = self.report_service.generate_daily_report(callback=callback)
            elif report_type == 'weekly':
                task_id = self.report_service.generate_weekly_report(callback=callback)
            elif report_type == 'monthly':
                task_id = self.report_service.generate_monthly_report(callback=callback)
            else:
                raise ValueError(f"Unknown report type: {report_type}")
            
            self.logger.info(f"Report generation started: {report_type} (task: {task_id})")
            return task_id
        except Exception as e:
            self.logger.error(f"Failed to generate report: {e}")
            return ""


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_gui_services_manager: Optional[GUIServicesManager] = None


def get_gui_services() -> Optional[GUIServicesManager]:
    """Get singleton GUI Services Manager instance."""
    return _gui_services_manager


def init_gui_services(db_manager: DatabaseManager) -> GUIServicesManager:
    """
    Initialize and return GUI Services Manager singleton.
    
    Args:
        db_manager: DatabaseManager instance
    
    Returns:
        GUIServicesManager instance
    """
    global _gui_services_manager
    
    _gui_services_manager = GUIServicesManager(db_manager)
    _gui_services_manager.init_services()
    
    return _gui_services_manager


# ============================================================================
# END OF GUI SERVICES INTEGRATION MODULE
# ============================================================================
