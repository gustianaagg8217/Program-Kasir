# ============================================================================
# GUI_MAIN.PY - Point of Sale (POS) System - GUI Interface (Tkinter)
# ============================================================================
# Fungsi: GUI modern dan user-friendly untuk sistem POS
# Fitur: Dashboard, Produk, Transaksi, Laporan, dengan antarmuka yang intuitif
# ============================================================================

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime
from tkcalendar import DateEntry
import os
import sys

# Import semua modules dari sistem POS
from database import DatabaseManager
from models import ProductManager, ValidationError, format_rp
from transaction import TransactionService, TransactionHandler, ReceiptManager
from laporan import ReportGenerator, ReportFormatter, CSVExporter
from telegram_bot import POSTelegramBot, TelegramConfigManager, TELEGRAM_AVAILABLE

# ============================================================================
# COLOR SCHEME & STYLING
# ============================================================================

COLORS = {
    'primary': '#2E86AB',      # Biru
    'secondary': '#A23B72',    # Ungu
    'success': '#38A169',      # Hijau
    'danger': '#DC2626',       # Merah
    'warning': '#F59E0B',      # Oranye
    'info': '#3B82F6',         # Biru muda
    'bg_main': '#F8FAFC',      # Abu-abu terang
    'bg_card': '#FFFFFF',      # Putih
    'text_primary': '#1E293B', # Hitam gelap
    'text_secondary': '#64748B', # Abu-abu
    'border': '#E2E8F0',       # Abu-abu border
}

FONTS = {
    'title': ('Segoe UI', 18, 'bold'),
    'heading': ('Segoe UI', 14, 'bold'),
    'subheading': ('Segoe UI', 12, 'bold'),
    'normal': ('Segoe UI', 10),
    'small': ('Segoe UI', 9),
    'mono': ('Courier New', 10),
}

# ============================================================================
# MAIN GUI APPLICATION
# ============================================================================

class POSGUIApplication(tk.Tk):
    """Main GUI Application untuk sistem POS."""
    
    def __init__(self):
        """Inisialisasi aplikasi GUI."""
        super().__init__()
        
        self.title("🛒 Sistem POS - Toko Accessories G-LIES")
        self.geometry("1200x700")
        self.configure(bg=COLORS['bg_main'])
        
        # Minimize to system tray style (maximize window)
        try:
            self.state('zoomed')  # Windows
        except:
            self.state('normal')
        
        # Initialize backend
        self._init_backend()
        
        # Setup UI
        self._setup_styles()
        self._create_widgets()
        
        # Center window on screen
        self.update_idletasks()
        
    def _init_backend(self):
        """Inisialisasi backend POS System."""
        try:
            self.db = DatabaseManager()
            self.product_manager = ProductManager(self.db)
            self.transaction_handler = TransactionHandler(self.db)
            self.report_generator = ReportGenerator(self.db)
            self.report_formatter = ReportFormatter()
            self.csv_exporter = CSVExporter()
            
            # Initialize Telegram Bot
            self.telegram_bot = None
            if TELEGRAM_AVAILABLE:
                try:
                    self.telegram_bot = POSTelegramBot()
                except Exception as e:
                    print(f"⚠️ Telegram bot init failed: {e}")
            
            self.current_transaction = None
        except Exception as e:
            messagebox.showerror("Error", f"Gagal inisialisasi sistem: {e}")
            sys.exit(1)
    
    def _setup_styles(self):
        """Setup custom ttk styles."""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors
        style.configure('TFrame', background=COLORS['bg_main'])
        style.configure('TLabel', background=COLORS['bg_main'], font=FONTS['normal'])
        style.configure('TButton', font=FONTS['normal'])
        
        # Primary button
        style.configure('Primary.TButton', font=FONTS['normal'])
        
        # Custom style untuk sidebar
        style.configure('Sidebar.TButton', 
                       font=FONTS['normal'],
                       padding=15)
        
        # Custom style untuk header
        style.configure('Header.TLabel',
                       font=FONTS['title'],
                       foreground=COLORS['text_primary'],
                       background=COLORS['bg_main'])
    
    def _create_widgets(self):
        """Create main widgets."""
        # Main container
        main_container = ttk.Frame(self)
        main_container.pack(fill='both', expand=True)
        
        # Create sidebar
        self.sidebar = self._create_sidebar(main_container)
        self.sidebar.pack(side='left', fill='y')
        
        # Create main content area
        self.content_area = ttk.Frame(main_container)
        self.content_area.pack(side='right', fill='both', expand=True, padx=10, pady=10)
        
        # Show landing page (Dashboard)
        self.show_dashboard()
    
    def _create_sidebar(self, parent):
        """Create navigation sidebar."""
        sidebar = ttk.Frame(parent, width=200)
        sidebar.pack(side='left', fill='y', ipady=20)
        
        # Logo/Title
        logo_label = ttk.Label(
            sidebar, 
            text="📊 POS SYSTEM", 
            font=FONTS['heading'],
            foreground=COLORS['primary']
        )
        logo_label.pack(pady=20)
        
        separator = ttk.Separator(sidebar, orient='horizontal')
        separator.pack(fill='x', padx=10)
        
        # Menu buttons
        menu_items = [
            ("🏠 Dashboard", self.show_dashboard),
            ("📦 Produk", self.show_products),
            ("🛒 Transaksi", self.show_transaction),
            ("📊 Laporan", self.show_reports),
            ("🤖 Telegram Bot", self.show_telegram),
            ("⚙️ Settings", self.show_settings),
            ("❌ Keluar", self.quit),
        ]
        
        for label, command in menu_items:
            btn = ttk.Button(
                sidebar,
                text=label,
                command=command,
                width=20
            )
            btn.pack(pady=5, padx=10, fill='x')
        
        return sidebar
    
    def _clear_content(self):
        """Clear content area."""
        for widget in self.content_area.winfo_children():
            widget.destroy()
    
    # ========================================================================
    # DASHBOARD PAGE
    # ========================================================================
    
    def show_dashboard(self):
        """Show dashboard page."""
        self._clear_content()
        
        # Header
        header = ttk.Label(
            self.content_area,
            text="📊 Dashboard",
            font=FONTS['title'],
            foreground=COLORS['primary']
        )
        header.pack(pady=10)
        
        # Stats cards container
        stats_frame = ttk.Frame(self.content_area)
        stats_frame.pack(fill='x', pady=10)
        
        # Get stats
        stats = self.db.get_database_stats()
        dashboard_data = self.report_generator.get_dashboard_summary()
        
        # Create stat cards
        cards_data = [
            ("📦 Total Produk", str(stats['total_products']), COLORS['info']),
            ("💰 Penjualan Hari Ini", format_rp(dashboard_data['hari_ini']['total_penjualan']), COLORS['success']),
            ("🔢 Transaksi Hari Ini", str(dashboard_data['hari_ini']['total_transaksi']), COLORS['warning']),
            ("📈 Rata-rata Transaksi", format_rp(int(dashboard_data['hari_ini']['rata_rata'])), COLORS['secondary']),
        ]
        
        for title, value, color in cards_data:
            self._create_stat_card(stats_frame, title, value, color)
        
        # Recent transactions section
        self._create_recent_transactions_section()
        
        # Action buttons
        actions_frame = ttk.Frame(self.content_area)
        actions_frame.pack(fill='x', pady=20)
        
        action_btns = [
            ("🛒 Proses Transaksi Baru", self.show_transaction),
            ("📦 Tambah Produk", self.show_add_product),
            ("📊 Lihat Laporan", self.show_reports),
        ]
        
        for label, command in action_btns:
            btn = ttk.Button(
                actions_frame,
                text=label,
                command=command,
                width=30
            )
            btn.pack(side='left', padx=5)
    
    def _create_stat_card(self, parent, title, value, color):
        """Create a stat card."""
        card = tk.Frame(parent, bg=color, relief='flat', bd=1)
        card.pack(side='left', padx=10, pady=5, fill='both', expand=True)
        
        title_label = tk.Label(
            card,
            text=title,
            font=FONTS['small'],
            bg=color,
            fg='white',
            padx=15,
            pady=5
        )
        title_label.pack()
        
        value_label = tk.Label(
            card,
            text=value,
            font=FONTS['heading'],
            bg=color,
            fg='white',
            padx=15,
            pady=10
        )
        value_label.pack()
    
    def _create_recent_transactions_section(self):
        """Create recent transactions display."""
        section_frame = tk.Frame(self.content_area, bg=COLORS['bg_card'], relief='flat', bd=1)
        section_frame.pack(fill='both', expand=True, pady=10)
        
        # Header
        header = tk.Label(
            section_frame,
            text="📋 Transaksi Terakhir",
            font=FONTS['subheading'],
            bg=COLORS['bg_card'],
            fg=COLORS['primary']
        )
        header.pack(anchor='w', padx=15, pady=10)
        
        # Get recent transactions from database
        recent_trans = self.report_generator.get_laporan_harian()
        
        if not recent_trans or recent_trans.get('transactions', []) == []:
            empty_label = tk.Label(
                section_frame,
                text="Belum ada transaksi hari ini",
                font=FONTS['normal'],
                bg=COLORS['bg_card'],
                fg=COLORS['text_secondary']
            )
            empty_label.pack(pady=20)
            return
        
        # Create treeview
        columns = ('No', 'ID', 'Waktu', 'Total', 'Kembalian')
        tree = ttk.Treeview(section_frame, columns=columns, height=8, show='headings')
        
        # Define column headings and widths
        widths = [30, 60, 150, 100, 100]
        for col, width in zip(columns, widths):
            tree.heading(col, text=col)
            tree.column(col, width=width)
        
        # Add data (store transaction_ids in a mapping)
        trans_list = recent_trans.get('transactions', [])
        self._trans_id_map = {}  # Store mapping for click handler
        for i, trans in enumerate(trans_list[-10:], 1):
            item_id = tree.insert('', 'end', values=(
                str(i),
                trans['id'],
                trans['tanggal'],
                format_rp(trans['total']),
                format_rp(trans['kembalian'])
            ))
            self._trans_id_map[item_id] = trans['id']  # Map tree item to transaction ID
        
        # Add click handler
        tree.bind('<Double-1>', lambda e: self._show_transaction_detail(tree, e))
        
        # Add hint label
        hint_label = tk.Label(
            section_frame,
            text="💡 Double-click untuk melihat detail transaksi",
            font=FONTS['small'],
            bg=COLORS['bg_card'],
            fg=COLORS['text_secondary']
        )
        hint_label.pack(anchor='w', padx=15, pady=5)
        
        tree.pack(fill='both', expand=True, padx=15, pady=10)
    
    def _show_transaction_detail(self, tree, event):
        """Show transaction detail dialog when double-clicked."""
        selection = tree.selection()
        if not selection:
            return
        
        item_id = selection[0]
        transaction_id = self._trans_id_map.get(item_id)
        
        if not transaction_id:
            return
        
        # Get transaction details from database
        trans_detail = self.db.get_transaction(transaction_id)
        
        if not trans_detail:
            messagebox.showerror("Error", "Transaksi tidak ditemukan")
            return
        
        trans = trans_detail['transaction']
        items = trans_detail['items']
        
        # Create detail dialog
        dialog = tk.Toplevel(self)
        dialog.title(f"📝 Detail Transaksi - ID {transaction_id}")
        dialog.geometry("600x500")
        dialog.configure(bg=COLORS['bg_main'])
        
        # Header
        header = tk.Label(
            dialog,
            text=f"Transaksi ID: {transaction_id}",
            font=FONTS['heading'],
            bg=COLORS['bg_main'],
            fg=COLORS['primary']
        )
        header.pack(pady=10)
        
        # Info section
        info_frame = tk.Frame(dialog, bg=COLORS['bg_card'], relief='flat', bd=1)
        info_frame.pack(fill='x', padx=10, pady=5)
        
        info_text = f"""
Tanggal/Waktu   : {trans['tanggal']}
        """
        
        info_label = tk.Label(
            info_frame,
            text=info_text,
            font=FONTS['small'],
            bg=COLORS['bg_card'],
            justify='left'
        )
        info_label.pack(anchor='w', padx=10, pady=10)
        
        # Items section
        items_frame = ttk.LabelFrame(dialog, text="📦 Item Transaksi", padding=10)
        items_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Create treeview untuk items detail
        columns = ('No', 'Produk', 'Qty', 'Harga', 'Subtotal')
        items_tree = ttk.Treeview(items_frame, columns=columns, height=10, show='headings')
        
        items_tree.heading('No', text='No')
        items_tree.heading('Produk', text='Produk')
        items_tree.heading('Qty', text='Qty')
        items_tree.heading('Harga', text='Harga Satuan')
        items_tree.heading('Subtotal', text='Subtotal')
        
        items_tree.column('No', width=30)
        items_tree.column('Produk', width=150)
        items_tree.column('Qty', width=50)
        items_tree.column('Harga', width=100)
        items_tree.column('Subtotal', width=100)
        
        # Add items
        for idx, item in enumerate(items, 1):
            items_tree.insert('', 'end', values=(
                str(idx),
                item.get('nama', 'N/A'),
                str(item.get('qty', 0)),
                format_rp(item.get('harga_satuan', 0)),
                format_rp(item.get('subtotal', 0))
            ))
        
        scrollbar = ttk.Scrollbar(items_frame, orient='vertical', command=items_tree.yview)
        items_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        items_tree.pack(fill='both', expand=True)
        
        # Summary section
        summary_frame = tk.Frame(dialog, bg=COLORS['bg_card'], relief='flat', bd=1)
        summary_frame.pack(fill='x', padx=10, pady=5)
        
        summary_text = f"""
Total Belanja    : {format_rp(trans['total'])}
Pembayaran       : {format_rp(trans['bayar'])}
Kembalian        : {format_rp(trans['kembalian'])}
        """
        
        summary_label = tk.Label(
            summary_frame,
            text=summary_text,
            font=FONTS['mono'],
            bg=COLORS['bg_card'],
            justify='left'
        )
        summary_label.pack(anchor='w', padx=10, pady=10)
        
        # Button frame
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill='x', padx=10, pady=10)
        
        print_btn = ttk.Button(
            btn_frame,
            text="🖨️ Print Resi",
            command=lambda: self._print_transaction_receipt(trans, items)
        )
        print_btn.pack(side='left', padx=5)
        
        close_btn = ttk.Button(dialog, text="Tutup", command=dialog.destroy)
        close_btn.pack(side='left', padx=5)
    
    def _generate_receipt_text(self, trans, items):
        """Generate receipt text format."""
        receipt = []
        receipt.append("=" * 40)
        receipt.append("TOKO ACCESSORIES G-LIES".center(40))
        receipt.append("Jl. Majalaya, Solokanjeruk, Bandung".center(40))
        receipt.append("=" * 40)
        receipt.append("")
        receipt.append(f"Transaksi ID  : {trans['id']}")
        receipt.append(f"Tanggal/Waktu : {trans['tanggal']}")
        receipt.append("-" * 40)
        receipt.append("Daftar Item:")
        receipt.append("-" * 40)
        
        for i, item in enumerate(items, 1):
            product_name = item.get('nama', 'N/A')[:25]  # Truncate long names
            qty = item.get('qty', 0)
            harga = item.get('harga_satuan', 0)
            subtotal = item.get('subtotal', 0)
            
            # Format: "Produk      Qty x Harga = Subtotal"
            receipt.append(f"{i}. {product_name}")
            receipt.append(f"   {qty}x {format_rp(harga)} = {format_rp(subtotal)}")
        
        receipt.append("-" * 40)
        receipt.append(f"Total Belanja  : {format_rp(trans['total'])}")
        receipt.append(f"Pembayaran     : {format_rp(trans['bayar'])}")
        receipt.append(f"Kembalian      : {format_rp(trans['kembalian'])}")
        receipt.append("=" * 40)
        receipt.append("Terima Kasih".center(40))
        receipt.append("=" * 40)
        
        return "\n".join(receipt)
    
    def _print_transaction_receipt(self, trans, items):
        """Print transaction receipt."""
        receipt_text = self._generate_receipt_text(trans, items)
        
        # Create print preview dialog
        preview_dialog = tk.Toplevel(self)
        preview_dialog.title("🖨️ Preview Resi")
        preview_dialog.geometry("500x600")
        preview_dialog.configure(bg=COLORS['bg_main'])
        
        # Header
        header = tk.Label(
            preview_dialog,
            text="Preview Resi",
            font=FONTS['heading'],
            bg=COLORS['bg_main'],
            fg=COLORS['primary']
        )
        header.pack(pady=10)
        
        # Receipt text display
        text_frame = ttk.Frame(preview_dialog)
        text_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        receipt_display = tk.Text(text_frame, font=FONTS['mono'], height=25, width=50)
        receipt_display.insert('1.0', receipt_text)
        receipt_display.config(state='disabled')  # Read-only
        
        scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=receipt_display.yview)
        receipt_display.config(yscroll=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        receipt_display.pack(fill='both', expand=True)
        
        # Buttons
        btn_frame = ttk.Frame(preview_dialog)
        btn_frame.pack(fill='x', padx=10, pady=10)
        
        def print_receipt():
            """Print resi ke printer."""
            try:
                # Save to temporary file
                import tempfile
                import subprocess
                
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as f:
                    f.write(receipt_text)
                    temp_file = f.name
                
                # Print the file (Windows)
                subprocess.run(['notepad', '/p', temp_file], check=True)
                messagebox.showinfo("Sukses", "Resi sedang dicetak...")
                preview_dialog.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Gagal mencetak: {e}")
        
        def save_receipt():
            """Save resi ke file."""
            try:
                from tkinter import filedialog
                
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".txt",
                    filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                    initialfile=f"resi_{trans['id']}.txt"
                )
                
                if file_path:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(receipt_text)
                    messagebox.showinfo("Sukses", f"Resi disimpan ke:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Gagal menyimpan: {e}")
        
        print_resi_btn = ttk.Button(
            btn_frame,
            text="🖨️ Cetak",
            command=print_receipt
        )
        print_resi_btn.pack(side='left', padx=5)
        
        save_btn = ttk.Button(
            btn_frame,
            text="💾 Simpan",
            command=save_receipt
        )
        save_btn.pack(side='left', padx=5)
        
        close_btn = ttk.Button(
            btn_frame,
            text="❌ Tutup",
            command=preview_dialog.destroy
        )
        close_btn.pack(side='left', padx=5)
    
    
    
    # ========================================================================
    # PRODUCTS PAGE
    # ========================================================================
    
    def show_products(self):
        """Show products management page."""
        self._clear_content()
        
        # Header with action button
        header_frame = ttk.Frame(self.content_area)
        header_frame.pack(fill='x', pady=10)
        
        header_label = ttk.Label(
            header_frame,
            text="📦 Kelola Produk",
            font=FONTS['title'],
            foreground=COLORS['primary']
        )
        header_label.pack(side='left')
        
        add_btn = ttk.Button(
            header_frame,
            text="➕ Tambah Produk Baru",
            command=self.show_add_product
        )
        add_btn.pack(side='right')
        
        # Products table
        products = self.product_manager.list_products()
        
        if not products:
            empty_label = ttk.Label(
                self.content_area,
                text="Belum ada produk. Klik 'Tambah Produk' untuk menambahkan.",
                font=FONTS['normal'],
                foreground=COLORS['text_secondary']
            )
            empty_label.pack(pady=20)
            return
        
        # Create treeview with scrollbar
        tree_frame = ttk.Frame(self.content_area)
        tree_frame.pack(fill='both', expand=True, pady=10)
        
        columns = ('No', 'Kode', 'Nama', 'Harga', 'Stok', 'Aksi')
        tree = ttk.Treeview(tree_frame, columns=columns, height=15, show='headings')
        
        # Define column headings
        tree.heading('No', text='No')
        tree.heading('Kode', text='Kode Produk')
        tree.heading('Nama', text='Nama Produk')
        tree.heading('Harga', text='Harga')
        tree.heading('Stok', text='Stok')
        tree.heading('Aksi', text='Aksi')
        
        tree.column('No', width=30)
        tree.column('Kode', width=80)
        tree.column('Nama', width=250)
        tree.column('Harga', width=100)
        tree.column('Stok', width=60)
        tree.column('Aksi', width=120)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        tree.pack(fill='both', expand=True)
        
        # Add products to table
        for i, prod in enumerate(products, 1):
            tree.insert('', 'end', values=(
                str(i),
                prod.kode,
                prod.nama,
                format_rp(prod.harga),
                f"{prod.stok} pcs",
                "✏️ Edit | 🗑️ Hapus"
            ))
        
        # Add click handler for edit/delete
        tree.bind('<Double-1>', lambda e: self._handle_product_click(tree, products))
    
    def show_add_product(self):
        """Show add product dialog."""
        dialog = tk.Toplevel(self)
        dialog.title("➕ Tambah Produk Baru")
        dialog.geometry("400x400")
        dialog.configure(bg=COLORS['bg_main'])
        
        # Header
        header = tk.Label(
            dialog,
            text="Tambah Produk Baru",
            font=FONTS['heading'],
            bg=COLORS['bg_main'],
            fg=COLORS['primary']
        )
        header.pack(pady=10)
        
        # Form fields
        fields = {}
        
        form_frame = ttk.Frame(dialog)
        form_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        field_configs = [
            ("Kode Produk:", "kode"),
            ("Nama Produk:", "nama"),
            ("Harga (Rp):", "harga"),
            ("Stok Awal:", "stok"),
        ]
        
        for label_text, field_name in field_configs:
            label = ttk.Label(form_frame, text=label_text, font=FONTS['normal'])
            label.pack(anchor='w', pady=5)
            
            entry = ttk.Entry(form_frame, width=30)
            entry.pack(fill='x', pady=5)
            fields[field_name] = entry
        
        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill='x', padx=20, pady=15)
        
        def save_product():
            try:
                kode = fields['kode'].get().strip().upper()
                nama = fields['nama'].get().strip()
                harga = int(fields['harga'].get().strip())
                stok = int(fields['stok'].get().strip())
                
                if not all([kode, nama, harga, stok]):
                    messagebox.showwarning("Peringatan", "Semua field harus diisi!")
                    return
                
                if self.product_manager.add_product(kode, nama, harga, stok):
                    messagebox.showinfo("Sukses", f"Produk '{nama}' berhasil ditambahkan!")
                    dialog.destroy()
                    self.show_products()
                else:
                    messagebox.showerror("Error", "Gagal menambahkan produk")
            except ValueError:
                messagebox.showerror("Error", "Harga dan Stok harus berupa angka!")
        
        save_btn = ttk.Button(
            btn_frame,
            text="💾 Simpan",
            command=save_product
        )
        save_btn.pack(side='left', padx=5)
        
        cancel_btn = ttk.Button(
            btn_frame,
            text="❌ Batal",
            command=dialog.destroy
        )
        cancel_btn.pack(side='left', padx=5)
    
    def _handle_product_click(self, tree, products):
        """Handle product row click for edit/delete."""
        selection = tree.selection()
        if not selection:
            return
        
        item = tree.item(selection[0])
        values = item['values']
        product_kode = values[1]
        
        # Show options dialog
        dialog = tk.Toplevel(self)
        dialog.title(f"Kelola Produk - {product_kode}")
        dialog.geometry("300x150")
        dialog.configure(bg=COLORS['bg_main'])
        
        msg = tk.Label(
            dialog,
            text=f"Apa yang ingin Anda lakukan dengan produk {product_kode}?",
            font=FONTS['normal'],
            bg=COLORS['bg_main'],
            wraplength=250
        )
        msg.pack(pady=15)
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill='x', padx=20, pady=10)
        
        edit_btn = ttk.Button(
            btn_frame,
            text="✏️ Edit",
            command=lambda: self._show_edit_product_dialog(product_kode, dialog)
        )
        edit_btn.pack(side='left', padx=5)
        
        delete_btn = ttk.Button(
            btn_frame,
            text="🗑️ Hapus",
            command=lambda: self._delete_product(product_kode, dialog)
        )
        delete_btn.pack(side='left', padx=5)
    
    def _show_edit_product_dialog(self, kode, parent_dialog):
        """Show edit product dialog."""
        product = self.product_manager.get_product(kode)
        
        if not product:
            messagebox.showerror("Error", "Produk tidak ditemukan")
            return
        
        parent_dialog.destroy()
        
        dialog = tk.Toplevel(self)
        dialog.title(f"✏️ Edit Produk - {kode}")
        dialog.geometry("400x350")
        dialog.configure(bg=COLORS['bg_main'])
        
        # Form fields
        fields = {}
        
        form_frame = ttk.Frame(dialog)
        form_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        field_configs = [
            ("Nama Produk:", "nama", product.nama),
            ("Harga (Rp):", "harga", str(product.harga)),
            ("Stok:", "stok", str(product.stok)),
        ]
        
        for label_text, field_name, value in field_configs:
            label = ttk.Label(form_frame, text=label_text, font=FONTS['normal'])
            label.pack(anchor='w', pady=5)
            
            entry = ttk.Entry(form_frame, width=30)
            entry.insert(0, value)
            entry.pack(fill='x', pady=5)
            fields[field_name] = entry
        
        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill='x', padx=20, pady=15)
        
        def save_changes():
            try:
                update_data = {
                    'nama': fields['nama'].get().strip(),
                    'harga': int(fields['harga'].get().strip()),
                    'stok': int(fields['stok'].get().strip()),
                }
                
                if self.product_manager.update_product(kode, **update_data):
                    messagebox.showinfo("Sukses", "Produk berhasil diupdate!")
                    dialog.destroy()
                    self.show_products()
                else:
                    messagebox.showerror("Error", "Gagal mengupdate produk")
            except ValueError:
                messagebox.showerror("Error", "Input tidak valid!")
        
        save_btn = ttk.Button(
            btn_frame,
            text="💾 Simpan",
            command=save_changes
        )
        save_btn.pack(side='left', padx=5)
        
        cancel_btn = ttk.Button(
            btn_frame,
            text="❌ Batal",
            command=dialog.destroy
        )
        cancel_btn.pack(side='left', padx=5)
    
    def _delete_product(self, kode, parent_dialog):
        """Delete a product."""
        if messagebox.askyesno("Konfirmasi", f"Hapus produk {kode}?"):
            if self.product_manager.delete_product(kode):
                messagebox.showinfo("Sukses", "Produk berhasil dihapus!")
                parent_dialog.destroy()
                self.show_products()
            else:
                messagebox.showerror("Error", "Gagal menghapus produk")
    
    # ========================================================================
    # TRANSACTION PAGE
    # ========================================================================
    
    def show_transaction(self):
        """Show transaction page."""
        self._clear_content()
        
        # Header
        header = ttk.Label(
            self.content_area,
            text="🛒 Proses Transaksi",
            font=FONTS['title'],
            foreground=COLORS['primary']
        )
        header.pack(pady=10)
        
        # Main container with two columns
        main_frame = ttk.Frame(self.content_area)
        main_frame.pack(fill='both', expand=True, pady=10)
        
        # Left side - Product search and add
        left_frame = ttk.LabelFrame(main_frame, text="📦 Tambah Item", padding=10)
        left_frame.pack(side='left', fill='both', expand=True, padx=5)
        
        ttk.Label(left_frame, text="Cari Produk:", font=FONTS['normal']).pack(anchor='w', pady=5)
        
        self.product_search_var = tk.StringVar()
        search_entry = ttk.Combobox(
            left_frame,
            textvariable=self.product_search_var,
            width=30,
            state='normal'
        )
        search_entry.pack(fill='x', pady=5)
        
        # Populate combobox with products
        products = self.product_manager.list_products()
        product_options = [f"{p.kode} - {p.nama}" for p in products]
        search_entry['values'] = product_options
        
        ttk.Label(left_frame, text="Jumlah (qty):", font=FONTS['normal']).pack(anchor='w', pady=5)
        self.qty_var = tk.StringVar(value="1")
        qty_entry = ttk.Entry(left_frame, textvariable=self.qty_var, width=30)
        qty_entry.pack(fill='x', pady=5)
        
        add_item_btn = ttk.Button(
            left_frame,
            text="➕ Tambah Item",
            command=self._add_transaction_item
        )
        add_item_btn.pack(fill='x', pady=10)
        
        # Right side - Cart summary
        right_frame = ttk.LabelFrame(main_frame, text="🛒 Keranjang Belanja", padding=10)
        right_frame.pack(side='right', fill='both', expand=True, padx=5)
        
        # Cart items display
        self.cart_tree = ttk.Treeview(
            right_frame,
            columns=('No', 'Produk', 'Qty', 'Harga', 'Subtotal'),
            height=10,
            show='headings'
        )
        
        self.cart_tree.heading('No', text='No')
        self.cart_tree.heading('Produk', text='Produk')
        self.cart_tree.heading('Qty', text='Qty')
        self.cart_tree.heading('Harga', text='Harga')
        self.cart_tree.heading('Subtotal', text='Subtotal')
        
        self.cart_tree.column('No', width=30)
        self.cart_tree.column('Produk', width=150)
        self.cart_tree.column('Qty', width=50)
        self.cart_tree.column('Harga', width=100)
        self.cart_tree.column('Subtotal', width=100)
        
        self.cart_tree.pack(fill='both', expand=True, pady=10)
        
        # Cart summary
        summary_frame = ttk.Frame(right_frame)
        summary_frame.pack(fill='x', pady=10)
        
        ttk.Label(summary_frame, text="Total:", font=FONTS['subheading']).pack(anchor='w')
        self.total_label = ttk.Label(
            summary_frame,
            text="Rp 0",
            font=FONTS['heading'],
            foreground=COLORS['success']
        )
        self.total_label.pack(anchor='w')
        
        # Payment section
        payment_frame = ttk.LabelFrame(self.content_area, text="💳 Pembayaran", padding=10)
        payment_frame.pack(fill='x', padx=5, pady=10)
        
        ttk.Label(payment_frame, text="Jumlah Pembayaran:", font=FONTS['normal']).pack(side='left')
        self.payment_var = tk.StringVar()
        payment_entry = ttk.Entry(payment_frame, textvariable=self.payment_var, width=20)
        payment_entry.pack(side='left', padx=5)
        
        # Buttons
        btn_frame = ttk.Frame(self.content_area)
        btn_frame.pack(fill='x', padx=5, pady=10)
        
        process_btn = ttk.Button(
            btn_frame,
            text="✅ Proses Pembayaran",
            command=self._process_payment
        )
        process_btn.pack(side='left', padx=5)
        
        clear_btn = ttk.Button(
            btn_frame,
            text="❌ Batalkan",
            command=self._clear_transaction
        )
        clear_btn.pack(side='left', padx=5)
        
        # Start a new transaction
        self.transaction_handler.start_transaction()
        self._update_cart_display()
    
    def _add_transaction_item(self):
        """Add item to transaction."""
        search_text = self.product_search_var.get().strip()
        
        if not search_text:
            messagebox.showwarning("Peringatan", "Pilih produk terlebih dahulu!")
            return
        
        try:
            kode = search_text.split(' - ')[0]
            product = self.product_manager.get_product(kode)
            
            if not product:
                messagebox.showerror("Error", "Produk tidak ditemukan!")
                return
            
            qty = int(self.qty_var.get())
            
            if qty <= 0:
                messagebox.showwarning("Peringatan", "Jumlah harus lebih dari 0!")
                return
            
            if qty > product.stok:
                messagebox.showwarning("Peringatan", f"Stok tidak cukup! (Tersedia: {product.stok})")
                return
            
            self.transaction_handler.add_item(kode, qty)
            self._update_cart_display()
            self.product_search_var.set("")
            self.qty_var.set("1")
            
            messagebox.showinfo("Sukses", f"✅ {product.nama} ditambahkan ke keranjang!")
        except ValueError:
            messagebox.showerror("Error", "Jumlah harus berupa angka!")
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}")
    
    def _update_cart_display(self):
        """Update cart display."""
        # Clear existing items
        for item in self.cart_tree.get_children():
            self.cart_tree.delete(item)
        
        # Get transaction summary
        summary = self.transaction_handler.get_transaction_summary()
        
        if summary and summary['items_count'] > 0:
            items = self.transaction_handler.get_items()
            if items:  # Check if items is not None
                for i, item in enumerate(items, 1):
                    self.cart_tree.insert('', 'end', values=(
                        str(i),
                        item['nama'],  # Sudah tersimpan dengan benar
                        str(item['qty']),
                        format_rp(item['harga_satuan']),
                        format_rp(item['subtotal'])
                    ))
            
            # Update total
            self.total_label.config(text=format_rp(summary['total']))
        else:
            self.total_label.config(text="Rp 0")
    
    def _process_payment(self):
        """Process payment."""
        summary = self.transaction_handler.get_transaction_summary()
        
        if not summary or summary['items_count'] == 0:
            messagebox.showwarning("Peringatan", "Keranjang belanja kosong!")
            return
        
        try:
            bayar = int(self.payment_var.get())
            
            if bayar < summary['total']:
                messagebox.showwarning("Peringatan", f"Pembayaran kurang! (Total: {format_rp(summary['total'])})")
                return
            
            # Complete transaction
            trans_id = self.transaction_handler.complete_transaction(
                bayar,
                store_name="TOKO ACCESSORIES G-LIES",
                store_address="Jl. Majalaya, Solokanjeruk, Bandung"
            )
            
            if trans_id:
                kembalian = bayar - summary['total']
                messagebox.showinfo(
                    "Transaksi Selesai",
                    f"✅ Transaksi berhasil!\n\nID: {trans_id}\nTotal: {format_rp(summary['total'])}\nKembalian: {format_rp(kembalian)}"
                )
                self.show_transaction()
            else:
                messagebox.showerror("Error", "Gagal memproses transaksi!")
        except ValueError:
            messagebox.showerror("Error", "Jumlah pembayaran harus berupa angka!")
    
    def _clear_transaction(self):
        """Clear transaction."""
        if messagebox.askyesno("Konfirmasi", "Batalkan transaksi?"):
            self.transaction_handler.cancel_transaction()
            self.show_transaction()
    
    # ========================================================================
    # REPORTS PAGE
    # ========================================================================
    
    def show_reports(self):
        """Show reports page."""
        self._clear_content()
        
        # Header
        header = ttk.Label(
            self.content_area,
            text="📊 Laporan & Analisis",
            font=FONTS['title'],
            foreground=COLORS['primary']
        )
        header.pack(pady=10)
        
        # Tabs for different reports
        notebook = ttk.Notebook(self.content_area)
        notebook.pack(fill='both', expand=True, pady=10, padx=10)
        
        # Tab 1: Daily Report
        daily_frame = ttk.Frame(notebook)
        notebook.add(daily_frame, text="📅 Laporan Harian")
        self._create_daily_report_tab(daily_frame)
        
        # Tab 2: Period Report
        period_frame = ttk.Frame(notebook)
        notebook.add(period_frame, text="📆 Laporan Periode")
        self._create_period_report_tab(period_frame)
        
        # Tab 3: Best Selling
        bestselling_frame = ttk.Frame(notebook)
        notebook.add(bestselling_frame, text="🏆 Produk Terlaris")
        self._create_bestselling_tab(bestselling_frame)
        
        # Tab 4: Stock Info
        stock_frame = ttk.Frame(notebook)
        notebook.add(stock_frame, text="📦 Informasi Stok")
        self._create_stock_info_tab(stock_frame)
    
    def _create_daily_report_tab(self, parent):
        """Create daily report tab."""
        laporan = self.report_generator.get_laporan_harian()
        
        # Summary
        summary_frame = ttk.LabelFrame(parent, text="📊 Summary", padding=10)
        summary_frame.pack(fill='x', padx=10, pady=10)
        
        info_text = f"""
Total Penjualan     : {format_rp(laporan.get('total_penjualan', 0))}
Total Transaksi     : {laporan.get('total_transaksi', 0)}
Rata-rata Transaksi : {format_rp(int(laporan.get('rata_rata_transaksi', 0)))}
Total Item          : {laporan.get('total_item', 0)}
        """
        
        info_label = tk.Label(
            summary_frame,
            text=info_text,
            font=FONTS['mono'],
            justify='left',
            bg=COLORS['bg_card']
        )
        info_label.pack(anchor='w')
        
        # Transactions list
        trans_frame = ttk.LabelFrame(parent, text="📋 Daftar Transaksi", padding=10)
        trans_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        columns = ('No', 'ID', 'Total', 'Pembayaran', 'Kembalian')
        tree = ttk.Treeview(trans_frame, columns=columns, height=15, show='headings')
        
        tree.heading('No', text='No')
        tree.heading('ID', text='ID')
        tree.heading('Total', text='Total')
        tree.heading('Pembayaran', text='Pembayaran')
        tree.heading('Kembalian', text='Kembalian')
        
        tree.column('No', width=30)
        tree.column('ID', width=60)
        tree.column('Total', width=120)
        tree.column('Pembayaran', width=120)
        tree.column('Kembalian', width=120)
        
        for i, trans in enumerate(laporan.get('transactions', []), 1):
            tree.insert('', 'end', values=(
                str(i),
                trans['id'],
                format_rp(trans['total']),
                format_rp(trans['bayar']),
                format_rp(trans['kembalian'])
            ))
        
        scrollbar = ttk.Scrollbar(trans_frame, orient='vertical', command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        tree.pack(fill='both', expand=True)
    
    def _create_period_report_tab(self, parent):
        """Create period report tab."""
        # Date range selector
        selector_frame = ttk.LabelFrame(parent, text="Pilih Periode", padding=10)
        selector_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(selector_frame, text="Dari Tanggal:", font=FONTS['normal']).pack(side='left', padx=5)
        start_date = DateEntry(selector_frame, width=12)
        start_date.pack(side='left', padx=5)
        
        ttk.Label(selector_frame, text="Sampai Tanggal:", font=FONTS['normal']).pack(side='left', padx=5)
        end_date = DateEntry(selector_frame, width=12)
        end_date.pack(side='left', padx=5)
        
        result_text = tk.Text(parent, height=20, width=80, font=FONTS['mono'])
        result_text.pack(fill='both', expand=True, padx=10, pady=10)
        
        def show_report():
            try:
                # Get dates from DateEntry widget
                start_str = start_date.get_date().strftime('%Y-%m-%d')
                end_str = end_date.get_date().strftime('%Y-%m-%d')
                
                laporan = self.report_generator.get_laporan_periode(start_str, end_str)
                
                if laporan is None:
                    messagebox.showerror("Error", "Gagal mengambil data laporan. Periksa format tanggal.")
                    return
                
                result_text.config(state='normal')
                result_text.delete(1.0, 'end')
                formatted_report = self.report_formatter.format_laporan_periode(laporan)
                result_text.insert('end', formatted_report)
                result_text.config(state='disabled')
            except Exception as e:
                messagebox.showerror("Error", f"Error: {str(e)}")
        
        show_btn = ttk.Button(selector_frame, text="📊 Tampilkan Laporan", command=show_report)
        show_btn.pack(side='left', padx=5)
    
    def _create_bestselling_tab(self, parent):
        """Create best selling products tab."""
        produk_laris = self.report_generator.get_produk_terlaris(limit=20)
        
        columns = ('No', 'Produk', 'Terjual', 'Total Penjualan')
        tree = ttk.Treeview(parent, columns=columns, height=20, show='headings')
        
        tree.heading('No', text='No')
        tree.heading('Produk', text='Produk')
        tree.heading('Terjual', text='Qty Terjual')
        tree.heading('Total Penjualan', text='Total Penjualan')
        
        tree.column('No', width=30)
        tree.column('Produk', width=250)
        tree.column('Terjual', width=100)
        tree.column('Total Penjualan', width=150)
        
        for i, item in enumerate(produk_laris, 1):
            tree.insert('', 'end', values=(
                str(i),
                item['nama'],
                str(item['qty_terjual']),
                format_rp(item['total_penjualan'])
            ))
        
        scrollbar = ttk.Scrollbar(parent, orient='vertical', command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        tree.pack(fill='both', expand=True, padx=10, pady=10)
    
    def _create_stock_info_tab(self, parent):
        """Create stock info tab."""
        stok_list = self.report_generator.get_stok_summary()
        
        columns = ('No', 'Kode', 'Produk', 'Stok', 'Status')
        tree = ttk.Treeview(parent, columns=columns, height=20, show='headings')
        
        tree.heading('No', text='No')
        tree.heading('Kode', text='Kode')
        tree.heading('Produk', text='Produk')
        tree.heading('Stok', text='Stok')
        tree.heading('Status', text='Status')
        
        tree.column('No', width=30)
        tree.column('Kode', width=80)
        tree.column('Produk', width=200)
        tree.column('Stok', width=80)
        tree.column('Status', width=100)
        
        for i, item in enumerate(stok_list, 1):
            status = "⚠️ Habis" if item['stok'] == 0 else "⚡ Minim" if item['stok'] < 5 else "✅ Normal"
            tree.insert('', 'end', values=(
                str(i),
                item['kode'],
                item['nama'],
                str(item['stok']),
                status
            ))
        
        scrollbar = ttk.Scrollbar(parent, orient='vertical', command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        tree.pack(fill='both', expand=True, padx=10, pady=10)
    
    # ========================================================================
    # TELEGRAM BOT PAGE
    # ========================================================================
    
    def show_telegram(self):
        """Show Telegram bot management page."""
        self._clear_content()
        
        if not TELEGRAM_AVAILABLE:
            header = ttk.Label(
                self.content_area,
                text="❌ Telegram Bot Tidak Tersedia",
                font=FONTS['title'],
                foreground=COLORS['danger']
            )
            header.pack(pady=20)
            
            msg = ttk.Label(
                self.content_area,
                text="Install python-telegram-bot terlebih dahulu:\npip install python-telegram-bot requests",
                font=FONTS['normal']
            )
            msg.pack(pady=20)
            return
        
        # Header
        header = ttk.Label(
            self.content_area,
            text="🤖 Manajemen Telegram Bot",
            font=FONTS['title'],
            foreground=COLORS['primary']
        )
        header.pack(pady=10)
        
        # Status info
        status_frame = ttk.LabelFrame(self.content_area, text="Status Bot", padding=10)
        status_frame.pack(fill='x', padx=10, pady=10)
        
        if self.telegram_bot and self.telegram_bot.available:
            status_text = "✅ Bot siap digunakan"
            status_color = COLORS['success']
        else:
            status_text = "❌ Bot belum dikonfigurasi"
            status_color = COLORS['danger']
        
        status_label = tk.Label(
            status_frame,
            text=status_text,
            font=FONTS['heading'],
            bg=COLORS['bg_card'],
            fg=status_color
        )
        status_label.pack(pady=10)
        
        # Device Token & Settings
        config_frame = ttk.LabelFrame(self.content_area, text="⚙️ Konfigurasi", padding=10)
        config_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        ttk.Label(config_frame, text="Bot Token:", font=FONTS['normal']).pack(anchor='w', pady=5)
        token_entry = ttk.Entry(config_frame, width=50)
        token_entry.pack(fill='x', pady=5)
        
        # Add more config fields here
        ttk.Label(config_frame, text="Admin Chat ID:", font=FONTS['normal']).pack(anchor='w', pady=5)
        admin_id_entry = ttk.Entry(config_frame, width=50)
        admin_id_entry.pack(fill='x', pady=5)
        
        # Buttons
        btn_frame = ttk.Frame(config_frame)
        btn_frame.pack(fill='x', pady=15)
        
        save_btn = ttk.Button(
            btn_frame,
            text="💾 Simpan Konfigurasi",
            command=lambda: messagebox.showinfo("Info", "Konfigurasi disimpan!")
        )
        save_btn.pack(side='left', padx=5)
        
        test_btn = ttk.Button(
            btn_frame,
            text="🧪 Test Koneksi",
            command=lambda: messagebox.showinfo("Info", "Testing connection...")
        )
        test_btn.pack(side='left', padx=5)
    
    # ========================================================================
    # SETTINGS PAGE
    # ========================================================================
    
    def show_settings(self):
        """Show settings page."""
        self._clear_content()
        
        # Header
        header = ttk.Label(
            self.content_area,
            text="⚙️ Pengaturan & Utility",
            font=FONTS['title'],
            foreground=COLORS['primary']
        )
        header.pack(pady=10)
        
        # Database stats
        stats_frame = ttk.LabelFrame(self.content_area, text="📊 Database Info", padding=10)
        stats_frame.pack(fill='x', padx=10, pady=10)
        
        stats = self.db.get_database_stats()
        
        stats_text = f"""
Total Produk      : {stats['total_products']}
Total Transaksi   : {stats['total_transactions']}
Total Items       : {stats['total_items']}
Database Path     : {stats['db_path']}
        """
        
        stats_label = tk.Label(
            stats_frame,
            text=stats_text,
            font=FONTS['mono'],
            justify='left',
            bg=COLORS['bg_card']
        )
        stats_label.pack(anchor='w')
        
        # About section
        about_frame = ttk.LabelFrame(self.content_area, text="ℹ️  Tentang Sistem", padding=10)
        about_frame.pack(fill='x', padx=10, pady=10)
        
        about_text = """
🛒 SISTEM POS - Toko Accessories G-LIES
Versi 1.0 - GUI Interface

Fitur:
✅ Manajemen Produk
✅ Proses Transaksi Real-time
✅ Laporan & Analisis
✅ Export CSV
✅ Integrasi Telegram Bot

Dikembangkan dengan Python & Tkinter
        """
        
        about_label = tk.Label(
            about_frame,
            text=about_text,
            font=FONTS['normal'],
            justify='left',
            bg=COLORS['bg_card']
        )
        about_label.pack(anchor='w')
        
        # Danger zone
        danger_frame = ttk.LabelFrame(self.content_area, text="⚠️ Zone Berbahaya", padding=10)
        danger_frame.pack(fill='x', padx=10, pady=10)
        
        danger_btn = ttk.Button(
            danger_frame,
            text="🚨 Reset Database (Hapus Semua Data)",
            command=self._reset_database
        )
        danger_btn.pack(fill='x', pady=10)
    
    def _reset_database(self):
        """Reset database with confirmation."""
        if messagebox.askyesno(
            "⚠️ PERHATIAN",
            "Ini akan MENGHAPUS SEMUA data di database!\n\nLanjutkan?"
        ):
            self.db.clear_database()
            messagebox.showinfo("Sukses", "Database berhasil direset!")
            self.show_settings()


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point."""
    app = POSGUIApplication()
    app.mainloop()


if __name__ == "__main__":
    main()
