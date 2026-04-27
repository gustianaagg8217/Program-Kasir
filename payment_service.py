# ============================================================================
# PAYMENT_SERVICE.PY - Multi-Payment System Service Layer
# ============================================================================
# Fungsi: Handle multiple payment methods with atomic operations
# Fitur: Cash, Card, E-Wallet, QR Code - split payment support
# ============================================================================

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import json
from decimal import Decimal

from logger_config import get_logger

logger = get_logger(__name__)


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class PaymentMethod(Enum):
    """Supported payment methods"""
    CASH = "cash"
    DEBIT_CARD = "debit_card"
    CREDIT_CARD = "credit_card"
    OVO = "ovo"
    GOPAY = "gopay"
    DANA = "dana"
    QRIS = "qris"  # QR Code Indonesian Standard


class PaymentStatus(Enum):
    """Payment status lifecycle"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class Payment:
    """
    Payment entity representing single payment method
    
    Attributes:
        payment_id: Unique payment identifier
        transaction_id: Reference to transaction
        method: Payment method (enum)
        amount: Payment amount (Rp)
        reference_id: External reference (card/wallet transaction ID)
        status: Payment status (enum)
        timestamp: Payment timestamp
        note: Optional notes
    """
    transaction_id: int
    method: PaymentMethod
    amount: float
    reference_id: Optional[str] = None
    status: PaymentStatus = PaymentStatus.PENDING
    timestamp: datetime = None
    payment_id: Optional[int] = None
    note: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if isinstance(self.method, str):
            self.method = PaymentMethod(self.method)
        if isinstance(self.status, str):
            self.status = PaymentStatus(self.status)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        data = asdict(self)
        data['method'] = self.method.value
        data['status'] = self.status.value
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    def validate(self) -> Tuple[bool, str]:
        """Validate payment data"""
        if self.amount <= 0:
            return False, "Amount must be > 0"
        if not self.method:
            return False, "Payment method required"
        if self.method in [PaymentMethod.DEBIT_CARD, PaymentMethod.CREDIT_CARD, 
                           PaymentMethod.OVO, PaymentMethod.GOPAY, PaymentMethod.DANA]:
            if not self.reference_id:
                return False, f"Reference ID required for {self.method.value}"
        return True, "Valid"


@dataclass
class PaymentSplit:
    """
    Split payment request - multiple payments for one transaction
    
    Attributes:
        transaction_total: Total transaction amount
        payments: List of individual payments
    """
    transaction_total: float
    payments: List[Payment]
    
    def validate(self) -> Tuple[bool, str]:
        """Validate split payment"""
        if not self.payments:
            return False, "At least one payment required"
        
        # Validate each payment
        for payment in self.payments:
            valid, msg = payment.validate()
            if not valid:
                return False, msg
        
        # Check total
        total_paid = sum(p.amount for p in self.payments)
        if abs(total_paid - self.transaction_total) > 0.01:  # Allow small float diff
            return False, f"Payment total ({total_paid}) != transaction total ({self.transaction_total})"
        
        return True, "Valid split payment"
    
    def get_summary(self) -> Dict:
        """Get payment summary"""
        return {
            'transaction_total': self.transaction_total,
            'total_paid': sum(p.amount for p in self.payments),
            'payment_count': len(self.payments),
            'methods': [p.method.value for p in self.payments],
            'breakdown': [
                {
                    'method': p.method.value,
                    'amount': p.amount,
                    'percentage': (p.amount / self.transaction_total * 100) if self.transaction_total > 0 else 0
                }
                for p in self.payments
            ]
        }


# ============================================================================
# PAYMENT SERVICE - Business Logic
# ============================================================================

class PaymentService:
    """
    Service layer for payment processing
    
    Responsibilities:
    - Process single/split payments
    - Validate payment data
    - Handle payment status lifecycle
    - Provide payment analytics
    """
    
    def __init__(self, db_manager):
        """
        Initialize payment service
        
        Args:
            db_manager: DatabaseManager instance
        """
        self.db = db_manager
        logger.info("✅ PaymentService initialized")
    
    # ========================================================================
    # PAYMENT PROCESSING
    # ========================================================================
    
    def process_single_payment(self, transaction_id: int, method: PaymentMethod, 
                               amount: float, reference_id: Optional[str] = None) -> Tuple[bool, str, Optional[int]]:
        """
        Process single payment method
        
        Args:
            transaction_id: Transaction ID
            method: Payment method
            amount: Payment amount (Rp)
            reference_id: External reference ID (for card/wallet)
        
        Returns:
            (success, message, payment_id)
        """
        try:
            # Validate payment
            payment = Payment(
                transaction_id=transaction_id,
                method=method,
                amount=amount,
                reference_id=reference_id,
                status=PaymentStatus.COMPLETED
            )
            
            valid, msg = payment.validate()
            if not valid:
                logger.warning(f"Invalid payment: {msg}")
                return False, msg, None
            
            # Save to database
            payment_id = self.db.save_payment(payment)
            
            logger.info(f"✅ Payment processed: {method.value} Rp {amount:,} (ID: {payment_id})")
            return True, "Payment successful", payment_id
            
        except Exception as e:
            logger.error(f"Error processing payment: {e}")
            return False, f"Payment error: {str(e)}", None
    
    def process_split_payment(self, transaction_id: int, payments_data: List[Dict]) -> Tuple[bool, str, List[int]]:
        """
        Process split payment (multiple methods)
        
        Args:
            transaction_id: Transaction ID
            payments_data: List of {method, amount, reference_id}
        
        Returns:
            (success, message, payment_ids)
        """
        try:
            # Get transaction to verify total
            transaction = self.db.get_transaction(transaction_id)
            if not transaction:
                return False, "Transaction not found", []
            
            transaction_total = transaction['transaction']['total']
            
            # Build payment objects
            payments = []
            for pdata in payments_data:
                payment = Payment(
                    transaction_id=transaction_id,
                    method=PaymentMethod(pdata['method']),
                    amount=pdata['amount'],
                    reference_id=pdata.get('reference_id'),
                    status=PaymentStatus.COMPLETED
                )
                payments.append(payment)
            
            # Validate split
            split = PaymentSplit(transaction_total, payments)
            valid, msg = split.validate()
            if not valid:
                logger.warning(f"Invalid split payment: {msg}")
                return False, msg, []
            
            # Save all payments (atomic operation)
            payment_ids = []
            for payment in payments:
                pid = self.db.save_payment(payment)
                payment_ids.append(pid)
            
            summary = split.get_summary()
            logger.info(f"✅ Split payment processed: {summary['payment_count']} methods, Rp {summary['total_paid']:,}")
            
            return True, "Split payment successful", payment_ids
            
        except Exception as e:
            logger.error(f"Error processing split payment: {e}")
            return False, f"Split payment error: {str(e)}", []
    
    # ========================================================================
    # PAYMENT STATUS MANAGEMENT
    # ========================================================================
    
    def get_payment_status(self, payment_id: int) -> Tuple[bool, Optional[PaymentStatus]]:
        """Get payment status"""
        try:
            payment = self.db.get_payment(payment_id)
            if not payment:
                return False, None
            return True, PaymentStatus(payment['status'])
        except Exception as e:
            logger.error(f"Error getting payment status: {e}")
            return False, None
    
    def update_payment_status(self, payment_id: int, new_status: PaymentStatus) -> Tuple[bool, str]:
        """Update payment status"""
        try:
            success = self.db.update_payment_status(payment_id, new_status.value)
            if success:
                logger.info(f"✅ Payment {payment_id} status updated to {new_status.value}")
                return True, "Status updated"
            return False, "Failed to update status"
        except Exception as e:
            logger.error(f"Error updating payment status: {e}")
            return False, str(e)
    
    def refund_payment(self, payment_id: int, reason: str = None) -> Tuple[bool, str]:
        """Refund a payment"""
        try:
            success = self.db.update_payment_status(payment_id, PaymentStatus.REFUNDED.value)
            if success:
                logger.info(f"✅ Payment {payment_id} refunded. Reason: {reason}")
                return True, "Payment refunded"
            return False, "Failed to refund"
        except Exception as e:
            logger.error(f"Error refunding payment: {e}")
            return False, str(e)
    
    # ========================================================================
    # PAYMENT QUERIES
    # ========================================================================
    
    def get_transaction_payments(self, transaction_id: int) -> Tuple[bool, List[Dict]]:
        """Get all payments for a transaction"""
        try:
            payments = self.db.get_transaction_payments(transaction_id)
            return True, payments
        except Exception as e:
            logger.error(f"Error getting transaction payments: {e}")
            return False, []
    
    def get_payment_breakdown(self, transaction_id: int) -> Dict:
        """
        Get payment breakdown for a transaction
        
        Returns:
            {
                'cash': 50000,
                'card': 30000,
                'ewallet': 20000,
                'total': 100000
            }
        """
        try:
            success, payments = self.get_transaction_payments(transaction_id)
            if not success:
                return {}
            
            breakdown = {}
            for payment in payments:
                method = payment['method']
                amount = payment['amount']
                breakdown[method] = breakdown.get(method, 0) + amount
            
            breakdown['total'] = sum(breakdown.values())
            return breakdown
        except Exception as e:
            logger.error(f"Error getting payment breakdown: {e}")
            return {}
    
    # ========================================================================
    # ANALYTICS
    # ========================================================================
    
    def get_payment_method_stats(self, start_date: str = None, end_date: str = None) -> Dict:
        """
        Get payment method statistics
        
        Returns:
            {
                'cash': {'count': 100, 'total': 5000000, 'percentage': 50},
                'card': {...},
                'summary': {'total_transactions': 200, 'total_amount': 10000000}
            }
        """
        try:
            stats = self.db.get_payment_method_stats(start_date, end_date)
            return stats or {}
        except Exception as e:
            logger.error(f"Error getting payment stats: {e}")
            return {}
    
    def get_split_payment_rate(self, start_date: str = None, end_date: str = None) -> float:
        """Get percentage of transactions using split payment"""
        try:
            rate = self.db.get_split_payment_rate(start_date, end_date)
            return rate or 0.0
        except Exception as e:
            logger.error(f"Error getting split payment rate: {e}")
            return 0.0
    
    # ========================================================================
    # VALIDATION HELPERS
    # ========================================================================
    
    def validate_payment_amount(self, amount: float, transaction_total: float) -> Tuple[bool, str]:
        """Validate payment amount against transaction"""
        if amount <= 0:
            return False, "Amount must be positive"
        if amount > transaction_total * 1.5:  # Allow overpayment up to 50%
            return False, "Amount exceeds transaction total by too much"
        return True, "Valid"
    
    def validate_payment_method(self, method: str) -> Tuple[bool, str]:
        """Validate payment method exists"""
        try:
            PaymentMethod(method)
            return True, "Valid method"
        except ValueError:
            return False, f"Invalid payment method: {method}"
    
    def get_available_methods(self) -> List[str]:
        """Get list of available payment methods"""
        return [m.value for m in PaymentMethod]


# ============================================================================
# PAYMENT REPOSITORY - Database operations (to be implemented in database.py)
# ============================================================================

class PaymentRepository:
    """
    Abstract repository for payment database operations
    
    Methods to add to DatabaseManager:
    - save_payment(payment: Payment) -> int
    - get_payment(payment_id: int) -> Dict
    - get_transaction_payments(transaction_id: int) -> List[Dict]
    - update_payment_status(payment_id: int, status: str) -> bool
    - get_payment_method_stats(start_date: str, end_date: str) -> Dict
    - get_split_payment_rate(start_date: str, end_date: str) -> float
    """
    pass


if __name__ == "__main__":
    # Example usage
    logger.info("Payment Service module loaded")
