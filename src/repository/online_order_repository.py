# ============================================================================
# ONLINE_ORDER_REPOSITORY.PY - Online Order Data Access Layer
# ============================================================================
# Fungsi: Handle online order storage and retrieval
# ============================================================================

from typing import List, Optional, Dict
from datetime import datetime

from ..core import OnlineOrder
from .base_repository import BaseRepository
from logger_config import get_logger

logger = get_logger(__name__)


class OnlineOrderRepository(BaseRepository):
    """Repository untuk Online Order data access."""
    
    def create(self, **kwargs) -> Dict:
        """Create online order record."""
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO online_orders (
                        external_order_id, platform, customer_name,
                        customer_phone, customer_email, shipping_address,
                        items_count, total, status, order_date, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    kwargs.get('external_order_id'),
                    kwargs.get('platform'),
                    kwargs.get('customer_name', ''),
                    kwargs.get('customer_phone', ''),
                    kwargs.get('customer_email', ''),
                    kwargs.get('shipping_address', ''),
                    kwargs.get('items_count', 0),
                    kwargs.get('total', 0),
                    kwargs.get('status', 'pending'),
                    kwargs.get('order_date', datetime.now()),
                    kwargs.get('notes', '')
                ))
                
                order_id = cursor.lastrowid
                logger.info(f"Online order created: ID {order_id}")
                
                return self.get_by_id(order_id)
                
        except Exception as e:
            logger.error(f"Error creating online order: {e}", exc_info=e)
            raise
    
    def get_by_id(self, order_id: int) -> Optional[Dict]:
        """Get online order by ID."""
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM online_orders WHERE id = ?
                """, (order_id,))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting online order {order_id}: {e}", exc_info=e)
            raise
    
    def get_by_external_id(self, external_order_id: str) -> Optional[Dict]:
        """Get order by platform order ID."""
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM online_orders
                    WHERE external_order_id = ?
                """, (external_order_id,))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting order {external_order_id}: {e}", exc_info=e)
            raise
    
    def get_by_status(self, statuses: List[str]) -> List[Dict]:
        """Get orders by status."""
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()
                
                placeholders = ','.join('?' * len(statuses))
                cursor.execute(f"""
                    SELECT * FROM online_orders
                    WHERE status IN ({placeholders})
                    ORDER BY order_date DESC
                """, statuses)
                
                orders = []
                for row in cursor.fetchall():
                    orders.append(dict(row))
                
                return orders
                
        except Exception as e:
            logger.error(f"Error getting orders by status: {e}", exc_info=e)
            raise
    
    def get_by_platform(self, platform: str) -> List[Dict]:
        """Get orders from specific platform."""
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM online_orders
                    WHERE platform = ?
                    ORDER BY order_date DESC
                """, (platform,))
                
                orders = []
                for row in cursor.fetchall():
                    orders.append(dict(row))
                
                return orders
                
        except Exception as e:
            logger.error(f"Error getting orders from platform {platform}: {e}", exc_info=e)
            raise
    
    def get_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get orders within date range."""
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM online_orders
                    WHERE order_date BETWEEN ? AND ?
                    ORDER BY order_date DESC
                """, (start_date, end_date))
                
                orders = []
                for row in cursor.fetchall():
                    orders.append(dict(row))
                
                return orders
                
        except Exception as e:
            logger.error(f"Error getting orders for date range: {e}", exc_info=e)
            raise
    
    def update(self, order_id: int, **kwargs) -> bool:
        """Update order record."""
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()
                
                # Build update query
                updates = []
                params = []
                
                for key, value in kwargs.items():
                    if key in ['status', 'tracking_number', 'delivery_date', 'notes', 'transaction_id']:
                        updates.append(f"{key} = ?")
                        params.append(value)
                
                if not updates:
                    return False
                
                params.append(order_id)
                
                cursor.execute(f"""
                    UPDATE online_orders SET {', '.join(updates)}
                    WHERE id = ?
                """, params)
                
                logger.info(f"Online order {order_id} updated")
                return True
                
        except Exception as e:
            logger.error(f"Error updating order {order_id}: {e}", exc_info=e)
            raise
    
    def delete(self, order_id: int) -> bool:
        """Delete order (mark as cancelled instead recommended)."""
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()
                
                # Soft delete
                cursor.execute("""
                    UPDATE online_orders SET status = 'cancelled'
                    WHERE id = ?
                """, (order_id,))
                
                logger.warning(f"Online order {order_id} marked as cancelled")
                return True
                
        except Exception as e:
            logger.error(f"Error deleting order {order_id}: {e}", exc_info=e)
            raise
    
    def get_all(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get all orders with pagination."""
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM online_orders
                    ORDER BY order_date DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))
                
                orders = []
                for row in cursor.fetchall():
                    orders.append(dict(row))
                
                return orders
                
        except Exception as e:
            logger.error(f"Error getting all orders: {e}", exc_info=e)
            raise
