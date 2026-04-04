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
    Domain model untuk Transaction / Sale.
    
    Attributes:
        id (int): Transaction ID
        tanggal (datetime): Transaction date/time
        items (List[TransactionItem]): Items dalam transaksi
        payment_method (str): Payment method (cash, debit, credit, etc)
        total_sebelum_pajak (int): Total before tax
        total_pajak (int): Total tax
        total (int): Final total
        uang_diterima (int): Amount received
        kembalian (int): Change
        catatan (str): Notes
        cashier_id (int): Cashier ID
        status (str): Transaction status (pending, completed, cancelled)
    """
    id: int = None  # None untuk transaksi baru
    tanggal: datetime = field(default_factory=datetime.now)
    items: List[TransactionItem] = field(default_factory=list)
    payment_method: str = "cash"
    total_sebelum_pajak: int = 0
    total_pajak: int = 0
    total: int = 0
    uang_diterima: int = 0
    kembalian: int = 0
    catatan: str = ""
    cashier_id: int = None
    status: str = "pending"  # pending, completed, cancelled
    
    def add_item(self, item: TransactionItem) -> None:
        """Add item to transaction."""
        self.items.append(item)
        self._recalculate()
    
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
# REPORT / ANALYTICS MODELS
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
