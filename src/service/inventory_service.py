# ============================================================================
# INVENTORY_SERVICE.PY - Real-Time Stock Management Service (Service Layer)
# ============================================================================
# Fungsi: Handle inventory/stock dengan atomic transactions
# Support reserve, commit, rollback untuk concurrent transaction handling
# ============================================================================

from typing import List, Optional, Dict, Tuple
from datetime import datetime

from ..core import (
    Product, Inventory, InventorySnapshot,
    InsufficientStockError, InventoryValidator,
    ValidationError, ServiceError
)
from ..repository import RepositoryFactory
from .base_service import BaseService
from logger_config import get_logger

logger = get_logger(__name__)


class StockReservation:
    """Track reserved stock for a transaction."""
    
    def __init__(self, reservation_id: str):
        self.reservation_id = reservation_id
        self.reservations: Dict[int, int] = {}  # {product_id: qty_reserved}
        self.created_at = datetime.now()
        self.status = "active"  # active, committed, rolled_back
    
    def add_reservation(self, product_id: int, qty: int) -> None:
        """Add stock reservation."""
        if product_id not in self.reservations:
            self.reservations[product_id] = 0
        self.reservations[product_id] += qty
    
    def get_reserved_qty(self, product_id: int) -> int:
        """Get reserved quantity for product."""
        return self.reservations.get(product_id, 0)
    
    def __str__(self) -> str:
        return f"Reservation {self.reservation_id}: {len(self.reservations)} items, {self.status}"


class InventoryService(BaseService):
    """
    Service untuk inventory/stock management dengan atomic operations.
    
    Fitur:
    - Real-time stock updates
    - Atomic transaction support (reserve → commit/rollback)
    - Prevent overselling
    - Stock history tracking
    - Low stock alerts
    - Concurrent transaction handling
    
    Methods:
        get_stock(): Get current stock
        check_availability(): Check if stock available
        reserve_stock(): Reserve stock for transaction
        commit_stock(): Finalize stock reduction
        rollback_stock(): Revert stock reservation
        adjust_stock(): Manual stock adjustment
        get_stock_history(): Get stock movements
        get_low_stock_items(): Get products with low stock
    """
    
    def __init__(self, repository_factory: RepositoryFactory):
        """Initialize InventoryService."""
        super().__init__(repository_factory)
        self._active_reservations: Dict[str, StockReservation] = {}
    
    def validate(self) -> bool:
        """Validate InventoryService initialization."""
        try:
            # Check if product and inventory repositories exist
            if not self.repositories.get('product') or not self.repositories.get('inventory'):
                raise ServiceError("Product or Inventory repository not available")
            
            self._log_info("InventoryService initialized")
            return True
        except Exception as e:
            self._log_error("InventoryService initialization failed", e)
            return False
    
    def get_stock(self, product_id: int) -> int:
        """
        Get current stock quantity for product.
        
        Args:
            product_id (int): Product ID
            
        Returns:
            int: Stock quantity
            
        Raises:
            ServiceError: If product not found
        """
        try:
            product_repo = self.repositories.get('product')
            product = product_repo.get_by_id(product_id)
            
            if not product:
                raise ServiceError(f"Produk ID {product_id} tidak ditemukan")
            
            return product.stok
        except Exception as e:
            self._log_error(f"Error getting stock for product {product_id}", e)
            raise
    
    def check_availability(self, product_id: int, required_qty: int) -> bool:
        """
        Check if product has sufficient stock.
        
        Args:
            product_id (int): Product ID
            required_qty (int): Required quantity
            
        Returns:
            bool: True if stock available
            
        Raises:
            InsufficientStockError: If stock insufficient
        """
        product_repo = self.repositories.get('product')
        product = product_repo.get_by_id(product_id)
        
        if not product:
            raise ServiceError(f"Produk ID {product_id} tidak ditemukan")
        
        # Calculate available quantity (accounting for active reservations)
        reserved_qty = sum(
            res.get_reserved_qty(product_id)
            for res in self._active_reservations.values()
            if res.status == "active"
        )
        
        available_qty = product.stok - reserved_qty
        
        if available_qty < required_qty:
            raise InsufficientStockError(
                product.nama,
                required_qty,
                available_qty
            )
        
        return True
    
    def reserve_stock(self, reservation_id: str, items: List[Tuple[int, int]]) -> StockReservation:
        """
        Reserve stock for a transaction (not deducted yet).
        
        Used before completing transaction to lock stock for multiple concurrent transactions.
        
        Args:
            reservation_id (str): Unique reservation ID (usually transaction ID)
            items (List[Tuple]): List of (product_id, qty) tuples
            
        Returns:
            StockReservation: Reservation object
            
        Raises:
            InsufficientStockError: If stock insufficient
            ValidationError: If input invalid
        """
        # Validate each item
        for product_id, qty in items:
            if not isinstance(product_id, int) or product_id <= 0:
                raise ValidationError(f"Product ID harus positif", "product_id")
            
            qty = InventoryValidator.validate_stock_quantity(qty)
            
            # Check availability
            self.check_availability(product_id, qty)
        
        # Create reservation
        reservation = StockReservation(reservation_id)
        for product_id, qty in items:
            reservation.add_reservation(product_id, qty)
        
        # Store in active reservations
        self._active_reservations[reservation_id] = reservation
        
        self._log_info(f"Stock reserved: {reservation}")
        return reservation
    
    def commit_stock(self, reservation_id: str, operation_type: str = "sale") -> bool:
        """
        Commit reserved stock (permanently deduct from inventory).
        
        Args:
            reservation_id (str): Reservation ID to commit
            operation_type (str): Type of operation (sale, return, adjustment)
            
        Returns:
            bool: True if successful
            
        Raises:
            ServiceError: If reservation not found or operation fails
        """
        reservation = self._active_reservations.get(reservation_id)
        if not reservation:
            raise ServiceError(f"Reservation {reservation_id} tidak ditemukan")
        
        if reservation.status != "active":
            raise ServiceError(f"Reservation {reservation_id} sudah {reservation.status}")
        
        try:
            product_repo = self.repositories.get('product')
            inventory_repo = self.repositories.get('inventory')
            
            # Deduct from each product
            for product_id, qty_to_deduct in reservation.reservations.items():
                product = product_repo.get_by_id(product_id)
                
                # Double-check stock is still available
                if product.stok < qty_to_deduct:
                    raise InsufficientStockError(
                        product.nama,
                        qty_to_deduct,
                        product.stok
                    )
                
                # Update stock
                new_stock = product.stok - qty_to_deduct
                product_repo.update_stock(product_id, new_stock)
                
                # Record inventory movement
                inventory_movement = Inventory(
                    id=None,
                    product_id=product_id,
                    qty_change=-qty_to_deduct,
                    operation=operation_type,
                    notes=f"Reserved transaction {reservation_id}",
                    created_at=datetime.now()
                )
                inventory_repo.create(
                    product_id=product_id,
                    qty_change=-qty_to_deduct,
                    operation=operation_type,
                    notes=f"Reserved transaction {reservation_id}"
                )
                
                self._log_info(f"Stock committed: Product {product_id}, Qty -
{qty_to_deduct}")
            
            # Mark reservation as committed
            reservation.status = "committed"
            
            return True
            
        except Exception as e:
            self._log_error(f"Error committing stock reservation {reservation_id}", e)
            # Rollback on error
            self.rollback_stock(reservation_id)
            raise ServiceError(f"Gagal commit stok: {str(e)}")
    
    def rollback_stock(self, reservation_id: str) -> bool:
        """
        Rollback stock reservation (release lock, no deduction).
        
        Used when transaction is cancelled or fails.
        
        Args:
            reservation_id (str): Reservation ID to rollback
            
        Returns:
            bool: True if successful
            
        Raises:
            ServiceError: If reservation not found
        """
        reservation = self._active_reservations.get(reservation_id)
        if not reservation:
            raise ServiceError(f"Reservation {reservation_id} tidak ditemukan")
        
        reservation.status = "rolled_back"
        
        self._log_info(f"Stock reservation rolled back: {reservation}")
        return True
    
    def adjust_stock(self, product_id: int, qty_change: int, reason: str = "") -> int:
        """
        Manual stock adjustment (restock, loss, correction, etc).
        
        Args:
            product_id (int): Product ID
            qty_change (int): Quantity to add (positive) or remove (negative)
            reason (str): Reason for adjustment
            
        Returns:
            int: New stock quantity
            
        Raises:
            ValidationError: If inputs invalid
            ServiceError: If operation fails
        """
        qty_change = int(qty_change)
        
        try:
            product_repo = self.repositories.get('product')
            inventory_repo = self.repositories.get('inventory')
            
            product = product_repo.get_by_id(product_id)
            if not product:
                raise ServiceError(f"Produk ID {product_id} tidak ditemukan")
            
            new_stock = product.stok + qty_change
            
            if new_stock < 0:
                raise ValidationError(
                    f"Stok tidak bisa negatif. Stok saat ini: {product.stok}",
                    "stock"
                )
            
            # Update stock
            product_repo.update_stock(product_id, new_stock)
            
            # Record movement
            operation = "restock" if qty_change > 0 else "adjustment"
            inventory_repo.create(
                product_id=product_id,
                qty_change=qty_change,
                operation=operation,
                notes=reason or f"Manual adjustment"
            )
            
            self._log_info(f"Stock adjusted: Product {product_id}, Change {qty_change:+d}, New stock: {new_stock}")
            return new_stock
            
        except Exception as e:
            self._log_error(f"Error adjusting stock for product {product_id}", e)
            raise
    
    def get_stock_history(self, product_id: int, limit: int = 100) -> List[Inventory]:
        """
        Get stock movement history for product.
        
        Args:
            product_id (int): Product ID
            limit (int): Max records to return
            
        Returns:
            List[Inventory]: Stock movements
        """
        try:
            inventory_repo = self.repositories.get('inventory')
            return inventory_repo.get_by_product(product_id, limit)
        except Exception as e:
            self._log_error(f"Error getting stock history for product {product_id}", e)
            return []
    
    def get_low_stock_items(self, threshold_percent: float = 1.0) -> List[Product]:
        """
        Get products with stock below minimum level.
        
        Args:
            threshold_percent (float): Additional threshold as % of min_stok
            
        Returns:
            List[Product]: Low stock products
        """
        try:
            product_repo = self.repositories.get('product')
            products = product_repo.get_all()
            
            low_stock = []
            for product in products:
                threshold = product.min_stok * (1 + threshold_percent / 100)
                if product.stok <= threshold:
                    low_stock.append(product)
            
            self._log_info(f"Found {len(low_stock)} products with low stock")
            return low_stock
            
        except Exception as e:
            self._log_error("Error getting low stock items", e)
            return []
    
    def get_stock_snapshot(self, product_id: int) -> Dict:
        """
        Get current inventory snapshot.
        
        Args:
            product_id (int): Product ID
            
        Returns:
            dict: Current stock info
        """
        try:
            product_repo = self.repositories.get('product')
            product = product_repo.get_by_id(product_id)
            
            if not product:
                raise ServiceError(f"Produk ID {product_id} tidak ditemukan")
            
            # Calculate reserved stock
            reserved_qty = sum(
                res.get_reserved_qty(product_id)
                for res in self._active_reservations.values()
                if res.status == "active"
            )
            
            available_qty = product.stok - reserved_qty
            
            return {
                'product_id': product_id,
                'product_name': product.nama,
                'current_stock': product.stok,
                'reserved_stock': reserved_qty,
                'available_stock': available_qty,
                'min_stock': product.min_stok,
                'is_low_stock': product.is_low_stock(),
                'snapshot_time': datetime.now()
            }
        except Exception as e:
            self._log_error(f"Error getting stock snapshot for product {product_id}", e)
            raise
    
    def cancel_reservation(self, reservation_id: str) -> bool:
        """
        Cancel/remove a reservation.
        
        Args:
            reservation_id (str): Reservation ID to cancel
            
        Returns:
            bool: True if successful
        """
        if reservation_id in self._active_reservations:
            self._active_reservations[reservation_id].status = "cancelled"
            self._log_info(f"Reservation cancelled: {reservation_id}")
            return True
        
        return False
    
    def get_active_reservations(self) -> Dict[str, StockReservation]:
        """Get all active reservations."""
        return {
            rid: res for rid, res in self._active_reservations.items()
            if res.status == "active"
        }
    
    def cleanup_expired_reservations(self, timeout_minutes: int = 30) -> int:
        """
        Clean up expired reservations (not committed within timeout).
        
        Args:
            timeout_minutes (int): Reservation expiry time in minutes
            
        Returns:
            int: Number of reservations cleaned up
        """
        cleaned = 0
        now = datetime.now()
        timeout_delta = __import__('datetime').timedelta(minutes=timeout_minutes)
        
        expired_ids = [
            rid for rid, res in self._active_reservations.items()
            if res.status == "active" and (now - res.created_at) > timeout_delta
        ]
        
        for rid in expired_ids:
            self.rollback_stock(rid)
            cleaned += 1
        
        if cleaned > 0:
            self._log_info(f"Cleaned up {cleaned} expired reservations")
        
        return cleaned
