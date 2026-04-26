# ============================================================================
# PRODUCT_SERVICE.PY - Business Logic Layer untuk Products
# ============================================================================
# Fungsi: Handle semua business rules, validasi, & transaction management
# Responsibilitas: NO direct database access (gunakan repository)
# ============================================================================

from typing import List, Optional, Dict, Any
from models import Product, ValidationError, validate_kode, validate_nama, validate_harga, validate_qty
from app.repositories.product_repository import ProductRepository
from app.utils.error_handler import ValidationError as ServiceValidationError, DatabaseError
from logger_config import get_logger

logger = get_logger(__name__)


class ProductService:
    """Service layer untuk product business logic."""
    
    def __init__(self, product_repository: ProductRepository):
        """
        Init dengan ProductRepository.
        
        Args:
            product_repository: ProductRepository instance
        """
        self.repo = product_repository
    
    def create_product(
        self,
        kode: str,
        nama: str,
        harga: int,
        qty: int,
        satuan: str = "pcs",
        foto: str = ""
    ) -> Product:
        """
        Create produk baru dengan validasi & business rules.
        
        Args:
            kode: Kode produk
            nama: Nama produk
            harga: Harga jual
            qty: Quantity stok
            satuan: Satuan item
            foto: Path foto
            
        Returns:
            Product object yang baru dibuat
            
        Raises:
            ServiceValidationError: Jika validasi gagal
            DatabaseError: Jika database error
        """
        try:
            # Validasi input
            kode = validate_kode(kode)
            nama = validate_nama(nama)
            harga = validate_harga(harga)
            qty = validate_qty(qty)
            
            # Check apakah kode sudah ada
            existing = self.repo.get_by_kode(kode)
            if existing:
                raise ServiceValidationError("Kode produk sudah ada", "Silakan gunakan kode yang berbeda")
            
            # Create di repository
            product = self.repo.create(kode, nama, harga, qty, satuan, foto)
            logger.info(f"Product created via service: {kode} - {nama}")
            
            return product
        
        except (ValidationError, ServiceValidationError):
            raise
        except Exception as e:
            logger.error(f"Error creating product: {e}")
            raise DatabaseError(str(e), "Gagal membuat produk")
    
    def get_product(self, kode: str) -> Optional[Product]:
        """Get produk berdasarkan kode."""
        product = self.repo.get_by_kode(kode)
        if not product:
            logger.warning(f"Product not found: {kode}")
        return product
    
    def list_products(self, limit: int = 0) -> List[Product]:
        """
        List semua products.
        
        Args:
            limit: Limit hasil (0 = unlimited)
            
        Returns:
            List of products
        """
        return self.repo.list_all(limit=limit)
    
    def update_product(
        self,
        kode: str,
        **kwargs
    ) -> bool:
        """
        Update produk berdasarkan kode.
        
        Args:
            kode: Kode produk
            **kwargs: Field yang mau di-update
            
        Returns:
            True jika berhasil
            
        Raises:
            ServiceValidationError: Jika validasi gagal
        """
        try:
            product = self.repo.get_by_kode(kode)
            if not product:
                raise ServiceValidationError(f"Produk {kode} tidak ditemukan")
            
            # Validasi field yang di-update
            if 'harga' in kwargs:
                kwargs['harga'] = validate_harga(kwargs['harga'])
            if 'qty' in kwargs:
                kwargs['qty'] = validate_qty(kwargs['qty'])
            if 'nama' in kwargs:
                kwargs['nama'] = validate_nama(kwargs['nama'])
            
            result = self.repo.update(product.id, **kwargs)
            if result:
                logger.info(f"Product updated: {kode}")
            return result
        except ServiceValidationError:
            raise
        except Exception as e:
            logger.error(f"Error updating product: {e}")
            raise DatabaseError(str(e))
    
    def delete_product(self, kode: str) -> bool:
        """
        Delete produk berdasarkan kode.
        
        Args:
            kode: Kode produk
            
        Returns:
            True jika berhasil
        """
        try:
            product = self.repo.get_by_kode(kode)
            if not product:
                raise ServiceValidationError(f"Produk {kode} tidak ditemukan")
            
            result = self.repo.delete(product.id)
            if result:
                logger.info(f"Product deleted: {kode}")
            return result
        except ServiceValidationError:
            raise
        except Exception as e:
            logger.error(f"Error deleting product: {e}")
            raise DatabaseError(str(e))
    
    def search_products(self, query: str) -> List[Product]:
        """
        Search produk by kode or nama.
        
        Args:
            query: Search query
            
        Returns:
            List of matching products
        """
        if not query or len(query.strip()) == 0:
            return []
        
        return self.repo.search(query.strip())
    
    def reduce_stock(self, kode: str, qty: int) -> bool:
        """
        Reduce stock untuk transaksi.
        
        Args:
            kode: Kode produk
            qty: Jumlah yang dikurangi
            
        Returns:
            True jika berhasil
            
        Raises:
            ServiceValidationError: Jika stok tidak cukup
        """
        try:
            product = self.repo.get_by_kode(kode)
            if not product:
                raise ServiceValidationError(f"Produk {kode} tidak ditemukan")
            
            qty = validate_qty(qty)
            
            if product.qty < qty:
                raise ServiceValidationError(
                    f"Stok {kode} hanya {product.qty}, tapi {qty} diminta",
                    f"Stok tidak cukup untuk {product.nama}"
                )
            
            new_qty = product.qty - qty
            result = self.repo.update(product.id, qty=new_qty)
            
            if result:
                logger.info(f"Stock reduced: {kode} dari {product.qty} ke {new_qty}")
            
            return result
        except ServiceValidationError:
            raise
        except Exception as e:
            logger.error(f"Error reducing stock: {e}")
            raise DatabaseError(str(e))
    
    def increase_stock(self, kode: str, qty: int) -> bool:
        """
        Increase stock (untuk stok opname, return, etc).
        
        Args:
            kode: Kode produk
            qty: Jumlah yang ditambah
            
        Returns:
            True jika berhasil
        """
        try:
            product = self.repo.get_by_kode(kode)
            if not product:
                raise ServiceValidationError(f"Produk {kode} tidak ditemukan")
            
            qty = validate_qty(qty)
            new_qty = product.qty + qty
            
            result = self.repo.update(product.id, qty=new_qty)
            if result:
                logger.info(f"Stock increased: {kode} dari {product.qty} ke {new_qty}")
            
            return result
        except ServiceValidationError:
            raise
        except Exception as e:
            logger.error(f"Error increasing stock: {e}")
            raise DatabaseError(str(e))
    
    def get_low_stock_products(self, threshold: int = 10) -> List[Dict[str, Any]]:
        """
        Get produk dengan stok rendah.
        
        Args:
            threshold: Minimum stok
            
        Returns:
            List of low stock products
        """
        return self.repo.get_low_stock(threshold)
    
    def get_total_inventory_value(self) -> int:
        """
        Calculate total inventory value.
        
        Returns:
            Total value dalam Rupiah
        """
        try:
            products = self.repo.list_all()
            total = sum(p.harga * p.qty for p in products)
            return total
        except Exception as e:
            logger.error(f"Error calculating inventory value: {e}")
            return 0
