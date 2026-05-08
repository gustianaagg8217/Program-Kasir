# ============================================================================
# INVOICE_MODEL.PY - Invoice Data Models
# ============================================================================
# Fungsi: Define Invoice and InvoiceItem models untuk invoice system
# ============================================================================

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime

# ============================================================================
# INVOICE MODELS
# ============================================================================

@dataclass
class InvoiceItem:
    """Model untuk item dalam invoice."""
    nama: str
    qty: int
    harga_satuan: int
    subtotal: int
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'nama': self.nama,
            'qty': self.qty,
            'harga_satuan': self.harga_satuan,
            'subtotal': self.subtotal
        }


@dataclass
class Invoice:
    """Model untuk invoice header."""
    id: Optional[int] = None
    invoice_number: Optional[str] = None
    total: int = 0
    bayar: int = 0
    kembalian: int = 0
    created_at: Optional[datetime] = None
    items: List[InvoiceItem] = field(default_factory=list)
    discount_percent: float = 0
    discount_amount: int = 0
    tax_percent: float = 0
    tax_amount: int = 0
    payment_type: str = 'lunas'  # 'lunas' atau 'termin'
    
    def add_item(self, item: InvoiceItem):
        """Add item ke invoice."""
        self.items.append(item)
    
    def get_items_count(self) -> int:
        """Get total items count."""
        return sum(item.qty for item in self.items)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'invoice_number': self.invoice_number,
            'total': self.total,
            'bayar': self.bayar,
            'kembalian': self.kembalian,
            'created_at': self.created_at,
            'items': [item.to_dict() for item in self.items],
            'discount_percent': self.discount_percent,
            'discount_amount': self.discount_amount,
            'tax_percent': self.tax_percent,
            'tax_amount': self.tax_amount,
            'payment_type': self.payment_type,
            'items_count': self.get_items_count()
        }
