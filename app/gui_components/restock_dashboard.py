# ============================================================================
# RESTOCK_DASHBOARD.PY - Restock Recommendations Dashboard Component
# ============================================================================
# Fungsi: Tkinter widget untuk view restock recommendations
# Responsibilitas: Display restock data, create purchase orders, export
# ============================================================================

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict, Any
from datetime import datetime
from app.ai.smart_restock import SmartRestock
from app.services.product_service import ProductService
from logger_config import get_logger

logger = get_logger(__name__)


class RestockDashboard:
    """
    Restock recommendations dashboard component.
    
    Features:
    - Display critical/low/ok stock items
    - Show restock quantity recommendations
    - Create purchase orders
    - Export restock list
    """
    
    def __init__(
        self,
        parent: tk.Widget,
        product_service: ProductService,
        restock_service: SmartRestock,
        width: int = 1000,
        height: int = 500
    ):
        """
        Init RestockDashboard.
        
        Args:
            parent: Parent tkinter widget
            product_service: ProductService instance
            restock_service: SmartRestock instance
            width: Width dalam pixels
            height: Height dalam pixels
        """
        self.product_service = product_service
        self.restock_service = restock_service
        self.width = width
        self.height = height
        
        # Create frame
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self._create_widgets()
        self._refresh_recommendations()
        
        logger.info("RestockDashboard initialized")
    
    def _create_widgets(self):
        """Create dashboard widgets."""
        # Control frame
        control_frame = ttk.LabelFrame(self.frame, text="Controls", padding=10)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Threshold controls
        ttk.Label(control_frame, text="Low Stock Threshold:").pack(side=tk.LEFT, padx=5)
        self.low_threshold = ttk.Spinbox(control_frame, from_=1, to=100, width=5)
        self.low_threshold.pack(side=tk.LEFT, padx=5)
        self.low_threshold.set(10)
        
        ttk.Label(control_frame, text="Critical Stock Threshold:").pack(side=tk.LEFT, padx=5)
        self.critical_threshold = ttk.Spinbox(control_frame, from_=1, to=50, width=5)
        self.critical_threshold.pack(side=tk.LEFT, padx=5)
        self.critical_threshold.set(5)
        
        # Buttons
        ttk.Button(
            control_frame,
            text="Refresh",
            command=self._refresh_recommendations
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            control_frame,
            text="Create PO",
            command=self._on_create_po
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            control_frame,
            text="Export",
            command=self._on_export
        ).pack(side=tk.LEFT, padx=5)
        
        # Notebook untuk tabs
        self.notebook = ttk.Notebook(self.frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Critical tab
        critical_frame = ttk.Frame(self.notebook)
        self.notebook.add(critical_frame, text="🔴 Critical (Immediate)")
        self._create_tab(critical_frame, 'critical')
        self.critical_treeview = self.last_treeview
        
        # Low stock tab
        low_frame = ttk.Frame(self.notebook)
        self.notebook.add(low_frame, text="🟡 Low Stock (Soon)")
        self._create_tab(low_frame, 'low')
        self.low_treeview = self.last_treeview
        
        # OK tab
        ok_frame = ttk.Frame(self.notebook)
        self.notebook.add(ok_frame, text="🟢 OK Stock")
        self._create_tab(ok_frame, 'ok')
        self.ok_treeview = self.last_treeview
        
        # Status bar
        self.status_label = ttk.Label(self.frame, text="Ready", relief=tk.SUNKEN)
        self.status_label.pack(fill=tk.X, padx=5, pady=5)
    
    def _create_tab(self, parent: tk.Widget, status: str):
        """Create tab dengan treeview."""
        # Scrollbar
        scrollbar = ttk.Scrollbar(parent)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Treeview
        treeview = ttk.Treeview(
            parent,
            columns=('Kode', 'Nama', 'Current', 'Harga', 'Total Value', 'Status'),
            height=20,
            yscrollcommand=scrollbar.set
        )
        scrollbar.config(command=treeview.yview)
        
        # Configure columns
        treeview.column('#0', width=0)
        treeview.column('Kode', anchor=tk.W, width=80)
        treeview.column('Nama', anchor=tk.W, width=250)
        treeview.column('Current', anchor=tk.CENTER, width=80)
        treeview.column('Harga', anchor=tk.RIGHT, width=100)
        treeview.column('Total Value', anchor=tk.RIGHT, width=120)
        treeview.column('Status', anchor=tk.CENTER, width=80)
        
        # Headings
        treeview.heading('#0', text='')
        treeview.heading('Kode', text='Kode')
        treeview.heading('Nama', text='Product Name')
        treeview.heading('Current', text='Current Qty')
        treeview.heading('Harga', text='Price (Rp)')
        treeview.heading('Total Value', text='Total Value (Rp)')
        treeview.heading('Status', text='Status')
        
        treeview.pack(fill=tk.BOTH, expand=True)
        
        self.last_treeview = treeview
        self.last_treeview._status = status
    
    def _refresh_recommendations(self):
        """Refresh restock recommendations dari SmartRestock service."""
        try:
            self.status_label.config(text="Fetching recommendations...")
            
            critical_threshold = int(self.critical_threshold.get())
            low_threshold = int(self.low_threshold.get())
            
            # Get recommendations
            recommendations = self.restock_service.get_restock_recommendations(
                low_stock_threshold=low_threshold,
                critical_stock_threshold=critical_threshold
            )
            
            # Clear treeviews
            for treeview in [self.critical_treeview, self.low_treeview, self.ok_treeview]:
                for item in treeview.get_children():
                    treeview.delete(item)
            
            # Populate treeviews
            for status_type, items in recommendations.items():
                if status_type == 'last_updated':
                    continue
                
                if status_type == 'critical':
                    treeview = self.critical_treeview
                elif status_type == 'low':
                    treeview = self.low_treeview
                else:
                    treeview = self.ok_treeview
                
                for item in items:
                    values = (
                        item['kode'],
                        item['nama'],
                        item['current_stock'],
                        f"Rp {item['harga']:,}",
                        f"Rp {item['current_stock'] * item['harga']:,}",
                        status_type.upper()
                    )
                    treeview.insert('', tk.END, values=values)
            
            critical_count = len(recommendations.get('critical', []))
            low_count = len(recommendations.get('low', []))
            ok_count = len(recommendations.get('ok', []))
            
            self.status_label.config(
                text=f"Critical: {critical_count} | Low: {low_count} | OK: {ok_count}"
            )
            logger.info(f"Restock recommendations refreshed: {critical_count} critical, {low_count} low")
        
        except Exception as e:
            messagebox.showerror("Error", f"Gagal fetch recommendations: {e}")
            logger.error(f"Error fetching restock recommendations: {e}")
            self.status_label.config(text=f"Error: {e}")
    
    def _on_create_po(self):
        """Create purchase order dari critical items."""
        try:
            # Get critical items from critical treeview
            items = []
            for item in self.critical_treeview.get_children():
                values = self.critical_treeview.item(item)['values']
                items.append({
                    'kode': values[0],
                    'nama': values[1],
                    'current_qty': int(values[2]),
                    'harga': int(values[3].replace('Rp ', '').replace(',', ''))
                })
            
            if not items:
                messagebox.showinfo("Info", "Tidak ada critical items untuk create PO")
                return
            
            po_file = f"po_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            
            with open(po_file, 'w') as f:
                f.write("PURCHASE ORDER\n")
                f.write(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 80 + "\n\n")
                f.write("Critical Items to Order:\n")
                f.write("-" * 80 + "\n")
                
                total_value = 0
                for item in items:
                    # Recommend to order 50 units atau 2x current qty
                    recommend_qty = max(50, item['current_qty'] * 2)
                    item_total = recommend_qty * item['harga']
                    total_value += item_total
                    
                    f.write(f"{item['kode']:20} {item['nama']:30} {recommend_qty:5} units @ Rp {item['harga']:10,} = Rp {item_total:15,}\n")
                
                f.write("-" * 80 + "\n")
                f.write(f"TOTAL: Rp {total_value:,}\n\n")
                f.write("Notes: This is an auto-generated PO. Adjust quantities as needed.\n")
            
            messagebox.showinfo("Sukses", f"PO created: {po_file}")
            logger.info(f"PO created: {po_file}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Gagal create PO: {e}")
            logger.error(f"Error creating PO: {e}")
    
    def _on_export(self):
        """Export restock recommendations to file."""
        try:
            export_file = f"restock_recommendations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            
            with open(export_file, 'w') as f:
                f.write("RESTOCK RECOMMENDATIONS REPORT\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 100 + "\n\n")
                
                # Critical
                f.write("CRITICAL ITEMS (Immediate Order Required):\n")
                f.write("-" * 100 + "\n")
                for item in self.critical_treeview.get_children():
                    values = self.critical_treeview.item(item)['values']
                    f.write(f"{values[0]:20} {values[1]:30} Current: {values[2]:5} {values[4]}\n")
                f.write("\n")
                
                # Low
                f.write("LOW STOCK ITEMS (Order Soon):\n")
                f.write("-" * 100 + "\n")
                for item in self.low_treeview.get_children():
                    values = self.low_treeview.item(item)['values']
                    f.write(f"{values[0]:20} {values[1]:30} Current: {values[2]:5} {values[4]}\n")
                f.write("\n")
                
                f.write("=" * 100 + "\n")
                f.write("End of Report\n")
            
            messagebox.showinfo("Sukses", f"Recommendations exported ke {export_file}")
            logger.info(f"Recommendations exported ke {export_file}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Gagal export: {e}")
            logger.error(f"Error exporting recommendations: {e}")
