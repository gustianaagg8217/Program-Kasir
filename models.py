# ============================================================================
# MODELS.PY - OOP Models untuk Product, Transaction, dan entities lainnya
# ============================================================================
# Fungsi: Definisikan class-based model untuk business logic POS
# Gunakan untuk validasi, formatting, dan business rules
# ============================================================================

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
from database import DatabaseManager
from logger_config import get_logger

logger = get_logger(__name__)

# ============================================================================
# VALIDASI UTILITY - Helper untuk validasi input
# ============================================================================

class ValidationError(Exception):
    """Custom exception untuk validation errors."""
    pass

def validate_harga(harga: int) -> int:
    """
    Validasi dan konversi harga.
    Harga harus positif.
    
    Args:
        harga (int): Harga dalam Rupiah
        
    Returns:
        int: Harga yang valid
        
    Raises:
        ValidationError: Jika harga tidak valid
    """
    if not isinstance(harga, (int, float)):
        raise ValidationError(f"Harga harus angka, bukan {type(harga)}")
    
    harga = int(harga)
    if harga <= 0:
        raise ValidationError("Harga harus lebih dari 0")
    
    return harga

def validate_qty(qty: int) -> int:
    """
    Validasi dan konversi quantity.
    
    Args:
        qty (int): Jumlah item
        
    Returns:
        int: Jumlah yang valid
        
    Raises:
        ValidationError: Jika qty tidak valid
    """
    if not isinstance(qty, (int, float)):
        raise ValidationError(f"Qty harus angka, bukan {type(qty)}")
    
    qty = int(qty)
    if qty <= 0:
        raise ValidationError("Qty harus lebih dari 0")
    
    return qty

def validate_kode(kode: str) -> str:
    """
    Validasi kode produk.
    Kode harus string non-empty, max 20 karakter.
    
    Args:
        kode (str): Kode produk
        
    Returns:
        str: Kode yang valid (uppercase)
        
    Raises:
        ValidationError: Jika kode tidak valid
    """
    if not isinstance(kode, str):
        raise ValidationError("Kode harus string")
    
    kode = kode.strip().upper()
    if len(kode) == 0:
        raise ValidationError("Kode tidak boleh kosong")
    if len(kode) > 20:
        raise ValidationError("Kode max 20 karakter")
    
    return kode

def validate_nama(nama: str) -> str:
    """
    Validasi nama produk.
    Nama harus string non-empty, min 2 karakter, max 20.
    
    Args:
        nama (str): Nama produk
        
    Returns:
        str: Nama yang valid
        
    Raises:
        ValidationError: Jika nama tidak valid
    """
    if not isinstance(nama, str):
        raise ValidationError("Nama harus string")
    
    nama = nama.strip()
    if len(nama) < 2:
        raise ValidationError("Nama minimal 2 karakter")
    if len(nama) > 20:
        raise ValidationError("Nama maksimal 20 karakter")
    
    return nama

# ============================================================================
# CURRENCY UTILITY - Format currency ke Rupiah
# ============================================================================

def format_rp(amount: int) -> str:
    """
    Format angka ke format currency Rupiah.
    
    Args:
        amount (int): Jumlah dalam Rupiah
        
    Returns:
        str: Format 'Rp X.XXX.XXX' (dengan separator ribuan)
        
    Contoh:
        format_rp(15000) → 'Rp 15.000'
        format_rp(1234567) → 'Rp 1.234.567'
    """
    if amount < 0:
        return f"-Rp {abs(amount):,.0f}".replace(',', '.')
    return f"Rp {amount:,.0f}".replace(',', '.')

# ============================================================================
# PRODUCT MODEL - Class untuk produk
# ============================================================================

@dataclass
class Product:
    """
    Merepresentasikan satu produk dalam sistem POS.
    
    Attributes:
        id (int): ID produk dari database (auto-generated)
        kode (str): Kode unik produk (contoh: 'PROD001')
        nama (str): Nama produk
        harga (int): Harga dalam Rupiah
        stok (int): Jumlah stok
        
    Methods:
        from_dict(): Konversi dict ke Product object
        to_dict(): Konversi ke dict
        validate(): Validasi semua field
        display(): Format display di console
    """
    
    id: Optional[int] = None
    kode: str = None
    nama: str = None
    harga: int = None
    stok: int = None
    
    def __post_init__(self):
        """
        Dijalankan otomatis setelah __init__.
        Gunakan untuk initial validation.
        """
        try:
            self.validate()
        except ValidationError as e:
            raise
    
    @staticmethod
    def from_dict(data: dict) -> 'Product':
        """
        Buat Product object dari dictionary.
        Berguna untuk konversi hasil database query.
        
        Args:
            data (dict): Dictionary berisi product data
            
        Returns:
            Product: Object Product instance
            
        Contoh:
            product_dict = {'id': 1, 'kode': 'PROD001', ...}
            product = Product.from_dict(product_dict)
        """
        return Product(
            id=data.get('id'),
            kode=data.get('kode'),
            nama=data.get('nama'),
            harga=data.get('harga'),
            stok=data.get('stok')
        )
    
    def to_dict(self) -> dict:
        """
        Konversi Product ke dictionary.
        
        Returns:
            dict: Product data dalam format dict
        """
        return {
            'id': self.id,
            'kode': self.kode,
            'nama': self.nama,
            'harga': self.harga,
            'stok': self.stok
        }
    
    def validate(self):
        """
        Validasi semua field Product.
        
        Raises:
            ValidationError: Jika ada field yang tidak valid
        """
        if self.kode:
            self.kode = validate_kode(self.kode)
        if self.nama:
            self.nama = validate_nama(self.nama)
        if self.harga:
            self.harga = validate_harga(self.harga)
        if self.stok is not None:
            self.stok = validate_qty(self.stok)
    
    def display(self) -> str:
        """
        Format display Product untuk ditampilkan di console/laporan.
        
        Returns:
            str: Formatted product info
            
        Contoh output:
            PROD001 | Mie Goreng     | Rp 15.000 | Stok: 100
        """
        return (
            f"{self.kode:<10} | "
            f"{self.nama:<20} | "
            f"{format_rp(self.harga):<15} | "
            f"Stok: {self.stok:>5}"
        )
    
    def __repr__(self) -> str:
        """String representation untuk debugging."""
        return f"Product(id={self.id}, kode={self.kode}, nama={self.nama}, harga={self.harga}, stok={self.stok})"

# ============================================================================
# TRANSACTION ITEM MODEL - Item dalam satu transaksi
# ============================================================================

@dataclass
class TransactionItem:
    """
    Merepresentasikan satu item (produk) dalam transaksi.
    
    Attributes:
        product_id (int): ID produk
        product_name (str): Nama produk (untuk display)
        qty (int): Jumlah
        harga_satuan (int): Harga per unit dalam Rupiah
        subtotal (int): Total (qty * harga_satuan)
        
    Methods:
        from_dict(): Buat dari dict
        to_dict(): Konversi ke dict
        get_subtotal(): Hitung subtotal
        display(): Format display
    """
    
    product_id: int
    product_name: str
    qty: int
    harga_satuan: int
    subtotal: int = None
    
    def __post_init__(self):
        """Validasi dan hitung subtotal."""
        self.qty = validate_qty(self.qty)
        self.harga_satuan = validate_harga(self.harga_satuan)
        
        # Auto-calculate subtotal jika belum ada
        if self.subtotal is None:
            self.subtotal = self.get_subtotal()
    
    @staticmethod
    def from_dict(data: dict) -> 'TransactionItem':
        """
        Buat TransactionItem dari dictionary.
        
        Args:
            data (dict): Dictionary berisi product_id, product_name, qty, harga_satuan
            
        Returns:
            TransactionItem: Object instance
        """
        return TransactionItem(
            product_id=data.get('product_id'),
            product_name=data.get('product_name', data.get('nama')),
            qty=data.get('qty'),
            harga_satuan=data.get('harga_satuan', data.get('harga')),
            subtotal=data.get('subtotal')
        )
    
    def to_dict(self) -> dict:
        """Konversi ke dict."""
        return {
            'product_id': self.product_id,
            'product_name': self.product_name,
            'qty': self.qty,
            'harga_satuan': self.harga_satuan,
            'subtotal': self.subtotal
        }
    
    def get_subtotal(self) -> int:
        """
        Hitung subtotal (qty * harga_satuan).
        
        Returns:
            int: Subtotal dalam Rupiah
        """
        return self.qty * self.harga_satuan
    
    def display(self) -> str:
        """
        Format display TransactionItem untuk receipt/laporan.
        
        Returns:
            str: Formatted item
            
        Contoh output:
            Mie Goreng           2x Rp 15.000 = Rp 30.000
        """
        return (
            f"{self.product_name:<20} "
            f"{self.qty:>3}x {format_rp(self.harga_satuan):<15} = "
            f"{format_rp(self.subtotal)}"
        )
    
    def __repr__(self) -> str:
        """String representation."""
        return (f"TransactionItem(product={self.product_name}, qty={self.qty}, "
                f"subtotal={format_rp(self.subtotal)})")

# ============================================================================
# TRANSACTION MODEL - Class untuk transaksi utama
# ============================================================================

@dataclass
class Transaction:
    """
    Merepresentasikan satu transaksi penjualan.
    
    Attributes:
        id (int): ID transaksi (auto-generated)
        items (List[TransactionItem]): Daftar item yang dibeli
        subtotal (int): Subtotal belanja (sum of subtotal items) sebelum discount/tax
        discount_percent (float): Diskon dalam persen (0-100)
        discount_amount (int): Diskon dalam rupiah (auto-calculated)
        tax_percent (float): Pajak (PPN) dalam persen (0-100)
        tax_amount (int): Pajak dalam rupiah (auto-calculated)
        total (int): Total belanja (subtotal - discount + tax)
        bayar (int): Jumlah uang pembeli
        kembalian (int): Kembalian = bayar - total
        tanggal (datetime): Waktu transaksi
        
    Methods:
        add_item(): Tambah item ke transaksi
        remove_item(): Hapus item dari transaksi
        calculate_total(): Hitung total belanja dengan discount/tax
        set_discount(): Set diskon
        set_tax(): Set pajak
        calculate_kembalian(): Hitung kembalian
        is_valid(): Cek apakah transaksi valid
    """
    
    id: Optional[int] = None
    items: List[TransactionItem] = None
    subtotal: int = 0  # Sebelum discount/tax
    discount_percent: float = 0.0  # Dalam persen
    discount_amount: int = 0  # Dalam rupiah
    tax_percent: float = 0.0  # Dalam persen
    tax_amount: int = 0  # Dalam rupiah
    total: int = 0  # Setelah discount/tax
    bayar: int = 0
    kembalian: int = 0
    tanggal: datetime = None
    
    def __post_init__(self):
        """Inisialisasi default values."""
        if self.items is None:
            self.items = []
        if self.tanggal is None:
            self.tanggal = datetime.now()
    
    def add_item(self, item: TransactionItem):
        """
        Tambah item ke transaksi.
        
        Args:
            item (TransactionItem): Item yang ditambahkan
        """
        if not isinstance(item, TransactionItem):
            raise TypeError("Item harus TransactionItem object")
        
        self.items.append(item)
        self.calculate_total()
    
    def remove_item(self, index: int):
        """
        Hapus item dari transaksi berdasarkan index.
        
        Args:
            index (int): Index item dalam list
            
        Raises:
            IndexError: Jika index tidak valid
        """
        if 0 <= index < len(self.items):
            self.items.pop(index)
            self.calculate_total()
        else:
            raise IndexError(f"Index {index} tidak valid")
    
    def get_item_count(self) -> int:
        """
        Hitung jumlah item (berbeda dengan qty).
        
        Returns:
            int: Jumlah unique item dalam transaksi
        """
        return len(self.items)
    
    def get_qty_total(self) -> int:
        """
        Hitung total quantity dari semua item.
        
        Returns:
            int: Total qty seluruh item
            
        Contoh: Jika ada 2 items dengan qty 3 dan 2, return 5
        """
        return sum(item.qty for item in self.items)
    
    def calculate_total(self) -> int:
        """
        Hitung total belanja dari semua item dengan discount dan tax.
        
        Formula:
        1. Hitung subtotal dari semua item
        2. Hitung diskon: discount_amount = subtotal * (discount_percent / 100)
        3. Hitung pajak: tax_amount = (subtotal - discount_amount) * (tax_percent / 100)
        4. Total = subtotal - discount_amount + tax_amount
        
        Returns:
            int: Total dalam Rupiah
        """
        # Step 1: Subtotal (sebelum discount/tax)
        self.subtotal = sum(item.subtotal for item in self.items)
        
        # Step 2: Hitung discount
        if self.discount_percent > 0:
            self.discount_amount = int(self.subtotal * (self.discount_percent / 100))
        else:
            self.discount_amount = 0
        
        # Step 3: Hitung pajak dari (subtotal - discount)
        base_for_tax = self.subtotal - self.discount_amount
        if self.tax_percent > 0:
            self.tax_amount = int(base_for_tax * (self.tax_percent / 100))
        else:
            self.tax_amount = 0
        
        # Step 4: Total akhir
        self.total = self.subtotal - self.discount_amount + self.tax_amount
        return self.total
    
    def set_discount(self, discount_percent: float) -> bool:
        """
        Set diskon dalam persen.
        
        Args:
            discount_percent (float): Diskon dalam persen (0-100)
            
        Returns:
            bool: True jika berhasil
            
        Raises:
            ValidationError: Jika diskon invalid
        """
        if discount_percent < 0 or discount_percent > 100:
            logger.warning(f"Invalid discount: {discount_percent}%")
            raise ValidationError("Diskon harus antara 0-100%")
        
        self.discount_percent = discount_percent
        self.calculate_total()
        logger.info(f"Discount set: {discount_percent}% (amount: Rp{self.discount_amount:,})")
        return True
    
    def set_tax(self, tax_percent: float) -> bool:
        """
        Set pajak (PPN) dalam persen.
        
        Args:
            tax_percent (float): Pajak dalam persen (>= 0)
            
        Returns:
            bool: True jika berhasil
            
        Raises:
            ValidationError: Jika pajak invalid
        """
        if tax_percent < 0 or tax_percent > 100:
            logger.warning(f"Invalid tax: {tax_percent}%")
            raise ValidationError("Pajak harus antara 0-100%")
        
        self.tax_percent = tax_percent
        self.calculate_total()
        logger.info(f"Tax set: {tax_percent}% (amount: Rp{self.tax_amount:,})")
        return True
    
    def set_bayar(self, bayar: int):
        """
        Set jumlah pembayaran dan hitung kembalian.
        
        Args:
            bayar (int): Jumlah uang pembayaran
            
        Raises:
            ValidationError: Jika bayar kurang dari total
        """
        bayar = validate_harga(bayar)
        
        if bayar < self.total:
            raise ValidationError(
                f"Pembayaran ({format_rp(bayar)}) kurang dari total "
                f"({format_rp(self.total)})"
            )
        
        self.bayar = bayar
        self.calculate_kembalian()
    
    def calculate_kembalian(self) -> int:
        """
        Hitung kembalian.
        
        Returns:
            int: Kembalian dalam Rupiah
        """
        self.kembalian = self.bayar - self.total
        return self.kembalian
    
    def is_valid(self) -> bool:
        """
        Cek apakah transaksi valid dan siap disimpan.
        
        Kondisi valid:
        - Ada minimal 1 item
        - Total > 0
        - Pembayaran >= total
        - Kembalian >= 0
        
        Returns:
            bool: True jika valid
        """
        if len(self.items) == 0:
            return False
        if self.total <= 0:
            return False
        if self.bayar < self.total:
            return False
        if self.kembalian < 0:
            return False
        return True
    
    @staticmethod
    def from_dict(data: dict, db: DatabaseManager = None) -> 'Transaction':
        """
        Buat Transaction dari dictionary (hasil query database).
        
        Args:
            data (dict): Transaction data dengan 'transaction' dan 'items' key
            db (DatabaseManager): Database instance (optional)
            
        Returns:
            Transaction: Object instance
        """
        trans = Transaction(
            id=data.get('id'),
            total=data.get('total', 0),
            bayar=data.get('bayar', 0),
            kembalian=data.get('kembalian', 0),
            tanggal=datetime.fromisoformat(data.get('tanggal')) if data.get('tanggal') else datetime.now()
        )
        
        if 'items' in data and isinstance(data['items'], list):
            for item_data in data['items']:
                trans.items.append(TransactionItem.from_dict(item_data))
        
        return trans
    
    def to_dict(self) -> dict:
        """Konversi ke dict."""
        return {
            'id': self.id,
            'items': [item.to_dict() for item in self.items],
            'total': self.total,
            'bayar': self.bayar,
            'kembalian': self.kembalian,
            'tanggal': self.tanggal.isoformat()
        }
    
    def get_items_summary(self) -> str:
        """
        Dapatkan summary items untuk display singkat.
        
        Returns:
            str: Contoh: "3 items (5 qty total)"
        """
        qty_total = self.get_qty_total()
        return f"{self.get_item_count()} item(s) ({qty_total} qty total)"
    
    def display_receipt(self) -> str:
        """
        Format display struk receipt lengkap.
        
        Returns:
            str: Formatted receipt dengan header, items, total, bayar, kembalian
        """
        receipt = []
        receipt.append("=" * 50)
        receipt.append("STRUK PENJUALAN")
        receipt.append("=" * 50)
        receipt.append(f"Tanggal: {self.tanggal.strftime('%Y-%m-%d %H:%M:%S')}")
        receipt.append("-" * 50)
        receipt.append("ITEM:")
        
        for item in self.items:
            receipt.append(f"  {item.display()}")
        
        receipt.append("-" * 50)
        receipt.append(f"TOTAL         : {format_rp(self.total)}")
        receipt.append(f"PEMBAYARAN    : {format_rp(self.bayar)}")
        receipt.append(f"KEMBALIAN     : {format_rp(self.kembalian)}")
        receipt.append("=" * 50)
        
        return "\n".join(receipt)
    
    def __repr__(self) -> str:
        """String representation."""
        return (f"Transaction(id={self.id}, items={len(self.items)}, "
                f"total={format_rp(self.total)})")

# ============================================================================
# PRODUCT MANAGER - Service class untuk mengelola produk
# ============================================================================

class ProductManager:
    """
    Service class untuk mengelola produk-produk di sistem.
    Menggabungkan Product model dengan database operations.
    
    Attributes:
        db (DatabaseManager): Instance database
        
    Methods:
        add_product(): Tambah produk baru
        get_product(): Ambil produk
        update_product(): Update produk
        delete_product(): Hapus produk
        list_products(): Ambil semua produk
    """
    
    def __init__(self, db: DatabaseManager):
        """
        Inisialisasi ProductManager.
        
        Args:
            db (DatabaseManager): Database instance
        """
        self.db = db
    
    def add_product(self, kode: str, nama: str, harga: int, stok: int) -> bool:
        """
        Tambah produk baru ke sistem.
        
        Args:
            kode (str): Kode produk unik
            nama (str): Nama produk
            harga (int): Harga dalam Rupiah
            stok (int): Jumlah stok awal
            
        Returns:
            bool: True jika berhasil
        """
        try:
            # Validasi menggunakan Product class
            product = Product(kode=kode, nama=nama, harga=harga, stok=stok)
            
            # Simpan ke database
            result = self.db.add_product(product.kode, product.nama, product.harga, product.stok)
            if result:
                logger.info(f"Product added via ProductManager: {kode} = {nama}")
            return result
        except ValidationError as e:
            logger.error(f"Product validation error: {e}")
            return False
    
    def get_product(self, kode: str) -> Optional[Product]:
        """
        Ambil produk dari database.
        
        Args:
            kode (str): Kode produk
            
        Returns:
            Product: Product object jika ditemukan
            None: Jika tidak ditemukan
        """
        data = self.db.get_product_by_kode(kode)
        return Product.from_dict(data) if data else None
    
    def list_products(self) -> List[Product]:
        """
        Ambil semua produk.
        
        Returns:
            List[Product]: List of Product objects
        """
        data_list = self.db.get_all_products()
        return [Product.from_dict(data) for data in data_list]
    
    def get_next_product_code(self) -> str:
        """
        Generate kode produk otomatis dengan format 4 digit (0001, 0002, 0003, dst).
        
        Method ini langsung query database untuk mencari kode tertinggi dan increment.
        Format hasil: 0001, 0002, 0003, ..., 0010, ..., 9999
        
        Returns:
            str: Kode produk berikutnya dengan format 4 digit
            
        Contoh:
            Jika sudah ada produk: 0001, 0002, 0003
            Maka return: "0004"
            
            Jika belum ada produk:
            Maka return: "0001"
        """
        return self.db.get_next_product_code()
    
    def update_product(self, kode: str, **kwargs) -> bool:
        """
        Update produk.
        
        Args:
            kode (str): Kode produk
            **kwargs: Field yang ingin diupdate (nama, harga, stok)
            
        Returns:
            bool: True jika berhasil
        """
        return self.db.update_product(kode, **kwargs)
    
    def delete_product(self, kode: str) -> bool:
        """
        Hapus produk.
        
        Args:
            kode (str): Kode produk
            
        Returns:
            bool: True jika berhasil
        """
        return self.db.delete_product(kode)

# ============================================================================
# TESTING - Jalankan jika file dijalankan standalone
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("POS MODELS - Testing")
    print("=" * 70)
    
    # Test Product Model
    print("\n1️⃣ TEST PRODUCT MODEL:")
    try:
        product = Product(
            kode="PROD001",
            nama="Mie Goreng",
            harga=15000,
            stok=100
        )
        print(f"✅ Product created: {product}")
        print(f"   Display: {product.display()}")
    except ValidationError as e:
        print(f"❌ Error: {e}")
    
    # Test TransactionItem Model
    print("\n2️⃣ TEST TRANSACTION ITEM MODEL:")
    try:
        item = TransactionItem(
            product_id=1,
            product_name="Mie Goreng",
            qty=2,
            harga_satuan=15000
        )
        print(f"✅ Item created: {item}")
        print(f"   Subtotal: {format_rp(item.get_subtotal())}")
        print(f"   Display: {item.display()}")
    except ValidationError as e:
        print(f"❌ Error: {e}")
    
    # Test Transaction Model
    print("\n3️⃣ TEST TRANSACTION MODEL:")
    try:
        trans = Transaction()
        item1 = TransactionItem(1, "Mie Goreng", 2, 15000)
        item2 = TransactionItem(2, "Teh Botol", 3, 5000)
        
        trans.add_item(item1)
        trans.add_item(item2)
        trans.set_bayar(50000)
        
        print(f"✅ Transaction created: {trans}")
        print(f"   Items: {trans.get_items_summary()}")
        print(f"   Is Valid: {trans.is_valid()}")
        print(f"\n{trans.display_receipt()}")
    except (ValidationError, TypeError) as e:
        print(f"❌ Error: {e}")
    
    # Test Currency Formatting
    print("\n4️⃣ TEST CURRENCY FORMATTING:")
    print(f"   format_rp(1000) = {format_rp(1000)}")
    print(f"   format_rp(15000) = {format_rp(15000)}")
    print(f"   format_rp(1234567) = {format_rp(1234567)}")
