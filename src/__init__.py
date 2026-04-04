# ============================================================================
# SRC/__init__.py - Main entry point for refactored POS System
# ============================================================================
# This module imports and exports all layers for easy access

from .core import (
    # Exceptions
    POSException,
    ValidationError, AuthenticationError, AuthorizationError,
    InsufficientStockError, ProductNotFoundError,
    TransactionError, PaymentError, DatabaseError,
    # Models
    Product, Transaction, TransactionItem,
    User, UserSession,
    format_rp,
    # Validators
    ProductValidator, QuantityValidator, PaymentValidator,
    UserValidator
)

from .repository import RepositoryFactory
from .service import ServiceFactory

__version__ = \"2.0.0\"
__author__ = \"POS Team\"
__all__ = [
    # Core exports
    'POSException',
    'ValidationError', 'AuthenticationError', 'AuthorizationError',
    'InsufficientStockError', 'ProductNotFoundError',
    'TransactionError', 'PaymentError', 'DatabaseError',
    'Product', 'Transaction', 'TransactionItem',
    'User', 'UserSession',
    'format_rp',
    'ProductValidator', 'QuantityValidator', 'PaymentValidator', 'UserValidator',
    # Factories
    'RepositoryFactory',
    'ServiceFactory',
    # Version
    '__version__', '__author__'
]
