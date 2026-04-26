# ============================================================================
# PRODUCT_REPOSITORY.PY - Database Access Layer untuk Products
# ============================================================================
# Fungsi: CRUD operations untuk product data
# Responsibilitas: Direct database access ONLY, no business logic
# ============================================================================

from typing import List, Optional, Dict, Any
from database import DatabaseManager
from models import Product
from logger_config import get_logger
from app.utils.error_handler import DatabaseError, NotFoundError

logger = get_logger(__name__)


class ProductRepository:
    """Repository untuk product data access."""
    
    def __init__(self, db: DatabaseManager):
        """
        Init dengan DatabaseManager instance.
        
        Args:
            db: DatabaseManager instance
        """
        self.db = db
    
    def create(self, kode: str, nama: str, harga: int, qty: int, satuan: str = "pcs", foto: str = "") -> Product:
        """
        Create produk baru di database.
        
        Args:
            kode: Kode produk
            nama: Nama produk
            harga: Harga jual
            qty: Quantity stok
            satuan: Satuan (default: pcs)
            foto: Path foto
            
        Returns:
            Product object yang baru dibuat
            
        Raises:
            DatabaseError: Jika insert gagal
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO products (kode, nama, harga, qty, satuan, foto)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (kode, nama, harga, qty, satuan, foto))
                conn.commit()
                
                product_id = cursor.lastrowid
                logger.info(f"Product created: ID={product_id}, kode={kode}")
                
                return Product(
                    id=product_id,
                    kode=kode,
                    nama=nama,
                    harga=harga,
                    qty=qty,
                    satuan=satuan,
                    foto=foto
                )
        except Exception as e:
            logger.error(f"Error creating product: {e}")
            raise DatabaseError(str(e), "Gagal membuat produk")
    
    def get_by_id(self, product_id: int) -> Optional[Product]:
        """
        Get produk berdasarkan ID.
        
        Args:
            product_id: Product ID
            
        Returns:
            Product object atau None jika tidak ada
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                return self._map_to_product(row)
        except Exception as e:
            logger.error(f"Error getting product by id: {e}")
            return None
    
    def get_by_kode(self, kode: str) -> Optional[Product]:
        """
        Get produk berdasarkan kode.
        
        Args:
            kode: Product kode
            
        Returns:
            Product object atau None
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM products WHERE kode = ?", (kode,))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                return self._map_to_product(row)
        except Exception as e:
            logger.error(f"Error getting product by kode: {e}")
            return None
    
    def list_all(self, limit: int = 0, offset: int = 0) -> List[Product]:
        """
        Get semua products dengan pagination.
        
        Args:
            limit: Limit hasil (0 = unlimited)
            offset: Offset untuk pagination
            
        Returns:
            List of Product objects
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                if limit > 0:
                    cursor.execute("SELECT * FROM products LIMIT ? OFFSET ?", (limit, offset))
                else:
                    cursor.execute("SELECT * FROM products")
                
                rows = cursor.fetchall()
                return [self._map_to_product(row) for row in rows]
        except Exception as e:
            logger.error(f"Error listing products: {e}")
            return []
    
    def update(self, product_id: int, **kwargs) -> bool:
        """
        Update product berdasarkan ID.
        
        Args:
            product_id: Product ID
            **kwargs: Field yang mau di-update (nama, harga, qty, satuan, foto)
            
        Returns:
            True jika berhasil, False jika gagal
        """
        try:
            allowed_fields = {'nama', 'harga', 'qty', 'satuan', 'foto'}
            fields_to_update = {k: v for k, v in kwargs.items() if k in allowed_fields}
            
            if not fields_to_update:
                return False
            
            set_clause = ", ".join([f"{k} = ?" for k in fields_to_update.keys()])
            values = list(fields_to_update.values()) + [product_id]
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"UPDATE products SET {set_clause} WHERE id = ?", values)
                conn.commit()
                
                logger.info(f"Product updated: ID={product_id}, fields={list(fields_to_update.keys())}")
                return True
        except Exception as e:
            logger.error(f"Error updating product: {e}")
            return False
    
    def delete(self, product_id: int) -> bool:
        """
        Delete product berdasarkan ID.
        
        Args:
            product_id: Product ID
            
        Returns:
            True jika berhasil, False jika gagal
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
                conn.commit()
                
                logger.info(f"Product deleted: ID={product_id}")
                return True
        except Exception as e:
            logger.error(f"Error deleting product: {e}")
            return False
    
    def search(self, query: str) -> List[Product]:
        """
        Search products berdasarkan kode atau nama.
        
        Args:
            query: Search query
            
        Returns:
            List of matching Product objects
        """
        try:
            query_pattern = f"%{query}%"
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM products 
                    WHERE kode LIKE ? OR nama LIKE ?
                """, (query_pattern, query_pattern))
                
                rows = cursor.fetchall()
                return [self._map_to_product(row) for row in rows]
        except Exception as e:
            logger.error(f"Error searching products: {e}")
            return []
    
    def get_low_stock(self, threshold: int = 10) -> List[Dict[str, Any]]:
        """
        Get produk dengan stok di bawah threshold.
        
        Args:
            threshold: Minimum stok
            
        Returns:
            List of low stock products
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, kode, nama, qty, satuan
                    FROM products
                    WHERE qty < ?
                    ORDER BY qty ASC
                """, (threshold,))
                
                rows = cursor.fetchall()
                return [
                    {'id': r[0], 'kode': r[1], 'nama': r[2], 'qty': r[3], 'satuan': r[4]}
                    for r in rows
                ]
        except Exception as e:
            logger.error(f"Error getting low stock: {e}")
            return []
    
    @staticmethod
    def _map_to_product(row: tuple) -> Product:
        """Map database row ke Product object."""
        return Product(
            id=row[0],
            kode=row[1],
            nama=row[2],
            harga=row[3],
            qty=row[4],
            satuan=row[5],
            foto=row[6] if len(row) > 6 else ""
        )
