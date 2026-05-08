# ============================================================================
# INVOICE_SERVICE.PY - Invoice Business Logic Service
# ============================================================================
# Fungsi: Manage invoice creation, retrieval, dan database operations
# ============================================================================

import os
import sys
from datetime import datetime
from typing import Optional, List, Dict

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .invoice_model import Invoice, InvoiceItem
from logger_config import get_logger

logger = get_logger(__name__)


class InvoiceService:
    """
    Service untuk mengelola invoice dari transaction.
    
    Responsibilities:
    - Generate invoice number dengan format INV-YYYYMMDD-HHMMSS
    - Create invoice dari transaction_id
    - Save invoice + items ke database
    - Retrieve invoice dari database
    
    Attributes:
        db (DatabaseManager): Database instance
    """
    
    def __init__(self, db):
        """
        Inisialisasi InvoiceService.
        
        Args:
            db (DatabaseManager): Database manager instance
        """
        self.db = db
    
    # ========================================================================
    # INVOICE NUMBER GENERATION
    # ========================================================================
    
    def generate_invoice_number(self) -> str:
        """
        Generate invoice number dengan format: INV-YYYYMMDD-HHMMSS
        
        Contoh: INV-20260428-143022
        
        Returns:
            str: Invoice number yang unique
        """
        now = datetime.now()
        invoice_number = now.strftime("INV-%Y%m%d-%H%M%S")
        return invoice_number
    
    # ========================================================================
    # CREATE INVOICE FROM TRANSACTION
    # ========================================================================
    
    def create_invoice_from_transaction(self, transaction_id: int) -> Optional[int]:
        """
        Create invoice dari transaction yang sudah ada.
        
        Workflow:
        1. Fetch transaction + items dari database
        2. Generate invoice number
        3. Insert ke invoices table
        4. Insert semua items ke invoice_items table
        5. Return invoice_id
        
        Args:
            transaction_id (int): ID dari transaction
            
        Returns:
            Optional[int]: Invoice ID jika berhasil, None jika gagal
        """
        try:
            # Fetch transaction detail from database
            trans_detail = self.db.get_transaction(transaction_id)
            
            if not trans_detail:
                logger.error(f"Transaction {transaction_id} not found")
                return None
            
            trans = trans_detail.get('transaction', {})
            items = trans_detail.get('items', [])
            
            # Generate invoice number
            invoice_number = self.generate_invoice_number()
            
            # Create invoice
            invoice = Invoice(
                invoice_number=invoice_number,
                total=trans.get('total', 0),
                bayar=trans.get('bayar', 0),
                kembalian=trans.get('kembalian', 0),
                discount_percent=trans.get('discount_percent', 0),
                discount_amount=trans.get('discount_amount', 0),
                tax_percent=trans.get('tax_percent', 0),
                tax_amount=trans.get('tax_amount', 0),
                payment_type=trans.get('payment_type', 'lunas'),
                created_at=datetime.now()
            )
            
            # Add items ke invoice
            for item in items:
                inv_item = InvoiceItem(
                    nama=item.get('nama', 'Unknown'),
                    qty=item.get('qty', 0),
                    harga_satuan=item.get('harga_satuan', 0),
                    subtotal=item.get('subtotal', 0)
                )
                invoice.add_item(inv_item)
            
            # Save invoice to database
            invoice_id = self._save_invoice_to_database(invoice)
            
            if invoice_id:
                logger.info(f"✅ Invoice created: {invoice_number} (ID: {invoice_id}) from transaction {transaction_id}")
                return invoice_id
            else:
                logger.error(f"Failed to save invoice for transaction {transaction_id}")
                return None
            
        except Exception as e:
            logger.error(f"Error creating invoice from transaction {transaction_id}: {e}", exc_info=True)
            return None
    
    # ========================================================================
    # SAVE INVOICE TO DATABASE
    # ========================================================================
    
    def _save_invoice_to_database(self, invoice: Invoice) -> Optional[int]:
        """
        Save invoice to database (header + items).
        
        Args:
            invoice (Invoice): Invoice object to save
            
        Returns:
            Optional[int]: Invoice ID jika berhasil, None jika gagal
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Insert invoice header
                cursor.execute("""
                    INSERT INTO invoices 
                    (invoice_number, total, bayar, kembalian, created_at,
                     discount_percent, discount_amount, tax_percent, tax_amount, payment_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    invoice.invoice_number,
                    invoice.total,
                    invoice.bayar,
                    invoice.kembalian,
                    invoice.created_at.isoformat() if invoice.created_at else datetime.now().isoformat(),
                    invoice.discount_percent,
                    invoice.discount_amount,
                    invoice.tax_percent,
                    invoice.tax_amount,
                    invoice.payment_type
                ))
                
                invoice_id = cursor.lastrowid
                
                # Insert invoice items
                for item in invoice.items:
                    cursor.execute("""
                        INSERT INTO invoice_items 
                        (invoice_id, nama, qty, harga_satuan, subtotal)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        invoice_id,
                        item.nama,
                        item.qty,
                        item.harga_satuan,
                        item.subtotal
                    ))
                
                conn.commit()
                logger.info(f"Invoice {invoice.invoice_number} saved to database with {len(invoice.items)} items")
                return invoice_id
                
        except Exception as e:
            logger.error(f"Error saving invoice to database: {e}", exc_info=True)
            return None
    
    # ========================================================================
    # RETRIEVE INVOICES
    # ========================================================================
    
    def get_all_invoices(self, limit: Optional[int] = None, offset: int = 0) -> List[Dict]:
        """
        Get semua invoices dari database (paling recent dulu).
        
        Args:
            limit (Optional[int]): Jumlah invoices to retrieve
            offset (int): Offset untuk pagination
            
        Returns:
            List[Dict]: List of invoice data
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM invoices ORDER BY created_at DESC"
                
                if limit:
                    query += f" LIMIT {limit} OFFSET {offset}"
                
                cursor.execute(query)
                invoices = [dict(row) for row in cursor.fetchall()]
                
                return invoices
                
        except Exception as e:
            logger.error(f"Error getting all invoices: {e}")
            return []
    
    def get_invoice_detail(self, invoice_id: int) -> Optional[Dict]:
        """
        Get detail invoice including items.
        
        Args:
            invoice_id (int): Invoice ID
            
        Returns:
            Optional[Dict]: Invoice detail dengan items, atau None jika tidak ditemukan
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get invoice header
                cursor.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
                invoice_row = cursor.fetchone()
                
                if not invoice_row:
                    logger.warning(f"Invoice {invoice_id} not found")
                    return None
                
                invoice_data = dict(invoice_row)
                
                # Get invoice items
                cursor.execute("SELECT * FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
                items = [dict(row) for row in cursor.fetchall()]
                
                invoice_data['items'] = items
                
                return invoice_data
                
        except Exception as e:
            logger.error(f"Error getting invoice detail {invoice_id}: {e}")
            return None
    
    def get_invoice_by_number(self, invoice_number: str) -> Optional[Dict]:
        """
        Get invoice by invoice number.
        
        Args:
            invoice_number (str): Invoice number (e.g., INV-20260428-143022)
            
        Returns:
            Optional[Dict]: Invoice detail dengan items, atau None
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get invoice header
                cursor.execute("SELECT * FROM invoices WHERE invoice_number = ?", (invoice_number,))
                invoice_row = cursor.fetchone()
                
                if not invoice_row:
                    logger.warning(f"Invoice {invoice_number} not found")
                    return None
                
                invoice_data = dict(invoice_row)
                invoice_id = invoice_data['id']
                
                # Get invoice items
                cursor.execute("SELECT * FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
                items = [dict(row) for row in cursor.fetchall()]
                
                invoice_data['items'] = items
                
                return invoice_data
                
        except Exception as e:
            logger.error(f"Error getting invoice by number {invoice_number}: {e}")
            return None
    
    def get_invoices_by_date(self, date_str: str) -> List[Dict]:
        """
        Get invoices yang dibuat pada tanggal tertentu.
        
        Args:
            date_str (str): Format YYYY-MM-DD
            
        Returns:
            List[Dict]: List of invoices
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT * FROM invoices 
                    WHERE DATE(created_at) = ?
                    ORDER BY created_at DESC
                """
                
                cursor.execute(query, (date_str,))
                invoices = [dict(row) for row in cursor.fetchall()]
                
                return invoices
                
        except Exception as e:
            logger.error(f"Error getting invoices by date {date_str}: {e}")
            return []
