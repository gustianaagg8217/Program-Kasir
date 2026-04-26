# ============================================================================
# USER_SERVICE.PY - Business Logic Layer untuk Users
# ============================================================================
# Fungsi: Handle authentication, user management, role-based access
# Responsibilitas: NO direct database access (gunakan repository)
# ============================================================================

from typing import Optional, Tuple
from app.repositories.user_repository import UserRepository, User
from app.utils.password_manager import PasswordManager
from app.utils.error_handler import ValidationError as ServiceValidationError, DatabaseError
from logger_config import get_logger

logger = get_logger(__name__)


class UserService:
    """Service layer untuk user management & authentication."""
    
    def __init__(self, user_repository: UserRepository):
        """
        Init dengan UserRepository.
        
        Args:
            user_repository: UserRepository instance
        """
        self.repo = user_repository
    
    def create_user(
        self,
        username: str,
        password: str,
        role: str = "cashier",
        email: str = ""
    ) -> User:
        """
        Create user baru dengan validasi & password hashing.
        
        Args:
            username: Username (unique)
            password: Plain text password
            role: 'admin' atau 'cashier'
            email: Email user
            
        Returns:
            User object yang dibuat
            
        Raises:
            ServiceValidationError: Jika validasi gagal
            DatabaseError: Jika database error
        """
        try:
            # Validasi username
            username = username.strip().lower()
            if len(username) < 3:
                raise ServiceValidationError("Username minimal 3 karakter")
            
            if self.repo.exists(username):
                raise ServiceValidationError("Username sudah ada", "Username ini sudah digunakan")
            
            # Validasi password strength
            is_strong, feedback = PasswordManager.check_password_strength(password)
            if not is_strong:
                raise ServiceValidationError(f"Password tidak kuat: {feedback}")
            
            # Validasi role
            if role not in ['admin', 'cashier']:
                raise ServiceValidationError("Role harus 'admin' atau 'cashier'")
            
            # Hash password
            password_hash = PasswordManager.hash_password(password)
            
            # Create user
            user = self.repo.create(username, password_hash, role, email)
            logger.info(f"User created: {username} ({role})")
            
            return user
        
        except ServiceValidationError:
            raise
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise DatabaseError(str(e), "Gagal membuat user")
    
    def authenticate(self, username: str, password: str) -> Tuple[bool, Optional[User]]:
        """
        Authenticate user dengan username & password.
        
        Args:
            username: Username
            password: Plain text password
            
        Returns:
            Tuple (success: bool, user: Optional[User])
        """
        try:
            user = self.repo.get_by_username(username.strip().lower())
            
            if not user:
                logger.warning(f"Login attempt with non-existent username: {username}")
                return (False, None)
            
            if not user.active:
                logger.warning(f"Login attempt with inactive user: {username}")
                return (False, None)
            
            # Verify password
            if PasswordManager.verify_password(password, user.password_hash):
                logger.info(f"User authenticated: {username}")
                return (True, user)
            else:
                logger.warning(f"Invalid password for user: {username}")
                return (False, None)
        
        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            return (False, None)
    
    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        """
        Change user password dengan verify old password dulu.
        
        Args:
            username: Username
            old_password: Current password
            new_password: New password
            
        Returns:
            True jika berhasil
            
        Raises:
            ServiceValidationError: Jika validasi gagal
        """
        try:
            # Verify old password
            authenticated, user = self.authenticate(username, old_password)
            if not authenticated:
                raise ServiceValidationError("Password lama salah", "Password saat ini tidak sesuai")
            
            # Validate new password strength
            is_strong, feedback = PasswordManager.check_password_strength(new_password)
            if not is_strong:
                raise ServiceValidationError(f"Password baru tidak kuat: {feedback}")
            
            # Hash new password
            new_hash = PasswordManager.hash_password(new_password)
            
            # Update password
            result = self.repo.update(user.id, password_hash=new_hash)
            if result:
                logger.info(f"Password changed for user: {username}")
            
            return result
        
        except ServiceValidationError:
            raise
        except Exception as e:
            logger.error(f"Error changing password: {e}")
            raise DatabaseError(str(e), "Gagal mengubah password")
    
    def reset_password(self, username: str) -> str:
        """
        Reset password user (generate temporary password).
        
        Args:
            username: Username
            
        Returns:
            Temporary password
            
        Raises:
            ServiceValidationError: Jika user tidak ditemukan
        """
        try:
            user = self.repo.get_by_username(username.strip().lower())
            if not user:
                raise ServiceValidationError(f"User {username} tidak ditemukan")
            
            # Generate temporary password
            temp_password = PasswordManager.generate_temp_password()
            temp_hash = PasswordManager.hash_password(temp_password)
            
            # Update password
            self.repo.update(user.id, password_hash=temp_hash)
            
            logger.info(f"Password reset for user: {username}")
            return temp_password
        
        except ServiceValidationError:
            raise
        except Exception as e:
            logger.error(f"Error resetting password: {e}")
            raise DatabaseError(str(e), "Gagal reset password")
    
    def get_user(self, username: str) -> Optional[User]:
        """Get user berdasarkan username (without password_hash)."""
        user = self.repo.get_by_username(username.strip().lower())
        if user:
            logger.info(f"User fetched: {username}")
        return user
    
    def list_users(self, active_only: bool = True) -> list[User]:
        """
        List semua users.
        
        Args:
            active_only: Hanya active users
            
        Returns:
            List of User objects
        """
        if active_only:
            return self.repo.get_active_users()
        return self.repo.list_all()
    
    def deactivate_user(self, username: str) -> bool:
        """
        Deactivate user (soft delete).
        
        Args:
            username: Username
            
        Returns:
            True jika berhasil
        """
        try:
            user = self.repo.get_by_username(username.strip().lower())
            if not user:
                raise ServiceValidationError(f"User {username} tidak ditemukan")
            
            result = self.repo.delete(user.id)
            if result:
                logger.info(f"User deactivated: {username}")
            
            return result
        
        except ServiceValidationError:
            raise
        except Exception as e:
            logger.error(f"Error deactivating user: {e}")
            raise DatabaseError(str(e), "Gagal deactivate user")
    
    def update_email(self, username: str, email: str) -> bool:
        """Update email user."""
        try:
            user = self.repo.get_by_username(username.strip().lower())
            if not user:
                raise ServiceValidationError(f"User {username} tidak ditemukan")
            
            result = self.repo.update(user.id, email=email)
            if result:
                logger.info(f"Email updated for user: {username}")
            
            return result
        
        except ServiceValidationError:
            raise
        except Exception as e:
            logger.error(f"Error updating email: {e}")
            raise DatabaseError(str(e))
