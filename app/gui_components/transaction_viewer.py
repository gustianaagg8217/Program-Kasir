# ============================================================================
# TRANSACTION_VIEWER.PY - Transaction History Viewer Component
# ============================================================================
# Fungsi: Tkinter widget untuk view transaction history dengan search/filter
# Responsibilitas: Display transactions, filtering, sorting, export
# ============================================================================

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from app.services.transaction_service import TransactionService
from logger_config import get_logger

logger = get_logger(__name__)


class TransactionViewer:
    """
    Transaction history viewer component.
    
    Features:
    - Display transactions dalam tabel
    - Filter by date range, payment method, user
    - Sort by column
    - Show transaction details
    - Export to file
    """
    
    def __init__(
        self,
        parent: tk.Widget,
        transaction_service: TransactionService,
        width: int = 1000,
        height: int = 500
    ):
        """
        Init TransactionViewer.
        
        Args:
            parent: Parent tkinter widget
            transaction_service: TransactionService instance
            width: Width dalam pixels
            height: Height dalam pixels
        """
        self.transaction_service = transaction_service
        self.width = width
        self.height = height
        
        # Create frame
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self._create_widgets()
        self._load_transactions()
        
        logger.info("TransactionViewer initialized")
    
    def _create_widgets(self):
        """Create viewer widgets."""
        # Filter frame
        filter_frame = ttk.LabelFrame(self.frame, text="Filter", padding=10)
        filter_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Date range filter
        ttk.Label(filter_frame, text="From:").pack(side=tk.LEFT, padx=5)
        self.from_date = ttk.Entry(filter_frame, width=12)
        self.from_date.pack(side=tk.LEFT, padx=5)
        self.from_date.insert(0, (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'))
        
        ttk.Label(filter_frame, text="To:").pack(side=tk.LEFT, padx=5)
        self.to_date = ttk.Entry(filter_frame, width=12)
        self.to_date.pack(side=tk.LEFT, padx=5)
        self.to_date.insert(0, datetime.now().strftime('%Y-%m-%d'))
        
        # Payment method filter
        ttk.Label(filter_frame, text="Method:").pack(side=tk.LEFT, padx=5)
        self.method_combo = ttk.Combobox(filter_frame, width=12, values=['All', 'cash', 'transfer', 'card', 'check'])
        self.method_combo.pack(side=tk.LEFT, padx=5)
        self.method_combo.set('All')
        
        # Buttons
        ttk.Button(
            filter_frame,
            text="Search",
            command=self._on_search
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            filter_frame,
            text="Clear Filters",
            command=self._on_clear_filters
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            filter_frame,
            text="Export",
            command=self._on_export
        ).pack(side=tk.LEFT, padx=5)
        
        # Treeview
        treeview_frame = ttk.Frame(self.frame)
        treeview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(treeview_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.treeview = ttk.Treeview(
            treeview_frame,
            columns=('ID', 'Date', 'Cashier', 'Items', 'Subtotal', 'Discount', 'Tax', 'Total', 'Method', 'Status'),
            height=20,
            yscrollcommand=scrollbar.set
        )
        scrollbar.config(command=self.treeview.yview)
        
        # Configure columns
        self.treeview.column('#0', width=0)
        self.treeview.column('ID', anchor=tk.W, width=50)
        self.treeview.column('Date', anchor=tk.W, width=120)
        self.treeview.column('Cashier', anchor=tk.W, width=100)
        self.treeview.column('Items', anchor=tk.CENTER, width=60)
        self.treeview.column('Subtotal', anchor=tk.RIGHT, width=100)
        self.treeview.column('Discount', anchor=tk.RIGHT, width=80)
        self.treeview.column('Tax', anchor=tk.RIGHT, width=80)
        self.treeview.column('Total', anchor=tk.RIGHT, width=100)
        self.treeview.column('Method', anchor=tk.CENTER, width=80)
        self.treeview.column('Status', anchor=tk.CENTER, width=80)
        
        # Headings
        self.treeview.heading('#0', text='')
        self.treeview.heading('ID', text='ID')
        self.treeview.heading('Date', text='Date')
        self.treeview.heading('Cashier', text='Cashier')
        self.treeview.heading('Items', text='Items')
        self.treeview.heading('Subtotal', text='Subtotal')
        self.treeview.heading('Discount', text='Discount')
        self.treeview.heading('Tax', text='Tax')
        self.treeview.heading('Total', text='Total')
        self.treeview.heading('Method', text='Method')
        self.treeview.heading('Status', text='Status')
        
        self.treeview.pack(fill=tk.BOTH, expand=True)
        
        # Double-click untuk view details
        self.treeview.bind('<Double-1>', self._on_row_double_click)
        
        # Status bar
        self.status_label = ttk.Label(self.frame, text="Ready", relief=tk.SUNKEN)
        self.status_label.pack(fill=tk.X, padx=5, pady=5)
    
    def _load_transactions(self):
        """Load transactions dari service."""
        try:
            self.status_label.config(text="Loading transactions...")
            
            from_date = self.from_date.get()
            to_date = self.to_date.get()
            
            transactions = self.transaction_service.get_transactions_by_date(from_date, to_date)
            
            # Clear treeview
            for item in self.treeview.get_children():
                self.treeview.delete(item)
            
            # Add transactions
            for trans in transactions:
                values = (
                    trans.id,
                    trans.tanggal.strftime('%Y-%m-%d %H:%M:%S') if hasattr(trans.tanggal, 'strftime') else str(trans.tanggal),
                    trans.username,
                    trans.total_items,
                    f"Rp {trans.subtotal:,}",
                    f"Rp {trans.discount:,}",
                    f"Rp {trans.tax:,}",
                    f"Rp {trans.total:,}",
                    trans.metode_bayar,
                    trans.status
                )
                self.treeview.insert('', tk.END, values=values)
            
            self.status_label.config(text=f"Loaded {len(transactions)} transactions")
            logger.info(f"Loaded {len(transactions)} transactions")
        
        except Exception as e:
            messagebox.showerror("Error", f"Gagal load transactions: {e}")
            logger.error(f"Error loading transactions: {e}")
            self.status_label.config(text=f"Error: {e}")
    
    def _on_search(self):
        """Handle search button click."""
        self._load_transactions()
    
    def _on_clear_filters(self):
        """Clear filter fields."""
        self.from_date.delete(0, tk.END)
        self.from_date.insert(0, (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'))
        
        self.to_date.delete(0, tk.END)
        self.to_date.insert(0, datetime.now().strftime('%Y-%m-%d'))
        
        self.method_combo.set('All')
        
        self._load_transactions()
    
    def _on_export(self):
        """Export transactions to file."""
        try:
            from_date = self.from_date.get()
            to_date = self.to_date.get()
            
            transactions = self.transaction_service.get_transactions_by_date(from_date, to_date)
            
            output_file = f"transactions_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            
            with open(output_file, 'w') as f:
                f.write(f"Transaction Export Report\n")
                f.write(f"Period: {from_date} to {to_date}\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 100 + "\n\n")
                
                for trans in transactions:
                    f.write(f"ID: {trans.id}\n")
                    f.write(f"Date: {trans.tanggal}\n")
                    f.write(f"Cashier: {trans.username}\n")
                    f.write(f"Items: {trans.total_items}\n")
                    f.write(f"Subtotal: Rp {trans.subtotal:,}\n")
                    f.write(f"Discount: Rp {trans.discount:,}\n")
                    f.write(f"Tax: Rp {trans.tax:,}\n")
                    f.write(f"Total: Rp {trans.total:,}\n")
                    f.write(f"Method: {trans.metode_bayar}\n")
                    f.write(f"Status: {trans.status}\n")
                    f.write("-" * 100 + "\n\n")
            
            messagebox.showinfo("Sukses", f"Data exported ke {output_file}")
            logger.info(f"Transactions exported ke {output_file}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Gagal export: {e}")
            logger.error(f"Error exporting transactions: {e}")
    
    def _on_row_double_click(self, event):
        """Handle row double-click untuk view details."""
        selection = self.treeview.selection()
        if selection:
            item = selection[0]
            values = self.treeview.item(item)['values']
            trans_id = values[0]
            
            trans = self.transaction_service.get_transaction(trans_id)
            if trans:
                details = f"""
Transaction Details:
==================
ID: {trans.id}
Date: {trans.tanggal}
Cashier: {trans.username}
Items: {trans.total_items}
Subtotal: Rp {trans.subtotal:,}
Discount: Rp {trans.discount:,}
Tax: Rp {trans.tax:,}
Total: Rp {trans.total:,}
Payment Method: {trans.metode_bayar}
Status: {trans.status}
Notes: {trans.catatan}
"""
                messagebox.showinfo("Transaction Details", details)
