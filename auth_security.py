# ============================================================================
# AUTH_SECURITY.PY - Secure Password Management with Bcrypt
# ============================================================================
# Fungsi: Handle password hashing with bcrypt, verification, and migration
# Author: Security Team
# Version: 2.0 (Bcrypt upgrade)
# ============================================================================

import bcrypt
import hashlib
from datetime import datetime, timedelta
from logger_config import get_logger

logger = get_logger(__name__)

# ============================================================================
# PASSWORD HASHING - Bcrypt Implementation
# ============================================================================

class PasswordManager:
    """
    Manage password hashing dan verification dengan bcrypt.
    
    Features:
    - Secure bcrypt hashing with salting
    - Backward compatibility dengan SHA256 (migration support)
    - Password strength validation
    """
    
    # Bcrypt rounds (higher = more secure but slower)
    BCRYPT_ROUNDS = 12
    
    # Placeholder untuk hash yang sudah lama (SHA256)
    SHA256_PREFIX = "sha256$"
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password menggunakan bcrypt dengan salt.
        
        Args:
            password (str): Password plain text
            
        Returns:
            str: Bcrypt hashed password (encoded as string)
            
        Contoh:
            hashed = PasswordManager.hash_password("mypassword123")
            # Returns: '$2b$12$...'
        """
        if not password or not isinstance(password, str):
            raise ValueError("Password harus berupa string dan tidak boleh kosong")
        
        try:
            # Generate bcrypt hash dengan salt
            salt = bcrypt.gensalt(rounds=PasswordManager.BCRYPT_ROUNDS)
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
            return hashed.decode('utf-8')
        except Exception as e:
            logger.error(f"Error hashing password: {e}")
            raise
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """
        Verify password dengan hashnya (bcrypt atau SHA256).
        
        Args:
            password (str): Password plain text
            password_hash (str): Hashed password dari database
            
        Returns:
            bool: True jika cocok, False jika tidak
            
        Contoh:
            is_valid = PasswordManager.verify_password("mypassword123", hashed)
        """
        if not password or not isinstance(password, str):
            return False
        
        if not password_hash or not isinstance(password_hash, str):
            return False
        
        try:
            # Check if it's new bcrypt hash (starts with $2a$, $2b$, or $2y$)
            if password_hash.startswith(('$2a$', '$2b$', '$2y$')):
                return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
            
            # Backward compatibility: Check SHA256 hashes
            # SHA256 hashes are stored as plain hex strings (64 chars)
            elif len(password_hash) == 64 and all(c in '0123456789abcdef' for c in password_hash):
                sha256_hash = hashlib.sha256(password.encode()).hexdigest()
                return sha256_hash == password_hash
            
            else:
                logger.warning(f"Unknown password hash format: {password_hash[:10]}...")
                return False
                
        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return False
    
    @staticmethod
    def is_legacy_hash(password_hash: str) -> bool:
        """
        Check apakah password hash adalah legacy SHA256.
        
        Args:
            password_hash (str): Hash yang akan dicek
            
        Returns:
            bool: True jika legacy SHA256, False jika bcrypt
        """
        if not password_hash:
            return False
        
        # Bcrypt hashes dimulai dengan $2a$, $2b$, atau $2y$
        if password_hash.startswith(('$2a$', '$2b$', '$2y$')):
            return False
        
        # Legacy SHA256 adalah 64 karakter hex
        if len(password_hash) == 64 and all(c in '0123456789abcdef' for c in password_hash):
            return True
        
        return False


# ============================================================================
# LOGIN ATTEMPT TRACKING & RATE LIMITING
# ============================================================================

class LoginAttemptTracker:
    """
    Track login attempts untuk security monitoring dan rate limiting.
    
    Features:
    - Log semua login attempts (berhasil dan gagal)
    - Rate limiting: max 5 attempts per 15 minutes
    - Account lockout setelah terlalu banyak attempts
    """
    
    # Rate limiting settings
    MAX_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 3
    RESET_DURATION_HOURS = 24
    
    def __init__(self, db_manager):
        """
        Initialize LoginAttemptTracker.
        
        Args:
            db_manager (DatabaseManager): Database instance
        """
        self.db = db_manager
    
    def record_attempt(self, username: str, success: bool, ip_address: str = None) -> dict:
        """
        Record login attempt ke database.
        
        Args:
            username (str): Username yang dicoba login
            success (bool): True jika login berhasil, False jika gagal
            ip_address (str): IP address attempt (optional)
            
        Returns:
            dict: Info attempt yang direcord
            
        Contoh:
            tracker.record_attempt("admin", success=False, ip_address="192.168.1.1")
        """
        try:
            result = self.db.record_login_attempt(username, success, ip_address)
            logger.info(f"Login attempt recorded: {username}, success={success}")
            return result
        except Exception as e:
            logger.error(f"Error recording login attempt: {e}")
            return {}
    
    def is_account_locked(self, username: str) -> bool:
        """
        Check apakah account dikunci karena terlalu banyak failed attempts.
        
        Args:
            username (str): Username
            
        Returns:
            bool: True jika account locked, False jika tidak
        """
        try:
            lock_status = self.db.check_login_lockout(username)
            if lock_status['is_locked']:
                remaining_minutes = lock_status['remaining_minutes']
                logger.warning(f"Account locked: {username}, remaining: {remaining_minutes}m")
                return True
            return False
        except Exception as e:
            logger.error(f"Error checking account lock: {e}")
            return False
    
    def get_failed_attempts_count(self, username: str) -> int:
        """
        Get jumlah failed attempts dalam periode lockout.
        
        Args:
            username (str): Username
            
        Returns:
            int: Jumlah failed attempts
        """
        try:
            count = self.db.get_failed_attempts_count(username)
            return count
        except Exception as e:
            logger.error(f"Error getting failed attempts count: {e}")
            return 0
    
    def get_login_history(self, username: str, limit: int = 10) -> list:
        """
        Get login attempt history untuk user.
        
        Args:
            username (str): Username
            limit (int): Maksimal records (default: 10)
            
        Returns:
            list: List of login attempts dengan timestamp
        """
        try:
            history = self.db.get_login_history(username, limit)
            return history
        except Exception as e:
            logger.error(f"Error getting login history: {e}")
            return []
    
    def reset_attempts(self, username: str) -> bool:
        """
        Reset failed attempts counter (usually after successful login).
        
        Args:
            username (str): Username
            
        Returns:
            bool: True jika berhasil
        """
        try:
            success = self.db.reset_login_attempts(username)
            if success:
                logger.info(f"Login attempts reset for: {username}")
            return success
        except Exception as e:
            logger.error(f"Error resetting login attempts: {e}")
            return False


# ============================================================================
# PASSWORD VALIDATION & STRENGTH CHECKING
# ============================================================================

class PasswordValidator:
    """
    Validate password strength dan requirements.
    """
    
    @staticmethod
    def validate_password(password: str) -> tuple[bool, str]:
        """
        Validate password strength.
        
        Requirements:
        - Minimal 8 karakter
        - Tidak boleh sama dengan username
        
        Args:
            password (str): Password yang akan divalidasi
            
        Returns:
            tuple: (is_valid, message)
            
        Contoh:
            valid, msg = PasswordValidator.validate_password("weak")
            # Returns: (False, "Password minimal 8 karakter")
        """
        if not password:
            return False, "❌ Password tidak boleh kosong"
        
        if len(password) < 8:
            return False, "❌ Password minimal 8 karakter"
        
        if len(password) > 128:
            return False, "❌ Password maksimal 128 karakter"
        
        return True, "✅ Password valid"
    
    @staticmethod
    def suggest_password() -> str:
        """
        Generate saran password yang kuat.
        
        Returns:
            str: Suggested password
        """
        import secrets
        import string
        
        alphabet = string.ascii_letters + string.digits + string.punctuation
        password = ''.join(secrets.choice(alphabet) for i in range(12))
        return password
