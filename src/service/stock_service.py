# ============================================================================
# STOCK_SERVICE.PY - Stock Management Service (Service Layer)
# ============================================================================
# Fungsi: Handle stock updates, low stock alerts, inventory tracking
# Ensure atomic stock operations
# ============================================================================

from typing import List, Optional
from datetime import datetime

from ..core import (
    InsufficientStockError, DatabaseError, 
    format_rp, QuantityValidator
)
from ..repository import RepositoryFactory
from .base_service import BaseService
from logger_config import get_logger

logger = get_logger(__name__)


class StockService(BaseService):
    """
    Business logic untuk Stock management.
    
    Responsibilities:
    - Deduct stock saat transaksi selesai
    - Add stock saat restock
    - Track stock movements (inventory history)
    - Alert untuk low stock
    - Validate stock tersedia sebelum transaksi
    
    Methods:
        validate_stock_available(): Check stok sebelum transaksi
        deduct_stock(): Kurangi stok (saat sale)
        add_stock(): Tambah stok (saat restock)
        adjust_stock(): Adjust stok (untuk koreksi)
        get_low_stock_products(): Get low stock products
        record_movement(): Record stock movement history
    """
    
    def validate(self) -> bool:
        """Validate StockService initialization."""
        try:
            self._log_info("StockService initialized")
            return True
        except Exception as e:
            self._log_error("StockService initialization failed", e)
            return False
    
    def validate_stock_available(self, product_id: int, qty_needed: int) -> bool:
        """
        Validate if sufficient stock available untuk transaction item.
        
        Args:
            product_id (int): Product ID
            qty_needed (int): Quantity needed
            
        Returns:
            bool: True if stock available
            
        Raises:
            InsufficientStockError: If stock tidak cukup
        """
        # Validate quantity
        qty_needed = QuantityValidator.validate_qty(qty_needed)
        
        # Get product
        product = self.repositories['product'].get_by_id(product_id)
        if not product:
            raise DatabaseError(f"Produk ID {product_id} tidak ditemukan", "validate_stock")
        
        # Check stock
        if product.stok < qty_needed:
            raise InsufficientStockError(
                product_name=product.nama,
                required=qty_needed,
                available=product.stok
            )
        
        return True
    
    def deduct_stock(self, product_id: int, qty_to_deduct: int, 
                    notes: str = "") -> Optional[int]:
        """
        Deduct stock (mengurangi stok saat sale).
        
        Process:
        1. Validate stock tersedia
        2. Update stock di database
        3. Record movement history
        4. Log operation
        
        Args:
            product_id (int): Product ID
            qty_to_deduct (int): Quantity to deduct (positive number)
            notes (str): Optional notes for history
            
        Returns:
            int: New stock level, or None if product not found
            
        Raises:
            InsufficientStockError: If current stock tidak cukup
            DatabaseError: If operation fails
        """
        # Validate quantity
        qty_to_deduct = QuantityValidator.validate_qty(qty_to_deduct)
        
        # Validate stock available
        self.validate_stock_available(product_id, qty_to_deduct)
        
        # Get product untuk logging
        product = self.repositories['product'].get_by_id(product_id)
        
        try:
            # Deduct stock (negative change)
            new_stok = self.repositories['product'].update_stok(
                product_id, 
                -qty_to_deduct
            )
            
            # Record movement
            self.record_movement(
                product_id=product_id,
                qty_change=-qty_to_deduct,
                operation=\"sale\",
                notes=notes
            )
            
            self._log_operation(
                \"Deduct Stock\",
                f\"Product={product.nama}, Qty={qty_to_deduct}, New Stock={new_stok}\",
                True
            )
            
            # Check if below min stock
            if product.min_stok > 0 and new_stok <= product.min_stok:
                self._log_warning(
                    f\"Low stock alert: {product.nama} stok {new_stok} <= min {product.min_stok}\"
                )
            
            return new_stok
        
        except Exception as e:
            self._log_error(f\"Gagal deduct stock product {product_id}\", e)
            raise
    
    def add_stock(self, product_id: int, qty_to_add: int, 
                 notes: str = \"\") -> Optional[int]:
        \"\"\"
        Add stock (menambah stok saat restock).
        
        Args:
            product_id (int): Product ID
            qty_to_add (int): Quantity to add (positive number)
            notes (str): Optional notes (e.g., \"Restock from supplier\")
            
        Returns:
            int: New stock level
            
        Raises:
            DatabaseError: If operation fails
        \"\"\"
        # Validate quantity
        qty_to_add = QuantityValidator.validate_qty(qty_to_add)
        
        # Get product
        product = self.repositories['product'].get_by_id(product_id)
        if not product:
            raise DatabaseError(f\"Produk ID {product_id} tidak ditemukan\", \"add_stock\")
        
        try:
            # Add stock (positive change)
            new_stok = self.repositories['product'].update_stok(
                product_id,
                qty_to_add
            )
            
            # Record movement
            self.record_movement(
                product_id=product_id,
                qty_change=qty_to_add,
                operation=\"restock\",
                notes=notes if notes else \"Restock\"
            )
            
            self._log_operation(
                \"Add Stock\",
                f\"Product={product.nama}, Qty={qty_to_add}, New Stock={new_stok}\",
                True
            )
            
            return new_stok
        
        except Exception as e:
            self._log_error(f\"Gagal add stock product {product_id}\", e)
            raise
    
    def adjust_stock(self, product_id: int, new_stock_level: int, 
                    reason: str = \"\") -> Optional[int]:
        \"\"\"
        Adjust stock to specific level (for corrections/adjustments).
        
        Args:
            product_id (int): Product ID
            new_stock_level (int): New stock level to set
            reason (str): Reason for adjustment
            
        Returns:
            int: Adjustment made (difference)
        \"\"\"
        # Validate
        new_stock_level = QuantityValidator.validate_qty(new_stock_level)
        
        # Get current stock
        product = self.repositories['product'].get_by_id(product_id)
        if not product:
            raise DatabaseError(f\"Produk ID {product_id} tidak ditemukan\", \"adjust_stock\")
        
        current_stok = product.stok
        adjustment = new_stock_level - current_stok
        
        try:
            # Update stock
            result_stok = self.repositories['product'].update_stok(
                product_id,
                adjustment
            )
            
            # Record movement
            self.record_movement(
                product_id=product_id,
                qty_change=adjustment,
                operation=\"adjustment\",
                notes=reason if reason else \"Stock adjustment\"
            )
            
            self._log_operation(
                \"Adjust Stock\",
                f\"Product={product.nama}, Old={current_stok}, New={new_stock_level}, Diff={adjustment}\",
                True
            )
            
            return adjustment
        
        except Exception as e:
            self._log_error(f\"Gagal adjust stock product {product_id}\", e)
            raise
    
    def record_movement(self, product_id: int, qty_change: int, 
                       operation: str, notes: str = \"\") -> int:
        \"\"\"
        Record stock movement history.
        
        Args:
            product_id (int): Product ID
            qty_change (int): Quantity change
            operation (str): Operation type (sale, restock, adjustment)
            notes (str): Optional notes
            
        Returns:
            int: Movement record ID
        \"\"\"
        try:
            movement_id = self.repositories['inventory'].create(
                product_id=product_id,
                qty_change=qty_change,
                operation=operation,
                notes=notes
            )
            
            return movement_id
        
        except Exception as e:
            self._log_error(f\"Gagal record movement for product {product_id}\", e)
            raise
    
    def get_low_stock_products(self) -> List:
        \"\"\"Get products with stock below minimum level.\"\"\"
        try:
            return self.repositories['product'].get_low_stock_products()
        except Exception as e:
            self._log_error(\"Gagal get low stock products\", e)
            return []
    
    def get_product_movements(self, product_id: int) -> List:
        \"\"\"Get stock movements history for a product.\"\"\"
        try:
            return self.repositories['inventory'].get_product_movements(product_id)
        except Exception as e:
            self._log_error(f\"Gagal get movements for product {product_id}\", e)
            return []
