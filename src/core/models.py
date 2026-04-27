# ============================================================================
# MODELS.PY - Domain Models (Core Layer)
# ============================================================================
# Fungsi: Define domain entities sebagai dataclass/simple class
# HANYA structure data, TIDAK contain business logic
# Logic dihandle oleh Service Layer
# ============================================================================

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


# ============================================================================
# PRODUCT / INVENTORY MODELS
# ============================================================================

@dataclass
class Product:
    """
    Domain model untuk Product.
    
    Attributes:
        id (int): Product ID (primary key)
        kode (str): Product code (unique)
        nama (str): Product name
        harga (int): Price in IDR
        stok (int): Current stock quantity
        min_stok (int): Minimum stock level for alerts
        kategori (str): Product category
        created_at (datetime): Creation timestamp
        updated_at (datetime): Last update timestamp
    """
    id: int
    kode: str
    nama: str
    harga: int
    stok: int
    min_stok: int = 0
    kategori: str = "General"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def __str__(self) -> str:
        return f"{self.kode} - {self.nama} (Rp{self.harga:,}, Stok: {self.stok})"
    
    def is_low_stock(self) -> bool:
        """Check if stock is below minimum."""
        return self.stok <= self.min_stok


@dataclass
class Inventory:
    """Tracks stock history & movements."""
    id: int
    product_id: int
    qty_change: int  # Positive for in, negative for out
    operation: str  # 'sale', 'restock', 'adjustment'
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)


# ============================================================================
# PAYMENT MODELS - Enterprise Multi-Payment Support
# ============================================================================

@dataclass
class Payment:
    """
    Represents a single payment method in a transaction.
    
    Supports: Cash, Debit/Credit Card, E-Wallet (OVO, GoPay, DANA), QR Code (QRIS)
    
    Attributes:
        id (int): Payment ID
        transaction_id (int): Parent transaction ID
        method (str): Payment method (cash, debit, credit, ovo, gopay, dana, qris)
        amount (int): Payment amount in IDR
        reference_id (str): Reference ID for tracking (card number masked, transaction ID, etc)
        status (str): Payment status (pending, success, failed)
        timestamp (datetime): Payment timestamp
        verified_by (str): Who verified this payment (for card/QR)
    """
    id: int = None
    transaction_id: int = None
    method: str = "cash"
    amount: int = 0
    reference_id: str = ""
    status: str = "pending"
    timestamp: datetime = field(default_factory=datetime.now)
    verified_by: str = ""
    
    def is_valid(self) -> bool:
        """Check if payment data is valid."""
        return (
            self.method in {"cash", "debit", "credit", "ovo", "gopay", "dana", "qris"} and
            self.amount > 0 and
            self.status in {"pending", "success", "failed"}
        )
    
    def __str__(self) -> str:
        return f"{self.method.upper()}: Rp {self.amount:,} ({self.status})"


@dataclass
class PaymentMethod:
    """Configuration for available payment methods."""
    code: str  # cash, debit, credit, ovo, gopay, dana, qris
    name: str
    enabled: bool = True
    requires_verification: bool = False
    fee_percent: float = 0.0
    is_qr_code: bool = False
    
    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


# ============================================================================
# TRANSACTION / SALES MODELS
# ============================================================================

@dataclass
class TransactionItem:
    """
    Single item dalam transaction.
    
    Attributes:
        product_id (int): Product ID
        product_code (str): Product code
        product_name (str): Product name
        qty (int): Quantity
        harga_satuan (int): Unit price
        discount_pct (float): Discount percentage (0-100)
        tax_pct (float): Tax percentage
    """
    product_id: int
    product_code: str
    product_name: str
    qty: int
    harga_satuan: int
    discount_pct: float = 0.0
    tax_pct: float = 0.0
    
    @property
    def subtotal(self) -> int:
        """Calculate subtotal before discount."""
        return self.qty * self.harga_satuan
    
    @property
    def discount_amount(self) -> int:
        """Calculate discount amount."""
        return int(self.subtotal * (self.discount_pct / 100))
    
    @property
    def after_discount(self) -> int:
        """Amount after discount."""
        return self.subtotal - self.discount_amount
    
    @property
    def tax_amount(self) -> int:
        """Calculate tax amount."""
        return int(self.after_discount * (self.tax_pct / 100))
    
    @property
    def total(self) -> int:
        """Total including tax."""
        return self.after_discount + self.tax_amount


@dataclass
class Transaction:
    """
    Domain model untuk Transaction / Sale - Enhanced with Multi-Payment & Online Support.
    
    Attributes:
        id (int): Transaction ID
        tanggal (datetime): Transaction date/time
        items (List[TransactionItem]): Items dalam transaksi
        
        # Multi-Payment Support
        payments (List[Payment]): List of payment methods used
        
        # Totals
        total_sebelum_pajak (int): Total before tax
        total_pajak (int): Total tax
        total (int): Final total (before payments)
        
        # Legacy single payment (for backward compatibility)
        payment_method (str): Primary payment method (cash, debit, credit, etc)
        uang_diterima (int): Amount received
        kembalian (int): Change
        
        # Transaction Details
        catatan (str): Notes
        cashier_id (int): Cashier ID
        
        # Online / Channel Support
        channel (str): "offline" (POS) or "online" (e-commerce)
        order_id (str): External order ID if online
        customer_name (str): Customer name (for online orders)
        customer_phone (str): Customer phone (for delivery)
        customer_email (str): Customer email
        shipping_address (str): Delivery address (for online)
        
        # Status Management
        status (str): Transaction status (pending, paid, completed, failed, cancelled)
        
        # Metadata
        created_at (datetime): When transaction was created
        completed_at (datetime): When transaction was completed
        reference_number (str): Receipt/reference number
    """
    id: int = None
    tanggal: datetime = field(default_factory=datetime.now)
    items: List[TransactionItem] = field(default_factory=list)
    
    # Multi-Payment
    payments: List[Payment] = field(default_factory=list)
    
    # Totals
    total_sebelum_pajak: int = 0
    total_pajak: int = 0
    total: int = 0
    
    # Legacy single payment (for backward compatibility)
    payment_method: str = "cash"
    uang_diterima: int = 0
    kembalian: int = 0
    
    # Transaction details
    catatan: str = ""
    cashier_id: int = None
    
    # Online/Channel
    channel: str = "offline"  # offline, online
    order_id: str = ""
    customer_name: str = ""
    customer_phone: str = ""
    customer_email: str = ""
    shipping_address: str = ""
    
    # Status
    status: str = "pending"  # pending, paid, completed, failed, cancelled
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime = field(default=None)
    reference_number: str = ""
    
    def add_item(self, item: TransactionItem) -> None:
        """Add item to transaction."""
        self.items.append(item)
        self._recalculate()
    
    def add_payment(self, payment: Payment) -> None:
        """Add payment method to transaction."""
        self.payments.append(payment)
    
    def get_total_paid(self) -> int:
        """Get total amount paid across all payment methods."""
        return sum(p.amount for p in self.payments if p.status == "success")
    
    def get_remaining_payment(self) -> int:
        """Get remaining amount that still needs payment."""
        return max(0, self.total - self.get_total_paid())
    
    def is_fully_paid(self) -> bool:
        """Check if transaction is fully paid."""
        return self.get_total_paid() >= self.total
    
    def is_online_order(self) -> bool:
        """Check if this is an online order."""
        return self.channel == "online"
    
    def _recalculate(self) -> None:
        """Recalculate totals."""
        self.total_sebelum_pajak = sum(item.after_discount for item in self.items)
        self.total_pajak = sum(item.tax_amount for item in self.items)
        self.total = self.total_sebelum_pajak + self.total_pajak


@dataclass
class RefundItem:
    """Items yang akan di-refund."""
    product_id: int
    product_name: str
    transaction_id: int
    qty: int
    reason: str


# ============================================================================
# USER / AUTHENTICATION MODELS
# ============================================================================

@dataclass
class User:
    """
    User in system.
    
    Attributes:
        id (int): User ID
        username (str): Username
        password_hash (str): Hashed password
        role (str): UserRole (admin, cashier)
        nama_lengkap (str): Full name
        is_active (bool): Active status
        created_at (datetime): Creation timestamp
    """
    id: int
    username: str
    password_hash: str
    role: str  # admin, cashier
    nama_lengkap: str = ""
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    
    def __str__(self) -> str:
        return f"{self.username} ({self.role})"


@dataclass
class UserSession:
    """Represents current logged-in user session."""
    user_id: int
    username: str
    role: str
    nama_lengkap: str
    login_time: datetime = field(default_factory=datetime.now)
    
    def is_admin(self) -> bool:
        return self.role == "admin"
    
    def is_cashier(self) -> bool:
        return self.role == "cashier"
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has permission."""
        # Admin has all permissions
        if self.is_admin():
            return True
        
        # Cashier permissions
        if self.is_cashier():
            cashier_permissions = {
                "transaksi.create", "transaksi.view",
                "produk.view", "laporan.view_own"
            }
            return permission in cashier_permissions
        
        return False


# ============================================================================
# ANALYTICS & REPORTING MODELS
# ============================================================================

@dataclass
class DailySalesReport:
    """Daily sales summary."""
    tanggal: datetime
    total_transaksi: int
    total_item: int
    total_penjualan: int
    total_pajak: int
    total_diskon: int
    payment_breakdown: dict  # {method: amount}


@dataclass
class ProductSalesReport:
    """Product sales analytics."""
    product_id: int
    product_name: str
    product_code: str
    total_qty_sold: int
    total_revenue: int
    total_transactions: int
    avg_qty_per_transaction: float


@dataclass
class SalesTrendData:
    """Sales trend analytics for period comparison."""
    period: str  # "daily", "weekly", "monthly"
    start_date: datetime
    end_date: datetime
    total_revenue: int
    total_transactions: int
    avg_transaction_value: int
    growth_percent: float  # % change from previous period
    peak_hour: int = None
    peak_day: str = None
    payment_methods: dict = field(default_factory=dict)  # {method: amount}
    top_products: List[dict] = field(default_factory=list)


@dataclass
class InventorySnapshot:
    """Inventory state at a point in time."""
    timestamp: datetime
    product_id: int
    qty_before: int
    qty_after: int
    movement_type: str  # sale, restock, adjustment
    reference_id: str  # transaction_id or reason


@dataclass
class ActivityLog:
    """Activity logging for security and audit trail."""
    id: int = None
    user_id: int = None
    username: str = ""
    action: str = ""  # login, logout, create_transaction, delete_product, etc
    resource_type: str = ""  # transaction, product, user, etc
    resource_id: str = ""  # ID of affected resource
    details: str = ""  # JSON-serialized details
    status: str = "success"  # success, failure
    timestamp: datetime = field(default_factory=datetime.now)
    ip_address: str = ""
    user_agent: str = ""
    
    def __str__(self) -> str:
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {self.username} - {self.action} ({self.status})"


# ============================================================================
# ONLINE ORDER MODELS
# ============================================================================

@dataclass
class OnlineOrder:
    """Online order (from e-commerce platform)."""
    id: int = None
    external_order_id: str = ""  # Order ID from online platform
    platform: str = ""  # shopify, woocommerce, tokopedia, shopee, etc
    customer_name: str = ""
    customer_phone: str = ""
    customer_email: str = ""
    shipping_address: str = ""
    items: List[TransactionItem] = field(default_factory=list)
    total: int = 0
    status: str = "pending"  # pending, confirmed, packed, shipped, delivered, cancelled
    order_date: datetime = field(default_factory=datetime.now)
    delivery_date: datetime = None
    notes: str = ""
    tracking_number: str = ""
    
    def link_to_transaction(self, transaction_id: int) -> None:
        """Link this online order to a POS transaction."""
        self.transaction_id = transaction_id


# ============================================================================
# BACKUP MODELS
# ============================================================================

@dataclass
class BackupFile:
    """Represents a backup file."""
    filename: str
    timestamp: datetime
    size_bytes: int
    status: str  # completed, in_progress, failed


# ============================================================================
# UTILITY
# ============================================================================

def format_rp(amount: int) -> str:
    """Format amount as Indonesian Rupiah.
    
    Args:
        amount (int): Amount in IDR
    
    Returns:
        str: Formatted string like "Rp 1.234.567"
    """
    return f"Rp {amount:,.0f}".replace(",", ".")
