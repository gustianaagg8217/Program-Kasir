# ============================================================================
# EXCEPTIONS.PY - Custom Exception Classes for POS System
# ============================================================================
# Fungsi: Define semua custom exceptions untuk error handling yang terstruktur
# Gunakan untuk: Validasi, Auth, Transaksi, Database, Business Logic
# ============================================================================

class POSException(Exception):
    """Base exception untuk semua POS System errors."""
    
    def __init__(self, message: str, code: str = "UNKNOWN_ERROR"):
        """
        Initialize exception.
        
        Args:
            message (str): Error message for user/log
            code (str): Error code for programmatic handling
        """
        super().__init__(message)
        self.message = message
        self.code = code
    
    def to_user_message(self) -> str:
        """Get user-friendly error message."""
        return self.message


# ============================================================================
# VALIDATION EXCEPTIONS
# ============================================================================

class ValidationError(POSException):
    """Exception untuk validation errors (input tidak valid)."""
    
    def __init__(self, message: str, field: str = None):
        super().__init__(message, "VALIDATION_ERROR")
        self.field = field


class ProductValidationError(ValidationError):
    """Exception untuk product validation errors."""
    
    def __init__(self, message: str, product_code: str = None):
        super().__init__(message, "PRODUCT_VALIDATION_ERROR")
        self.product_code = product_code


class TransactionValidationError(ValidationError):
    """Exception untuk transaction validation errors."""
    
    def __init__(self, message: str):
        super().__init__(message, "TRANSACTION_VALIDATION_ERROR")


# ============================================================================
# AUTHENTICATION/AUTHORIZATION EXCEPTIONS
# ============================================================================

class AuthenticationError(POSException):
    """Exception untuk authentication failures (login error)."""
    
    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message, "AUTHENTICATION_ERROR")


class AuthorizationError(POSException):
    """Exception untuk authorization failures (permission denied)."""
    
    def __init__(self, message: str = "Permission denied", required_role: str = None):
        super().__init__(message, "AUTHORIZATION_ERROR")
        self.required_role = required_role


# ============================================================================
# BUSINESS LOGIC EXCEPTIONS
# ============================================================================

class InsufficientStockError(POSException):
    """Exception untuk stock tidak cukup."""
    
    def __init__(self, product_name: str, required: int, available: int):
        message = f"Stok '{product_name}' tidak cukup. Diperlukan: {required}, tersedia: {available}"
        super().__init__(message, "INSUFFICIENT_STOCK")
        self.product_name = product_name
        self.required = required
        self.available = available


class ProductNotFoundError(POSException):
    """Exception untuk produk tidak ditemukan."""
    
    def __init__(self, product_code: str = None, product_id: int = None):
        if product_code:
            message = f"Produk dengan kode '{product_code}' tidak ditemukan"
        elif product_id:
            message = f"Produk dengan ID {product_id} tidak ditemukan"
        else:
            message = "Produk tidak ditemukan"
        
        super().__init__(message, "PRODUCT_NOT_FOUND")
        self.product_code = product_code
        self.product_id = product_id


class TransactionError(POSException):
    """Exception untuk transaction processing errors."""
    
    def __init__(self, message: str):
        super().__init__(message, "TRANSACTION_ERROR")


class PaymentError(POSException):
    """Exception untuk payment processing errors."""
    
    def __init__(self, message: str):
        super().__init__(message, "PAYMENT_ERROR")


# ============================================================================
# DATABASE EXCEPTIONS
# ============================================================================

class DatabaseError(POSException):
    """Exception untuk database operation errors."""
    
    def __init__(self, message: str, operation: str = None):
        super().__init__(message, "DATABASE_ERROR")
        self.operation = operation


class DataIntegrityError(DatabaseError):
    """Exception untuk data integrity violations."""
    
    def __init__(self, message: str):
        super().__init__(message, "DATA_INTEGRITY_ERROR")


# ============================================================================
# SERVICE EXCEPTIONS
# ============================================================================

class ServiceError(POSException):
    """Base exception untuk service layer errors."""
    pass


class InvalidOperationError(ServiceError):
    """Exception untuk invalid operation attempts."""
    
    def __init__(self, message: str):
        super().__init__(message, "INVALID_OPERATION")


class NotFoundError(ServiceError):
    """Generic not found exception."""
    
    def __init__(self, resource: str, identifier: str = None):
        if identifier:
            message = f"{resource} dengan '{identifier}' tidak ditemukan"
        else:
            message = f"{resource} tidak ditemukan"
        super().__init__(message, "NOT_FOUND")
        self.resource = resource
        self.identifier = identifier


# ============================================================================
# CONFIGURATION EXCEPTIONS
# ============================================================================

class ConfigurationError(POSException):
    """Exception untuk configuration errors."""
    
    def __init__(self, message: str):
        super().__init__(message, "CONFIG_ERROR")


# ============================================================================
# EXTERNAL SERVICE EXCEPTIONS (TELEGRAM, etc)
# ============================================================================

class ExternalServiceError(POSException):
    """Exception untuk external service errors (Telegram, etc)."""
    
    def __init__(self, service_name: str, message: str):
        full_message = f"{service_name}: {message}"
        super().__init__(full_message, "EXTERNAL_SERVICE_ERROR")
        self.service_name = service_name
