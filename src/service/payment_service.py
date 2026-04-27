# ============================================================================
# PAYMENT_SERVICE.PY - Multi-Payment Processing Service (Service Layer)
# ============================================================================
# Fungsi: Handle multi-payment transactions dengan split payment support
# Validasi payment methods, track payment status, calculate fees
# ============================================================================

from typing import List, Optional, Dict
from datetime import datetime

from ..core import (
    Payment, PaymentMethod, PaymentValidator,
    PaymentError, ValidationError
)
from ..repository import RepositoryFactory
from .base_service import BaseService
from logger_config import get_logger

logger = get_logger(__name__)


class PaymentService(BaseService):
    """
    Service untuk multi-payment processing.
    
    Fitur:
    - Support multiple payment methods per transaction
    - Split payment validation (cash + e-wallet, etc)
    - Payment method configuration
    - Fee calculation
    - Payment status tracking
    
    Methods:
        create_payment(): Create payment record
        validate_split_payment(): Validate split payment combination
        calculate_payment_fee(): Calculate payment fee
        mark_payment_success(): Mark payment as successful
        mark_payment_failed(): Mark payment as failed
        get_payment_status(): Get payment status
    """
    
    def __init__(self, repository_factory: RepositoryFactory):
        """Initialize PaymentService."""
        super().__init__(repository_factory)
        self._init_payment_methods()
    
    def validate(self) -> bool:
        """Validate PaymentService initialization."""
        try:
            # Ensure payment methods are configured
            self._init_payment_methods()
            self._log_info("PaymentService initialized")
            return True
        except Exception as e:
            self._log_error("PaymentService initialization failed", e)
            return False
    
    def _init_payment_methods(self) -> None:
        """Initialize available payment methods."""
        self.payment_methods: Dict[str, PaymentMethod] = {
            "cash": PaymentMethod(
                code="cash",
                name="Tunai",
                enabled=True,
                requires_verification=False,
                fee_percent=0.0
            ),
            "debit": PaymentMethod(
                code="debit",
                name="Kartu Debit",
                enabled=True,
                requires_verification=True,
                fee_percent=1.5
            ),
            "credit": PaymentMethod(
                code="credit",
                name="Kartu Kredit",
                enabled=True,
                requires_verification=True,
                fee_percent=2.5
            ),
            "ovo": PaymentMethod(
                code="ovo",
                name="OVO",
                enabled=True,
                requires_verification=True,
                fee_percent=1.0
            ),
            "gopay": PaymentMethod(
                code="gopay",
                name="GoPay",
                enabled=True,
                requires_verification=True,
                fee_percent=1.0
            ),
            "dana": PaymentMethod(
                code="dana",
                name="DANA",
                enabled=True,
                requires_verification=True,
                fee_percent=1.0
            ),
            "qris": PaymentMethod(
                code="qris",
                name="QRIS",
                enabled=True,
                requires_verification=True,
                fee_percent=0.7,
                is_qr_code=True
            ),
        }
    
    def get_available_payment_methods(self) -> List[PaymentMethod]:
        """Get list of available payment methods."""
        return [m for m in self.payment_methods.values() if m.enabled]
    
    def is_payment_method_available(self, method_code: str) -> bool:
        """Check if payment method is available."""
        method = self.payment_methods.get(method_code)
        return method is not None and method.enabled
    
    def create_payment(self, method: str, amount: int, reference_id: str = "") -> Payment:
        """
        Create payment record.
        
        Args:
            method (str): Payment method code
            amount (int): Payment amount in IDR
            reference_id (str): Reference ID (e.g., transaction/card number)
            
        Returns:
            Payment: Payment object
            
        Raises:
            PaymentError: If validation fails
        """
        # Validate input
        method = PaymentValidator.validate_payment_method(method)
        amount = PaymentValidator.validate_payment_amount(amount)
        
        # Check if method is available
        if not self.is_payment_method_available(method):
            raise PaymentError(f"Metode pembayaran {method} tidak tersedia")
        
        # Create payment
        payment = Payment(
            method=method,
            amount=amount,
            reference_id=reference_id.strip(),
            status="pending",
            timestamp=datetime.now()
        )
        
        self._log_info(f"Created payment: {payment}")
        return payment
    
    def validate_split_payment(self, payments: List[Payment], total_amount: int) -> bool:
        """
        Validate split payment combination.
        
        Args:
            payments (List[Payment]): List of payment methods
            total_amount (int): Total transaction amount
            
        Returns:
            bool: True if valid
            
        Raises:
            PaymentError: If validation fails
        """
        # Validate each payment
        for payment in payments:
            if not payment.is_valid():
                raise PaymentError(f"Payment tidak valid: {payment}")
        
        # Validate total matches
        PaymentValidator.validate_split_payment(payments, total_amount)
        
        self._log_info(f"Split payment validated: {len(payments)} methods, total {total_amount}")
        return True
    
    def calculate_payment_fee(self, method: str, amount: int) -> int:
        """
        Calculate payment fee based on method.
        
        Args:
            method (str): Payment method code
            amount (int): Payment amount
            
        Returns:
            int: Fee amount in IDR
        """
        method = PaymentValidator.validate_payment_method(method)
        
        payment_method = self.payment_methods.get(method)
        if not payment_method:
            raise PaymentError(f"Metode pembayaran {method} tidak ditemukan")
        
        fee = int(amount * (payment_method.fee_percent / 100))
        self._log_info(f"Fee calculated for {method}: Rp {fee:,} ({payment_method.fee_percent}%)")
        
        return fee
    
    def get_net_amount(self, method: str, gross_amount: int) -> Dict[str, int]:
        """
        Calculate net amount after fees.
        
        Args:
            method (str): Payment method code
            gross_amount (int): Gross amount (before fees)
            
        Returns:
            dict: {
                'gross': gross amount,
                'fee': fee amount,
                'net': net amount after fee
            }
        """
        fee = self.calculate_payment_fee(method, gross_amount)
        
        return {
            'gross': gross_amount,
            'fee': fee,
            'net': gross_amount - fee
        }
    
    def mark_payment_success(self, payment: Payment, verified_by: str = "") -> Payment:
        """
        Mark payment as successful.
        
        Args:
            payment (Payment): Payment object
            verified_by (str): Who verified this payment
            
        Returns:
            Payment: Updated payment object
        """
        payment.status = "success"
        payment.timestamp = datetime.now()
        payment.verified_by = verified_by
        
        self._log_info(f"Payment marked successful: {payment}")
        return payment
    
    def mark_payment_failed(self, payment: Payment, reason: str = "") -> Payment:
        """
        Mark payment as failed.
        
        Args:
            payment (Payment): Payment object
            reason (str): Failure reason
            
        Returns:
            Payment: Updated payment object
        """
        payment.status = "failed"
        payment.timestamp = datetime.now()
        payment.verified_by = reason
        
        self._log_warning(f"Payment marked failed: {payment} (Reason: {reason})")
        return payment
    
    def get_payment_status(self, payment_id: int) -> str:
        """
        Get payment status from database.
        
        Args:
            payment_id (int): Payment ID
            
        Returns:
            str: Payment status
        """
        try:
            payment_repo = self.repositories.get('payment')
            if not payment_repo:
                raise PaymentError("Payment repository tidak tersedia")
            
            payment = payment_repo.get_by_id(payment_id)
            return payment.status if payment else None
        except Exception as e:
            self._log_error(f"Error getting payment status: {e}", e)
            raise PaymentError(f"Gagal mendapatkan status pembayaran: {str(e)}")
    
    def refund_payment(self, payment: Payment, reason: str = "") -> Payment:
        """
        Process refund for a payment.
        
        Args:
            payment (Payment): Payment object to refund
            reason (str): Refund reason
            
        Returns:
            Payment: Updated payment object with refund status
        """
        payment.status = "refunded"
        payment.verified_by = f"Refund: {reason}"
        payment.timestamp = datetime.now()
        
        self._log_info(f"Payment refunded: {payment}")
        return payment
    
    def validate_card_number(self, card_number: str) -> bool:
        """
        Validate credit/debit card using Luhn algorithm.
        
        Args:
            card_number (str): Card number (digits only)
            
        Returns:
            bool: True if valid
        """
        # Remove spaces/dashes
        card_number = card_number.replace(" ", "").replace("-", "")
        
        if not card_number.isdigit() or len(card_number) < 13 or len(card_number) > 19:
            raise PaymentError("Nomor kartu tidak valid")
        
        # Luhn algorithm
        total = 0
        for i, digit in enumerate(reversed(card_number)):
            d = int(digit)
            if i % 2 == 1:
                d *= 2
                if d > 9:
                    d -= 9
            total += d
        
        if total % 10 != 0:
            raise PaymentError("Nomor kartu gagal validasi Luhn")
        
        return True
    
    def mask_card_number(self, card_number: str) -> str:
        """
        Mask card number for security (show only last 4 digits).
        
        Args:
            card_number (str): Full card number
            
        Returns:
            str: Masked card number (e.g., "****-****-****-1234")
        """
        clean = card_number.replace(" ", "").replace("-", "")
        if len(clean) < 4:
            return "****"
        return f"****-****-****-{clean[-4:]}"
    
    def get_payment_summary(self, payments: List[Payment]) -> Dict:
        """
        Get summary of payments.
        
        Args:
            payments (List[Payment]): List of payments
            
        Returns:
            dict: Summary with totals by method
        """
        summary = {
            'total_payments': len(payments),
            'total_amount': 0,
            'by_method': {},
            'by_status': {}
        }
        
        for payment in payments:
            # By method
            if payment.method not in summary['by_method']:
                summary['by_method'][payment.method] = 0
            summary['by_method'][payment.method] += payment.amount
            
            # By status
            if payment.status not in summary['by_status']:
                summary['by_status'][payment.status] = 0
            summary['by_status'][payment.status] += 1
            
            # Total
            if payment.status == "success":
                summary['total_amount'] += payment.amount
        
        return summary
