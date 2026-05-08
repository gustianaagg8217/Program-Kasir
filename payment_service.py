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
# TERMIN PAYMENT SERVICE - Handle pembayaran termin/cicilan
# ============================================================================

class TerminPaymentService:
    """
    Service untuk mengelola pembayaran termin/cicilan invoice.
    
    Responsibilities:
    - Create termin payment untuk invoice
    - Track pembayaran termin
    - Manage due dates dan payment reminders
    - Generate termin payment reports
    """
    
    def __init__(self, db_manager):
        """
        Initialize TerminPaymentService
        
        Args:
            db_manager: DatabaseManager instance
        """
        self.db = db_manager
        logger.info("✅ TerminPaymentService initialized")
    
    def create_termin_invoice(self, transaction_id: int, customer_name: str,
                             payment_schedule: List[Dict], customer_phone: str = None,
                             customer_email: str = None, customer_address: str = None) -> Tuple[bool, str, Optional[int]]:
        """
        Convert transaksi menjadi invoice termin dengan jadwal pembayaran.
        
        Args:
            transaction_id (int): ID transaction
            customer_name (str): Nama customer
            payment_schedule (List[Dict]): List of {amount, due_date}
                Contoh: [
                    {'amount': 500000, 'due_date': '2026-05-05'},
                    {'amount': 500000, 'due_date': '2026-06-05'}
                ]
            customer_phone (str, optional): Nomor telepon customer
            customer_email (str, optional): Email customer
            customer_address (str, optional): Alamat customer
        
        Returns:
            (success, message, invoice_id)
        """
        try:
            # Validate schedule
            if not payment_schedule:
                return False, "Jadwal pembayaran tidak boleh kosong", None
            
            # Ambil data transaksi
            trans_detail = self.db.get_transaction(transaction_id)
            if not trans_detail:
                return False, f"Transaksi {transaction_id} tidak ditemukan", None
            
            trans = trans_detail.get('transaction', {})
            total = trans.get('total', 0)
            payment_received = trans.get('bayar', 0)  # DP yang sudah dibayar
            
            # Validate schedule total
            schedule_total = sum(item.get('amount', 0) for item in payment_schedule)
            
            # Untuk termin, schedule_total seharusnya = total - payment_received (DP)
            # Tapi jika payment_received belum tersimpan, kita lakukan validasi lenient
            expected_schedule_total = total - payment_received
            
            # Validasi lenient: schedule_total harus positif dan <= total
            if schedule_total <= 0:
                return False, f"Total jadwal harus positif (diterima: {schedule_total})", None
            
            if schedule_total > total:
                return False, f"Total jadwal ({schedule_total}) tidak boleh lebih dari total transaksi ({total})", None
            
            # Log jika ada perbedaan antara expected dan actual schedule
            if schedule_total != total and schedule_total != expected_schedule_total:
                logger.warning(f"⚠️ Schedule validation: expected={expected_schedule_total}, actual={schedule_total}, total={total}, dp={payment_received}")
            
            # Update transaksi dengan termin info
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE transactions
                    SET payment_type = ?, payment_status = ?, customer_name = ?
                    WHERE id = ?
                """, ('termin', 'pending', customer_name, transaction_id))
                conn.commit()
            
            # Create invoice dari transaction
            from invoice.invoice_service import InvoiceService
            invoice_service = InvoiceService(self.db)
            invoice_id = invoice_service.create_invoice_from_transaction(transaction_id)
            
            if not invoice_id:
                return False, "Gagal membuat invoice", None
            
            # Update invoice dengan termin info
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE invoices
                    SET payment_type = ?, payment_status = ?, customer_name = ?,
                        customer_phone = ?, customer_email = ?, customer_address = ?
                    WHERE id = ?
                """, ('termin', 'pending', customer_name, customer_phone, customer_email, customer_address, invoice_id))
                conn.commit()
            
            # Create pembayaran termin untuk setiap jadwal
            for idx, schedule_item in enumerate(payment_schedule):
                amount = schedule_item.get('amount', 0)
                due_date = schedule_item.get('due_date', '')
                notes = schedule_item.get('notes', f'Cicilan ke-{idx+1}')
                
                self.db.add_termin_payment(
                    invoice_id=invoice_id,
                    payment_amount=amount,
                    payment_date=datetime.now().strftime('%Y-%m-%d'),
                    due_date=due_date,
                    transaction_id=transaction_id,
                    notes=notes
                )
            
            logger.info(f"Termin invoice created: invoice_id={invoice_id}, customer={customer_name}")
            return True, f"Invoice termin berhasil dibuat (ID: {invoice_id})", invoice_id
            
        except Exception as e:
            logger.error(f"Error creating termin invoice: {e}", exc_info=True)
            return False, f"Error: {str(e)}", None
    
    def record_termin_payment(self, invoice_id: int, payment_amount: int, 
                             notes: str = None) -> Tuple[bool, str]:
        """
        Catat pembayaran termin dari customer dengan fleksibilitas.
        
        Mendukung:
        - Pembayaran sesuai cicilan (Rp 49,333)
        - Pembayaran lebih dari cicilan (Rp 150,000)
        - Pelunasan langsung sisa hutang
        
        Args:
            invoice_id (int): ID invoice
            payment_amount (int): Jumlah pembayaran
            notes (str, optional): Catatan pembayaran
        
        Returns:
            (success, message)
        """
        try:
            # Ambil invoice
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
                row = cursor.fetchone()
                invoice = dict(row) if row else None
            
            if not invoice:
                return False, f"Invoice {invoice_id} tidak ditemukan"
            
            # Hitung total yang sudah dibayar sebelumnya (termasuk DP)
            dp_amount = invoice.get('bayar', 0)  # DP yang sudah dibayar
            completed_payments = self.db.calculate_total_paid_termin(invoice_id)  # Completed cicilan
            total_paid_before = dp_amount + completed_payments
            total_hutang = invoice['total']
            sisa_hutang = total_hutang - total_paid_before
            
            # Validasi pembayaran
            if payment_amount <= 0:
                return False, "Jumlah pembayaran harus lebih dari 0"
            
            if payment_amount > sisa_hutang:
                return False, f"Pembayaran melebihi sisa hutang. Sisa hutang: Rp {sisa_hutang:,.0f}"
            
            # Ambil termin payments pending
            termin_payments = self.db.get_termin_payments_by_invoice(invoice_id)
            pending_payments = [p for p in termin_payments if p['status'] == 'pending']
            
            if not pending_payments:
                return False, "Tidak ada pembayaran termin yang pending"
            
            # Process pembayaran secara iteratif untuk handle pembayaran > 1 cicilan
            remaining_payment = payment_amount
            cicilan_terbayar = 0
            
            for idx, pending in enumerate(pending_payments):
                if remaining_payment <= 0:
                    break
                
                cicilan_amount = pending['payment_amount']
                
                # Mark cicilan ini sebagai completed jika pembayaran >= cicilan amount
                if remaining_payment >= cicilan_amount:
                    # Bayar cicilan penuh
                    success = self.db.update_termin_payment_status(
                        pending['id'],
                        'completed',
                        notes or 'Pembayaran termin diterima'
                    )
                    
                    if not success:
                        return False, f"Gagal mencatat pembayaran cicilan ke-{idx+1}"
                    
                    remaining_payment -= cicilan_amount
                    cicilan_terbayar += 1
                else:
                    # Pembayaran cicilan parsial - jangan mark sebagai completed
                    # Update catatan saja untuk logging
                    logger.info(f"Partial payment for cicilan {idx+1}: {remaining_payment} dari {cicilan_amount}")
                    break
            
            # Check total pembayaran sekarang
            total_paid = total_paid_before + payment_amount
            
            if total_paid >= total_hutang:
                # Update invoice status jadi completed
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE invoices
                        SET payment_status = ?
                        WHERE id = ?
                    """, ('completed', invoice_id))
                    conn.commit()
                
                logger.info(f"Termin invoice fully paid: invoice_id={invoice_id}")
                msg = f"✅ Pembayaran termin tercatat. Cicilan SELESAI untuk invoice {invoice['invoice_number']}"
                if cicilan_terbayar > 0:
                    msg += f" ({cicilan_terbayar} cicilan terbayar)"
                return True, msg
            else:
                remaining = total_hutang - total_paid
                logger.info(f"Termin payment recorded: invoice_id={invoice_id}, remaining={remaining}")
                msg = f"✅ Pembayaran termin tercatat (Rp {payment_amount:,.0f})"
                if cicilan_terbayar > 0:
                    msg += f" - {cicilan_terbayar} cicilan terbayar"
                msg += f"\n📌 Sisa Hutang: Rp {remaining:,.0f}"
                return True, msg
        
        except Exception as e:
            logger.error(f"Error recording termin payment: {e}", exc_info=True)
            return False, f"Error: {str(e)}"
    
    def get_termin_summary(self, invoice_id: int) -> Dict:
        """
        Ambil summary pembayaran termin untuk invoice.
        
        Args:
            invoice_id (int): ID invoice
        
        Returns:
            Dict: Summary dengan total, paid, remaining, dll
        """
        try:
            # Ambil invoice
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
                row = cursor.fetchone()
                invoice = dict(row) if row else None
            
            if not invoice:
                return {}
            
            # Ambil termin payments
            termin_payments = self.db.get_termin_payments_by_invoice(invoice_id)
            
            # Calculate (including DP/bayar yang sudah dibayar)
            total = invoice['total']
            dp_amount = invoice.get('bayar', 0)  # DP yang sudah dibayar upfront
            completed_payments = self.db.calculate_total_paid_termin(invoice_id)  # Completed cicilan
            total_paid = dp_amount + completed_payments  # Total yang sudah dibayar (DP + cicilan)
            remaining = total - total_paid
            
            completed = sum(1 for p in termin_payments if p['status'] == 'completed')
            pending = sum(1 for p in termin_payments if p['status'] == 'pending')
            
            return {
                'invoice_id': invoice_id,
                'invoice_number': invoice['invoice_number'],
                'customer_name': invoice.get('customer_name', ''),
                'total': total,
                'total_paid': total_paid,
                'remaining': remaining,
                'percentage_paid': (total_paid / total * 100) if total > 0 else 0,
                'total_cicilan': len(termin_payments),
                'cicilan_completed': completed,
                'cicilan_pending': pending,
                'payments': termin_payments
            }
        except Exception as e:
            logger.error(f"Error getting termin summary: {e}")
            return {}


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
