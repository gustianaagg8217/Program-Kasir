# ============================================================================
# INVENTORY_REPOSITORY.PY - Inventory/Stock Data Access Layer
# ============================================================================
# Fungsi: Handle inventory movement tracking and stock history
# CRUD operations untuk Inventory records
# ============================================================================

from typing import List, Optional
from datetime import datetime

from ..core import Inventory
from .base_repository import BaseRepository
from logger_config import get_logger

logger = get_logger(__name__)


class InventoryRepository(BaseRepository):
    """
    Repository untuk Inventory (stock movements) data access.
    
    Handles:
    - Record stock movements (sales, restocks, adjustments)
    - Retrieve stock history
    - Calculate stock changes over time
    """
    
    def create(self, **kwargs) -> Inventory:
        """Create new inventory movement record."""
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO inventory (
                        product_id, qty_change, operation, notes, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    kwargs.get('product_id'),
                    kwargs.get('qty_change'),
                    kwargs.get('operation'),
                    kwargs.get('notes', ''),
                    kwargs.get('created_at', datetime.now())
                ))
                
                movement_id = cursor.lastrowid
                logger.info(f"Inventory movement recorded: ID {movement_id}")
                
                return self.get_by_id(movement_id)
                
        except Exception as e:
            logger.error(f"Error creating inventory movement: {e}", exc_info=e)
            raise
    
    def get_by_id(self, movement_id: int) -> Optional[Inventory]:
        """Get inventory movement by ID."""
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM inventory WHERE id = ?
                """, (movement_id,))
                
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_inventory(row)
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting inventory movement {movement_id}: {e}", exc_info=e)
            raise
    
    def get_by_product(self, product_id: int, limit: int = 100) -> List[Inventory]:
        """Get stock history for product."""
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM inventory
                    WHERE product_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (product_id, limit))
                
                movements = []
                for row in cursor.fetchall():
                    movements.append(self._row_to_inventory(row))
                
                return movements
                
        except Exception as e:
            logger.error(f"Error getting inventory for product {product_id}: {e}", exc_info=e)
            raise
    
    def get_by_operation(self, operation: str) -> List[Inventory]:
        """Get movements by operation type."""
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM inventory
                    WHERE operation = ?
                    ORDER BY created_at DESC
                """, (operation,))
                
                movements = []
                for row in cursor.fetchall():
                    movements.append(self._row_to_inventory(row))
                
                return movements
                
        except Exception as e:
            logger.error(f"Error getting inventory by operation {operation}: {e}", exc_info=e)
            raise
    
    def get_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Inventory]:
        """Get movements within date range."""
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM inventory
                    WHERE created_at BETWEEN ? AND ?
                    ORDER BY created_at DESC
                """, (start_date, end_date))
                
                movements = []
                for row in cursor.fetchall():
                    movements.append(self._row_to_inventory(row))
                
                return movements
                
        except Exception as e:
            logger.error(f"Error getting inventory for date range: {e}", exc_info=e)
            raise
    
    def get_total_movement(self, product_id: int, operation: str = None) -> int:
        """Get total qty movement for product."""
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()
                
                if operation:
                    cursor.execute("""
                        SELECT SUM(qty_change) as total
                        FROM inventory
                        WHERE product_id = ? AND operation = ?
                    """, (product_id, operation))
                else:
                    cursor.execute("""
                        SELECT SUM(qty_change) as total
                        FROM inventory
                        WHERE product_id = ?
                    """, (product_id,))
                
                row = cursor.fetchone()
                return row['total'] or 0 if row else 0
                
        except Exception as e:
            logger.error(f"Error calculating movement for product {product_id}: {e}", exc_info=e)
            raise
    
    def delete(self, movement_id: int) -> bool:
        """Delete inventory movement (should be rare)."""
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()
                
                cursor.execute("DELETE FROM inventory WHERE id = ?", (movement_id,))
                
                logger.warning(f"Inventory movement {movement_id} deleted")
                return True
                
        except Exception as e:
            logger.error(f"Error deleting inventory movement {movement_id}: {e}", exc_info=e)
            raise
    
    def get_all(self, limit: int = 1000, offset: int = 0) -> List[Inventory]:
        """Get all movements with pagination."""
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM inventory
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))
                
                movements = []
                for row in cursor.fetchall():
                    movements.append(self._row_to_inventory(row))
                
                return movements
                
        except Exception as e:
            logger.error(f"Error getting all inventory movements: {e}", exc_info=e)
            raise
    
    @staticmethod
    def _row_to_inventory(row) -> Inventory:
        """Convert database row to Inventory object."""
        return Inventory(
            id=row['id'] if 'id' in row.keys() else None,
            product_id=row['product_id'] if 'product_id' in row.keys() else None,
            qty_change=row['qty_change'] if 'qty_change' in row.keys() else 0,
            operation=row['operation'] if 'operation' in row.keys() else 'sale',
            notes=row['notes'] if 'notes' in row.keys() else '',
            created_at=row['created_at'] if 'created_at' in row.keys() else datetime.now()
        )
