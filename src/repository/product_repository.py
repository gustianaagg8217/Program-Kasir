# ============================================================================
# PRODUCT_REPOSITORY.PY - Product Data Access Layer
# ============================================================================
# Fungsi: Handle semua DB operations untuk Product entity
# Separate dari business logic (yang di service layer)
# ============================================================================

from typing import List, Optional
from datetime import datetime

from ..core import Product, Inventory, ProductNotFoundError, DatabaseError
from .base_repository import CacheableRepository


class ProductRepository(CacheableRepository):
    """
    Repository untuk Product CRUD operations.
    
    Methods:
        create(kode, nama, harga, stok, ...): Create product
        get_by_id(product_id): Get product by ID
        get_by_kode(kode): Get product by code (with cache)
        list_all(): List all products (with cache)
        update(product_id, ...): Update product
        delete(product_id): Delete product
        update_stok(product_id, qty_change): Update stock quantity
        get_low_stock_products(): Get products below min stock
    """
    
    def create(self, kode: str, nama: str, harga: int, stok: int = 0, 
               min_stok: int = 0, kategori: str = "General") -> Product:
        """
        Create new product.
        
        Args:
            kode (str): Product code (unique)
            nama (str): Product name
            harga (int): Price in IDR
            stok (int): Initial stock quantity
            min_stok (int): Minimum stock level
            kategori (str): Product category
            
        Returns:
            Product: Created product with ID
            
        Raises:
            DatabaseError: If creation fails
        """
        with self.get_db() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO products (kode, nama, harga, stok, min_stok, kategori, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (kode, nama, harga, stok, min_stok, kategori, datetime.now(), datetime.now()))
                
                product_id = cursor.lastrowid
                
                # Invalidate cache
                self._invalidate_cache("products")
                
                return Product(
                    id=product_id,
                    kode=kode,
                    nama=nama,
                    harga=harga,
                    stok=stok,
                    min_stok=min_stok,
                    kategori=kategori,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
            except Exception as e:
                raise DatabaseError(f"Gagal create product: {str(e)}", "create")
    
    def read(self, product_id: int) -> Optional[Product]:
        """Get product by ID (without cache)."""
        return self.get_by_id(product_id)
    
    def get_by_id(self, product_id: int) -> Optional[Product]:
        """
        Get product by ID.
        
        Args:
            product_id (int): Product ID
            
        Returns:
            Product: Product object or None if not found
        """
        with self.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, kode, nama, harga, stok, min_stok, kategori, created_at, updated_at
                FROM products WHERE id = ?
            """, (product_id,))
            
            row = cursor.fetchone()
            return self._map_row_to_product(row) if row else None
    
    def get_by_kode(self, kode: str) -> Optional[Product]:
        """
        Get product by code (with cache).
        
        Args:
            kode (str): Product code
            
        Returns:
            Product: Product object or None if not found
        """
        # Check cache first
        cache_key = f"product_kode_{kode.upper()}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached
        
        with self.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, kode, nama, harga, stok, min_stok, kategori, created_at, updated_at
                FROM products WHERE UPPER(kode) = UPPER(?)
            """, (kode,))
            
            row = cursor.fetchone()
            product = self._map_row_to_product(row) if row else None
            
            if product:
                self._set_cache(cache_key, product)
            
            return product
    
    def list_all(self) -> List[Product]:
        """
        Get all products (with cache).
        
        Returns:
            List[Product]: List of all products
        """
        cache_key = "products_all"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached
        
        with self.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, kode, nama, harga, stok, min_stok, kategori, created_at, updated_at
                FROM products ORDER BY nama ASC
            """)
            
            rows = cursor.fetchall()
            products = [self._map_row_to_product(row) for row in rows]
            
            self._set_cache(cache_key, products)
            return products
    
    def update(self, product_id: int, **kwargs) -> bool:
        """
        Update product.
        
        Args:
            product_id (int): Product ID
            **kwargs: Fields to update (nama, harga, stok, min_stok, kategori)
            
        Returns:
            bool: True if updated successfully
        """
        # Build dynamic update query
        allowed_fields = {'nama', 'harga', 'stok', 'min_stok', 'kategori'}
        fields_to_update = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not fields_to_update:
            return False
        
        # Add updated_at timestamp
        fields_to_update['updated_at'] = datetime.now()
        
        set_clause = ', '.join([f"{k} = ?" for k in fields_to_update.keys()])
        values = list(fields_to_update.values()) + [product_id]
        
        with self.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE products SET {set_clause} WHERE id = ?
            """, values)
            
            # Invalidate cache
            self._invalidate_cache("products")
            
            return cursor.rowcount > 0
    
    def delete(self, product_id: int) -> bool:
        """
        Delete product.
        
        Args:
            product_id (int): Product ID
            
        Returns:
            bool: True if deleted
        """
        with self.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
            
            # Invalidate cache
            self._invalidate_cache("products")
            
            return cursor.rowcount > 0
    
    def update_stok(self, product_id: int, qty_change: int) -> Optional[int]:
        """
        Update product stock (add/subtract).
        
        Args:
            product_id (int): Product ID
            qty_change (int): Change in quantity (positive to add, negative to subtract)
            
        Returns:
            int: New stock level, or None if product not found
            
        Raises:
            DatabaseError: If operation fails
        """
        with self.get_db() as conn:
            cursor = conn.cursor()
            
            # Get current stock
            cursor.execute("SELECT stok FROM products WHERE id = ?", (product_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            current_stok = row[0]
            new_stok = current_stok + qty_change
            
            # Ensure stock doesn't go below 0
            if new_stok < 0:
                raise DatabaseError(
                    f"Stok tidak boleh negatif. Current: {current_stok}, change: {qty_change}",
                    "update_stok"
                )
            
            # Update stock
            cursor.execute("""
                UPDATE products SET stok = ?, updated_at = ? WHERE id = ?
            """, (new_stok, datetime.now(), product_id))
            
            # Invalidate cache
            self._invalidate_cache("products")
            
            return new_stok
    
    def get_low_stock_products(self, threshold: int = None) -> List[Product]:
        """
        Get products with stock below minimum level.
        
        Args:
            threshold (int): Custom threshold (if None, use product's min_stok)
            
        Returns:
            List[Product]: List of low stock products
        """
        with self.get_db() as conn:
            cursor = conn.cursor()
            
            if threshold is None:
                cursor.execute("""
                    SELECT id, kode, nama, harga, stok, min_stok, kategori, created_at, updated_at
                    FROM products WHERE stok <= min_stok ORDER BY stok ASC
                """)
            else:
                cursor.execute("""
                    SELECT id, kode, nama, harga, stok, min_stok, kategori, created_at, updated_at
                    FROM products WHERE stok <= ? ORDER BY stok ASC
                """, (threshold,))
            
            rows = cursor.fetchall()
            return [self._map_row_to_product(row) for row in rows]
    
    def search_by_name(self, search_term: str) -> List[Product]:
        """
        Search products by name (case-insensitive).
        
        Args:
            search_term (str): Search term
            
        Returns:
            List[Product]: List of matching products
        """
        with self.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, kode, nama, harga, stok, min_stok, kategori, created_at, updated_at
                FROM products WHERE UPPER(nama) LIKE UPPER(?) ORDER BY nama ASC
            """, (f"%{search_term}%",))
            
            rows = cursor.fetchall()
            return [self._map_row_to_product(row) for row in rows]
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    @staticmethod
    def _map_row_to_product(row) -> Product:
        """Convert database row to Product object."""
        if row is None:
            return None
        
        return Product(
            id=row['id'],
            kode=row['kode'],
            nama=row['nama'],
            harga=row['harga'],
            stok=row['stok'],
            min_stok=row['min_stok'],
            kategori=row['kategori'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )


class InventoryRepository(CacheableRepository):
    """
    Repository untuk Inventory tracking (stock movements).
    
    Methods:
        record_movement(product_id, qty_change, operation): Record stock change
        get_movements(product_id): Get all movements for a product
    """
    
    def create(self, product_id: int, qty_change: int, operation: str, notes: str = "") -> int:
        """
        Record inventory movement.
        
        Args:
            product_id (int): Product ID
            qty_change (int): Quantity change (positive=in, negative=out)
            operation (str): Operation type (sale, restock, adjustment)
            notes (str): Optional notes
            
        Returns:
            int: Movement ID
        """
        with self.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO inventory (product_id, qty_change, operation, notes, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (product_id, qty_change, operation, notes, datetime.now()))
            
            return cursor.lastrowid
    
    def read(self, entity_id: int) -> Optional[Inventory]:
        """Get movement by ID."""
        with self.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, product_id, qty_change, operation, notes, created_at
                FROM inventory WHERE id = ?
            """, (entity_id,))
            
            row = cursor.fetchone()
            return self._map_row_to_inventory(row) if row else None
    
    def list_all(self) -> List[Inventory]:
        """List all movements."""
        with self.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, product_id, qty_change, operation, notes, created_at
                FROM inventory ORDER BY created_at DESC LIMIT 1000
            """)
            
            rows = cursor.fetchall()
            return [self._map_row_to_inventory(row) for row in rows]
    
    def get_product_movements(self, product_id: int) -> List[Inventory]:
        """Get all movements for a product."""
        with self.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, product_id, qty_change, operation, notes, created_at
                FROM inventory WHERE product_id = ? ORDER BY created_at DESC
            """, (product_id,))
            
            rows = cursor.fetchall()
            return [self._map_row_to_inventory(row) for row in rows]
    
    def update(self, entity_id: int, **kwargs) -> bool:
        """Not typically used for inventory movements."""
        return False
    
    def delete(self, entity_id: int) -> bool:
        """Delete movement record."""
        with self.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM inventory WHERE id = ?", (entity_id,))
            return cursor.rowcount > 0
    
    @staticmethod
    def _map_row_to_inventory(row) -> Inventory:
        """Convert database row to Inventory object."""
        if row is None:
            return None
        
        return Inventory(
            id=row['id'],
            product_id=row['product_id'],
            qty_change=row['qty_change'],
            operation=row['operation'],
            notes=row['notes'],
            created_at=row['created_at']
        )
