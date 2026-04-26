# ============================================================================
# ERROR_HANDLER.PY - Centralized Error Handling & User Messages
# ============================================================================
# Fungsi: Menangani error secara konsisten, log, & tampilkan pesan user-friendly
# Fitur: Type-specific error handling, logging, fallback messages
# ============================================================================

from typing import Optional, Callable
from logger_config import get_logger
import traceback
import sys

logger = get_logger(__name__)

# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class PosError(Exception):
    """Base exception untuk semua POS system errors."""
    def __init__(self, message: str, code: str = "UNKNOWN_ERROR", user_message: Optional[str] = None):
        """
        Init error dengan message, code, dan user-friendly message.
        
        Args:
            message: Technical error message untuk logging
            code: Error code (e.g., 'PRODUCT_NOT_FOUND')
            user_message: User-friendly message (jika None, generate otomatis)
        """
        self.message = message
        self.code = code
        self.user_message = user_message or self._generate_user_message()
        super().__init__(self.message)
    
    def _generate_user_message(self) -> str:
        """Generate user-friendly message berdasarkan error code."""
        messages = {
            'PRODUCT_NOT_FOUND': '❌ Produk tidak ditemukan',
            'INVALID_QUANTITY': '❌ Jumlah tidak valid (harus angka > 0)',
            'INSUFFICIENT_STOCK': '❌ Stok tidak cukup',
            'INVALID_PRICE': '❌ Harga tidak valid',
            'PRODUCT_EXISTS': '❌ Produk sudah ada',
            'DATABASE_ERROR': '❌ Kesalahan database, hubungi admin',
            'PERMISSION_DENIED': '❌ Anda tidak memiliki akses',
            'INVALID_CREDENTIALS': '❌ Username atau password salah',
            'SESSION_EXPIRED': '❌ Sesi berakhir, silakan login ulang',
            'UNKNOWN_ERROR': '❌ Terjadi kesalahan, silakan coba lagi',
        }
        return messages.get(self.code, self.message)


class ValidationError(PosError):
    """Error untuk validasi input."""
    def __init__(self, message: str, user_message: Optional[str] = None):
        super().__init__(message, "VALIDATION_ERROR", user_message)


class DatabaseError(PosError):
    """Error untuk database operations."""
    def __init__(self, message: str, user_message: Optional[str] = None):
        super().__init__(message, "DATABASE_ERROR", user_message or "Kesalahan database, silakan hubungi admin")


class NotFoundError(PosError):
    """Error untuk resource tidak ditemukan."""
    def __init__(self, resource: str):
        message = f"{resource} tidak ditemukan"
        super().__init__(message, f"{resource.upper()}_NOT_FOUND", f"❌ {message}")


class PermissionError(PosError):
    """Error untuk akses ditolak."""
    def __init__(self, message: str = "Anda tidak memiliki akses"):
        super().__init__(message, "PERMISSION_DENIED", f"❌ {message}")


# ============================================================================
# ERROR HANDLER - Main error handling logic
# ============================================================================

class ErrorHandler:
    """Centralized error handler untuk consistent error management."""
    
    @staticmethod
    def handle(
        exception: Exception,
        context: str = "",
        callback: Optional[Callable[[str], None]] = None
    ) -> tuple[str, str]:
        """
        Handle exception dengan logging & user message.
        
        Args:
            exception: Exception yang ditangkap
            context: Konteks error (e.g., 'product_creation')
            callback: Optional callback function untuk notify GUI (e.g., messagebox.showerror)
            
        Returns:
            Tuple (error_code, user_message)
        """
        
        # Extract info
        if isinstance(exception, PosError):
            error_code = exception.code
            user_message = exception.user_message
            technical_message = exception.message
        else:
            error_code = "UNKNOWN_ERROR"
            user_message = "❌ Terjadi kesalahan sistem"
            technical_message = str(exception)
        
        # Log error
        logger.error(
            f"[{error_code}] Context: {context} | Message: {technical_message}",
            exc_info=exception
        )
        
        # Print traceback untuk debugging
        if "--debug" in sys.argv:
            traceback.print_exc()
        
        # Callback untuk GUI notification
        if callback:
            try:
                callback(user_message)
            except Exception as cb_error:
                logger.error(f"Error in error callback: {cb_error}")
        
        return (error_code, user_message)
    
    @staticmethod
    def log_warning(message: str, context: str = ""):
        """Log warning tanpa throw exception."""
        if context:
            logger.warning(f"[{context}] {message}")
        else:
            logger.warning(message)
    
    @staticmethod
    def log_info(message: str, context: str = ""):
        """Log info message."""
        if context:
            logger.info(f"[{context}] {message}")
        else:
            logger.info(message)


# ============================================================================
# DECORATOR FOR AUTO ERROR HANDLING
# ============================================================================

def safe_operation(context: str = ""):
    """
    Decorator untuk auto error handling di methods.
    
    Usage:
        @safe_operation("product_creation")
        def create_product(self, data):
            ...
    
    Jika terjadi error, akan di-log otomatis & return error response.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_context = context or func.__name__
                ErrorHandler.handle(e, error_context)
                raise
        return wrapper
    return decorator
