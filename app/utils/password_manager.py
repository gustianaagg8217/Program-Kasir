# ============================================================================
# PASSWORD_MANAGER.PY - Secure Password Hashing & Verification
# ============================================================================
# Fungsi: Handle password hashing dengan bcrypt untuk security
# Fitur: Hash generation, verification, password strength checking
# ============================================================================

import bcrypt
from typing import Tuple
from logger_config import get_logger

logger = get_logger(__name__)


class PasswordManager:
    """Manage password hashing & verification dengan bcrypt."""
    
    # Bcrypt salt rounds (higher = more secure but slower)
    # 10 = good balance antara security & performance
    SALT_ROUNDS = 10
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password menggunakan bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password (bcrypt hash)
            
        Raises:
            ValueError: Jika password kosong atau tidak valid
        """
        if not password or len(password) < 6:
            raise ValueError("Password minimal 6 karakter")
        
        try:
            # Generate salt dan hash
            salt = bcrypt.gensalt(rounds=PasswordManager.SALT_ROUNDS)
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
            
            # Return as string (bcrypt returns bytes)
            return hashed.decode('utf-8')
        except Exception as e:
            logger.error(f"Error hashing password: {e}")
            raise
    
    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """
        Verify plain text password terhadap hashed password.
        
        Args:
            password: Plain text password (user input)
            hashed_password: Hashed password (dari database)
            
        Returns:
            True jika password cocok, False jika tidak
        """
        try:
            # bcrypt.checkpw expects bytes
            return bcrypt.checkpw(
                password.encode('utf-8'),
                hashed_password.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return False
    
    @staticmethod
    def check_password_strength(password: str) -> Tuple[bool, str]:
        """
        Check password strength & return feedback.
        
        Args:
            password: Password to check
            
        Returns:
            Tuple (is_strong: bool, feedback: str)
        """
        issues = []
        
        # Minimum length
        if len(password) < 6:
            issues.append("Minimal 6 karakter")
        
        # Should have uppercase
        if not any(c.isupper() for c in password):
            issues.append("Harus ada huruf besar (A-Z)")
        
        # Should have lowercase
        if not any(c.islower() for c in password):
            issues.append("Harus ada huruf kecil (a-z)")
        
        # Should have number
        if not any(c.isdigit() for c in password):
            issues.append("Harus ada angka (0-9)")
        
        # Should have special character (optional but recommended)
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in password):
            issues.append("Rekomendasi: tambahkan karakter khusus (!@#$%...)")
        
        is_strong = len(issues) == 0
        feedback = " | ".join(issues) if issues else "✅ Password kuat"
        
        return (is_strong, feedback)
    
    @staticmethod
    def generate_temp_password(length: int = 12) -> str:
        """
        Generate temporary password untuk reset.
        
        Args:
            length: Password length
            
        Returns:
            Random temporary password
        """
        import secrets
        import string
        
        # Mix of uppercase, lowercase, digits, and special chars
        chars = string.ascii_letters + string.digits + "!@#$%&"
        temp_pwd = ''.join(secrets.choice(chars) for _ in range(length))
        
        logger.info("Temporary password generated")
        return temp_pwd
