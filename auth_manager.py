# ============================================================================
# AUTH_MANAGER.PY - User Authentication & Authorization System
# ============================================================================
# Fungsi: Handle user login, logout, role-based access control
# Manage current_user session dan permissions
# ============================================================================

from typing import Optional
from logger_config import get_logger
from database import DatabaseManager
from auth_security import LoginAttemptTracker, PasswordValidator

logger = get_logger(__name__)

# ============================================================================
# USER CLASS - Represents logged-in user
# ============================================================================

class User:
    """
    Represents a logged-in user dalam POS System.
    
    Attributes:
        id (int): User ID dari database
        username (str): Username
        role (str): User role (admin, cashier)
        is_active (bool): Is user active
    """
    
    def __init__(self, user_id: int, username: str, role: str, is_active: bool = True):
        """
        Initialize User instance.
        
        Args:
            user_id (int): User ID
            username (str): Username
            role (str): User role
            is_active (bool): Active status
        """
        self.id = user_id
        self.username = username
        self.role = role
        self.is_active = is_active
    
    def has_permission(self, permission: str) -> bool:
        """
        Check apakah user punya permission tertentu.
        
        Args:
            permission (str): Permission code
            
        Returns:
            bool: True jika user punya permission
        """
        if not self.is_active:
            return False
        
        # Admin punya semua permission
        if self.role == "admin":
            return True
        
        # Cashier permissions
        if self.role == "cashier":
            allowed_permissions = [
                "transaksi.view",
                "transaksi.create",
                "produk.view",
                "laporan.view_own",
                "settings.view_profile"
            ]
            return permission in allowed_permissions
        
        return False
    
    def is_admin(self) -> bool:
        """Check apakah user adalah admin."""
        return self.role == "admin" and self.is_active
    
    def is_cashier(self) -> bool:
        """Check apakah user adalah cashier."""
        return self.role == "cashier" and self.is_active
    
    def __str__(self) -> str:
        """String representation."""
        return f"User({self.username}, role={self.role})"


# ============================================================================
# AUTH MANAGER - Authentication & Authorization
# ============================================================================

class AuthManager:
    """
    User authentication dan authorization manager.
    
    Handle:
    - User login/logout
    - Session management
    - Role-based access control
    - Password verification
    
    Attributes:
        db (DatabaseManager): Database instance
        current_user (User): Currently logged-in user (None if not logged in)
    """
    
    def __init__(self, db: DatabaseManager):
        """
        Initialize AuthManager.
        
        Args:
            db (DatabaseManager): Database instance
        """
        self.db = db
        self.current_user: Optional[User] = None
        
        # Initialize login attempt tracker untuk security
        self.login_tracker = LoginAttemptTracker(db)
    
    # ========================================================================
    # AUTHENTICATION
    # ========================================================================
    
    def login(self, username: str, password: str, ip_address: str = None) -> tuple[bool, str]:
        """
        Attempt user login dengan rate limiting dan attempt logging.
        
        Security features:
        - Rate limiting: Maximum 5 failed attempts per 15 minutes
        - Login attempt tracking: Semua attempts di-log (success dan failed)
        - Account lockout: Otomatis lock setelah 5 failed attempts
        
        Args:
            username (str): Username
            password (str): Password (plain text)
            ip_address (str): IP address dari login attempt (optional)
            
        Returns:
            tuple: (success: bool, message: str)
                   (True, "Login successful") jika berhasil
                   (False, "error message") jika gagal
        """
        try:
            # Check if account is locked due to too many failed attempts
            lockout_status = self.db.check_login_lockout(username)
            if lockout_status['is_locked']:
                remaining_mins = lockout_status['remaining_minutes']
                msg = f"❌ Akun terkunci karena terlalu banyak login gagal. Coba lagi dalam {remaining_mins} menit."
                logger.warning(f"Login blocked (account locked): {username} from {ip_address}")
                self.login_tracker.record_attempt(username, success=False, ip_address=ip_address)
                return False, msg
            
            # Verify user credentials
            user_data = self.db.verify_user_login(username, password)
            
            if user_data is None:
                # Record failed attempt
                failed_count = self.db.get_failed_attempts_count(username)
                self.login_tracker.record_attempt(username, success=False, ip_address=ip_address)
                
                attempts_left = 5 - (failed_count + 1)
                if attempts_left <= 0:
                    msg = f"❌ Username atau password salah. Akun akan terkunci."
                else:
                    msg = f"❌ Username atau password salah. Sisa {attempts_left} percobaan."
                
                logger.warning(f"Failed login attempt: {username} from {ip_address} (Total failed: {failed_count + 1})")
                return False, msg
            
            # Create User object
            self.current_user = User(
                user_id=user_data['id'],
                username=user_data['username'],
                role=user_data['role'],
                is_active=bool(user_data.get('is_active', 1))
            )
            
            if not self.current_user.is_active:
                self.current_user = None
                self.login_tracker.record_attempt(username, success=False, ip_address=ip_address)
                logger.warning(f"Login attempt with inactive user: {username}")
                return False, "❌ User tidak aktif. Hubungi administrator."
            
            # Record successful login
            self.login_tracker.record_attempt(username, success=True, ip_address=ip_address)
            
            # Reset failed attempts counter after successful login
            self.db.reset_login_attempts(username)
            
            logger.info(f"User logged in successfully: {username} (role: {self.current_user.role}) from {ip_address}")
            return True, f"✅ Selamat datang, {username}!"
            
        except Exception as e:
            logger.error(f"Login error: {e}", exc_info=True)
            return False, f"❌ Terjadi kesalahan: {e}"
    
    def logout(self) -> bool:
        """
        Logout current user.
        
        Returns:
            bool: True jika berhasil
        """
        if self.current_user:
            logger.info(f"User logged out: {self.current_user.username}")
            username = self.current_user.username
            self.current_user = None
            return True
        return False
    
    # ========================================================================
    # SESSION MANAGEMENT
    # ========================================================================
    
    def is_logged_in(self) -> bool:
        """
        Check apakah user sedang logged in.
        
        Returns:
            bool: True jika logged in
        """
        return self.current_user is not None and self.current_user.is_active
    
    def get_current_user(self) -> Optional[User]:
        """
        Get current logged-in user.
        
        Returns:
            User: Currently logged-in user atau None
        """
        return self.current_user
    
    def get_username(self) -> str:
        """
        Get username dari current user.
        
        Returns:
            str: Username atau "Not Logged In"
        """
        if self.current_user:
            return self.current_user.username
        return "Not Logged In"
    
    def get_role(self) -> str:
        """
        Get role dari current user.
        
        Returns:
            str: Role atau "guest"
        """
        if self.current_user:
            return self.current_user.role
        return "guest"
    
    # ========================================================================
    # AUTHORIZATION - Role-based access control
    # ========================================================================
    
    def check_permission(self, permission: str) -> bool:
        """
        Check apakah current user punya permission.
        
        Args:
            permission (str): Permission code
            
        Returns:
            bool: True jika user punya permission
        """
        if not self.is_logged_in():
            return False
        return self.current_user.has_permission(permission)
    
    def require_admin(self) -> bool:
        """
        Check apakah current user adalah admin.
        
        Returns:
            bool: True jika admin
        """
        return self.is_logged_in() and self.current_user.is_admin()
    
    def require_permission(self, permission: str) -> bool:
        """
        Require specific permission, return False jika tidak punya.
        
        Args:
            permission (str): Permission code
            
        Returns:
            bool: True jika punya permission
        """
        has_perm = self.check_permission(permission)
        if not has_perm:
            logger.warning(f"Access denied for {self.get_username()}: {permission}")
        return has_perm
    
    # ========================================================================
    # USER MANAGEMENT (Admin only)
    # ========================================================================
    
    def create_user(self, username: str, password: str, role: str = "cashier") -> tuple[bool, str]:
        """
        Create new user (admin only).
        
        Args:
            username (str): Username
            password (str): Password
            role (str): Role (admin, cashier)
            
        Returns:
            tuple: (success, message)
        """
        # Check permission
        if not self.require_admin():
            return False, "❌ Hanya admin yang bisa membuat user"
        
        try:
            result = self.db.create_user(username, password, role)
            if result:
                logger.info(f"User created: {username} (role: {role})")
                return True, f"✅ User '{username}' berhasil dibuat"
            else:
                return False, f"❌ User '{username}' sudah ada"
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False, f"❌ Error: {e}"
    
    def list_users(self) -> tuple[bool, list]:
        """
        List all users (admin only).
        
        Returns:
            tuple: (success, users_list)
        """
        if not self.require_admin():
            return False, []
        
        try:
            users = self.db.get_all_users()
            return True, users
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            return False, []
    
    def deactivate_user(self, user_id: int) -> tuple[bool, str]:
        """
        Deactivate user (admin only).
        
        Args:
            user_id (int): User ID
            
        Returns:
            tuple: (success, message)
        """
        if not self.require_admin():
            return False, "❌ Hanya admin yang bisa deactivate user"
        
        try:
            result = self.db.deactivate_user(user_id)
            if result:
                logger.info(f"User deactivated: ID {user_id}")
                return True, "✅ User berhasil di-deactivate"
            else:
                return False, "❌ Gagal deactivate user"
        except Exception as e:
            logger.error(f"Error deactivating user: {e}")
            return False, f"❌ Error: {e}"
    
    # ========================================================================
    # SECURITY & MONITORING (Admin only)
    # ========================================================================
    
    def get_user_login_history(self, username: str, limit: int = 10) -> tuple[bool, list]:
        """
        Get login attempt history untuk specific user (admin only).
        
        Args:
            username (str): Username
            limit (int): Maksimal records (default: 10)
            
        Returns:
            tuple: (success, history_list)
        """
        if not self.require_admin():
            return False, []
        
        try:
            history = self.db.get_login_history(username, limit)
            logger.info(f"Login history retrieved for: {username} (admin: {self.get_username()})")
            return True, history
        except Exception as e:
            logger.error(f"Error getting login history: {e}")
            return False, []
    
    def get_security_summary(self, username: str) -> tuple[bool, dict]:
        """
        Get security summary untuk specific user (admin only).
        
        Includes:
        - Account lockout status
        - Failed attempts count
        - Recent login history
        - Last successful login
        
        Args:
            username (str): Username
            
        Returns:
            tuple: (success, summary_dict)
        """
        if not self.require_admin():
            return False, {}
        
        try:
            summary = self.db.get_security_summary(username)
            logger.info(f"Security summary retrieved for: {username}")
            return True, summary
        except Exception as e:
            logger.error(f"Error getting security summary: {e}")
            return False, {}
    
    def get_all_failed_attempts(self, limit: int = 50) -> tuple[bool, list]:
        """
        Get all recent failed login attempts across all users (admin only).
        
        Useful untuk security monitoring dan threat detection.
        
        Args:
            limit (int): Maksimal records (default: 50)
            
        Returns:
            tuple: (success, attempts_list)
        """
        if not self.require_admin():
            return False, []
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT username, ip_address, attempted_at, success
                    FROM login_attempts
                    WHERE success = 0
                    ORDER BY attempted_at DESC
                    LIMIT ?
                """, (limit,))
                
                attempts = [dict(row) for row in cursor.fetchall()]
                logger.info(f"Failed attempts retrieved: {len(attempts)} records (admin: {self.get_username()})")
                return True, attempts
        except Exception as e:
            logger.error(f"Error getting failed attempts: {e}")
            return False, []
    
    def unlock_account(self, username: str) -> tuple[bool, str]:
        """
        Manually unlock user account (admin only).
        
        Args:
            username (str): Username
            
        Returns:
            tuple: (success, message)
        """
        if not self.require_admin():
            return False, "❌ Hanya admin yang bisa unlock account"
        
        try:
            # Delete failed attempts untuk user
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM login_attempts
                    WHERE username = ? AND success = 0
                """, (username,))
                conn.commit()
            
            logger.info(f"Account unlocked by admin {self.get_username()}: {username}")
            return True, f"✅ Account '{username}' berhasil di-unlock"
        except Exception as e:
            logger.error(f"Error unlocking account: {e}")
            return False, f"❌ Error: {e}"


# ============================================================================
# TESTING - Jalankan jika file dijalankan standalone
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("AUTH MANAGER - Testing")
    print("=" * 70)
    
    # Setup database
    db = DatabaseManager()
    auth = AuthManager(db)
    
    # Test login
    print("\n✅ Testing login:")
    success, msg = auth.login("admin", "admin123")
    print(f"Result: {msg}")
    
    if success:
        print(f"Logged in as: {auth.get_username()} (role: {auth.get_role()})")
        print(f"Is admin: {auth.current_user.is_admin()}")
        print(f"Permission check: {auth.check_permission('transaksi.view')}")
