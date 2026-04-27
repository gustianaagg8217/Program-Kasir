# ============================================================================
# VALIDATORS.PY - Centralized Validation Logic (Core Layer)
# ============================================================================
# Fungsi: Define semua validation rules untuk domain entities
# Gunakan oleh Service Layer untuk validate input sebelum business logic
# ============================================================================

from typing import Tuple
from .exceptions import (
    ValidationError, ProductValidationError, 
    TransactionValidationError, PaymentError
)


class ProductValidator:
    """Validation rules untuk Product."""
    
    MIN_KODE_LENGTH = 2
    MAX_KODE_LENGTH = 20
    
    @staticmethod
    def validate_kode(kode: str) -> str:
        """
        Validate product code.
        
        Rules:
        - Non-empty
        - 2-20 chars
        - Alphanumeric + underscore/dash only
        
        Returns:
            str: Valid code (uppercase)
            
        Raises:
            ProductValidationError
        """
        if not isinstance(kode, str):
            raise ProductValidationError("Kode harus text", "kode")
        
        kode = kode.strip().upper()
        
        if not kode or len(kode) < ProductValidator.MIN_KODE_LENGTH:
            raise ProductValidationError(
                f"Kode minimal {ProductValidator.MIN_KODE_LENGTH} karakter",
                "kode"
            )
        
        if len(kode) > ProductValidator.MAX_KODE_LENGTH:
            raise ProductValidationError(
                f"Kode maksimal {ProductValidator.MAX_KODE_LENGTH} karakter",
                "kode"
            )
        
        # Allow only alphanumeric, dash, underscore
        if not all(c.isalnum() or c in '-_' for c in kode):
            raise ProductValidationError(
                "Kode hanya boleh alphanumeric, dash, dan underscore",
                "kode"
            )
        
        return kode
    
    @staticmethod
    def validate_nama(nama: str) -> str:
        """
        Validate product name.
        
        Rules:
        - Non-empty
        - Max 100 chars
        
        Returns:
            str: Valid name
            
        Raises:
            ProductValidationError
        """
        if not isinstance(nama, str):
            raise ProductValidationError("Nama harus text", "nama")
        
        nama = nama.strip()
        
        if not nama:
            raise ProductValidationError("Nama produk tidak boleh kosong", "nama")
        
        if len(nama) > 100:
            raise ProductValidationError(
                "Nama produk maksimal 100 karakter", "nama"
            )
        
        return nama
    
    @staticmethod
    def validate_harga(harga) -> int:
        """
        Validate product price.
        
        Rules:
        - Positive integer
        - Min 100 (0.01 USD)
        - Max 999,999,999 (for practical reasons)
        
        Returns:
            int: Valid price in IDR
            
        Raises:
            ProductValidationError
        """
        try:
            harga = int(harga)
        except (ValueError, TypeError):
            raise ProductValidationError(
                "Harga harus angka positif", "harga"
            )
        
        if harga <= 0:
            raise ProductValidationError(
                "Harga harus lebih dari 0", "harga"
            )
        
        if harga > 999_999_999:
            raise ProductValidationError(
                "Harga terlalu besar", "harga"
            )
        
        return harga
    
    @staticmethod
    def validate_stok(stok) -> int:
        """
        Validate stock quantity.
        
        Rules:
        - Non-negative integer
        - Max 999,999
        
        Returns:
            int: Valid stock quantity
            
        Raises:
            ProductValidationError
        """
        try:
            stok = int(stok)
        except (ValueError, TypeError):
            raise ProductValidationError(
                "Stok harus angka", "stok"
            )
        
        if stok < 0:
            raise ProductValidationError(
                "Stok tidak boleh negatif", "stok"
            )
        
        if stok > 999_999:
            raise ProductValidationError(
                "Stok terlalu besar", "stok"
            )
        
        return stok
    
    @staticmethod
    def validate_min_stok(min_stok) -> int:
        """Validate minimum stock level."""
        return ProductValidator.validate_stok(min_stok)


class QuantityValidator:
    """Validation rules untuk quantity dalam transaction."""
    
    MAX_QTY_PER_ITEM = 9999
    
    @staticmethod
    def validate_qty(qty) -> int:
        """
        Validate transaction item quantity.
        
        Rules:
        - Positive integer
        - Max 9999
        
        Returns:
            int: Valid quantity
            
        Raises:
            ValidationError
        """
        try:
            qty = int(qty)
        except (ValueError, TypeError):
            raise ValidationError(
                "Qty harus angka positif",
                "qty"
            )
        
        if qty <= 0:
            raise ValidationError(
                "Qty harus lebih dari 0",
                "qty"
            )
        
        if qty > QuantityValidator.MAX_QTY_PER_ITEM:
            raise ValidationError(
                f"Qty maksimal {QuantityValidator.MAX_QTY_PER_ITEM}",
                "qty"
            )
        
        return qty


class PaymentValidator:
    """Validation rules untuk payment."""
    
    VALID_METHODS = ["cash", "debit", "credit", "transfer", "check"]
    
    @staticmethod
    def validate_payment_method(method: str) -> str:
        """
        Validate payment method.
        
        Returns:
            str: Valid method
            
        Raises:
            PaymentError
        """
        method = method.strip().lower() if isinstance(method, str) else ""
        
        if method not in PaymentValidator.VALID_METHODS:
            raise PaymentError(
                f"Metode pembayaran tidak valid. Pilih dari: {', '.join(PaymentValidator.VALID_METHODS)}"
            )
        
        return method
    
    @staticmethod
    def validate_payment_amount(amount, total) -> Tuple[int, int]:
        """
        Validate payment amount and calculate change.
        
        Args:
            amount: Amount received from customer
            total: Total amount to pay
            
        Returns:
            Tuple[int, int]: (amount validating, change)
            
        Raises:
            PaymentError
        """
        try:
            amount = int(amount)
        except (ValueError, TypeError):
            raise PaymentError("Jumlah pembayaran harus angka")
        
        if amount <= 0:
            raise PaymentError("Jumlah pembayaran harus positif")
        
        if amount < total:
            raise PaymentError(
                f"Pembayaran kurang. Kurangnya: Rp {total - amount:,}"
            )
        
        change = amount - total
        return amount, change


class DiscountTaxValidator:
    """Validation rules untuk discount dan tax."""
    
    MAX_DISCOUNT_PCT = 100
    MAX_TAX_PCT = 100
    
    @staticmethod
    def validate_discount_pct(discount_pct) -> float:
        """
        Validate discount percentage.
        
        Rules:
        - 0 to 100
        
        Returns:
            float: Valid discount percentage
            
        Raises:
            ValidationError
        """
        try:
            discount_pct = float(discount_pct)
        except (ValueError, TypeError):
            raise ValidationError(
                "Diskon harus angka",
                "discount_pct"
            )
        
        if discount_pct < 0 or discount_pct > DiscountTaxValidator.MAX_DISCOUNT_PCT:
            raise ValidationError(
                f"Diskon antara 0-{DiscountTaxValidator.MAX_DISCOUNT_PCT}%",
                "discount_pct"
            )
        
        return discount_pct
    
    @staticmethod
    def validate_tax_pct(tax_pct) -> float:
        """Validate tax percentage."""
        try:
            tax_pct = float(tax_pct)
        except (ValueError, TypeError):
            raise ValidationError(
                "Pajak harus angka",
                "tax_pct"
            )
        
        if tax_pct < 0 or tax_pct > DiscountTaxValidator.MAX_TAX_PCT:
            raise ValidationError(
                f"Pajak antara 0-{DiscountTaxValidator.MAX_TAX_PCT}%",
                "tax_pct"
            )
        
        return tax_pct


class UserValidator:
    """Validation rules untuk User."""
    
    MIN_USERNAME_LENGTH = 3
    MIN_PASSWORD_LENGTH = 6
    MAX_USERNAME_LENGTH = 50
    
    VALID_ROLES = ["admin", "cashier"]
    
    @staticmethod
    def validate_username(username: str) -> str:
        """
        Validate username.
        
        Rules:
        - 3-50 alphanumeric + underscore
        - Unique (checked by repository)
        
        Returns:
            str: Valid username
            
        Raises:
            ValidationError
        """
        if not isinstance(username, str):
            raise ValidationError("Username harus text", "username")
        
        username = username.strip().lower()
        
        if len(username) < UserValidator.MIN_USERNAME_LENGTH:
            raise ValidationError(
                f"Username minimal {UserValidator.MIN_USERNAME_LENGTH} karakter",
                "username"
            )
        
        if len(username) > UserValidator.MAX_USERNAME_LENGTH:
            raise ValidationError(
                f"Username maksimal {UserValidator.MAX_USERNAME_LENGTH} karakter",
                "username"
            )
        
        if not all(c.isalnum() or c == '_' for c in username):
            raise ValidationError(
                "Username hanya boleh alphanumeric dan underscore",
                "username"
            )
        
        return username
    
    @staticmethod
    def validate_password(password: str) -> str:
        """
        Validate password.
        
        Rules:
        - Min 6 chars
        
        Returns:
            str: Valid password
            
        Raises:
            ValidationError
        """
        if not isinstance(password, str):
            raise ValidationError("Password harus text", "password")
        
        if len(password) < UserValidator.MIN_PASSWORD_LENGTH:
            raise ValidationError(
                f"Password minimal {UserValidator.MIN_PASSWORD_LENGTH} karakter",
                "password"
            )
        
        return password
    
    @staticmethod
    def validate_role(role: str) -> str:
        """
        Validate user role.
        
        Returns:
            str: Valid role
            
        Raises:
            ValidationError
        """
        role = role.strip().lower() if isinstance(role, str) else ""
        
        if role not in UserValidator.VALID_ROLES:
            raise ValidationError(
                f"Role tidak valid. Pilih dari: {', '.join(UserValidator.VALID_ROLES)}",
                "role"
            )
        
        return role


class PaymentValidator:
    """Validation rules untuk Payment (Multi-Payment Support)."""
    
    VALID_PAYMENT_METHODS = ["cash", "debit", "credit", "ovo", "gopay", "dana", "qris"]
    VALID_PAYMENT_STATUS = ["pending", "success", "failed"]
    MIN_PAYMENT_AMOUNT = 1000  # Rp 1000 minimum
    MAX_PAYMENT_AMOUNT = 999_999_999
    
    @staticmethod
    def validate_payment_method(method: str) -> str:
        """
        Validate payment method.
        
        Returns:
            str: Valid payment method
            
        Raises:
            PaymentError
        """
        if not isinstance(method, str):
            raise PaymentError("Metode pembayaran harus text")
        
        method = method.strip().lower()
        
        if method not in PaymentValidator.VALID_PAYMENT_METHODS:
            raise PaymentError(
                f"Metode pembayaran tidak valid. Pilih dari: {', '.join(PaymentValidator.VALID_PAYMENT_METHODS)}"
            )
        
        return method
    
    @staticmethod
    def validate_payment_amount(amount: int) -> int:
        """
        Validate payment amount.
        
        Rules:
        - Positive integer
        - Min 1000, Max 999,999,999
        
        Returns:
            int: Valid amount
            
        Raises:
            PaymentError
        """
        try:
            amount = int(amount)
        except (ValueError, TypeError):
            raise PaymentError("Jumlah pembayaran harus angka positif")
        
        if amount < PaymentValidator.MIN_PAYMENT_AMOUNT:
            raise PaymentError(
                f"Jumlah pembayaran minimal Rp {PaymentValidator.MIN_PAYMENT_AMOUNT:,}"
            )
        
        if amount > PaymentValidator.MAX_PAYMENT_AMOUNT:
            raise PaymentError("Jumlah pembayaran terlalu besar")
        
        return amount
    
    @staticmethod
    def validate_payment_status(status: str) -> str:
        """Validate payment status."""
        if not isinstance(status, str):
            raise PaymentError("Status pembayaran harus text")
        
        status = status.strip().lower()
        
        if status not in PaymentValidator.VALID_PAYMENT_STATUS:
            raise PaymentError(
                f"Status pembayaran tidak valid. Pilih dari: {', '.join(PaymentValidator.VALID_PAYMENT_STATUS)}"
            )
        
        return status
    
    @staticmethod
    def validate_split_payment(payments: list, total_amount: int) -> bool:
        """
        Validate split payment (multiple payment methods).
        
        Rules:
        - Total payment must equal transaction total (or slightly less due to rounding)
        - Each payment must be valid
        
        Args:
            payments: List of Payment objects
            total_amount: Total transaction amount
            
        Returns:
            bool: True if valid
            
        Raises:
            PaymentError
        """
        if not payments:
            raise PaymentError("Tidak ada metode pembayaran")
        
        total_paid = sum(p.amount for p in payments)
        
        # Allow small rounding difference (max 100 rupiah)
        if abs(total_paid - total_amount) > 100:
            raise PaymentError(
                f"Total pembayaran ({total_paid}) tidak sesuai dengan total transaksi ({total_amount})"
            )
        
        return True


class InventoryValidator:
    """Validation rules untuk Inventory/Stock operations."""
    
    @staticmethod
    def validate_stock_quantity(qty: int) -> int:
        """Validate stock quantity."""
        try:
            qty = int(qty)
        except (ValueError, TypeError):
            raise ValidationError("Jumlah stok harus angka", "qty")
        
        if qty < 0:
            raise ValidationError("Jumlah stok tidak boleh negatif", "qty")
        
        if qty > 999_999:
            raise ValidationError("Jumlah stok terlalu besar", "qty")
        
        return qty
    
    @staticmethod
    def validate_operation_type(operation: str) -> str:
        """Validate inventory operation type."""
        valid_operations = ["sale", "restock", "adjustment", "return"]
        
        if not isinstance(operation, str):
            raise ValidationError("Tipe operasi harus text", "operation")
        
        operation = operation.strip().lower()
        
        if operation not in valid_operations:
            raise ValidationError(
                f"Tipe operasi tidak valid. Pilih dari: {', '.join(valid_operations)}",
                "operation"
            )
        
        return operation

