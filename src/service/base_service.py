# ============================================================================
# BASE_SERVICE.PY - Abstract Base Service (Service Layer)
# ============================================================================
# Fungsi: Define interface untuk semua business logic services
# Ensure consistent error handling, logging, validation
# ============================================================================

from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime

from ..core import POSException
from ..repository import RepositoryFactory
from logger_config import get_logger

logger = get_logger(__name__)


class BaseService(ABC):
    """
    Abstract base service untuk semua business logic operations.
    
    Fitur:
    - Centralized error handling
    - Logging untuk semua operations
    - Dependency injection (repositories)
    - Validation before operations
    
    Subclass harus:
    - Call parent __init__ untuk setup
    - Implement abstract methods
    - Use self.repositories untuk data access
    - Raise custom exceptions (POSException subclasses)
    """
    
    def __init__(self, repository_factory: RepositoryFactory):
        """
        Initialize base service.
        
        Args:
            repository_factory (RepositoryFactory): Factory untuk repositories
        """
        self.repository_factory = repository_factory
        self.repositories = repository_factory.get_all_repositories()
        self.logger = get_logger(self.__class__.__name__)
    
    def _log_info(self, message: str) -> None:
        """Log info message."""
        self.logger.info(message)
    
    def _log_warning(self, message: str) -> None:
        """Log warning message."""
        self.logger.warning(message)
    
    def _log_error(self, message: str, exc: Exception = None) -> None:
        """Log error message."""
        if exc:
            self.logger.error(message, exc_info=exc)
        else:
            self.logger.error(message)
    
    def _log_operation(self, operation: str, details: str = "", success: bool = True) -> None:
        """Log operation result."""
        status = "SUCCESS" if success else "FAILED"
        self.logger.info(f"[{status}] {operation} - {details}")
    
    @abstractmethod
    def validate(self) -> bool:
        """Validate service initialization. Override in subclass."""
        return True


class ProductService(BaseService):
    """
    Business logic untuk Product management.
    
    Responsibilities:
    - Create, read, update, delete products
    - Validate product data
    - Handle product lifecycle
    - Manage stock levels
    
    Methods:
        create_product(): Create new product with validation
        get_product(): Get product by ID/code
        list_products(): List all products
        update_product(): Update product with validation
        delete_product(): Delete product
        search_products(): Search products by name
    """
    
    def validate(self) -> bool:
        """Validate ProductService initialization."""
        try:
            # Check if database is accessible
            products = self.repositories['product'].list_all()
            self._log_info(f"ProductService initialized. {len(products)} products in system")
            return True
        except Exception as e:
            self._log_error("ProductService initialization failed", e)
            return False
    
    def create_product(self, kode: str, nama: str, harga: int, 
                      stok: int = 0, min_stok: int = 0, 
                      kategori: str = "General") -> 'Product':
        """
        Create new product dengan validation.
        
        Args:
            kode (str): Product code (unique)
            nama (str): Product name
            harga (int): Price in IDR
            stok (int): Initial stock
            min_stok (int): Minimum stock level
            kategori (str): Product category
            
        Returns:
            Product: Created product object
            
        Raises:
            ProductValidationError: If validation fails
            DatabaseError: If database operation fails
        """
        from ..core import ProductValidator
        
        # Validate all inputs
        kode = ProductValidator.validate_kode(kode)
        nama = ProductValidator.validate_nama(nama)
        harga = ProductValidator.validate_harga(harga)
        stok = ProductValidator.validate_stok(stok)
        min_stok = ProductValidator.validate_min_stok(min_stok)
        
        # Check kode uniqueness
        existing = self.repositories['product'].get_by_kode(kode)
        if existing:
            from ..core import ProductValidationError
            raise ProductValidationError(f"Kode '{kode}' sudah digunakan", kode)
        
        # Create product via repository
        try:
            product = self.repositories['product'].create(
                kode=kode,
                nama=nama,
                harga=harga,
                stok=stok,
                min_stok=min_stok,
                kategori=kategori
            )
            
            self._log_operation(
                "Create Product",
                f"ID={product.id}, Code={kode}, Name={nama}",
                True
            )
            
            return product
        
        except Exception as e:
            self._log_error(f"Gagal create product {kode}", e)
            raise
    
    def get_product_by_id(self, product_id: int) -> Optional['Product']:
        """Get product by ID."""
        return self.repositories['product'].get_by_id(product_id)
    
    def get_product_by_kode(self, kode: str) -> Optional['Product']:
        """Get product by code (cached)."""
        return self.repositories['product'].get_by_kode(kode)
    
    def list_products(self) -> list:
        """Get all products (cached)."""
        try:
            products = self.repositories['product'].list_all()
            return products
        except Exception as e:
            self._log_error("Gagal list products", e)
            return []
    
    def update_product(self, product_id: int, **kwargs) -> bool:
        """
        Update product with validation.
        
        Args:
            product_id (int): Product ID
            **kwargs: Fields to update (nama, harga, stok, min_stok, kategori)
            
        Returns:
            bool: True if updated
        """
        from ..core import ProductValidator, format_rp
        
        # Validate fields
        if 'harga' in kwargs:
            kwargs['harga'] = ProductValidator.validate_harga(kwargs['harga'])
        if 'stok' in kwargs:
            kwargs['stok'] = ProductValidator.validate_stok(kwargs['stok'])
        if 'min_stok' in kwargs:
            kwargs['min_stok'] = ProductValidator.validate_min_stok(kwargs['min_stok'])
        if 'nama' in kwargs:
            kwargs['nama'] = ProductValidator.validate_nama(kwargs['nama'])
        
        # Update via repository
        try:
            success = self.repositories['product'].update(product_id, **kwargs)
            
            if success:
                details = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
                self._log_operation("Update Product", f"ID={product_id}, {details}", True)
            
            return success
        
        except Exception as e:
            self._log_error(f"Gagal update product {product_id}", e)
            raise
    
    def delete_product(self, product_id: int) -> bool:
        """
        Delete product.
        
        Args:
            product_id (int): Product ID
            
        Returns:
            bool: True if deleted
        """
        try:
            success = self.repositories['product'].delete(product_id)
            self._log_operation("Delete Product", f"ID={product_id}", success)
            return success
        except Exception as e:
            self._log_error(f"Gagal delete product {product_id}", e)
            raise
    
    def search_products_by_name(self, search_term: str) -> list:
        """Search products by name."""
        try:
            return self.repositories['product'].search_by_name(search_term)
        except Exception as e:
            self._log_error(f"Gagal search products '{search_term}'", e)
            return []
    
    def get_low_stock_products(self) -> list:
        """Get products with stock below minimum level."""
        try:
            products = self.repositories['product'].get_low_stock_products()
            return products
        except Exception as e:
            self._log_error("Gagal get low stock products", e)
            return []
