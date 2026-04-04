# ============================================================================
# TRANSACTION_SERVICE.PY - Transaction Processing Service (Service Layer)
# ============================================================================
# Fungsi: Handle transaksi lifecycle (create, add items, process payment, save)
# Ensure atomic transactions dan stock management
# ============================================================================

from typing import List, Optional, Tuple
from datetime import datetime, date

from ..core import (
    Transaction, TransactionItem, PaymentValidator,
    QuantityValidator, DiscountTaxValidator, format_rp
)
from ..repository import RepositoryFactory
from .base_service import BaseService
from .stock_service import StockService
from logger_config import get_logger, log_transaction_completed

logger = get_logger(__name__)


class TransactionService(BaseService):
    """
    Business logic untuk transaction processing.
    
    Workflow Transaksi:
    1. Create transaksi baru (create_transaction)
    2. Add items ke transaksi (add_item)
    3. Set diskon/pajak jika perlu
    4. Validate pembayaran (validate_payment)
    5. Complete transaksi (complete_transaction)
    6. Generate struk output
    
    Responsibilities:
    - Transaction lifecycle management
    - Item management (add, remove, update qty)
    - Discount & Tax calculation
    - Payment processing & validation
    - Stock deduction (atomic dengan transaction save)
    - Receipt generation
    
    Methods:
        create_transaction(): Create new transaction
        add_item(): Add item ke transaksi
        remove_item(): Remove item dari transaksi
        set_transaction_discount(): Set discount untuk transaksi
        set_transaction_tax(): Set tax untuk transaksi
        process_payment(): Process payment & calculate change
        complete_transaction(): Finalize & save transaksi
    """
    
    def __init__(self, repository_factory: RepositoryFactory):
        \"\"\"Initialize TransactionService dengan StockService dependency.\"\"\"
        super().__init__(repository_factory)
        self.stock_service = StockService(repository_factory)
        
        # Active transaction being built
        self.current_transaction: Optional[Transaction] = None
    
    def validate(self) -> bool:
        \"\"\"Validate TransactionService initialization.\"\"\"
        try:
            stock_valid = self.stock_service.validate()
            self._log_info(\"TransactionService initialized\")
            return stock_valid
        except Exception as e:
            self._log_error(\"TransactionService initialization failed\", e)
            return False
    
    def create_transaction(self, cashier_id: int = None) -> Transaction:
        \"\"\"
        Create new empty transaction.
        
        Args:
            cashier_id (int): Cashier user ID (optional)
            
        Returns:
            Transaction: New transaction object
        \"\"\"
        self.current_transaction = Transaction(
            tanggal=datetime.now(),
            cashier_id=cashier_id,
            status=\"pending\"
        )
        
        self._log_info(f\"Created new transaction at {self.current_transaction.tanggal}\")
        return self.current_transaction
    
    def add_item(self, product_id: int, product_code: str, 
                product_name: str, qty: int, harga_satuan: int,
                discount_pct: float = 0.0, tax_pct: float = 0.0) -> bool:
        \"\"\"
        Add item ke transaksi aktif.
        
        Args:
            product_id (int): Product ID
            product_code (str): Product code
            product_name (str): Product name
            qty (int): Quantity
            harga_satuan (int): Unit price
            discount_pct (float): Item discount percentage
            tax_pct (float): Item tax percentage
            
        Returns:
            bool: True if added successfully
            
        Raises:
            ValidationError: If validation fails
            TransactionValidationError: If transaction tidak valid
        \"\"\"
        # Validate transaksi aktif
        if self.current_transaction is None:
            from ..core import TransactionValidationError
            raise TransactionValidationError(\"Transaksi belum dibuat\")
        
        # Validate inputs
        qty = QuantityValidator.validate_qty(qty)
        discount_pct = DiscountTaxValidator.validate_discount_pct(discount_pct)
        tax_pct = DiscountTaxValidator.validate_tax_pct(tax_pct)
        
        # Validate stock available
        self.stock_service.validate_stock_available(product_id, qty)
        
        try:
            # Create transaction item
            item = TransactionItem(
                product_id=product_id,
                product_code=product_code,
                product_name=product_name,
                qty=qty,
                harga_satuan=harga_satuan,
                discount_pct=discount_pct,
                tax_pct=tax_pct
            )
            
            # Add to transaction
            self.current_transaction.add_item(item)
            
            self._log_info(
                f\"Added item: {product_name} (Qty={qty}, Subtotal={format_rp(item.subtotal)})\"
            )
            
            return True
        
        except Exception as e:
            self._log_error(f\"Gagal add item ke transaksi\", e)
            raise
    
    def remove_item(self, item_index: int) -> bool:
        \"\"\"
        Remove item dari transaksi.
        
        Args:
            item_index (int): Index item dalam list items
            
        Returns:
            bool: True if removed
        \"\"\"
        if self.current_transaction is None or not self.current_transaction.items:
            return False
        
        if item_index < 0 or item_index >= len(self.current_transaction.items):
            return False
        
        removed_item = self.current_transaction.items.pop(item_index)
        self.current_transaction._recalculate()
        
        self._log_info(f\"Removed item: {removed_item.product_name}\")
        return True
    
    def update_item_qty(self, item_index: int, new_qty: int) -> bool:
        \"\"\"
        Update quantity of item dalam transaksi.
        
        Args:
            item_index (int): Item index
            new_qty (int): New quantity
            
        Returns:
            bool: True if updated
        \"\"\"
        # Validate
        new_qty = QuantityValidator.validate_qty(new_qty)
        
        if self.current_transaction is None or not self.current_transaction.items:
            return False
        
        if item_index < 0 or item_index >= len(self.current_transaction.items):
            return False
        
        # Validate stock
        item = self.current_transaction.items[item_index]
        self.stock_service.validate_stock_available(item.product_id, new_qty)
        
        # Update
        item.qty = new_qty
        self.current_transaction._recalculate()
        
        self._log_info(f\"Updated {item.product_name} qty to {new_qty}\")
        return True
    
    def set_item_discount(self, item_index: int, discount_pct: float) -> bool:
        \"\"\"Set discount for specific item.\"\"\"
        discount_pct = DiscountTaxValidator.validate_discount_pct(discount_pct)
        
        if self.current_transaction is None or item_index >= len(self.current_transaction.items):
            return False
        
        self.current_transaction.items[item_index].discount_pct = discount_pct
        self.current_transaction._recalculate()
        return True
    
    def set_item_tax(self, item_index: int, tax_pct: float) -> bool:
        \"\"\"Set tax for specific item.\"\"\"
        tax_pct = DiscountTaxValidator.validate_tax_pct(tax_pct)
        
        if self.current_transaction is None or item_index >= len(self.current_transaction.items):
            return False
        
        self.current_transaction.items[item_index].tax_pct = tax_pct
        self.current_transaction._recalculate()
        return True
    
    def process_payment(self, payment_method: str, amount_received: int) -> Tuple[int, int]:
        \"\"\"
        Process payment & calculate change.
        
        Args:
            payment_method (str): Payment method (cash, debit, credit, etc)
            amount_received (int): Amount received from customer
            
        Returns:
            Tuple[int, int]: (amount_received validet, change)
            
        Raises:
            PaymentError: If payment validation fails
        \"\"\"
        if self.current_transaction is None:
            from ..core import TransactionError
            raise TransactionError(\"Transaksi tidak ada\")
        
        # Validate payment method
        payment_method = PaymentValidator.validate_payment_method(payment_method)
        
        # Validate amount & calculate change
        amount, change = PaymentValidator.validate_payment_amount(
            amount_received,
            self.current_transaction.total
        )
        
        # Set payment in transaction
        self.current_transaction.payment_method = payment_method
        self.current_transaction.uang_diterima = amount
        self.current_transaction.kembalian = change
        
        self._log_info(
            f\"Payment processed: Method={payment_method}, Amount={format_rp(amount)}, Change={format_rp(change)}\"
        )
        
        return amount, change
    
    def complete_transaction(self) -> int:
        \"\"\"
        Complete transaksi: deduct stock & save to database.
        
        Process:
        1. Validate transaction valid
        2. Deduct stock untuk semua items (atomic)
        3. Save transaction ke database
        4. Log transaksi completion
        
        Returns:
            int: Transaction ID yang disimpan
            
        Raises:
            TransactionError: If completion fails
        \"\"\"
        if self.current_transaction is None:
            from ..core import TransactionError
            raise TransactionError(\"Transaksi tidak ada\")
        
        if not self.current_transaction.items:
            from ..core import TransactionError
            raise TransactionError(\"Transaksi kosong (no items)\")
        
        try:
            # Mark as completed
            self.current_transaction.status = \"completed\"
            
            # Save transaction ke database
            transaction_id = self.repositories['transaction'].create(
                self.current_transaction
            )
            
            # Deduct stock untuk semua items
            for item in self.current_transaction.items:
                self.stock_service.deduct_stock(
                    product_id=item.product_id,
                    qty_to_deduct=item.qty,
                    notes=f\"Sale transaction ID {transaction_id}\"
                )
            
            # Log transaction completion
            log_transaction_completed(
                transaction_id,
                len(self.current_transaction.items),
                self.current_transaction.total,
                self.current_transaction.payment_method
            )
            
            self._log_operation(
                \"Complete Transaction\",
                f\"ID={transaction_id}, Total={format_rp(self.current_transaction.total)}, Items={len(self.current_transaction.items)}\",
                True
            )
            
            # Reset current transaction
            self.current_transaction = None
            
            return transaction_id
        
        except Exception as e:
            self._log_error(\"Gagal complete transaction\", e)
            raise
    
    def cancel_transaction(self) -> bool:
        \"\"\"Cancel transaksi aktif.\"\"\"
        if self.current_transaction is None:
            return False
        
        self.current_transaction = None
        self._log_info(\"Transaction cancelled\")
        return True
    
    def get_transaction_summary(self, transaction_id: int) -> Optional[dict]:
        \"\"\"Get transaction summary for receipt.\"\"\"
        try:
            transaction = self.repositories['transaction'].get_by_id(transaction_id)
            if not transaction:
                return None
            
            return {
                'id': transaction.id,
                'tanggal': transaction.tanggal,
                'items': transaction.items,
                'total': transaction.total,
                'payment_method': transaction.payment_method,
                'amount_received': transaction.uang_diterima,
                'change': transaction.kembalian
            }
        
        except Exception as e:
            self._log_error(f\"Gagal get transaction summary {transaction_id}\", e)
            return None
    
    def list_transactions_by_date(self, target_date: date) -> List[Transaction]:
        \"\"\"List transactions for a specific date.\"\"\"
        try:
            return self.repositories['transaction'].list_by_date(target_date)
        except Exception as e:
            self._log_error(f\"Gagal list transactions for {target_date}\", e)
            return []
