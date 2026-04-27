# ============================================================================
# ONLINE_ORDER_SERVICE.PY - Online Order & E-Commerce Service (Service Layer)
# ============================================================================
# Fungsi: Handle online orders dari platform e-commerce
# Support order status tracking, payment processing, delivery management
# API-ready design untuk integrasi dengan Shopify, WooCommerce, etc
# ============================================================================

from typing import List, Optional, Dict
from datetime import datetime

from ..core import (
    OnlineOrder, Transaction, Payment, TransactionItem,
    ValidationError, ServiceError, NotFoundError
)
from ..repository import RepositoryFactory
from .base_service import BaseService
from .inventory_service import InventoryService
from .payment_service import PaymentService
from .transaction_service import TransactionService
from logger_config import get_logger

logger = get_logger(__name__)


class OnlineOrderService(BaseService):
    """
    Service untuk online order management.
    
    Fitur:
    - Order intake dari multiple platforms (Shopify, WooCommerce, Tokopedia, Shopee)
    - Order status tracking (pending, confirmed, packed, shipped, delivered, cancelled)
    - Integration dengan inventory service
    - Integration dengan payment service
    - Order fulfillment workflow
    - API endpoint support (JSON-ready)
    
    Methods:
        create_order(): Create online order from platform
        get_order(): Get order by ID
        update_order_status(): Update order status
        link_order_to_transaction(): Link online order to POS transaction
        get_pending_orders(): Get unfulfilled orders
        fulfill_order(): Mark order as ready for shipment
        cancel_order(): Cancel order
    """
    
    def __init__(self, repository_factory: RepositoryFactory):
        """Initialize OnlineOrderService with dependencies."""
        super().__init__(repository_factory)
        self.inventory_service = InventoryService(repository_factory)
        self.payment_service = PaymentService(repository_factory)
        self.transaction_service = TransactionService(repository_factory)
        self.order_repo = self.repositories.get('online_order')
    
    def validate(self) -> bool:
        """Validate OnlineOrderService initialization."""
        try:
            self._log_info("OnlineOrderService initialized")
            return True
        except Exception as e:
            self._log_error("OnlineOrderService initialization failed", e)
            return False
    
    def create_order(
        self,
        external_order_id: str,
        platform: str,
        customer_name: str,
        customer_phone: str,
        customer_email: str,
        items: List[Dict],
        shipping_address: str,
        total: int,
        notes: str = ""
    ) -> OnlineOrder:
        """
        Create online order from e-commerce platform.
        
        Args:
            external_order_id (str): Order ID from platform (e.g., Shopify order #123)
            platform (str): Platform name (shopify, woocommerce, tokopedia, shopee, etc)
            customer_name (str): Customer full name
            customer_phone (str): Customer phone number
            customer_email (str): Customer email
            items (List[Dict]): Order items [{product_id, product_name, qty, price}, ...]
            shipping_address (str): Full shipping address
            total (int): Order total in IDR
            notes (str): Additional notes
            
        Returns:
            OnlineOrder: Created order
            
        Raises:
            ValidationError: If input invalid
            ServiceError: If creation fails
        """
        try:
            # Validate inputs
            if not external_order_id or not platform:
                raise ValidationError("Order ID dan platform harus diisi", "order_input")
            
            if total <= 0:
                raise ValidationError("Total order harus lebih dari 0", "total")
            
            if not items:
                raise ValidationError("Order harus memiliki minimal 1 item", "items")
            
            # Convert items dict to TransactionItem objects
            transaction_items = []
            for item in items:
                trans_item = TransactionItem(
                    product_id=item.get('product_id', 0),
                    product_code=item.get('product_code', ''),
                    product_name=item.get('product_name', ''),
                    qty=item.get('qty', 1),
                    harga_satuan=item.get('price', 0)
                )
                transaction_items.append(trans_item)
            
            # Create order
            order = OnlineOrder(
                external_order_id=external_order_id,
                platform=platform,
                customer_name=customer_name,
                customer_phone=customer_phone,
                customer_email=customer_email,
                items=transaction_items,
                shipping_address=shipping_address,
                total=total,
                status="pending",
                order_date=datetime.now(),
                notes=notes
            )
            
            # Save to database if repository available
            if self.order_repo:
                try:
                    # Convert to dict for storage
                    order_data = self._order_to_dict(order)
                    order = self.order_repo.create(**order_data)
                except Exception as e:
                    self._log_warning(f"Could not save order to database: {e}")
            
            self._log_info(f"Online order created: {order.external_order_id} ({order.platform})")
            return order
            
        except Exception as e:
            self._log_error(f"Error creating online order: {e}", e)
            raise ServiceError(f"Gagal membuat order online: {str(e)}")
    
    def get_order(self, order_id: int = None, external_order_id: str = None) -> Optional[OnlineOrder]:
        """
        Get online order by ID.
        
        Args:
            order_id (int): Internal order ID
            external_order_id (str): Platform order ID
            
        Returns:
            OnlineOrder: Order object or None if not found
        """
        try:
            if not self.order_repo:
                raise ServiceError("Order repository not available")
            
            if order_id:
                return self.order_repo.get_by_id(order_id)
            elif external_order_id:
                return self.order_repo.get_by_external_id(external_order_id)
            
            raise ValidationError("Order ID atau external ID harus diisi", "order_id")
            
        except Exception as e:
            self._log_error(f"Error getting order: {e}", e)
            return None
    
    def update_order_status(self, order_id: int, new_status: str) -> OnlineOrder:
        """
        Update order status.
        
        Valid statuses: pending, confirmed, packed, shipped, delivered, cancelled
        
        Args:
            order_id (int): Order ID
            new_status (str): New status
            
        Returns:
            OnlineOrder: Updated order
            
        Raises:
            ValidationError: If status invalid
            ServiceError: If update fails
        """
        VALID_STATUSES = ["pending", "confirmed", "packed", "shipped", "delivered", "cancelled"]
        
        if new_status not in VALID_STATUSES:
            raise ValidationError(
                f"Status tidak valid. Pilih dari: {', '.join(VALID_STATUSES)}",
                "status"
            )
        
        try:
            order = self.get_order(order_id)
            if not order:
                raise NotFoundError("Order", str(order_id))
            
            old_status = order.status
            order.status = new_status
            
            if self.order_repo:
                self.order_repo.update(order_id, {'status': new_status})
            
            self._log_info(f"Order {order_id} status changed: {old_status} → {new_status}")
            return order
            
        except Exception as e:
            self._log_error(f"Error updating order status: {e}", e)
            raise
    
    def link_order_to_transaction(
        self,
        order_id: int,
        transaction_id: int,
        payment_method: str = "transfer"
    ) -> Dict:
        """
        Link online order to POS transaction.
        
        Args:
            order_id (int): Online order ID
            transaction_id (int): POS transaction ID
            payment_method (str): How was it paid (transfer, cod, etc)
            
        Returns:
            dict: Link result
        """
        try:
            order = self.get_order(order_id)
            if not order:
                raise NotFoundError("Order", str(order_id))
            
            # Update order status to confirmed
            order.status = "confirmed"
            
            if self.order_repo:
                self.order_repo.update(
                    order_id,
                    {
                        'status': 'confirmed',
                        'transaction_id': transaction_id
                    }
                )
            
            self._log_info(f"Order {order_id} linked to transaction {transaction_id}")
            
            return {
                'success': True,
                'order_id': order_id,
                'transaction_id': transaction_id,
                'status': 'confirmed'
            }
            
        except Exception as e:
            self._log_error(f"Error linking order to transaction: {e}", e)
            raise ServiceError(f"Gagal link order ke transaksi: {str(e)}")
    
    def get_pending_orders(self, platform: str = None) -> List[OnlineOrder]:
        """
        Get all unfulfilled orders.
        
        Args:
            platform (str): Filter by platform (optional)
            
        Returns:
            List[OnlineOrder]: Pending orders
        """
        try:
            if not self.order_repo:
                return []
            
            pending_statuses = ["pending", "confirmed"]
            orders = self.order_repo.get_by_status(pending_statuses)
            
            if platform:
                orders = [o for o in orders if o.platform == platform]
            
            return orders
        except Exception as e:
            self._log_error("Error getting pending orders", e)
            return []
    
    def fulfill_order(
        self,
        order_id: int,
        tracking_number: str = ""
    ) -> Dict:
        """
        Mark order as ready for shipment (packed/shipped).
        
        Args:
            order_id (int): Order ID
            tracking_number (str): Tracking number for shipment
            
        Returns:
            dict: Fulfillment result
        """
        try:
            order = self.get_order(order_id)
            if not order:
                raise NotFoundError("Order", str(order_id))
            
            # Update status and tracking
            order.status = "shipped"
            order.tracking_number = tracking_number
            order.delivery_date = None  # Will be updated when delivered
            
            if self.order_repo:
                self.order_repo.update(
                    order_id,
                    {
                        'status': 'shipped',
                        'tracking_number': tracking_number
                    }
                )
            
            self._log_info(f"Order {order_id} fulfilled: {tracking_number}")
            
            return {
                'success': True,
                'order_id': order_id,
                'status': 'shipped',
                'tracking_number': tracking_number
            }
            
        except Exception as e:
            self._log_error(f"Error fulfilling order: {e}", e)
            raise ServiceError(f"Gagal fulfill order: {str(e)}")
    
    def mark_delivered(self, order_id: int) -> Dict:
        """
        Mark order as delivered.
        
        Args:
            order_id (int): Order ID
            
        Returns:
            dict: Delivery result
        """
        try:
            order = self.get_order(order_id)
            if not order:
                raise NotFoundError("Order", str(order_id))
            
            order.status = "delivered"
            order.delivery_date = datetime.now()
            
            if self.order_repo:
                self.order_repo.update(
                    order_id,
                    {
                        'status': 'delivered',
                        'delivery_date': datetime.now().isoformat()
                    }
                )
            
            self._log_info(f"Order {order_id} marked delivered")
            
            return {
                'success': True,
                'order_id': order_id,
                'status': 'delivered',
                'delivery_date': order.delivery_date
            }
            
        except Exception as e:
            self._log_error(f"Error marking order delivered: {e}", e)
            raise ServiceError(f"Gagal tandai order delivered: {str(e)}")
    
    def cancel_order(self, order_id: int, reason: str = "") -> Dict:
        """
        Cancel online order.
        
        Args:
            order_id (int): Order ID
            reason (str): Cancellation reason
            
        Returns:
            dict: Cancellation result
        """
        try:
            order = self.get_order(order_id)
            if not order:
                raise NotFoundError("Order", str(order_id))
            
            order.status = "cancelled"
            order.notes = f"Cancelled: {reason}" if reason else "Cancelled"
            
            if self.order_repo:
                self.order_repo.update(
                    order_id,
                    {
                        'status': 'cancelled',
                        'notes': order.notes
                    }
                )
            
            self._log_info(f"Order {order_id} cancelled: {reason}")
            
            return {
                'success': True,
                'order_id': order_id,
                'status': 'cancelled',
                'reason': reason
            }
            
        except Exception as e:
            self._log_error(f"Error cancelling order: {e}", e)
            raise ServiceError(f"Gagal cancel order: {str(e)}")
    
    def get_order_summary(self, order_id: int) -> Dict:
        """
        Get complete order summary (API-ready).
        
        Args:
            order_id (int): Order ID
            
        Returns:
            dict: Order summary
        """
        try:
            order = self.get_order(order_id)
            if not order:
                raise NotFoundError("Order", str(order_id))
            
            return self._order_to_dict(order)
            
        except Exception as e:
            self._log_error(f"Error getting order summary: {e}", e)
            raise
    
    def _order_to_dict(self, order: OnlineOrder) -> Dict:
        """Convert OnlineOrder to dict (for API response or database storage)."""
        return {
            'external_order_id': order.external_order_id,
            'platform': order.platform,
            'customer_name': order.customer_name,
            'customer_phone': order.customer_phone,
            'customer_email': order.customer_email,
            'shipping_address': order.shipping_address,
            'items_count': len(order.items),
            'total': order.total,
            'status': order.status,
            'order_date': order.order_date.isoformat() if order.order_date else None,
            'delivery_date': order.delivery_date.isoformat() if order.delivery_date else None,
            'tracking_number': order.tracking_number,
            'notes': order.notes
        }
    
    def generate_platform_report(self, platform: str = None, days: int = 30) -> Dict:
        """
        Generate report for specific e-commerce platform.
        
        Args:
            platform (str): Platform name
            days (int): Report for last N days
            
        Returns:
            dict: Platform report
        """
        try:
            from datetime import timedelta
            
            if not self.order_repo:
                return {}
            
            start_date = datetime.now() - timedelta(days=days)
            orders = self.order_repo.get_by_date_range(start_date, datetime.now())
            
            if platform:
                orders = [o for o in orders if o.platform == platform]
            
            # Generate report
            report = {
                'platform': platform or 'all',
                'period_days': days,
                'total_orders': len(orders),
                'total_revenue': sum(o.total for o in orders),
                'by_status': {},
                'avg_order_value': 0
            }
            
            for order in orders:
                status = order.status
                if status not in report['by_status']:
                    report['by_status'][status] = 0
                report['by_status'][status] += 1
            
            if orders:
                report['avg_order_value'] = report['total_revenue'] // len(orders)
            
            return report
            
        except Exception as e:
            self._log_error("Error generating platform report", e)
            return {}
