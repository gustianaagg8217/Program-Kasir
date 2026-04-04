# ============================================================================
# AUTH_SERVICE.PY - Authentication & User Management Service (Service Layer)
# ============================================================================
# Fungsi: Handle user login, logout, password management
# Role-based access control & session management
# ============================================================================

import hashlib
from typing import Optional
from datetime import datetime

from ..core import (
    User, UserSession, AuthenticationError, AuthorizationError,
    UserValidator, ValidationError
)
from ..repository import RepositoryFactory
from .base_service import BaseService
from logger_config import get_logger

logger = get_logger(__name__)


class AuthenticationService(BaseService):
    \"\"\"
    Business logic untuk authentication & authorization.
    
    Responsibilities:
    - User login (password verification)
    - User logout
    - Password hashing & verification
    - Session management
    - Permission checking
    - Role-based access control
    
    Methods:
        login(): Authenticate user
        logout(): Logout user
        create_user(): Create new user
        change_password(): Change user password
        update_user(): Update user info
        delete_user(): Deactivate user
        get_user_permissions(): Get list of user permissions
    \"\"\"
    
    def validate(self) -> bool:
        \"\"\"Validate AuthenticationService initialization.\"\"\"
        try:
            # Check if users table accessible
            users = self.repositories['user'].list_all()
            self._log_info(f\"AuthenticationService initialized. {len(users)} active users\")
            return True
        except Exception as e:
            self._log_error(\"AuthenticationService initialization failed\", e)
            return False
    
    @staticmethod
    def hash_password(password: str) -> str:
        \"\"\"
        Hash password using SHA-256.
        
        Args:
            password (str): Plain text password
            
        Returns:
            str: Hashed password (hex)
        \"\"\"
        return hashlib.sha256(password.encode()).hexdigest()
    
    def login(self, username: str, password: str) -> UserSession:
        \"\"\"
        Authenticate user by username & password.
        
        Args:
            username (str): Username
            password (str): Plain text password
            
        Returns:
            UserSession: User session object if login successful
            
        Raises:
            AuthenticationError: If login fails
        \"\"\"
        try:
            # Validate inputs
            username = UserValidator.validate_username(username)
            
            # Get user
            user = self.repositories['user'].get_by_username(username)
            if not user:
                self._log_warning(f\"Login failed: User '{username}' not found\")
                raise AuthenticationError(\"Username atau password salah\")
            
            # Check active
            if not user.is_active:
                self._log_warning(f\"Login failed: User '{username}' is inactive\")
                raise AuthenticationError(\"User tidak aktif\")
            
            # Verify password
            password_hash = self.hash_password(password)
            if user.password_hash != password_hash:
                self._log_warning(f\"Login failed: Wrong password for '{username}'\")
                raise AuthenticationError(\"Username atau password salah\")
            
            # Create session
            session = UserSession(
                user_id=user.id,
                username=user.username,
                role=user.role,
                nama_lengkap=user.nama_lengkap,
                login_time=datetime.now()
            )
            
            self._log_operation(
                \"User Login\",
                f\"Username={username}, Role={user.role}\",
                True
            )
            
            return session
        
        except AuthenticationError:
            raise
        except Exception as e:
            self._log_error(f\"Login error for user '{username}'\", e)
            raise AuthenticationError(\"Gagal login. Silakan coba lagi\")
    
    def create_user(self, username: str, password: str, role: str,
                   nama_lengkap: str = \"\") -> User:
        \"\"\"
        Create new user.
        
        Args:
            username (str): Username (unique)
            password (str): Plain text password
            role (str): User role (admin, cashier)
            nama_lengkap (str): Full name
            
        Returns:
            User: Created user object
            
        Raises:
            ValidationError: If validation fails
            DatabaseError: If user creation fails
        \"\"\"
        try:
            # Validate inputs
            username = UserValidator.validate_username(username)
            password = UserValidator.validate_password(password)
            role = UserValidator.validate_role(role)
            
            # Check username uniqueness
            existing = self.repositories['user'].get_by_username(username)
            if existing:
                raise ValidationError(f\"Username '{username}' sudah digunakan\", \"username\")
            
            # Hash password
            password_hash = self.hash_password(password)
            
            # Create user
            user = self.repositories['user'].create(
                username=username,
                password_hash=password_hash,
                role=role,
                nama_lengkap=nama_lengkap,
                is_active=True
            )
            
            self._log_operation(
                \"Create User\",
                f\"Username={username}, Role={role}\",
                True
            )
            
            return user
        
        except Exception as e:
            self._log_error(f\"Gagal create user '{username}'\", e)
            raise
    
    def change_password(self, user_id: int, old_password: str,
                       new_password: str) -> bool:
        \"\"\"
        Change user password.
        
        Args:
            user_id (int): User ID
            old_password (str): Current plain text password
            new_password (str): New plain text password
            
        Returns:
            bool: True if changed successfully
            
        Raises:
            AuthenticationError: If old password wrong
        \"\"\"
        try:
            # Get user
            user = self.repositories['user'].get_by_id(user_id)
            if not user:
                raise AuthenticationError(\"User tidak ditemukan\")
            
            # Verify old password
            old_hash = self.hash_password(old_password)
            if user.password_hash != old_hash:
                self._log_warning(f\"Wrong old password for user {user_id}\")
                raise AuthenticationError(\"Password lama salah\")
            
            # Validate new password
            new_password = UserValidator.validate_password(new_password)
            
            # Hash & update
            new_hash = self.hash_password(new_password)
            success = self.repositories['user'].update_password(user_id, new_hash)
            
            if success:
                self._log_operation(
                    \"Change Password\",
                    f\"User={user.username}\",
                    True
                )
            
            return success
        
        except Exception as e:
            self._log_error(f\"Gagal change password for user {user_id}\", e)
            raise
    
    def update_user(self, user_id: int, **kwargs) -> bool:
        \"\"\"
        Update user info.
        
        Args:
            user_id (int): User ID
            **kwargs: Fields to update (nama_lengkap, is_active, role)
            
        Returns:
            bool: True if updated
        \"\"\"
        try:
            # Validate fields
            if 'role' in kwargs:
                kwargs['role'] = UserValidator.validate_role(kwargs['role'])
            
            # Update
            success = self.repositories['user'].update(user_id, **kwargs)
            
            if success:
                details = \", \".join([f\"{k}={v}\" for k, v in kwargs.items()])
                self._log_operation(\"Update User\", f\"ID={user_id}, {details}\", True)
            
            return success
        
        except Exception as e:
            self._log_error(f\"Gagal update user {user_id}\", e)
            raise
    
    def deactivate_user(self, user_id: int) -> bool:
        \"\"\"
        Deactivate user (soft delete).
        
        Args:
            user_id (int): User ID
            
        Returns:
            bool: True if deactivated
        \"\"\"
        return self.update_user(user_id, is_active=False)
    
    def activate_user(self, user_id: int) -> bool:
        \"\"\"Activate user.\"\"\"
        return self.update_user(user_id, is_active=True)
    
    def get_user(self, user_id: int) -> Optional[User]:
        \"\"\"Get user by ID.\"\"\"
        try:
            return self.repositories['user'].get_by_id(user_id)
        except Exception as e:
            self._log_error(f\"Gagal get user {user_id}\", e)
            return None
    
    def list_users(self) -> list:
        \"\"\"List all active users.\"\"\"
        try:
            return self.repositories['user'].list_all()
        except Exception as e:
            self._log_error(\"Gagal list users\", e)
            return []
    
    def get_user_permissions(self, role: str) -> list:
        \"\"\"
        Get list of permissions for a role.
        
        Args:
            role (str): User role
            
        Returns:
            list: List of permission strings
        \"\"\"
        permissions = {
            'admin': [
                # Produk
                'produk.create', 'produk.read', 'produk.update', 'produk.delete',
                # Transaksi
                'transaksi.create', 'transaksi.read', 'transaksi.list', 'transaksi.delete',
                # Laporan
                'laporan.view_all', 'laporan.export',
                # User Management
                'user.create', 'user.read', 'user.update', 'user.delete',
                # Settings
                'settings.manage_config', 'settings.manage_backup'
            ],
            'cashier': [
                # Produk
                'produk.read', 'produk.search',
                # Transaksi
                'transaksi.create', 'transaksi.read',
                # Laporan
                'laporan.view_own',
                # Settings
                'settings.change_password'
            ]
        }
        
        return permissions.get(role.lower(), [])
    
    def check_permission(self, session: UserSession, permission: str) -> bool:
        \"\"\"
        Check if user session has permission.
        
        Args:
            session (UserSession): User session
            permission (str): Permission code
            
        Returns:
            bool: True if user has permission
        \"\"\"
        if session.is_admin():
            return True
        
        permissions = self.get_user_permissions(session.role)
        return permission in permissions
    
    def require_permission(self, session: UserSession, permission: str) -> None:
        \"\"\"
        Require permission or raise AuthorizationError.
        
        Args:
            session (UserSession): User session
            permission (str): Required permission
            
        Raises:
            AuthorizationError: If permission denied
        \"\"\"
        if not self.check_permission(session, permission):
            raise AuthorizationError(
                f\"Permission denied. Required: {permission}\",
                required_role=session.role
            )
