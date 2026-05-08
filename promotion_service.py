# ============================================================================
# PROMOTION_SERVICE.PY - Service untuk mengelola promosi dan diskon
# ============================================================================
# Fungsi: Business logic untuk promosi, validasi promo, dan apply diskon
# Author: POS Team
# Version: 1.0
# ============================================================================

from datetime import datetime
from logger_config import get_logger

logger = get_logger(__name__)


class PromotionService:
    """
    Service untuk mengelola promosi dan diskon pada transaksi.
    
    Fitur:
    - Cek promosi aktif
    - Hitung diskon dari promosi
    - Apply promosi ke transaction items
    """
    
    def __init__(self, db):
        """
        Initialize PromotionService.
        
        Args:
            db: DatabaseManager instance
        """
        self.db = db
    
    def get_applicable_promotions(self, product_name: str = None, current_date: str = None) -> list:
        """
        Get promosi yang applicable untuk hari ini.
        
        Args:
            product_name: Nama produk (optional, filter berdasarkan deskripsi)
            current_date: Current date (YYYY-MM-DD), default ke hari ini
            
        Returns:
            list: List of applicable promotions
        """
        promotions = self.db.get_active_promotions(current_date)
        
        # Filter by product name if provided
        if product_name:
            promotions = [p for p in promotions 
                         if not p.get('deskripsi') or product_name.lower() in p['deskripsi'].lower()]
        
        return promotions
    
    def calculate_discount_for_quantity(self, qty: float, satuan: str, promotions: list = None) -> dict:
        """
        Hitung diskon untuk quantity tertentu.
        
        Support untuk "berlaku_kelipatan":
        - Jika berlaku_kelipatan=True: diskon dikalikan berdasarkan kelipatan min_qty
        - Contoh: min_qty=5, berlaku_kelipatan=True, nilai_diskon=2000 (nominal)
          - Beli 5 kg -> diskon 2000 (1x)
          - Beli 10 kg -> diskon 4000 (2x)
          - Beli 15 kg -> diskon 6000 (3x)
        
        Args:
            qty: Quantity produk
            satuan: Satuan produk (kg, pcs, dll)
            promotions: List of promotions untuk dicek (default fetch dari DB)
            
        Returns:
            dict: {
                'applicable': bool,
                'promotion_id': int or None,
                'promotion_name': str or None,
                'discount_percent': int or None,
                'discount_nominal': int or None,
                'multiplier': int (default 1 jika berlaku_kelipatan=False),
                'description': str or None
            }
        """
        if promotions is None:
            promotions = self.db.get_active_promotions()
        
        # Cari promosi yang applicable
        for promo in promotions:
            # Check satuan - skip jika satuan promosi adalah 'Rp' atau invalid (satuan qty-based)
            if promo['satuan'].lower() in ['rp', 'rupiah']:
                continue
                
            # Check satuan
            if satuan.lower() != promo['satuan'].lower():
                continue
            
            # Check minimum quantity
            if qty >= promo['min_qty']:
                # Hitung multiplier jika berlaku_kelipatan
                multiplier = 1
                # Konversi ke boolean (SQLite menyimpan sebagai 0/1)
                berlaku_kelipatan = bool(promo.get('berlaku_kelipatan', 0))
                if berlaku_kelipatan:
                    multiplier = int(qty / promo['min_qty'])
                    logger.debug(f"Kelipatan aktif (qty): {promo['nama_promosi']}, Qty={qty}, Min={promo['min_qty']}, Multiplier={multiplier}")
                
                if promo['tipe_diskon'] == 'persentase':
                    return {
                        'applicable': True,
                        'promotion_id': promo['id'],
                        'promotion_name': promo['nama_promosi'],
                        'discount_percent': promo['nilai_diskon'],
                        'discount_nominal': None,
                        'multiplier': multiplier,
                        'description': promo['deskripsi']
                    }
                elif promo['tipe_diskon'] == 'nominal':
                    return {
                        'applicable': True,
                        'promotion_id': promo['id'],
                        'promotion_name': promo['nama_promosi'],
                        'discount_percent': None,
                        'discount_nominal': promo['nilai_diskon'],
                        'multiplier': multiplier,
                        'description': promo['deskripsi']
                    }
        
        return {
            'applicable': False,
            'promotion_id': None,
            'promotion_name': None,
            'discount_percent': None,
            'discount_nominal': None,
            'multiplier': 1,
            'description': None
        }
    
    def calculate_discount_for_total(self, total_amount: int, promotions: list = None) -> dict:
        """
        Hitung diskon berdasarkan total pembelian (harga).
        
        Fitur ini untuk promosi yang ditetapkan berdasarkan minimum pembelian (harga),
        bukan berdasarkan qty/satuan. Contoh: "Beli Rp 200.000 dapat diskon 5%"
        
        Support untuk "berlaku_kelipatan": 
        - Jika berlaku_kelipatan=True: diskon dikalikan berdasarkan kelipatan min_qty
        - Contoh: min_qty=200000, berlaku_kelipatan=True, nilai_diskon=12000 (nominal)
          - Beli 200000 -> diskon 12000 (1x)
          - Beli 400000 -> diskon 24000 (2x)
          - Beli 600000 -> diskon 36000 (3x)
        
        Args:
            total_amount: Total harga pembelian (Rp)
            promotions: List of promotions untuk dicek (default fetch dari DB)
            
        Returns:
            dict: {
                'applicable': bool,
                'promotion_id': int or None,
                'promotion_name': str or None,
                'discount_percent': int or None,
                'discount_nominal': int or None,
                'multiplier': int (default 1 jika berlaku_kelipatan=False),
                'description': str or None
            }
        """
        if promotions is None:
            promotions = self.db.get_active_promotions()
        
        # Cari promosi yang applicable berdasarkan total amount
        for promo in promotions:
            # Hanya proses promosi dengan satuan 'Rp' atau 'rupiah' (price-based)
            if promo['satuan'].lower() not in ['rp', 'rupiah']:
                continue
            
            # Check minimum amount (min_qty field digunakan untuk min_amount dalam mode Rp)
            if total_amount >= promo['min_qty']:
                # Hitung multiplier jika berlaku_kelipatan
                multiplier = 1
                # Konversi ke boolean (SQLite menyimpan sebagai 0/1)
                berlaku_kelipatan_raw = promo.get('berlaku_kelipatan', 0)
                berlaku_kelipatan = bool(berlaku_kelipatan_raw)
                
                logger.info(f"✅ Promo matched: {promo['nama_promosi']}")
                logger.info(f"   Total: Rp{total_amount:,}, Min: Rp{promo['min_qty']:,}")
                logger.info(f"   berlaku_kelipatan raw: {berlaku_kelipatan_raw} (type: {type(berlaku_kelipatan_raw).__name__})")
                logger.info(f"   berlaku_kelipatan bool: {berlaku_kelipatan}")
                
                if berlaku_kelipatan:
                    multiplier = int(total_amount / promo['min_qty'])
                    logger.info(f"   ✓ KELIPATAN AKTIF: Multiplier = {multiplier}")
                else:
                    logger.info(f"   ✗ KELIPATAN TIDAK AKTIF: Multiplier = 1")
                
                if promo['tipe_diskon'] == 'persentase':
                    return {
                        'applicable': True,
                        'promotion_id': promo['id'],
                        'promotion_name': promo['nama_promosi'],
                        'discount_percent': promo['nilai_diskon'],
                        'discount_nominal': None,
                        'multiplier': multiplier,
                        'description': promo['deskripsi']
                    }
                elif promo['tipe_diskon'] == 'nominal':
                    return {
                        'applicable': True,
                        'promotion_id': promo['id'],
                        'promotion_name': promo['nama_promosi'],
                        'discount_percent': None,
                        'discount_nominal': promo['nilai_diskon'],
                        'multiplier': multiplier,
                        'description': promo['deskripsi']
                    }
        
        return {
            'applicable': False,
            'promotion_id': None,
            'promotion_name': None,
            'discount_percent': None,
            'discount_nominal': None,
            'multiplier': 1,
            'description': None
        }
    
    def apply_promotion_to_price(self, original_price: int, discount_info: dict) -> dict:
        """
        Apply diskon dari promosi ke harga.
        
        Args:
            original_price: Harga original (tanpa diskon)
            discount_info: Result dari calculate_discount_for_quantity()
            
        Returns:
            dict: {
                'original_price': int,
                'discount_amount': int,
                'final_price': int,
                'promotion_info': dict
            }
        """
        discount_amount = 0
        
        if discount_info['applicable']:
            if discount_info['discount_percent']:
                discount_amount = int(original_price * discount_info['discount_percent'] / 100)
            elif discount_info['discount_nominal']:
                discount_amount = discount_info['discount_nominal']
        
        final_price = max(0, original_price - discount_amount)
        
        return {
            'original_price': original_price,
            'discount_amount': discount_amount,
            'final_price': final_price,
            'promotion_info': discount_info
        }
    
    def validate_promotion_period(self, start_date: str, end_date: str) -> tuple:
        """
        Validasi periode promosi.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            tuple: (is_valid, message)
        """
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            
            if start > end:
                return False, "Tanggal mulai harus lebih kecil dari tanggal selesai"
            
            return True, "Valid"
        except ValueError as e:
            return False, f"Format tanggal tidak valid: {str(e)}"
    
    def validate_promotion_data(self, nama_promosi: str, tipe_diskon: str, 
                                nilai_diskon: int, min_qty: float) -> tuple:
        """
        Validasi data promosi.
        
        Args:
            nama_promosi: Nama promosi
            tipe_diskon: Tipe diskon
            nilai_diskon: Nilai diskon
            min_qty: Minimum quantity
            
        Returns:
            tuple: (is_valid, message)
        """
        if not nama_promosi or not nama_promosi.strip():
            return False, "Nama promosi tidak boleh kosong"
        
        if tipe_diskon not in ['persentase', 'nominal']:
            return False, "Tipe diskon harus 'persentase' atau 'nominal'"
        
        if nilai_diskon <= 0:
            return False, "Nilai diskon harus lebih besar dari 0"
        
        if tipe_diskon == 'persentase' and nilai_diskon > 100:
            return False, "Diskon persentase tidak boleh lebih dari 100%"
        
        if min_qty <= 0:
            return False, "Minimum quantity harus lebih besar dari 0"
        
        return True, "Valid"
