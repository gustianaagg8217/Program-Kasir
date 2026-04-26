# ============================================================================
# SESSION_MANAGER.PY - Application Session Management
# ============================================================================
# Fungsi: Manage user sessions, current user, permissions
# Responsibilitas: Session lifecycle, user context, security checks
# ============================================================================

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from app.repositories.user_repository import User
from logger_config import get_logger

logger = get_logger(__name__)


@dataclass
class SessionInfo:
    """Session information."""
    user_id: int
    username: str
    role: str
    email: str
    login_time: datetime
    last_activity: datetime
    
    def is_active(self, timeout_minutes: int = 30) -> bool:
        """Check jika session masih active."""
        elapsed = datetime.now() - self.last_activity
        return elapsed < timedelta(minutes=timeout_minutes)
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'role': self.role,
            'email': self.email,
            'login_time': self.login_time.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'is_active': self.is_active()
        }


class SessionManager:
    """
    Manager untuk application sessions.
    
    Provide:
    - User session tracking
    - Permission checking
    - Session lifecycle management
    - Security controls
    """
    
    def __init__(self, session_timeout_minutes: int = 30):
        """
        Init SessionManager.
        
        Args:
            session_timeout_minutes: Session timeout duration
        """
        self.current_session: Optional[SessionInfo] = None
        self.session_timeout = session_timeout_minutes
        self.session_history: List[Dict] = []
        logger.info(f"SessionManager initialized (timeout={session_timeout_minutes}min)")
    
    def create_session(self, user: User) -> SessionInfo:
        """
        Create new session untuk user.
        
        Args:
            user: User object dari authentication
            
        Returns:
            SessionInfo object
        """
        session = SessionInfo(
            user_id=user.id,
            username=user.username,
            role=user.role,
            email=user.email,
            login_time=datetime.now(),
            last_activity=datetime.now()
        )
        
        self.current_session = session
        
        self.session_history.append({
            'action': 'login',
            'username': user.username,
            'role': user.role,
            'timestamp': datetime.now().isoformat(),
            'ip': 'local'  # TODO: Get actual IP
        })
        
        logger.info(f"Session created untuk user: {user.username} (role={user.role})")
        return session
    
    def get_current_session(self) -> Optional[SessionInfo]:
        """Get current session."""
        if self.current_session and self.current_session.is_active(self.session_timeout):
            self.current_session.update_activity()
            return self.current_session
        
        if self.current_session:
            logger.warning(f"Session timeout untuk user: {self.current_session.username}")
            self.destroy_session()
        
        return None
    
    def is_authenticated(self) -> bool:
        """Check jika user authenticated."""
        return self.get_current_session() is not None
    
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Get current user info."""
        session = self.get_current_session()
        if session:
            return {
                'user_id': session.user_id,
                'username': session.username,
                'role': session.role,
                'email': session.email
            }
        return None
    
    def get_current_role(self) -> Optional[str]:
        """Get current user role."""
        session = self.get_current_session()
        return session.role if session else None
    
    def is_admin(self) -> bool:
        """Check jika current user adalah admin."""
        return self.get_current_role() == 'admin'
    
    def is_cashier(self) -> bool:
        """Check jika current user adalah cashier."""
        return self.get_current_role() == 'cashier'
    
    def has_permission(self, permission: str) -> bool:
        """
        Check jika user punya permission.
        
        Args:
            permission: Permission string (e.g., 'edit_products', 'view_reports')
            
        Returns:
            True jika punya permission
        """
        role = self.get_current_role()
        
        # Admin punya semua permission
        if role == 'admin':
            return True
        
        # Cashier permissions
        if role == 'cashier':
            cashier_permissions = [
                'view_dashboard',
                'create_transaction',
                'view_inventory',
                'print_receipt'
            ]
            return permission in cashier_permissions
        
        return False
    
    def require_permission(self, permission: str) -> bool:
        """
        Require permission, raise jika tidak punya.
        
        Args:
            permission: Permission string
            
        Raises:
            PermissionError: Jika tidak punya permission
        """
        if not self.has_permission(permission):
            logger.warning(f"Permission denied: {permission} untuk user: {self.get_current_user()}")
            raise PermissionError(f"Tidak memiliki permission: {permission}")
        return True
    
    def destroy_session(self):
        """Destroy current session."""
        if self.current_session:
            username = self.current_session.username
            
            self.session_history.append({
                'action': 'logout',
                'username': username,
                'timestamp': datetime.now().isoformat(),
                'duration': (datetime.now() - self.current_session.login_time).total_seconds()
            })
            
            logger.info(f"Session destroyed untuk user: {username}")
            self.current_session = None
    
    def get_session_info(self) -> Optional[Dict[str, Any]]:
        """Get current session information."""
        session = self.get_current_session()
        return session.to_dict() if session else None
    
    def get_session_history(self, limit: int = 100) -> List[Dict]:
        """Get session history."""
        return self.session_history[-limit:]
    
    def update_activity(self):
        """Update current session activity timestamp."""
        if self.current_session:
            self.current_session.update_activity()


# Global session manager instance
_session_manager = None

def get_session_manager(timeout_minutes: int = 30) -> SessionManager:
    """Get atau create global session manager."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager(session_timeout_minutes=timeout_minutes)
    return _session_manager
