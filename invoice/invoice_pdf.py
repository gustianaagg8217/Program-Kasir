# ============================================================================
# INVOICE_PDF.PY - PDF Generation untuk Invoice
# ============================================================================
# Fungsi: Generate professional invoice PDF files
# ============================================================================

import os
import sys
from datetime import datetime
from typing import Optional, Dict

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logger_config import get_logger

# Try to import reportlab
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("⚠️ reportlab not installed. Install with: pip install reportlab")

logger = get_logger(__name__)


def format_rp(amount: int) -> str:
    """Format amount as Rupiah currency."""
    if isinstance(amount, str):
        try:
            amount = int(float(amount))
        except (ValueError, TypeError):
            return str(amount)
    return f"Rp {amount:,.0f}".replace(',', '.')


class InvoicePDFGenerator:
    """
    Generate professional invoice PDF dari invoice data.
    
    Features:
    - Company header dengan logo dan info
    - Invoice details (number, date)
    - Items table dengan format rapi
    - Summary (subtotal, discount, tax, total)
    - Payment info
    
    Attributes:
        invoice_dir (str): Directory untuk simpan PDF files
    """
    
    def __init__(self, invoice_dir: str = "invoices"):
        """
        Inisialisasi PDF generator.
        
        Args:
            invoice_dir (str): Directory untuk simpan invoices
        """
        self.invoice_dir = invoice_dir
        
        # Create directory jika belum ada
        if not os.path.exists(invoice_dir):
            os.makedirs(invoice_dir)
            logger.info(f"Created invoice directory: {invoice_dir}")
        
        if not REPORTLAB_AVAILABLE:
            logger.warning("⚠️ reportlab not available, PDF generation will be skipped")
    
    def generate_invoice_pdf(self, invoice_data: Dict, 
                            store_name: str = "TOKO UBI BAROKAH IBU AWANG",
                            store_address: str = "Jl. Desa Mekarbakti, pertigaan Cilembu.",
                            store_phone: Optional[str] = None,
                            db = None) -> Optional[str]:
        """
        Generate invoice PDF.
        
        Args:
            invoice_data (Dict): Invoice data dari database
            store_name (str): Nama toko
            store_address (str): Alamat toko
            store_phone (Optional[str]): Nomor telepon toko
            db (Optional): Database manager untuk lookup cicilan payments (untuk termin)
            
        Returns:
            Optional[str]: File path jika berhasil, None jika gagal
        """
        if not REPORTLAB_AVAILABLE:
            logger.warning("reportlab not available, skipping PDF generation")
            return None
        
        try:
            invoice_number = invoice_data.get('invoice_number', 'UNKNOWN')
            filename = f"{invoice_number}.pdf"
            filepath = os.path.join(self.invoice_dir, filename)
            
            # Create PDF document
            doc = SimpleDocTemplate(
                filepath,
                pagesize=A4,
                rightMargin=0.75*inch,
                leftMargin=0.75*inch,
                topMargin=0.75*inch,
                bottomMargin=0.75*inch
            )
            
            # Container untuk elements
            elements = []
            styles = getSampleStyleSheet()
            
            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=colors.HexColor('#2E86AB'),
                spaceAfter=6,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=12,
                textColor=colors.HexColor('#2E86AB'),
                spaceAfter=6,
                fontName='Helvetica-Bold'
            )
            
            # ================================================================
            # HEADER SECTION
            # ================================================================
            
            # Store name
            elements.append(Paragraph(store_name, title_style))
            elements.append(Spacer(1, 6))
            
            # Store address and phone
            address_text = f"{store_address}"
            if store_phone:
                address_text += f" | {store_phone}"
            elements.append(Paragraph(address_text, styles['Normal']))
            elements.append(Spacer(1, 12))
            
            # Invoice title and number
            invoice_number_para = Paragraph(
                f"<b>INVOICE</b><br/>{invoice_number}",
                ParagraphStyle(
                    'InvoiceNumber',
                    parent=styles['Heading2'],
                    fontSize=14,
                    alignment=TA_CENTER,
                    fontName='Helvetica-Bold'
                )
            )
            elements.append(invoice_number_para)
            elements.append(Spacer(1, 12))
            
            # ================================================================
            # INVOICE INFO SECTION (Date)
            # ================================================================
            
            created_at = invoice_data.get('created_at', datetime.now())
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at)
                except:
                    created_at = datetime.now()
            
            date_text = created_at.strftime("%d %B %Y %H:%M:%S")
            elements.append(Paragraph(f"<b>Tanggal:</b> {date_text}", styles['Normal']))
            elements.append(Spacer(1, 12))
            
            # ================================================================
            # ITEMS TABLE
            # ================================================================
            
            items = invoice_data.get('items', [])
            
            # Build table data
            table_data = [
                ['No', 'Deskripsi Produk', 'Qty', 'Harga Satuan', 'Subtotal']
            ]
            
            total_qty = 0
            for idx, item in enumerate(items, 1):
                nama = item.get('nama', 'Unknown Product')
                qty = int(item.get('qty', 0))
                harga_satuan = int(item.get('harga_satuan', 0))
                subtotal = int(item.get('subtotal', 0))
                
                total_qty += qty
                
                table_data.append([
                    str(idx),
                    nama,
                    str(qty),
                    format_rp(harga_satuan),
                    format_rp(subtotal)
                ])
            
            # Create table
            table = Table(table_data, colWidths=[0.5*inch, 3*inch, 0.7*inch, 1.3*inch, 1.5*inch])
            
            # Style table
            table.setStyle(TableStyle([
                # Header row
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E86AB')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                
                # Data rows
                ('ALIGN', (0, 1), (0, -1), 'CENTER'),
                ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 12))
            
            # ================================================================
            # SUMMARY SECTION
            # ================================================================
            
            total = int(invoice_data.get('total', 0))
            bayar = int(invoice_data.get('bayar', 0))
            kembalian = int(invoice_data.get('kembalian', 0))
            discount_amount = int(invoice_data.get('discount_amount', 0))
            tax_amount = int(invoice_data.get('tax_amount', 0))
            
            # Summary table
            summary_data = []
            
            # Subtotal
            subtotal = total + discount_amount - tax_amount
            summary_data.append(['Subtotal', format_rp(subtotal)])
            
            # Discount
            if discount_amount > 0:
                discount_pct = invoice_data.get('discount_percent', 0)
                summary_data.append([f"Diskon ({discount_pct}%)", f"-{format_rp(discount_amount)}"])
            
            # Tax
            if tax_amount > 0:
                tax_pct = invoice_data.get('tax_percent', 0)
                summary_data.append([f"Pajak ({tax_pct}%)", f"+{format_rp(tax_amount)}"])
            
            # Total
            summary_data.append(['TOTAL', format_rp(total)])
            
            # Payment section - berbeda untuk termin vs lunas
            payment_type = invoice_data.get('payment_type', 'lunas')
            
            if payment_type == 'termin':
                # For termin payment: show DP and remaining balance
                summary_data.append(['DP (Down Payment)', format_rp(bayar)])
                
                # Calculate sisa hutang
                # If database is available, include completed cicilan payments
                sisa_hutang = total - bayar
                if db:
                    try:
                        invoice_id = invoice_data.get('id')
                        if invoice_id:
                            # Get completed cicilan payments
                            completed_payments = db.calculate_total_paid_termin(invoice_id)
                            sisa_hutang = total - bayar - completed_payments
                    except Exception as e:
                        logger.warning(f"Could not get cicilan payments: {e}")
                        sisa_hutang = total - bayar
                
                summary_data.append(['Sisa Hutang', format_rp(sisa_hutang)])
            else:
                # For cash payment: show payment and change
                summary_data.append(['Pembayaran', format_rp(bayar)])
                summary_data.append(['Kembalian', format_rp(kembalian)])
            
            summary_table = Table(summary_data, colWidths=[4*inch, 2*inch])
            summary_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, -3), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, -3), (-1, -1), 11),
                ('BACKGROUND', (0, -3), (-1, -3), colors.HexColor('#38A169')),
                ('TEXTCOLOR', (0, -3), (-1, -3), colors.white),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (1, 0), (1, -1), 10),
            ]))
            
            elements.append(summary_table)
            elements.append(Spacer(1, 20))
            
            # ================================================================
            # FOOTER
            # ================================================================
            
            footer_text = "Terima kasih atas pembelian Anda!<br/>Barang yang sudah dibeli tidak dapat dikembalikan."
            elements.append(Paragraph(footer_text, 
                ParagraphStyle(
                    'Footer',
                    parent=styles['Normal'],
                    alignment=TA_CENTER,
                    fontSize=9,
                    textColor=colors.HexColor('#64748B')
                )
            ))
            
            # Build PDF
            doc.build(elements)
            
            logger.info(f"✅ Invoice PDF generated: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error generating invoice PDF: {e}", exc_info=True)
            return None
    
    def get_invoice_filepath(self, invoice_number: str) -> str:
        """Get filepath untuk invoice yang sudah digenerate."""
        return os.path.join(self.invoice_dir, f"{invoice_number}.pdf")
