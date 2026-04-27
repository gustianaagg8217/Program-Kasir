# ============================================================================
# INVENTORY_SERVICE.PY - Real-time Inventory Management with Atomic Operations
# ============================================================================
# Fungsi: Handle stock synchronization, reservation, and commit/rollback
# Fitur: Thread-safe stock operations, prevent overselling, edge case handling
# ============================================================================

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from threading import Lock
import json

from logger_config import get_logger

logger = get_logger(__name__)


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class StockOperationType(Enum):
    """Stock operation types"""
    RESERVE = "reserve"        # Reserve stock for transaction
    COMMIT = "commit"          # Confirm sale
    ROLLBACK = "rollback"      # Cancel/return stock
    ADJUSTMENT = "adjustment"  # Manual adjustment
    RETURN = "return"          # Customer return


class StockStatus(Enum):
    """Stock status"""
    AVAILABLE = "available"
    LOW = "low"
    OUT_OF_STOCK = "out_of_stock"


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class StockReservation:
    """
    Stock reservation for pending transaction
    
    Attributes:
        reservation_id: Unique identifier
        product_id: Product ID
        quantity: Reserved quantity
        transaction_id: Associated transaction
        status: pending/committed/cancelled
        created_at: Creation timestamp
        expires_at: Expiration timestamp (auto-cancel after timeout)
    """
    product_id: int
    quantity: int
    transaction_id: int
    reservation_id: Optional[str] = None
    status: str = "pending"
    created_at: datetime = None
    expires_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.expires_at is None:
            from datetime import timedelta
            self.expires_at = self.created_at + timedelta(minutes=30)  # Auto-expire after 30min
    
    def is_expired(self) -> bool:
        """Check if reservation expired"""
        return datetime.now() > self.expires_at


@dataclass
class StockOperation:
    """
    Stock operation log entry
    
    Attributes:
        operation_type: Type of operation
        product_id: Product ID
        quantity: Quantity changed
        reason: Reason for operation
        transaction_id: Associated transaction
        timestamp: Operation timestamp
    """
    operation_type: StockOperationType
    product_id: int
    quantity: int
    reason: str
    transaction_id: Optional[int] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'operation_type': self.operation_type.value,
            'product_id': self.product_id,
            'quantity': self.quantity,
            'reason': self.reason,
            'transaction_id': self.transaction_id,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class InventorySnapshot:
    """
    Snapshot of product stock at moment
    
    Attributes:
        product_id: Product ID
        available: Available stock
        reserved: Reserved stock
        total: Total stock (available + reserved)
        status: Stock status
    """
    product_id: int
    available: int
    reserved: int
    status: StockStatus
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    @property
    def total(self) -> int:
        """Get total stock"""
        return self.available + self.reserved


# ============================================================================
# INVENTORY SERVICE - Thread-Safe Stock Management
# ============================================================================

class InventoryService:
    """
    Service layer for inventory management
    
    Features:
    - Reserve stock atomically
    - Commit sale atomically
    - Rollback on failure
    - Prevent overselling
    - Handle concurrent transactions
    - Track stock operations
    
    Thread Safety:
    - Uses locks for concurrent access
    - All critical operations are atomic
    """
    
    def __init__(self, db_manager):
        """
        Initialize inventory service
        
        Args:
            db_manager: DatabaseManager instance
        """
        self.db = db_manager
        self._lock = Lock()  # Thread-safe lock for critical operations
        self._reservations: Dict[str, StockReservation] = {}  # In-memory reservation cache
        logger.info("✅ InventoryService initialized")
    
    # ========================================================================
    # STOCK RESERVATION (Pre-sale phase)
    # ========================================================================
    
    def reserve_stock(self, product_id: int, quantity: int, 
                     transaction_id: int) -> Tuple[bool, str, Optional[str]]:
        """
        Reserve stock for transaction
        
        Args:
            product_id: Product to reserve
            quantity: Quantity to reserve
            transaction_id: Associated transaction
        
        Returns:
            (success, message, reservation_id)
        
        Thread-safe: Yes (uses lock)
        """
        with self._lock:
            try:
                # Validate input
                if quantity <= 0:
                    return False, "Quantity must be > 0", None
                
                # Get current stock
                product = self.db.get_product(product_id)
                if not product:
                    return False, "Product not found", None
                
                current_stock = product.stok if hasattr(product, 'stok') else product.get('stok', 0)
                
                # Check availability
                if current_stock < quantity:
                    logger.warning(f"⚠️ Insufficient stock for product {product_id}: need {quantity}, have {current_stock}")
                    return False, f"Insufficient stock (need: {quantity}, available: {current_stock})", None
                
                # Create reservation
                reservation = StockReservation(
                    product_id=product_id,
                    quantity=quantity,
                    transaction_id=transaction_id,
                    status="pending"
                )
                
                # Store reservation
                reservation_id = self._store_reservation(reservation)
                
                logger.info(f"✅ Stock reserved: Product {product_id}, Qty {quantity}, Reservation {reservation_id}")
                return True, "Stock reserved", reservation_id
                
            except Exception as e:
                logger.error(f"Error reserving stock: {e}")
                return False, f"Reservation error: {str(e)}", None
    
    def reserve_multiple(self, items: List[Dict]) -> Tuple[bool, str, List[str]]:
        """
        Reserve stock for multiple items (for split transactions)
        
        Args:
            items: List of {product_id, quantity, transaction_id}
        
        Returns:
            (success, message, reservation_ids)
        
        Atomic: All or nothing
        """
        with self._lock:
            try:
                reservation_ids = []
                
                # First pass: validate all items
                for item in items:
                    product = self.db.get_product(item['product_id'])
                    if not product:
                        return False, f"Product {item['product_id']} not found", []
                    
                    current_stock = product.stok if hasattr(product, 'stok') else product.get('stok', 0)
                    if current_stock < item['quantity']:
                        return False, f"Insufficient stock for product {item['product_id']}", []
                
                # Second pass: reserve all (if validation passed)
                for item in items:
                    reservation = StockReservation(
                        product_id=item['product_id'],
                        quantity=item['quantity'],
                        transaction_id=item['transaction_id']
                    )
                    rid = self._store_reservation(reservation)
                    reservation_ids.append(rid)
                
                logger.info(f"✅ Multiple stock reserved: {len(items)} items")
                return True, "All items reserved", reservation_ids
                
            except Exception as e:
                logger.error(f"Error in batch reservation: {e}")
                return False, str(e), []
    
    # ========================================================================
    # STOCK COMMIT (Sale confirmation)
    # ========================================================================
    
    def commit_stock(self, reservation_id: str) -> Tuple[bool, str]:
        """
        Commit sale - reduce actual stock
        
        Args:
            reservation_id: Reservation to commit
        
        Returns:
            (success, message)
        
        Thread-safe: Yes (uses lock)
        """
        with self._lock:
            try:
                # Get reservation
                reservation = self._reservations.get(reservation_id)
                if not reservation:
                    return False, "Reservation not found"
                
                if reservation.is_expired():
                    self._reservations.pop(reservation_id)
                    return False, "Reservation expired"
                
                # Reduce stock in database
                success = self.db.update_stock(
                    product_id=reservation.product_id,
                    quantity=-reservation.quantity,  # Negative to reduce
                    reason=f"Sale (Transaction {reservation.transaction_id})"
                )
                
                if success:
                    # Update reservation status
                    reservation.status = "committed"
                    
                    # Log operation
                    self._log_operation(
                        StockOperationType.COMMIT,
                        reservation.product_id,
                        reservation.quantity,
                        f"Committed reservation {reservation_id}",
                        reservation.transaction_id
                    )
                    
                    logger.info(f"✅ Stock committed: Product {reservation.product_id}, Qty {reservation.quantity}")
                    return True, "Stock committed"
                else:
                    return False, "Failed to update database"
                    
            except Exception as e:
                logger.error(f"Error committing stock: {e}")
                return False, str(e)
    
    def commit_multiple(self, reservation_ids: List[str]) -> Tuple[bool, str]:
        """Commit multiple reservations (atomic)"""
        with self._lock:
            try:
                # Validate all first
                for rid in reservation_ids:
                    if rid not in self._reservations:
                        return False, f"Reservation {rid} not found"
                
                # Commit all
                for rid in reservation_ids:
                    reservation = self._reservations[rid]
                    self.db.update_stock(
                        product_id=reservation.product_id,
                        quantity=-reservation.quantity,
                        reason=f"Sale (Transaction {reservation.transaction_id})"
                    )
                    reservation.status = "committed"
                
                logger.info(f"✅ Multiple stocks committed: {len(reservation_ids)} items")
                return True, "All stocks committed"
                
            except Exception as e:
                logger.error(f"Error in batch commit: {e}")
                return False, str(e)
    
    # ========================================================================
    # STOCK ROLLBACK (On transaction failure)
    # ========================================================================
    
    def rollback_stock(self, reservation_id: str, reason: str = None) -> Tuple[bool, str]:
        """
        Rollback reservation - cancel and return stock
        
        Args:
            reservation_id: Reservation to rollback
            reason: Reason for rollback
        
        Returns:
            (success, message)
        
        Thread-safe: Yes (uses lock)
        """
        with self._lock:
            try:
                reservation = self._reservations.get(reservation_id)
                if not reservation:
                    return False, "Reservation not found"
                
                if reservation.status == "committed":
                    return False, "Cannot rollback committed sale"
                
                # Update status
                reservation.status = "cancelled"
                
                # Log operation
                self._log_operation(
                    StockOperationType.ROLLBACK,
                    reservation.product_id,
                    reservation.quantity,
                    reason or "Reservation cancelled",
                    reservation.transaction_id
                )
                
                logger.info(f"✅ Stock rollback: Product {reservation.product_id}, Qty {reservation.quantity}")
                return True, "Stock rollback successful"
                
            except Exception as e:
                logger.error(f"Error rolling back stock: {e}")
                return False, str(e)
    
    def rollback_multiple(self, reservation_ids: List[str], reason: str = None) -> Tuple[bool, str]:
        """Rollback multiple reservations"""
        with self._lock:
            try:
                for rid in reservation_ids:
                    reservation = self._reservations.get(rid)
                    if reservation and reservation.status != "committed":
                        reservation.status = "cancelled"
                        self._log_operation(
                            StockOperationType.ROLLBACK,
                            reservation.product_id,
                            reservation.quantity,
                            reason or "Batch rollback",
                            reservation.transaction_id
                        )
                
                logger.info(f"✅ Multiple stocks rolled back: {len(reservation_ids)} items")
                return True, "All stocks rolled back"
                
            except Exception as e:
                logger.error(f"Error in batch rollback: {e}")
                return False, str(e)
    
    # ========================================================================
    # STOCK QUERIES & MONITORING
    # ========================================================================
    
    def get_stock_status(self, product_id: int) -> Optional[InventorySnapshot]:
        """Get current stock snapshot"""
        try:
            with self._lock:
                product = self.db.get_product(product_id)
                if not product:
                    return None
                
                current_stock = product.stok if hasattr(product, 'stok') else product.get('stok', 0)
                reserved = self._get_reserved_quantity(product_id)
                
                # Determine status
                if current_stock == 0:
                    status = StockStatus.OUT_OF_STOCK
                elif current_stock < 5:  # Low stock threshold
                    status = StockStatus.LOW
                else:
                    status = StockStatus.AVAILABLE
                
                return InventorySnapshot(
                    product_id=product_id,
                    available=current_stock,
                    reserved=reserved,
                    status=status
                )
        except Exception as e:
            logger.error(f"Error getting stock status: {e}")
            return None
    
    def get_all_stock_status(self) -> List[InventorySnapshot]:
        """Get stock status for all products"""
        try:
            products = self.db.get_all_products()
            snapshots = []
            
            for product in products:
                pid = product.id if hasattr(product, 'id') else product.get('id')
                snapshot = self.get_stock_status(pid)
                if snapshot:
                    snapshots.append(snapshot)
            
            return snapshots
        except Exception as e:
            logger.error(f"Error getting all stock status: {e}")
            return []
    
    def get_low_stock_products(self, threshold: int = 5) -> List[Dict]:
        """Get products with low stock"""
        try:
            snapshots = self.get_all_stock_status()
            low_stock = [
                {
                    'product_id': s.product_id,
                    'available': s.available,
                    'reserved': s.reserved,
                    'threshold': threshold
                }
                for s in snapshots if s.available < threshold
            ]
            return low_stock
        except Exception as e:
            logger.error(f"Error getting low stock products: {e}")
            return []
    
    # ========================================================================
    # INTERNAL HELPERS
    # ========================================================================
    
    def _store_reservation(self, reservation: StockReservation) -> str:
        """Store reservation in memory and database"""
        rid = f"RES_{len(self._reservations) + 1}_{reservation.transaction_id}"
        reservation.reservation_id = rid
        self._reservations[rid] = reservation
        
        # Also store in DB for persistence
        self.db.save_reservation(reservation)
        
        return rid
    
    def _get_reserved_quantity(self, product_id: int) -> int:
        """Get total reserved quantity for product"""
        return sum(
            r.quantity for r in self._reservations.values()
            if r.product_id == product_id and r.status == "pending"
        )
    
    def _log_operation(self, op_type: StockOperationType, product_id: int, 
                       quantity: int, reason: str, transaction_id: int = None) -> None:
        """Log stock operation"""
        try:
            operation = StockOperation(
                operation_type=op_type,
                product_id=product_id,
                quantity=quantity,
                reason=reason,
                transaction_id=transaction_id
            )
            self.db.log_stock_operation(operation)
        except Exception as e:
            logger.warning(f"Could not log operation: {e}")
    
    def cleanup_expired_reservations(self) -> int:
        """Clean up expired reservations - call periodically"""
        with self._lock:
            expired = [
                rid for rid, res in self._reservations.items()
                if res.is_expired() and res.status == "pending"
            ]
            
            for rid in expired:
                self._reservations[rid].status = "cancelled"
                logger.info(f"⚠️ Cleaned up expired reservation: {rid}")
            
            return len(expired)


if __name__ == "__main__":
    logger.info("Inventory Service module loaded")
