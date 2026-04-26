# ============================================================================
# PRINT_MANAGER.PY - Cross-Platform Printing Support
# ============================================================================
# Fungsi: Generate & print receipts, reports, labels cross-platform
# Responsibilitas: PDF generation, printer management, formatting
# ============================================================================

import os
import sys
import platform
import subprocess
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
from logger_config import get_logger

logger = get_logger(__name__)


class PrintTemplate:
    """Template untuk print output."""
    
    def __init__(self, name: str, width: int = 80):
        """
        Init print template.
        
        Args:
            name: Template name
            width: Line width dalam characters
        """
        self.name = name
        self.width = width
        self.content = []
    
    def add_line(self, text: str = "", align: str = "left", char: str = " "):
        """
        Add line ke template.
        
        Args:
            text: Text to print
            align: 'left', 'center', 'right'
            char: Padding character
        """
        if align == "center":
            line = text.center(self.width, char)
        elif align == "right":
            line = text.rjust(self.width, char)
        else:
            line = text.ljust(self.width, char)
        
        self.content.append(line)
    
    def add_separator(self, char: str = "-"):
        """Add separator line."""
        self.content.append(char * self.width)
    
    def add_blank(self):
        """Add blank line."""
        self.content.append("")
    
    def add_two_column(self, left: str, right: str, width_left: int = None):
        """Add two-column line."""
        if width_left is None:
            width_left = self.width // 2
        
        width_right = self.width - width_left
        line = left.ljust(width_left) + right.rjust(width_right)
        self.content.append(line)
    
    def get_content(self) -> str:
        """Get full template content."""
        return "\n".join(self.content)
    
    def clear(self):
        """Clear template."""
        self.content = []


class PrintManager:
    """
    Manager untuk printing operations cross-platform.
    
    Support:
    - Text printing (console, file)
    - PDF generation (placeholder)
    - Network printer support
    - Print queue management
    """
    
    def __init__(self, default_printer: str = None):
        """
        Init PrintManager.
        
        Args:
            default_printer: Default printer name
        """
        self.default_printer = default_printer
        self.system = platform.system()
        self.print_jobs = {}
        logger.info(f"PrintManager initialized on {self.system}")
    
    def create_receipt_template(
        self,
        store_name: str,
        receipt_number: str,
        cashier: str,
        items: List[Dict[str, Any]],
        subtotal: int,
        discount: int,
        tax: int,
        total: int,
        payment_method: str,
        notes: str = "",
        width: int = 80
    ) -> PrintTemplate:
        """
        Create receipt template.
        
        Args:
            store_name: Nama toko
            receipt_number: Nomor receipt
            cashier: Nama cashier
            items: List of items {kode, nama, qty, harga, subtotal}
            subtotal: Subtotal
            discount: Discount amount
            tax: Tax amount
            total: Total price
            payment_method: Metode pembayaran
            notes: Catatan
            width: Line width
            
        Returns:
            PrintTemplate object
        """
        template = PrintTemplate("receipt", width=width)
        
        # Header
        template.add_line(store_name, align="center")
        template.add_line(f"Receipt #{receipt_number}", align="center")
        template.add_line(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), align="center")
        template.add_blank()
        
        # Cashier info
        template.add_line(f"Cashier: {cashier}")
        template.add_separator()
        template.add_blank()
        
        # Items header
        template.add_line("ITEM".ljust(30) + "QTY".rjust(5) + "PRICE".rjust(20))
        template.add_separator("-")
        
        # Items
        for item in items:
            item_line = item['nama'][:30].ljust(30)
            qty_line = str(item['qty']).rjust(5)
            price_line = f"Rp {item['subtotal']:,}".rjust(20)
            template.add_line(item_line + qty_line + price_line)
        
        template.add_blank()
        template.add_separator("-")
        
        # Totals
        template.add_two_column("SUBTOTAL", f"Rp {subtotal:,}")
        if discount > 0:
            template.add_two_column("DISCOUNT", f"-Rp {discount:,}")
        if tax > 0:
            template.add_two_column("TAX", f"+Rp {tax:,}")
        
        template.add_separator()
        template.add_two_column("TOTAL", f"Rp {total:,}")
        template.add_separator()
        
        template.add_blank()
        template.add_line(f"Payment: {payment_method}", align="center")
        
        if notes:
            template.add_blank()
            template.add_line(f"Notes: {notes}")
        
        template.add_blank()
        template.add_line("Thank You!", align="center")
        template.add_line("Please come again", align="center")
        template.add_blank()
        
        return template
    
    def create_report_template(
        self,
        title: str,
        report_date: str,
        data: Dict[str, Any],
        width: int = 100
    ) -> PrintTemplate:
        """
        Create report template.
        
        Args:
            title: Report title
            report_date: Report date range
            data: Report data dictionary
            width: Line width
            
        Returns:
            PrintTemplate object
        """
        template = PrintTemplate("report", width=width)
        
        # Header
        template.add_line(title, align="center")
        template.add_line(report_date, align="center")
        template.add_line(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), align="center")
        template.add_blank()
        template.add_separator()
        
        # Data
        for key, value in data.items():
            if isinstance(value, dict):
                template.add_line(f"{key.upper()}:")
                for sub_key, sub_value in value.items():
                    template.add_line(f"  {sub_key}: {sub_value}")
            else:
                template.add_line(f"{key}: {value}")
        
        template.add_blank()
        template.add_separator()
        
        return template
    
    def print_text(self, text: str, printer: str = None) -> bool:
        """
        Print text ke printer.
        
        Args:
            text: Text content
            printer: Printer name (default: default_printer)
            
        Returns:
            True jika sukses
        """
        try:
            printer = printer or self.default_printer
            
            if self.system == "Windows":
                # Windows: Use notepad print
                temp_file = Path("temp_print.txt")
                temp_file.write_text(text)
                
                if printer:
                    subprocess.run(
                        f'notepad.exe /p "{temp_file}"',
                        shell=True,
                        check=True
                    )
                else:
                    subprocess.run(
                        f'notepad.exe /p "{temp_file}"',
                        shell=True,
                        check=True
                    )
                
                temp_file.unlink()
                logger.info(f"Printed to Windows printer: {printer or 'default'}")
                return True
            
            elif self.system == "Linux":
                # Linux: Use lp command
                if printer:
                    subprocess.run(
                        f"lp -d {printer}",
                        input=text,
                        shell=True,
                        text=True,
                        check=True
                    )
                else:
                    subprocess.run(
                        "lp",
                        input=text,
                        shell=True,
                        text=True,
                        check=True
                    )
                
                logger.info(f"Printed to Linux printer: {printer or 'default'}")
                return True
            
            elif self.system == "Darwin":
                # macOS: Use lp command
                if printer:
                    subprocess.run(
                        f"lp -d {printer}",
                        input=text,
                        shell=True,
                        text=True,
                        check=True
                    )
                else:
                    subprocess.run(
                        "lp",
                        input=text,
                        shell=True,
                        text=True,
                        check=True
                    )
                
                logger.info(f"Printed to macOS printer: {printer or 'default'}")
                return True
            
            else:
                logger.warning(f"Platform {self.system} tidak supported untuk printing")
                return False
        
        except Exception as e:
            logger.error(f"Error printing: {e}")
            return False
    
    def print_receipt(
        self,
        receipt_template: PrintTemplate,
        printer: str = None,
        also_save: bool = False,
        output_file: str = None
    ) -> bool:
        """
        Print receipt ke printer dan/atau save ke file.
        
        Args:
            receipt_template: PrintTemplate object
            printer: Printer name
            also_save: Also save to file
            output_file: Output file path
            
        Returns:
            True jika sukses
        """
        try:
            content = receipt_template.get_content()
            
            # Print to printer
            if printer or self.default_printer:
                if not self.print_text(content, printer):
                    logger.warning("Failed to print to printer, trying console")
                    print(content)
            else:
                print(content)
            
            # Also save to file
            if also_save or output_file:
                if not output_file:
                    output_file = f"receipts/receipt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                
                Path(output_file).parent.mkdir(parents=True, exist_ok=True)
                Path(output_file).write_text(content)
                logger.info(f"Receipt saved: {output_file}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error printing receipt: {e}")
            return False
    
    def get_available_printers(self) -> List[str]:
        """
        Get list of available printers.
        
        Returns:
            List of printer names
        """
        try:
            if self.system == "Windows":
                # Windows: Use wmic command
                result = subprocess.run(
                    "wmic printerconfig get name",
                    capture_output=True,
                    text=True,
                    shell=True
                )
                printers = [line.strip() for line in result.stdout.split('\n') if line.strip() and line.strip() != 'Name']
                return printers
            
            elif self.system in ["Linux", "Darwin"]:
                # Linux/macOS: Use lpstat command
                result = subprocess.run(
                    "lpstat -p -d",
                    capture_output=True,
                    text=True,
                    shell=True
                )
                printers = [line.strip() for line in result.stdout.split('\n') if line.strip()]
                return printers
            
            else:
                logger.warning(f"Platform {self.system} tidak supported untuk printer detection")
                return []
        
        except Exception as e:
            logger.error(f"Error getting printers: {e}")
            return []
    
    def save_as_file(
        self,
        template: PrintTemplate,
        output_file: str,
        format: str = "txt"
    ) -> bool:
        """
        Save template ke file.
        
        Args:
            template: PrintTemplate object
            output_file: Output file path
            format: File format ('txt', 'pdf' placeholder)
            
        Returns:
            True jika sukses
        """
        try:
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            
            if format == "txt":
                Path(output_file).write_text(template.get_content())
            else:
                # TODO Phase 4+: Implement PDF generation
                logger.warning(f"Format {format} not yet implemented")
                Path(output_file).write_text(template.get_content())
            
            logger.info(f"Saved to {output_file}")
            return True
        
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            return False


# Global print manager instance
_print_manager = None

def get_print_manager(default_printer: str = None) -> PrintManager:
    """Get atau create global print manager."""
    global _print_manager
    if _print_manager is None:
        _print_manager = PrintManager(default_printer=default_printer)
    return _print_manager
