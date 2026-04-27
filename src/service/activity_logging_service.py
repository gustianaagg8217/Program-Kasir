# ============================================================================
# ACTIVITY_LOGGING_SERVICE.PY - Activity Logging & Audit Trail (Service Layer)
# ============================================================================
# Fungsi: Track user activities untuk security dan compliance
# Log: login, logout, transactions, product changes, access violations
# ============================================================================

from typing import List, Optional, Dict
from datetime import datetime
import json

from ..core import (
    ActivityLog, User,
    ValidationError, ServiceError
)
from ..repository import RepositoryFactory
from .base_service import BaseService
from logger_config import get_logger

logger = get_logger(__name__)


class ActivityLoggingService(BaseService):
    """
    Service untuk activity logging & audit trail.
    
    Fitur:
    - User activity tracking
    - Transaction logging
    - Product change logging
    - Access violation tracking
    - Audit report generation
    - Data encryption for sensitive info
    
    Methods:
        log_activity(): Log user activity
        log_login(): Log user login
        log_logout(): Log user logout
        log_transaction(): Log transaction
        log_product_change(): Log product modification
        log_access_violation(): Log unauthorized access attempt
        get_activity_log(): Get activity history
        get_user_activity(): Get specific user activities
        generate_audit_report(): Generate audit report
    """
    
    def __init__(self, repository_factory: RepositoryFactory):
        """Initialize ActivityLoggingService."""
        super().__init__(repository_factory)
        self.activity_repo = self.repositories.get('activity')
    
    def validate(self) -> bool:
        """Validate ActivityLoggingService initialization."""
        try:
            self._log_info("ActivityLoggingService initialized")
            return True
        except Exception as e:
            self._log_error("ActivityLoggingService initialization failed", e)
            return False
    
    def log_activity(
        self,
        user_id: int = None,
        username: str = "",
        action: str = "",
        resource_type: str = "",
        resource_id: str = "",
        details: dict = None,
        status: str = "success",
        ip_address: str = "",
        user_agent: str = ""
    ) -> ActivityLog:
        """
        Log user activity to database.
        
        Args:
            user_id (int): User ID
            username (str): Username
            action (str): Action performed (login, create_transaction, delete_product, etc)
            resource_type (str): Type of resource (transaction, product, user, etc)
            resource_id (str): ID of the resource
            details (dict): Additional details as dict
            status (str): success or failure
            ip_address (str): User's IP address
            user_agent (str): Browser user agent
            
        Returns:
            ActivityLog: Activity log record
        """
        try:
            # Serialize details
            details_str = json.dumps(details or {})
            
            # Create activity log
            activity = ActivityLog(
                user_id=user_id,
                username=username,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details_str,
                status=status,
                timestamp=datetime.now(),
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Save to database if repository available
            if self.activity_repo:
                try:
                    activity = self.activity_repo.create(
                        user_id=user_id,
                        username=username,
                        action=action,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        details=details_str,
                        status=status,
                        ip_address=ip_address,
                        user_agent=user_agent
                    )
                except Exception as e:
                    self._log_warning(f"Could not save activity to database: {e}")
            
            self._log_info(f"Activity logged: {activity}")
            return activity
            
        except Exception as e:
            self._log_error(f"Error logging activity: {e}", e)
            raise ServiceError(f"Gagal mencatat aktivitas: {str(e)}")
    
    def log_login(self, user_id: int, username: str, ip_address: str = "") -> ActivityLog:
        """
        Log user login.
        
        Args:
            user_id (int): User ID
            username (str): Username
            ip_address (str): IP address
            
        Returns:
            ActivityLog: Login log
        """
        return self.log_activity(
            user_id=user_id,
            username=username,
            action="login",
            resource_type="user",
            resource_id=str(user_id),
            status="success",
            ip_address=ip_address,
            details={'event': 'user login'}
        )
    
    def log_logout(self, user_id: int, username: str) -> ActivityLog:
        """
        Log user logout.
        
        Args:
            user_id (int): User ID
            username (str): Username
            
        Returns:
            ActivityLog: Logout log
        """
        return self.log_activity(
            user_id=user_id,
            username=username,
            action="logout",
            resource_type="user",
            resource_id=str(user_id),
            status="success",
            details={'event': 'user logout'}
        )
    
    def log_failed_login(self, username: str, ip_address: str = "", reason: str = "") -> ActivityLog:
        """
        Log failed login attempt.
        
        Args:
            username (str): Username
            ip_address (str): IP address
            reason (str): Reason for failure
            
        Returns:
            ActivityLog: Failed login log
        """
        return self.log_activity(
            username=username,
            action="login_failed",
            resource_type="user",
            status="failure",
            ip_address=ip_address,
            details={'reason': reason, 'event': 'failed login attempt'}
        )
    
    def log_transaction(
        self,
        user_id: int,
        username: str,
        transaction_id: int,
        action: str,
        total: int,
        item_count: int,
        status: str = "success"
    ) -> ActivityLog:
        """
        Log transaction activity.
        
        Args:
            user_id (int): Cashier user ID
            username (str): Cashier username
            transaction_id (int): Transaction ID
            action (str): create, complete, cancel, refund, etc
            total (int): Transaction total
            item_count (int): Number of items
            status (str): success or failure
            
        Returns:
            ActivityLog: Transaction log
        """
        return self.log_activity(
            user_id=user_id,
            username=username,
            action=f"transaction_{action}",
            resource_type="transaction",
            resource_id=str(transaction_id),
            status=status,
            details={
                'transaction_id': transaction_id,
                'total': total,
                'item_count': item_count
            }
        )
    
    def log_product_change(
        self,
        user_id: int,
        username: str,
        product_id: int,
        action: str,
        before_state: dict = None,
        after_state: dict = None
    ) -> ActivityLog:
        """
        Log product modification.
        
        Args:
            user_id (int): User ID
            username (str): Username
            product_id (int): Product ID
            action (str): create, update, delete, restock
            before_state (dict): Product state before change
            after_state (dict): Product state after change
            
        Returns:
            ActivityLog: Product change log
        """
        return self.log_activity(
            user_id=user_id,
            username=username,
            action=f"product_{action}",
            resource_type="product",
            resource_id=str(product_id),
            details={
                'before': before_state or {},
                'after': after_state or {}
            }
        )
    
    def log_access_violation(
        self,
        username: str,
        action: str,
        reason: str,
        ip_address: str = "",
        user_id: int = None
    ) -> ActivityLog:
        """
        Log unauthorized access attempt.
        
        Args:
            username (str): Username
            action (str): Attempted action
            reason (str): Reason for denial
            ip_address (str): IP address
            user_id (int): User ID if known
            
        Returns:
            ActivityLog: Access violation log
        """
        return self.log_activity(
            user_id=user_id,
            username=username,
            action=f"access_denied_{action}",
            resource_type="security",
            status="failure",
            ip_address=ip_address,
            details={'reason': reason, 'event': 'access violation'}
        )
    
    def get_activity_log(
        self,
        limit: int = 100,
        offset: int = 0,
        action_filter: str = None,
        status_filter: str = None
    ) -> List[ActivityLog]:
        """
        Get activity log with optional filters.
        
        Args:
            limit (int): Max records
            offset (int): Skip records
            action_filter (str): Filter by action
            status_filter (str): Filter by status
            
        Returns:
            List[ActivityLog]: Activity records
        """
        try:
            if not self.activity_repo:
                return []
            
            return self.activity_repo.get_all(
                limit=limit,
                offset=offset,
                action=action_filter,
                status=status_filter
            )
        except Exception as e:
            self._log_error("Error retrieving activity log", e)
            return []
    
    def get_user_activity(
        self,
        user_id: int,
        limit: int = 100,
        days: int = 7
    ) -> List[ActivityLog]:
        """
        Get activity log for specific user.
        
        Args:
            user_id (int): User ID
            limit (int): Max records
            days (int): Look back N days
            
        Returns:
            List[ActivityLog]: User activities
        """
        try:
            if not self.activity_repo:
                return []
            
            return self.activity_repo.get_by_user(
                user_id=user_id,
                limit=limit,
                days=days
            )
        except Exception as e:
            self._log_error(f"Error retrieving activity for user {user_id}", e)
            return []
    
    def get_user_login_history(self, user_id: int, limit: int = 50) -> List[Dict]:
        """
        Get user login/logout history.
        
        Args:
            user_id (int): User ID
            limit (int): Max records
            
        Returns:
            List[Dict]: Login history
        """
        try:
            activities = self.get_user_activity(user_id, limit)
            
            logins = []
            for activity in activities:
                if activity.action in ["login", "logout"]:
                    logins.append({
                        'timestamp': activity.timestamp,
                        'action': activity.action,
                        'ip_address': activity.ip_address,
                        'status': activity.status
                    })
            
            return logins
        except Exception as e:
            self._log_error(f"Error getting login history for user {user_id}", e)
            return []
    
    def get_transaction_audit_trail(self, transaction_id: int) -> List[ActivityLog]:
        """
        Get all activities related to a transaction.
        
        Args:
            transaction_id (int): Transaction ID
            
        Returns:
            List[ActivityLog]: Transaction activities
        """
        try:
            if not self.activity_repo:
                return []
            
            return self.activity_repo.get_by_resource(
                resource_type="transaction",
                resource_id=str(transaction_id)
            )
        except Exception as e:
            self._log_error(f"Error getting audit trail for transaction {transaction_id}", e)
            return []
    
    def generate_audit_report(
        self,
        start_date: datetime = None,
        end_date: datetime = None,
        include_actions: List[str] = None
    ) -> Dict:
        """
        Generate audit report for period.
        
        Args:
            start_date (datetime): Report start date
            end_date (datetime): Report end date
            include_actions (List[str]): Filter by actions
            
        Returns:
            dict: Audit report
        """
        try:
            activities = self.get_activity_log(limit=10000)
            
            # Filter by date
            if start_date or end_date:
                activities = [
                    a for a in activities
                    if (not start_date or a.timestamp >= start_date) and
                       (not end_date or a.timestamp <= end_date)
                ]
            
            # Filter by actions
            if include_actions:
                activities = [a for a in activities if a.action in include_actions]
            
            # Generate report
            report = {
                'period_start': start_date,
                'period_end': end_date,
                'total_activities': len(activities),
                'by_action': {},
                'by_user': {},
                'by_status': {},
                'failures': [],
                'critical_events': []
            }
            
            for activity in activities:
                # By action
                if activity.action not in report['by_action']:
                    report['by_action'][activity.action] = 0
                report['by_action'][activity.action] += 1
                
                # By user
                if activity.username not in report['by_user']:
                    report['by_user'][activity.username] = 0
                report['by_user'][activity.username] += 1
                
                # By status
                if activity.status not in report['by_status']:
                    report['by_status'][activity.status] = 0
                report['by_status'][activity.status] += 1
                
                # Track failures
                if activity.status == "failure":
                    report['failures'].append({
                        'timestamp': activity.timestamp,
                        'user': activity.username,
                        'action': activity.action,
                        'reason': activity.details
                    })
                
                # Track critical events
                if activity.action in ["login_failed", "access_denied", "product_delete"]:
                    report['critical_events'].append({
                        'timestamp': activity.timestamp,
                        'event': activity.action,
                        'user': activity.username
                    })
            
            self._log_info(f"Audit report generated: {report['total_activities']} activities")
            return report
            
        except Exception as e:
            self._log_error("Error generating audit report", e)
            return {}
    
    def export_activity_log(self, filename: str) -> bool:
        """
        Export activity log to CSV file.
        
        Args:
            filename (str): Output filename
            
        Returns:
            bool: True if successful
        """
        try:
            import csv
            
            activities = self.get_activity_log(limit=100000)
            
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'Timestamp', 'Username', 'Action', 'Resource Type',
                    'Resource ID', 'Status', 'IP Address', 'Details'
                ])
                
                for activity in activities:
                    writer.writerow([
                        activity.timestamp,
                        activity.username,
                        activity.action,
                        activity.resource_type,
                        activity.resource_id,
                        activity.status,
                        activity.ip_address,
                        activity.details
                    ])
            
            self._log_info(f"Activity log exported to {filename}")
            return True
            
        except Exception as e:
            self._log_error(f"Error exporting activity log: {e}", e)
            return False
