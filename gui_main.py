# ============================================================================
# GUI_MAIN.PY - Point of Sale (POS) System - GUI Interface (Tkinter)
# ============================================================================
# Fungsi: GUI modern dan user-friendly untuk sistem POS
# Fitur: Dashboard, Produk, Transaksi, Laporan, dengan antarmuka yang intuitif
# ============================================================================

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from datetime import datetime, timedelta
from tkcalendar import DateEntry
import os
import sys

# Matplotlib integration
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# Import semua modules dari sistem POS
from database import DatabaseManager
from models import ProductManager, ValidationError, Product, format_rp, format_satuan
from transaction import TransactionService, TransactionHandler, ReceiptManager
from laporan import ReportGenerator, ReportFormatter, CSVExporter
from telegram_bot import POSTelegramBot, TelegramConfigManager, TELEGRAM_AVAILABLE
from stok_opname import StokOpnameService
from logger_config import get_logger, log_user_login, log_user_logout, log_product_added, log_product_updated, log_product_deleted, log_transaction_completed

# Import Phase 4-5 Integration Services
try:
    from app.integration import init_gui_services, get_gui_services
    from app.gui_components import show_login_dialog
    PHASE_45_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Phase 4-5 modules not available: {e}")
    PHASE_45_AVAILABLE = False

logger = get_logger(__name__)

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
# LOGIN WINDOW - Form login dengan role-based access
# ============================================================================

class LoginWindow(tk.Toplevel):
    """
    Window login untuk autentikasi user.
    Mendukung 2 role: admin dan cashier.
    """
    
    def __init__(self, parent, db):
        """
        Inisialisasi login window.
        
        Args:
            parent: Parent window (biasanya root)
            db: DatabaseManager instance
        """
        super().__init__(parent)
        self.db = db
        self.result = None
        
        # Window settings
        self.title("Login - Sistem POS")
        self.geometry("400x300")
        # Don't use transient with withdrawn parent - causes display issues
        # self.transient(parent)  # DISABLED - causes window not to show
        # self.grab_set()  # DISABLED - causes window to hang
        self.resizable(False, False)
        
        # Make sure this window is on top and has focus
        self.attributes('-topmost', True)
        self.attributes('-topmost', False)
        
        # Center window on screen
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - 200
        y = (screen_height // 2) - 150
        self.geometry(f"+{x}+{y}")
        
        # Ensure window is visible and focused
        self.lift()
        self.focus_set()
        
        # Create UI
        self._create_ui()
        
    def _create_ui(self):
        """Create login form UI."""
        # Header
        header = ttk.Label(
            self,
            text="Login Aplikasi POS",
            font=FONTS['title'],
            foreground=COLORS['primary']
        )
        header.pack(pady=20)
        
        # Form frame
        form_frame = ttk.Frame(self, padding=20)
        form_frame.pack(fill='both', expand=True)
        
        # Username
        ttk.Label(form_frame, text="Username:", font=FONTS['normal']).pack(anchor='w', pady=(0, 5))
        self.username_var = tk.StringVar()
        username_entry = ttk.Entry(form_frame, textvariable=self.username_var, width=30)
        username_entry.pack(fill='x', pady=(0, 15))
        username_entry.focus()
        
        # Password
        ttk.Label(form_frame, text="Password:", font=FONTS['normal']).pack(anchor='w', pady=(0, 5))
        self.password_var = tk.StringVar()
        password_entry = ttk.Entry(form_frame, textvariable=self.password_var, show="*", width=30)
        password_entry.pack(fill='x', pady=(0, 20))
        
        # Bind Enter key
        password_entry.bind('<Return>', lambda e: self._login())
        
        # Button frame
        btn_frame = ttk.Frame(form_frame)
        btn_frame.pack(fill='x')
        
        login_btn = ttk.Button(
            btn_frame,
            text="✅ Login",
            command=self._login
        )
        login_btn.pack(side='left', padx=5)
        
        exit_btn = ttk.Button(
            btn_frame,
            text="❌ Keluar",
            command=self.destroy
        )
        exit_btn.pack(side='left', padx=5)
        
        # Info message
        info_label = ttk.Label(
            self,
            text="Demo: username='admin' password='admin123'\n"
                 "      atau username='cashier' password='cashier123'",
            font=FONTS['small'],
            foreground=COLORS['text_secondary'],
            justify='center'
        )
        info_label.pack(pady=10)
    
    def _login(self):
        """Process login."""
        username = self.username_var.get().strip()
        password = self.password_var.get()
        
        if not username or not password:
            messagebox.showwarning("Peringatan", "Username dan password harus diisi!")
            logger.warning(f"Login attempt with empty credentials")
            return
        
        # Verify login
        user = self.db.verify_user_login(username, password)
        
        if user:
            self.result = user
            logger.info(f"User login successful: {username} ({user['role']})")
            self.destroy()
        else:
            messagebox.showerror("Login Gagal", "Username atau password salah!")
            logger.warning(f"Failed login attempt for user: {username}")
            self.password_var.set("")
    
    def get_user(self):
        """Get logged-in user data."""
        return self.result


# ============================================================================
# MAIN GUI APPLICATION
# ============================================================================

class POSGUIApplication(tk.Tk):
    """Main GUI Application untuk sistem POS."""
    
    def __init__(self, user=None):
        """
        Inisialisasi aplikasi GUI.
        
        Args:
            user (dict): Data user yang login {id, username, role}
        """
        super().__init__()
        
        # Store user info
        self.current_user = user or {'username': 'Guest', 'role': 'guest'}
        
        self.title(f"🛒 Sistem POS - {self.current_user['username']} ({self.current_user['role'].upper()})")
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
        self._setup_keyboard_shortcuts()
        
        # Center window on screen
        self.update_idletasks()
        
    def _init_backend(self):
        """Inisialisasi backend POS System."""
        try:
            # Initialize Telegram Bot FIRST (sebelum DatabaseManager)
            self.telegram_bot = None
            if TELEGRAM_AVAILABLE:
                try:
                    self.telegram_bot = POSTelegramBot()
                except Exception as e:
                    print(f"⚠️ Telegram bot init failed: {e}")
            
            # Initialize DatabaseManager dengan telegram_bot untuk low stock alerts
            self.db = DatabaseManager(telegram_bot=self.telegram_bot)
            
            # Create automatic backup on startup
            if self.db.backup_database():
                logger.info("Daily backup created successfully")
            
            self.product_manager = ProductManager(self.db)
            self.transaction_handler = TransactionHandler(self.db)
            self.report_generator = ReportGenerator(self.db)
            self.report_formatter = ReportFormatter()
            self.csv_exporter = CSVExporter()
            self.stok_opname_service = StokOpnameService(self.db)
            
            # Initialize Phase 4-5 Services (new refactored architecture)
            self.gui_services = None
            if PHASE_45_AVAILABLE:
                try:
                    logger.info("Initializing Phase 4-5 services...")
                    self.gui_services = init_gui_services(self.db)
                    if self.gui_services:
                        logger.info("✅ Phase 4-5 services initialized")
                    else:
                        logger.warning("⚠️ Phase 4-5 services initialization failed")
                except Exception as e:
                    logger.warning(f"⚠️ Phase 4-5 services not available: {e}")
                    self.gui_services = None
            else:
                logger.info("ℹ️ Phase 4-5 modules not available (optional)")
            
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
    
    def _setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for faster operation."""
        # Enter → Add item to transaction
        self.bind('<Return>', self._on_enter_pressed)
        
        # F1 → New transaction (show transaction page)
        self.bind('<F1>', lambda e: self.show_transaction())
        
        # F2 → Process payment
        self.bind('<F2>', lambda e: self._process_payment())
        
        # Escape → Cancel transaction
        self.bind('<Escape>', lambda e: self._clear_transaction())
        
        logger.info("Keyboard shortcuts registered:")
        logger.info("  Enter → Add item")
        logger.info("  F1 → New transaction")
        logger.info("  F2 → Process payment")
        logger.info("  Escape → Cancel transaction")
    
    def _on_enter_pressed(self, event):
        """Handle Enter key press - add item to transaction."""
        # Only process if transaction page is active and search field has focus or is empty
        try:
            # Check if product_listbox exists (means we're on transaction page)
            if hasattr(self, 'product_listbox'):
                # Check if any product is selected in listbox
                selection = self.product_listbox.curselection()
                if selection:
                    # If listbox has selection, select from list
                    self._select_from_list()
                    self._add_transaction_item()
                elif hasattr(self, 'product_search_var'):
                    # If product_search field has value, add the item
                    if self.product_search_var.get().strip():
                        self._add_transaction_item()
        except Exception as e:
            logger.debug(f"Enter key handler: {e}")
    
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
        """Create navigation sidebar dengan role-based access."""
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
        
        # User info
        user_info = ttk.Frame(sidebar)
        user_info.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(
            user_info,
            text=f"User: {self.current_user['username']}",
            font=FONTS['small'],
            foreground=COLORS['text_secondary']
        ).pack(anchor='w')
        
        role_color = COLORS['success'] if self.current_user['role'] == 'admin' else COLORS['info']
        ttk.Label(
            user_info,
            text=f"Role: {self.current_user['role'].upper()}",
            font=FONTS['small'],
            foreground=role_color
        ).pack(anchor='w')
        
        separator = ttk.Separator(sidebar, orient='horizontal')
        separator.pack(fill='x', padx=10)
        
        # Menu buttons
        menu_items = [
            ("🏠 Dashboard", self.show_dashboard, True),  # visible for all
            ("📦 Produk", self.show_products, True),
            ("� Stok Opname", self.show_stok_opname, True),
            ("�🛒 Transaksi", self.show_transaction, True),
            ("📊 Laporan", self.show_reports, True),
            ("🤖 Telegram Bot", self.show_telegram, True),
        ]
        
        # Add Phase 4-5 features if available
        if PHASE_45_AVAILABLE and self.gui_services:
            menu_items.extend([
                ("📜 Riwayat Transaksi", self.show_transaction_history, True),
                ("📋 Restock Rekomendasi", self.show_restock_dashboard, True),
            ])
        
        # Add Settings only for admin
        if self.current_user['role'] == 'admin':
            menu_items.append(("⚙️ Settings", self.show_settings, True))
        
        menu_items.append(("🚪 Logout", self._logout, True))
        
        for label, command, visible in menu_items:
            if visible:
                btn = ttk.Button(
                    sidebar,
                    text=label,
                    command=command,
                    width=20
                )
                btn.pack(pady=5, padx=10, fill='x')
        
        return sidebar
    
    def _logout(self):
        """Logout user dan kembali ke login screen."""
        if messagebox.askyesno("Logout", f"Keluar dari akun {self.current_user['username']}?"):
            # Shutdown Phase 4-5 services gracefully
            if PHASE_45_AVAILABLE and self.gui_services:
                try:
                    self.gui_services.destroy_user_session()
                    self.gui_services.shutdown()
                    logger.info("✅ Phase 4-5 services shut down")
                except Exception as e:
                    logger.warning(f"⚠️ Error shutting down services: {e}")
            
            log_user_logout(self.current_user['username'])
            self.destroy()  # Close main application window
    
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
        
        # Create scrollable content area with canvas and scrollbar
        canvas = tk.Canvas(self.content_area, bg=COLORS['bg_main'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.content_area, orient='vertical', command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Add mouse wheel scrolling support
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Use scrollable_frame as the content container instead of self.content_area
        # Header
        header = ttk.Label(
            scrollable_frame,
            text="📊 Dashboard",
            font=FONTS['title'],
            foreground=COLORS['primary']
        )
        header.pack(pady=10)
        
        # Stats cards container
        stats_frame = ttk.Frame(scrollable_frame)
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
        
        # Daily sales chart (last 7 days)
        chart_frame = ttk.Frame(scrollable_frame)
        chart_frame.pack(fill='both', expand=True, pady=10)
        
        self._create_daily_sales_chart(chart_frame)
        
        # AI Recommendations section (top 3 products)
        # NOTE: If dashboard loads slowly, comment out this line:
        self._create_ai_recommendations_section(scrollable_frame)
        
        # Recent transactions section
        self._create_recent_transactions_section(scrollable_frame)
        
        # Action buttons
        actions_frame = ttk.Frame(scrollable_frame)
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
    
    def _create_recent_transactions_section(self, parent):
        """Create recent transactions display."""
        section_frame = tk.Frame(parent, bg=COLORS['bg_card'], relief='flat', bd=1)
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
        columns = ('No', 'Produk', 'Waktu', 'Total', 'Kembalian')
        
        # Create frame for treeview with scrollbar
        tree_frame = ttk.Frame(section_frame)
        tree_frame.pack(fill='both', expand=True, padx=15, pady=10)
        
        # Scrollbar for treeview
        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical')
        scrollbar.pack(side='right', fill='y')
        
        tree = ttk.Treeview(
            tree_frame, 
            columns=columns, 
            height=8, 
            show='headings',
            yscrollcommand=scrollbar.set
        )
        scrollbar.config(command=tree.yview)
        
        # Define column headings and widths
        widths = [30, 250, 150, 100, 100]
        for col, width in zip(columns, widths):
            tree.heading(col, text=col)
            tree.column(col, width=width)
        
        # Add data (store transaction_ids in a mapping)
        trans_list = recent_trans.get('transactions', [])
        self._trans_id_map = {}  # Store mapping for click handler
        for i, trans in enumerate(trans_list[-10:], 1):
            # Get product names from transaction
            product_names = trans.get('product_names', 'N/A')
            
            item_id = tree.insert('', 'end', values=(
                str(i),
                product_names,
                trans['tanggal'],
                format_rp(trans['total']),
                format_rp(trans['kembalian'])
            ))
            self._trans_id_map[item_id] = trans['id']  # Map tree item to transaction ID
        
        # Add click handler
        tree.bind('<Double-1>', lambda e: self._show_transaction_detail(tree, e))
        
        tree.pack(fill='both', expand=True, side='left')
        
        # Add hint label
        hint_label = tk.Label(
            section_frame,
            text="💡 Double-click untuk melihat detail transaksi",
            font=FONTS['small'],
            bg=COLORS['bg_card'],
            fg=COLORS['text_secondary']
        )
        hint_label.pack(anchor='w', padx=15, pady=5)
    
    def _create_ai_recommendations_section(self, parent):
        """Create AI recommendations section showing top 3 best-selling products."""
        try:
            # Try to get top 3 products - with error handling and simple queries
            try:
                # Test if we can even access the database quickly
                top_products = self.report_generator.get_produk_terlaris(limit=3)
                
                # Debug: log what we got
                logger.info(f"Top products data: {top_products}")
                
                # If no products, skip this section entirely for performance
                if not top_products:
                    return
                    
            except Exception as e:
                logger.warning(f"Skipping recommendations (error/slow): {e}")
                return
            
            # Create container
            rec_frame = tk.Frame(parent, bg=COLORS['bg_main'], relief='flat')
            rec_frame.pack(fill='x', pady=5)
            
            # Header - simple text without emoji
            header = tk.Label(
                rec_frame,
                text="🏆 Top 3 Produk Terlaris",
                font=FONTS['subheading'],
                bg=COLORS['bg_main'],
                fg=COLORS['primary']
            )
            header.pack(anchor='w', padx=15, pady=8)
            
            # Create cards for top 3 products
            cards_container = tk.Frame(rec_frame, bg=COLORS['bg_main'])
            cards_container.pack(fill='both', expand=True, padx=15, pady=3)
            
            # Colors for ranking (gold, silver, bronze)
            rank_colors = ['#FFD700', '#C0C0C0', '#CD7F32']
            
            for idx, product in enumerate(top_products):
                try:
                    # Card with LARGER height for proper display (increased from 110 to 160)
                    card = tk.Frame(
                        cards_container,
                        bg=COLORS['bg_card'],
                        relief='solid',
                        bd=1,
                        height=160
                    )
                    card.pack(side='left', padx=8, pady=3, fill='both', expand=True)
                    card.pack_propagate(False)  # Respect the fixed height
                    
                    # Rank label - with medal emoji
                    rank_emoji = ['🥇', '🥈', '🥉'][idx]
                    rank_text = ['#1', '#2', '#3'][idx]
                    rank_label = tk.Label(
                        card,
                        text=f"{rank_emoji} Rank {rank_text}",
                        font=(FONTS['small'][0], FONTS['small'][1], 'bold'),
                        bg=COLORS['bg_card'],
                        fg=rank_colors[idx]
                    )
                    rank_label.pack(anchor='w', padx=8, pady=4, fill='x')
                    
                    # Product name - ensure it's visible and properly formatted
                    product_name = product.get('nama') or product.get('name') or 'Unknown Product'
                    name = str(product_name)[:45]  # Limit length
                    name_label = tk.Label(
                        card,
                        text=name,
                        font=(FONTS['normal'][0], 10, 'bold'),
                        bg=COLORS['bg_card'],
                        fg=COLORS['text_primary'],
                        wraplength=145,
                        justify='left'
                    )
                    name_label.pack(anchor='w', padx=8, pady=3, fill='both', expand=True)
                    
                    # Quantity sold
                    qty = product.get('total_qty', 0)
                    qty_label = tk.Label(
                        card,
                        text=f"📦 {qty} unit",
                        font=FONTS['small'],
                        bg=COLORS['bg_card'],
                        fg=COLORS['text_secondary']
                    )
                    qty_label.pack(anchor='w', padx=8, pady=2)
                    
                    # Revenue
                    revenue = product.get('total_revenue', 0)
                    revenue_label = tk.Label(
                        card,
                        text=f"💰 {format_rp(revenue)}",
                        font=(FONTS['small'][0], 9, 'bold'),
                        bg=COLORS['bg_card'],
                        fg=COLORS['success']
                    )
                    revenue_label.pack(anchor='w', padx=8, pady=2)
                    
                    logger.info(f"Product {idx+1}: {product_name} (qty={qty}, revenue={revenue})")
                    
                except Exception as e:
                    logger.warning(f"Error rendering product card {idx}: {e}")
                    continue
                    
        except Exception as e:
            logger.warning(f"AI recommendations skipped: {e}")
    
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
        """Generate receipt text format with discount and tax."""
        receipt = []
        
        # Load store config
        store_config = self._load_store_config()
        store_name = store_config.get('store', {}).get('name', 'TOKO UBI BAROKAH IBU AWANG')
        store_address = store_config.get('store', {}).get('address', 'Jl. Desa Mekarbakti, pertigaan Cilembu.')
        store_phone = store_config.get('store', {}).get('phone', '')
        receipt_width = store_config.get('receipt', {}).get('width', 40)
        show_phone = store_config.get('receipt', {}).get('show_phone', True)
        
        # Header
        receipt.append("=" * receipt_width)
        receipt.append(store_name.center(receipt_width))
        receipt.append(store_address.center(receipt_width))
        if show_phone and store_phone:
            receipt.append(store_phone.center(receipt_width))
        receipt.append("=" * receipt_width)
        receipt.append("")
        
        # Transaction info
        receipt.append(f"Transaksi ID  : {trans['id']}")
        
        # Format datetime nicely
        try:
            trans_datetime = datetime.strptime(trans['tanggal'], '%Y-%m-%d %H:%M:%S')
            formatted_date = trans_datetime.strftime('%d/%m/%Y %H:%M:%S')
        except:
            formatted_date = trans['tanggal']
        
        receipt.append(f"Tanggal/Waktu : {formatted_date}")
        receipt.append("-" * receipt_width)
        receipt.append("Daftar Item:")
        receipt.append("-" * receipt_width)
        
        subtotal = 0
        for i, item in enumerate(items, 1):
            product_name = item.get('nama', 'N/A')[:receipt_width - 10]  # Leave room for number
            qty = item.get('qty', 0)
            harga = item.get('harga_satuan', 0)
            subtotal_item = item.get('subtotal', 0)
            subtotal += subtotal_item
            
            # Format: "Produk | Qty x Harga = Subtotal"
            receipt.append(f"{i}. {product_name}")
            qty_text = f"{qty}x {format_rp(harga)}"
            total_text = format_rp(subtotal_item)
            # Right-align the totals
            line = f"   {qty_text} = {total_text}"
            receipt.append(line)
        
        receipt.append("-" * receipt_width)
        
        # Summary with proper alignment
        receipt.append(self._format_receipt_line("Subtotal", format_rp(subtotal), receipt_width))
        
        # Add discount if applicable
        discount = trans.get('discount_amount', 0)
        if discount > 0:
            discount_pct = trans.get('discount_percent', 0)
            discount_line = f"Diskon ({discount_pct}%)"
            receipt.append(self._format_receipt_line(discount_line, f"-{format_rp(discount)}", receipt_width))
        
        # Add tax if applicable
        tax = trans.get('tax_amount', 0)
        if tax > 0:
            tax_pct = trans.get('tax_percent', 0)
            tax_line = f"Pajak ({tax_pct}%)"
            receipt.append(self._format_receipt_line(tax_line, f"+{format_rp(tax)}", receipt_width))
        
        receipt.append("-" * receipt_width)
        receipt.append(self._format_receipt_line("Total Belanja", format_rp(trans['total']), receipt_width, bold=True))
        receipt.append(self._format_receipt_line("Pembayaran", format_rp(trans['bayar']), receipt_width))
        receipt.append(self._format_receipt_line("Kembalian", format_rp(trans['kembalian']), receipt_width))
        receipt.append("=" * receipt_width)
        
        # Thank you message
        receipt.append("Terima Kasih".center(receipt_width))
        
        # Footer message
        footer_msg = "Barang yang sudah dibeli\ntidak dapat dikembalikan"
        for line in footer_msg.split('\n'):
            receipt.append(line.center(receipt_width))
        
        receipt.append("=" * receipt_width)
        
        return "\n".join(receipt)
    
    def _format_receipt_line(self, label, value, width=40, bold=False):
        """Format a receipt line with label on left and value right-aligned."""
        # Calculate spacing
        label_len = len(label)
        value_len = len(value)
        spacing = width - label_len - value_len
        
        if spacing < 1:
            spacing = 1
        
        line = label + (" " * spacing) + value
        return line[:width]  # Ensure max width
    
    def _load_store_config(self):
        """Load store configuration from JSON file."""
        try:
            import json
            config_path = os.path.join(os.path.dirname(__file__), 'store_config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load store config: {e}")
        
        # Return default config
        return {
            'store': {
                'name': 'TOKO UBI BAROKAH IBU AWANG',
                'address': 'Jl. Desa Mekarbakti, pertigaan Cilembu.',
                'phone': ''
            },
            'receipt': {
                'width': 40,
                'show_phone': True
            }
        }
    
    def _print_report_dialog(self, report_content, filename_prefix):
        """Generic print dialog untuk semua jenis laporan/dokumen."""
        # Create print preview dialog
        preview_dialog = tk.Toplevel(self)
        preview_dialog.title(f"🖨️ Preview - {filename_prefix}")
        preview_dialog.geometry("600x600")
        preview_dialog.configure(bg=COLORS['bg_main'])
        
        # Header
        header = tk.Label(
            preview_dialog,
            text="Preview Dokumen",
            font=FONTS['heading'],
            bg=COLORS['bg_main'],
            fg=COLORS['primary']
        )
        header.pack(pady=10)
        
        # Report text display
        text_frame = ttk.Frame(preview_dialog)
        text_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        report_display = tk.Text(text_frame, font=FONTS['mono'], height=30, width=70)
        report_display.insert('1.0', report_content)
        report_display.config(state='disabled')  # Read-only
        
        scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=report_display.yview)
        report_display.config(yscroll=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        report_display.pack(fill='both', expand=True)
        
        # Buttons
        btn_frame = ttk.Frame(preview_dialog)
        btn_frame.pack(fill='x', padx=10, pady=10)
        
        def print_document():
            """Print dokumen ke printer."""
            try:
                # Save to temporary file
                import tempfile
                import subprocess
                
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as f:
                    f.write(report_content)
                    temp_file = f.name
                
                # Print the file (Windows)
                subprocess.run(['notepad', '/p', temp_file], check=True)
                messagebox.showinfo("Sukses", "Dokumen sedang dicetak...")
                preview_dialog.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Gagal mencetak: {e}")
        
        def save_document():
            """Save dokumen ke file."""
            try:
                from tkinter import filedialog
                
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".txt",
                    filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                    initialfile=f"{filename_prefix}.txt"
                )
                
                if file_path:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(report_content)
                    messagebox.showinfo("Sukses", f"Dokumen disimpan ke:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Gagal menyimpan: {e}")
        
        print_btn = ttk.Button(
            btn_frame,
            text="🖨️ Cetak",
            command=print_document
        )
        print_btn.pack(side='left', padx=5)
        
        save_btn = ttk.Button(
            btn_frame,
            text="💾 Simpan",
            command=save_document
        )
        save_btn.pack(side='left', padx=5)
        
        close_btn = ttk.Button(
            btn_frame,
            text="❌ Tutup",
            command=preview_dialog.destroy
        )
        close_btn.pack(side='left', padx=5)
    
    def _print_transaction_receipt(self, trans, items):
        """Print transaction receipt."""
        receipt_text = self._generate_receipt_text(trans, items)
        self._print_report_dialog(receipt_text, f"resi_{trans['id']}")
    
    def _create_daily_sales_chart(self, parent):
        """Create daily sales chart for the last 7 days."""
        try:
            # Calculate date range (last 7 days)
            today = datetime.now().date()
            start_date = (today - timedelta(days=6)).strftime('%Y-%m-%d')
            end_date = today.strftime('%Y-%m-%d')
            
            # Get daily sales data
            report_data = self.report_generator.get_laporan_periode(start_date, end_date)
            
            if not report_data or not report_data.get('harian_breakdown'):
                # No data, show empty message
                empty_label = tk.Label(
                    parent,
                    text="📈 Belum ada data penjualan (7 hari terakhir)",
                    font=FONTS['small'],
                    fg=COLORS['text_secondary']
                )
                empty_label.pack(pady=20)
                return
            
            # Extract daily data
            daily_data = report_data['harian_breakdown']
            
            # Fill missing days with zero values
            all_days = []
            current = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            day_totals = {d['tanggal']: d['total'] for d in daily_data}
            
            while current <= end:
                date_str = current.strftime('%Y-%m-%d')
                all_days.append(date_str)
                current += timedelta(days=1)
            
            # Prepare data for chart
            dates = []
            sales_values = []
            
            for date_str in all_days:
                # Format date as "Mon 1" style (day abbreviation + date number)
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                day_abbr = date_obj.strftime('%a')
                day_num = date_obj.strftime('%d').lstrip('0')
                dates.append(f"{day_abbr}\n{day_num}")
                sales_values.append(day_totals.get(date_str, 0))
            
            # Create matplotlib figure
            fig = Figure(figsize=(10, 4), dpi=100)
            ax = fig.add_subplot(111)
            
            # Create bar chart
            colors = [COLORS['success'] if val > 0 else COLORS['text_secondary'] for val in sales_values]
            bars = ax.bar(dates, sales_values, color=colors, edgecolor='black', linewidth=0.5)
            
            # Add value labels on top of bars
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                            f'Rp {int(height):,}',
                            ha='center', va='bottom', fontsize=8, rotation=0)
            
            # Styling
            ax.set_title('📈 Penjualan 7 Hari Terakhir', fontsize=12, fontweight='bold', pad=15)
            ax.set_ylabel('Total Penjualan (Rp)', fontsize=10)
            ax.set_xlabel('Tanggal', fontsize=10)
            ax.grid(axis='y', alpha=0.3, linestyle='--')
            
            # Format y-axis labels as currency
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'Rp {int(x/1000)}K'))
            
            fig.tight_layout()
            
            # Embed in Tkinter
            canvas = FigureCanvasTkAgg(fig, master=parent)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True)
            
        except Exception as e:
            logger.error(f"Error creating daily sales chart: {e}", exc_info=True)
            error_label = tk.Label(
                parent,
                text=f"⚠️ Gagal membuat chart: {str(e)}",
                font=FONTS['small'],
                fg=COLORS['danger']
            )
            error_label.pack(pady=20)
    
    
    
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
        
        # ====== SEARCH BAR ======
        search_frame = ttk.Frame(self.content_area)
        search_frame.pack(fill='x', pady=10, padx=5)
        
        search_label = ttk.Label(search_frame, text="🔍 Cari Produk:", font=FONTS['normal'])
        search_label.pack(side='left', padx=5)
        
        search_var = tk.StringVar()
        
        search_entry = ttk.Entry(search_frame, textvariable=search_var, width=40)
        search_entry.pack(side='left', padx=5, fill='x', expand=True)
        
        clear_btn = ttk.Button(
            search_frame,
            text="✕ Hapus",
            command=lambda: search_var.set("")
        )
        clear_btn.pack(side='right', padx=5)
        
        # Create treeview with scrollbar
        tree_frame = ttk.Frame(self.content_area)
        tree_frame.pack(fill='both', expand=True, pady=10)
        
        columns = ('No', 'Kode', 'Nama', 'Harga', 'Stok', 'Satuan', 'Aksi')
        tree = ttk.Treeview(tree_frame, columns=columns, height=15, show='headings')
        
        # Define column headings
        tree.heading('No', text='No')
        tree.heading('Kode', text='Kode Produk')
        tree.heading('Nama', text='Nama Produk')
        tree.heading('Harga', text='Harga')
        tree.heading('Stok', text='Stok')
        tree.heading('Satuan', text='Satuan')
        tree.heading('Aksi', text='Aksi')
        
        tree.column('No', width=30)
        tree.column('Kode', width=80)
        tree.column('Nama', width=250)
        tree.column('Harga', width=100)
        tree.column('Stok', width=60)
        tree.column('Satuan', width=60)
        tree.column('Aksi', width=120)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        tree.pack(fill='both', expand=True)
        
        # Store reference to original products for filtering
        self._product_list = products
        self._product_tree = tree
        self._all_products = products
        
        def update_product_list(*args):
            """Update product list based on search input."""
            search_term = search_var.get().lower().strip()
            
            # Clear existing items
            for item in tree.get_children():
                tree.delete(item)
            
            # Filter products
            filtered_products = []
            if search_term:
                for prod in products:
                    if (search_term in str(prod.kode).lower() or 
                        search_term in prod.nama.lower()):
                        filtered_products.append(prod)
            else:
                filtered_products = products
            
            # Add filtered products to table
            for i, prod in enumerate(filtered_products, 1):
                tree.insert('', 'end', values=(
                    str(i),
                    prod.kode,
                    prod.nama,
                    format_rp(prod.harga),
                    f"{prod.stok} {format_satuan(prod.satuan)}",
                    format_satuan(prod.satuan),
                    "✏️ Edit | 🗑️ Hapus"
                ))
            
            # Store filtered list for click handler
            self._current_filtered_products = filtered_products
        
        # Bind search input to update function
        search_var.trace('w', update_product_list)
        
        # Initial population of tree
        self._current_filtered_products = products
        update_product_list()
        
        # Add click handler for edit/delete
        tree.bind('<Double-1>', lambda e: self._handle_product_click(tree, self._current_filtered_products))
    
    def show_add_product(self):
        """Show add product dialog dengan opsi foto produk."""
        dialog = tk.Toplevel(self)
        dialog.title("➕ Tambah Produk Baru")
        dialog.geometry("450x500")
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
        foto_path_var = tk.StringVar(value="")
        
        form_frame = ttk.Frame(dialog)
        form_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Get next product code automatically
        next_code = self.db.get_next_product_code()
        
        # Kode Produk field (read-only, auto-generated)
        kode_label = ttk.Label(form_frame, text="Kode Produk (Otomatis):", font=FONTS['normal'])
        kode_label.pack(anchor='w', pady=5)
        
        kode_display = ttk.Label(
            form_frame,
            text=f"🏷️ {next_code}",
            font=("Arial", 14, "bold"),
            foreground=COLORS['success']
        )
        kode_display.pack(anchor='w', pady=5, padx=10)
        
        # Store the auto-generated code
        fields['kode'] = next_code
        
        # Other fields
        field_configs = [
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
        
        # Satuan dropdown field
        ttk.Label(form_frame, text="Satuan:", font=FONTS['normal']).pack(anchor='w', pady=5)
        
        satuan_options = ["kg", "pcs", "ltr"]
        satuan_var = tk.StringVar(value="pcs")
        satuan_combo = ttk.Combobox(
            form_frame,
            textvariable=satuan_var,
            values=satuan_options,
            state='readonly',
            width=27
        )
        satuan_combo.pack(fill='x', pady=5)
        fields['satuan'] = satuan_var
        
        # Foto field (OPSIONAL)
        ttk.Label(form_frame, text="📸 Foto Produk (Opsional):", font=FONTS['normal']).pack(anchor='w', pady=(15, 5))
        
        foto_frame = ttk.Frame(form_frame)
        foto_frame.pack(fill='x', pady=5)
        
        foto_display = ttk.Label(
            foto_frame,
            text="Belum ada file dipilih",
            font=FONTS['small'],
            foreground=COLORS['text_secondary']
        )
        foto_display.pack(side='left', fill='x', expand=True)
        
        def browse_photo():
            filename = filedialog.askopenfilename(
                title="Pilih Foto Produk",
                filetypes=[("Image Files", "*.jpg *.jpeg *.png *.bmp"), ("All Files", "*.*")]
            )
            if filename:
                foto_path_var.set(filename)
                display_name = os.path.basename(filename)
                foto_display.config(text=f"✅ {display_name}", foreground=COLORS['success'])
        
        browse_btn = ttk.Button(
            foto_frame,
            text="📁 Browse",
            command=browse_photo
        )
        browse_btn.pack(side='right', padx=5)
        
        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill='x', padx=20, pady=15)
        
        def save_product():
            try:
                kode = fields['kode']  # Use auto-generated code
                nama = fields['nama'].get().strip()
                harga = int(fields['harga'].get().strip())
                stok = int(fields['stok'].get().strip())
                satuan = fields['satuan'].get().strip() or 'pcs'
                
                if not all([kode, nama, harga, stok]):
                    messagebox.showwarning("Peringatan", "Semua field harus diisi!")
                    return
                
                # Handle foto upload
                foto_path = None
                foto_file = foto_path_var.get()
                if foto_file and os.path.exists(foto_file):
                    try:
                        import shutil
                        if not os.path.exists('product_photos'):
                            os.makedirs('product_photos')
                        
                        filename = os.path.basename(foto_file)
                        # Rename dengan kode produk untuk unique identifier
                        filename_new = f"{kode}_{filename}"
                        foto_path = os.path.join('product_photos', filename_new)
                        
                        shutil.copy2(foto_file, foto_path)
                    except Exception as e:
                        messagebox.showwarning("Peringatan", f"Gagal menyimpan foto: {e}")
                        foto_path = None
                
                logger.info(f"Attempting to add product: kode={kode}, nama={nama}, harga={harga}, stok={stok}, satuan={satuan}")
                
                if self.product_manager.add_product(kode, nama, harga, stok, satuan=satuan, foto_path=foto_path):
                    foto_status = "dengan foto" if foto_path else "tanpa foto"
                    messagebox.showinfo("Sukses", f"Produk '{nama}' (Kode: {kode}) berhasil ditambahkan! ({foto_status})")
                    log_product_added(kode, nama)
                    dialog.destroy()
                    self.show_products()
                else:
                    messagebox.showerror("Error", "Gagal menambahkan produk. Periksa logs untuk detail error.")
            except ValueError as e:
                messagebox.showerror("Error", f"Input tidak valid: {e}\n\nHarga dan Stok harus berupa angka!")
            except ValidationError as e:
                messagebox.showerror("❌ Error Validasi", str(e))
                logger.error(f"Product validation error: {e}")
            except Exception as e:
                logger.error(f"Unexpected error in save_product: {e}", exc_info=True)
                messagebox.showerror("Error", f"Terjadi kesalahan: {e}")
        
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
        
        # Extract kode and strip whitespace
        # Note: Treeview converts numeric strings to integers, so we need to format back to 4-digit code
        product_kode = str(values[1]).strip()
        
        # If the kode is numeric and shorter than 4 digits, pad with leading zeros
        if product_kode.isdigit() and len(product_kode) < 4:
            product_kode = product_kode.zfill(4)
        
        # Find the actual product object from the products list
        selected_product = None
        for prod in products:
            if str(prod.kode).strip() == product_kode:
                selected_product = prod
                break
        
        if not selected_product:
            messagebox.showerror("Error", f"Produk dengan kode '{product_kode}' tidak ditemukan!")
            return
        
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
        """Show edit product dialog with photo upload option."""
        # Ensure kode is stripped of whitespace
        kode = str(kode).strip()
        
        # Get product from database
        product = self.product_manager.get_product(kode)
        
        if not product:
            messagebox.showerror("Error", f"Produk dengan kode '{kode}' tidak ditemukan!\n\nMungkin produk sudah dihapus atau ada masalah dengan database.")
            parent_dialog.destroy()
            return
        
        parent_dialog.destroy()
        
        dialog = tk.Toplevel(self)
        dialog.title(f"✏️ Edit Produk - {kode}")
        dialog.geometry("450x500")
        dialog.configure(bg=COLORS['bg_main'])
        
        # Form fields
        fields = {}
        foto_path_var = tk.StringVar(value=product.foto_path or "")
        
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
        
        # Satuan dropdown field
        ttk.Label(form_frame, text="Satuan:", font=FONTS['normal']).pack(anchor='w', pady=5)
        
        satuan_options = ["kg", "pcs", "ltr"]
        # Normalize product satuan to lowercase for proper selection
        current_satuan = (product.satuan or "pcs").lower()
        satuan_var = tk.StringVar(value=current_satuan)
        satuan_combo = ttk.Combobox(
            form_frame,
            textvariable=satuan_var,
            values=satuan_options,
            state='readonly',
            width=27
        )
        satuan_combo.pack(fill='x', pady=5)
        fields['satuan'] = satuan_var
        
        # Foto field (OPSIONAL)
        ttk.Label(form_frame, text="📸 Foto Produk (Opsional):", font=FONTS['normal']).pack(anchor='w', pady=(15, 5))
        
        foto_frame = ttk.Frame(form_frame)
        foto_frame.pack(fill='x', pady=5)
        
        # Show current foto path if exists
        current_foto_text = "Belum ada file dipilih"
        current_foto_color = COLORS['text_secondary']
        if product.foto_path:
            current_foto_text = f"✅ {os.path.basename(product.foto_path)}"
            current_foto_color = COLORS['success']
        
        foto_display = tk.Label(
            foto_frame,
            text=current_foto_text,
            font=FONTS['small'],
            fg=current_foto_color,
            bg=COLORS['bg_main']
        )
        foto_display.pack(side='left', fill='x', expand=True)
        
        def browse_photo():
            filename = filedialog.askopenfilename(
                title="Pilih Foto Produk",
                filetypes=[("Image Files", "*.jpg *.jpeg *.png *.bmp"), ("All Files", "*.*")]
            )
            if filename:
                foto_path_var.set(filename)
                display_name = os.path.basename(filename)
                foto_display.config(text=f"✅ {display_name}", fg=COLORS['success'])
        
        browse_btn = ttk.Button(
            foto_frame,
            text="📁 Browse",
            command=browse_photo
        )
        browse_btn.pack(side='right', padx=5)
        
        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill='x', padx=20, pady=15)
        
        def save_changes():
            try:
                update_data = {
                    'nama': fields['nama'].get().strip(),
                    'harga': int(fields['harga'].get().strip()),
                    'stok': int(fields['stok'].get().strip()),
                    'satuan': fields['satuan'].get().strip(),
                }
                
                # Validate using Product model
                Product(kode=kode, nama=update_data['nama'], harga=update_data['harga'], stok=update_data['stok'], satuan=update_data['satuan'])
                
                # Handle foto upload
                foto_file = foto_path_var.get()
                if foto_file and os.path.exists(foto_file):
                    try:
                        import shutil
                        if not os.path.exists('product_photos'):
                            os.makedirs('product_photos')
                        
                        filename = os.path.basename(foto_file)
                        # Rename dengan kode produk untuk unique identifier
                        filename_new = f"{kode}_{filename}"
                        foto_path = os.path.join('product_photos', filename_new)
                        
                        shutil.copy2(foto_file, foto_path)
                        update_data['foto_path'] = foto_path
                    except Exception as e:
                        messagebox.showwarning("Peringatan", f"Gagal menyimpan foto: {e}")
                
                if self.product_manager.update_product(kode, **update_data):
                    messagebox.showinfo("Sukses", "Produk berhasil diupdate!")
                    log_product_updated(kode, update_data['nama'])
                    dialog.destroy()
                    self.show_products()
                else:
                    messagebox.showerror("Error", "Gagal mengupdate produk")
            except ValueError:
                messagebox.showerror("Error", "Input tidak valid! Harga dan Stok harus berupa angka!")
            except ValidationError as e:
                messagebox.showerror("❌ Error Validasi", str(e))
                logger.error(f"Product validation error: {e}")
        
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
        kode = str(kode).strip()
        
        if messagebox.askyesno("Konfirmasi", f"Yakin ingin menghapus produk '{kode}'?\n\nTindakan ini tidak dapat dibatalkan!"):
            if self.product_manager.delete_product(kode):
                messagebox.showinfo("Sukses", "Produk berhasil dihapus!")
                log_product_deleted(kode, "")
                parent_dialog.destroy()
                self.show_products()
            else:
                messagebox.showerror("Error", f"Gagal menghapus produk '{kode}'")
        else:
            parent_dialog.destroy()
    
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
        
        ttk.Label(left_frame, text="Cari Produk (Kode/Nama):", font=FONTS['normal']).pack(anchor='w', pady=5)
        
        self.product_search_var = tk.StringVar()
        search_entry = ttk.Entry(
            left_frame,
            textvariable=self.product_search_var,
            width=30
        )
        search_entry.pack(fill='x', pady=5)
        search_entry.focus()
        
        # Bind KeyRelease event for dynamic filtering
        search_entry.bind('<KeyRelease>', lambda e: self._filter_product_list())
        search_entry.bind('<Down>', lambda e: self._focus_product_list())
        search_entry.bind('<Return>', lambda e: self._select_from_list())
        
        # Create frame for product suggestions
        suggestion_frame = ttk.Frame(left_frame)
        suggestion_frame.pack(fill='both', expand=True, pady=5)
        
        # Scrollbar for listbox
        scrollbar = ttk.Scrollbar(suggestion_frame)
        scrollbar.pack(side='right', fill='y')
        
        # Product suggestions listbox
        self.product_listbox = tk.Listbox(
            suggestion_frame,
            height=8,
            yscrollcommand=scrollbar.set,
            font=FONTS['small']
        )
        self.product_listbox.pack(fill='both', expand=True, side='left')
        scrollbar.config(command=self.product_listbox.yview)
        
        # Bind selection events
        self.product_listbox.bind('<Button-1>', lambda e: self._select_from_list())
        self.product_listbox.bind('<Return>', lambda e: self._select_from_list())
        
        # Store all products for filtering
        self.all_products = self.product_manager.list_products()
        
        # Initial population
        self._filter_product_list()
        
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
        
        ttk.Label(summary_frame, text="Subtotal:", font=FONTS['normal']).pack(anchor='w')
        self.subtotal_label = ttk.Label(
            summary_frame,
            text="Rp 0",
            font=FONTS['normal'],
            foreground=COLORS['text_secondary']
        )
        self.subtotal_label.pack(anchor='w')
        
        ttk.Label(summary_frame, text="Diskon:", font=FONTS['normal']).pack(anchor='w', pady=(10, 0))
        self.discount_label = ttk.Label(
            summary_frame,
            text="Rp 0",
            font=FONTS['normal'],
            foreground=COLORS['danger']
        )
        self.discount_label.pack(anchor='w')
        
        ttk.Label(summary_frame, text="Pajak:", font=FONTS['normal']).pack(anchor='w', pady=(10, 0))
        self.tax_label = ttk.Label(
            summary_frame,
            text="Rp 0",
            font=FONTS['normal'],
            foreground=COLORS['info']
        )
        self.tax_label.pack(anchor='w')
        
        ttk.Label(summary_frame, text="Total:", font=FONTS['subheading']).pack(anchor='w', pady=(10, 0))
        self.total_label = ttk.Label(
            summary_frame,
            text="Rp 0",
            font=FONTS['heading'],
            foreground=COLORS['success']
        )
        self.total_label.pack(anchor='w')
        
        # Discount & Tax and Payment sections (side by side)
        discount_payment_container = ttk.Frame(self.content_area)
        discount_payment_container.pack(fill='both', expand=True, padx=5, pady=10)
        
        # Discount & Tax section (left side)
        discount_tax_frame = ttk.LabelFrame(discount_payment_container, text="💰 Diskon & Pajak", padding=10)
        discount_tax_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))
        
        # Discount section
        discount_inner = ttk.Frame(discount_tax_frame)
        discount_inner.pack(side='left', padx=20)
        
        ttk.Label(discount_inner, text="Diskon (%):", font=FONTS['normal']).pack(side='left', padx=5)
        self.discount_var = tk.StringVar(value="0")
        discount_entry = ttk.Entry(discount_inner, textvariable=self.discount_var, width=10)
        discount_entry.pack(side='left', padx=5)
        discount_entry.bind('<KeyRelease>', lambda e: self._update_discount())
        
        # Tax section
        tax_inner = ttk.Frame(discount_tax_frame)
        tax_inner.pack(side='left', padx=20)
        
        ttk.Label(tax_inner, text="Pajak - PPN (%):", font=FONTS['normal']).pack(side='left', padx=5)
        self.tax_var = tk.StringVar(value="0")
        tax_entry = ttk.Entry(tax_inner, textvariable=self.tax_var, width=10)
        tax_entry.pack(side='left', padx=5)
        tax_entry.bind('<KeyRelease>', lambda e: self._update_tax())
        
        # Payment section (right side)
        payment_frame = ttk.LabelFrame(discount_payment_container, text="💳 Pembayaran", padding=10)
        payment_frame.pack(side='right', fill='both', expand=True, padx=(5, 0))
        
        ttk.Label(payment_frame, text="Jumlah Pembayaran:", font=FONTS['normal']).pack(side='left')
        self.payment_var = tk.StringVar()
        payment_entry = ttk.Entry(payment_frame, textvariable=self.payment_var, width=20)
        payment_entry.pack(side='left', padx=5)
        
        # Buttons (in payment frame, right side)
        process_btn = ttk.Button(
            payment_frame,
            text="✅ Proses Pembayaran",
            command=self._process_payment
        )
        process_btn.pack(side='left', padx=5)
        
        clear_btn = ttk.Button(
            payment_frame,
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
            # Extract kode from search text (format: "KODE - Nama Produk")
            kode = search_text.split(' - ')[0].strip() if ' - ' in search_text else search_text
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
    
    def _filter_product_list(self):
        """Filter product list based on search keyword (kode or nama)."""
        keyword = self.product_search_var.get().strip().lower()
        
        # Clear listbox
        self.product_listbox.delete(0, tk.END)
        
        # If no keyword, show all products
        if not keyword:
            for product in self.all_products:
                display_text = f"{product.kode} - {product.nama} ({product.stok})"
                self.product_listbox.insert(tk.END, display_text)
            return
        
        # Filter products by kode or nama
        filtered = []
        for product in self.all_products:
            kode_match = keyword in product.kode.lower()
            nama_match = keyword in product.nama.lower()
            
            if kode_match or nama_match:
                filtered.append(product)
        
        # Display filtered products with highlighting
        for product in filtered:
            display_text = f"{product.kode} - {product.nama} ({product.stok})"
            self.product_listbox.insert(tk.END, display_text)
        
        # If only one match, select it automatically
        if len(filtered) == 1:
            self.product_listbox.selection_set(0)
            self.product_listbox.see(0)
        
        # Log filtering action
        if filtered:
            logger.info(f"Product search: '{keyword}' - Found {len(filtered)} products")
    
    def _focus_product_list(self):
        """Move focus to product listbox when Down arrow is pressed."""
        if self.product_listbox.size() > 0:
            self.product_listbox.selection_set(0)
            self.product_listbox.activate(0)
            self.product_listbox.focus()
    
    def _select_from_list(self):
        """Select product from listbox."""
        try:
            selection = self.product_listbox.curselection()
            if selection:
                selected_item = self.product_listbox.get(selection[0])
                self.product_search_var.set(selected_item)
                logger.info(f"Product selected: {selected_item}")
        except:
            pass
    
    def _update_cart_display(self):
        """Update cart display with discount and tax calculations."""
        # Clear existing items
        for item in self.cart_tree.get_children():
            self.cart_tree.delete(item)
        
        # Get transaction
        trans = self.transaction_handler.transaction_service.get_current_transaction()
        
        if trans and trans.get_item_count() > 0:
            items = self.transaction_handler.get_items()
            if items:  # Check if items is not None
                for i, item in enumerate(items, 1):
                    self.cart_tree.insert('', 'end', values=(
                        str(i),
                        item['nama'],
                        str(item['qty']),
                        format_rp(item['harga_satuan']),
                        format_rp(item['subtotal'])
                    ))
            
            # Update subtotal, discount, tax, and total
            self.subtotal_label.config(text=format_rp(trans.subtotal))
            self.discount_label.config(text=f"-Rp {trans.discount_amount:,}")
            self.tax_label.config(text=f"+Rp {trans.tax_amount:,}")
            self.total_label.config(text=format_rp(trans.total))
        else:
            self.subtotal_label.config(text="Rp 0")
            self.discount_label.config(text="Rp 0")
            self.tax_label.config(text="Rp 0")
            self.total_label.config(text="Rp 0")
    
    def _update_discount(self):
        """Update discount and recalculate total."""
        try:
            discount_percent = float(self.discount_var.get() or "0")
            
            # Validasi
            if discount_percent < 0 or discount_percent > 100:
                messagebox.showwarning("Peringatan", "Diskon harus antara 0-100%")
                self.discount_var.set("0")
                return
            
            # Set discount di transaction
            trans = self.transaction_handler.transaction_service.get_current_transaction()
            if trans:
                trans.set_discount(discount_percent)
                self._update_cart_display()
                logger.info(f"Discount updated: {discount_percent}%")
        except ValueError:
            messagebox.showwarning("Peringatan", "Diskon harus berupa angka!")
            self.discount_var.set("0")
    
    def _update_tax(self):
        """Update tax and recalculate total."""
        try:
            tax_percent = float(self.tax_var.get() or "0")
            
            # Validasi
            if tax_percent < 0 or tax_percent > 100:
                messagebox.showwarning("Peringatan", "Pajak harus antara 0-100%")
                self.tax_var.set("0")
                return
            
            # Set tax di transaction
            trans = self.transaction_handler.transaction_service.get_current_transaction()
            if trans:
                trans.set_tax(tax_percent)
                self._update_cart_display()
                logger.info(f"Tax updated: {tax_percent}%")
        except ValueError:
            messagebox.showwarning("Peringatan", "Pajak harus berupa angka!")
            self.tax_var.set("0")
    
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
                store_name="TOKO UBI BAROKAH IBU AWANG",
                store_address="Jl. Desa Mekarbakti, pertigaan Cilembu."
            )
            
            if trans_id:
                kembalian = bayar - summary['total']
                
                # Ask to print receipt
                print_resi = messagebox.askyesno(
                    "Transaksi Selesai",
                    f"✅ Transaksi berhasil!\n\nID: {trans_id}\nTotal: {format_rp(summary['total'])}\nKembalian: {format_rp(kembalian)}\n\n🖨️ Cetak resi?"
                )
                
                if print_resi:
                    # Get transaction detail for printing
                    transaction = self.db.get_transaction(trans_id)
                    if transaction:
                        trans_data = transaction.get('transaction', transaction)
                        items = transaction.get('items', [])
                        receipt_text = self._generate_receipt_text(trans_data, items)
                        self._print_report_dialog(receipt_text, f"resi_{trans_id}")
                        messagebox.showinfo("Resi Dicetak", "✅ Resi berhasil dicetak!")
                    self.show_transaction()
                else:
                    messagebox.showinfo("Resi Tidak Dicetak", "⚠️ Resi tidak dicetak.\nResi dapat diakses dari Dashboard atau Laporan.")
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
        
        columns = ('No', 'ID', 'Produk', 'Total', 'Pembayaran', 'Kembalian')
        tree = ttk.Treeview(trans_frame, columns=columns, height=15, show='headings')
        
        tree.heading('No', text='No')
        tree.heading('ID', text='ID')
        tree.heading('Produk', text='Produk')
        tree.heading('Total', text='Total')
        tree.heading('Pembayaran', text='Pembayaran')
        tree.heading('Kembalian', text='Kembalian')
        
        tree.column('No', width=30)
        tree.column('ID', width=60)
        tree.column('Produk', width=250)
        tree.column('Total', width=100)
        tree.column('Pembayaran', width=100)
        tree.column('Kembalian', width=100)
        
        for i, trans in enumerate(laporan.get('transactions', []), 1):
            tree.insert('', 'end', values=(
                str(i),
                trans['id'],
                trans.get('product_names', ''),
                format_rp(trans['total']),
                format_rp(trans['bayar']),
                format_rp(trans['kembalian'])
            ))
        
        scrollbar = ttk.Scrollbar(trans_frame, orient='vertical', command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        tree.pack(fill='both', expand=True)
        
        # Print button
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill='x', padx=10, pady=10)
        
        def print_daily_report():
            """Print laporan harian."""
            report_text = f"""
{'='*70}
LAPORAN PENJUALAN HARIAN
{'='*70}
Tanggal: {laporan.get('tanggal', 'N/A')}

RINGKASAN:
├─ Total Penjualan      : {format_rp(laporan.get('total_penjualan', 0))}
├─ Total Transaksi      : {laporan.get('total_transaksi', 0)}
├─ Rata-rata Transaksi  : {format_rp(int(laporan.get('rata_rata_transaksi', 0)))}
└─ Total Item           : {laporan.get('total_item', 0)}

DAFTAR TRANSAKSI:
{'─'*70}
"""
            for i, trans in enumerate(laporan.get('transactions', []), 1):
                report_text += f"""
{i}. Transaksi ID: {trans['id']}
   Produk     : {trans.get('product_names', 'N/A')}
   Total      : {format_rp(trans['total'])}
   Pembayaran : {format_rp(trans['bayar'])}
   Kembalian  : {format_rp(trans['kembalian'])}
"""
            
            report_text += f"\n{'='*70}\n"
            self._print_report_dialog(report_text, f"Laporan_Harian_{laporan.get('tanggal', 'today')}")
        
        print_btn = ttk.Button(btn_frame, text="🖨️ Cetak Laporan", command=print_daily_report)
        print_btn.pack(side='left', padx=5)
    
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
        
        def print_report():
            """Print laporan ke file."""
            try:
                if result_text.get(1.0, 'end').strip() == '':
                    messagebox.showwarning("Peringatan", "Tampilkan laporan terlebih dahulu!")
                    return
                
                report_content = result_text.get(1.0, 'end')
                self._print_report_dialog(report_content, f"Laporan_Periode_{start_date.get_date().strftime('%Y%m%d')}_{end_date.get_date().strftime('%Y%m%d')}")
            except Exception as e:
                messagebox.showerror("Error", f"Error: {str(e)}")
        
        show_btn = ttk.Button(selector_frame, text="📊 Tampilkan Laporan", command=show_report)
        show_btn.pack(side='left', padx=5)
        
        print_btn = ttk.Button(selector_frame, text="🖨️ Cetak Laporan", command=print_report)
        print_btn.pack(side='left', padx=5)
    
    def _create_bestselling_tab(self, parent):
        """Create best selling products tab."""
        produk_laris = self.report_generator.get_produk_terlaris(limit=20)
        
        # Header frame with print button
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill='x', padx=10, pady=10)
        
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
                str(item['total_qty']),
                format_rp(item['total_revenue'])
            ))
        
        def print_bestselling():
            """Print laporan produk terlaris."""
            report_text = f"""
{'='*70}
LAPORAN PRODUK TERLARIS
{'='*70}
Tanggal: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{'─'*70}
"""
            total_revenue = 0
            for i, item in enumerate(produk_laris, 1):
                total_revenue += item['total_revenue']
                report_text += f"""
{i}. {item['nama']}
   Qty Terjual    : {item['total_qty']} pcs
   Total Penjualan: {format_rp(item['total_revenue'])}
"""
            
            report_text += f"""
{'─'*70}
TOTAL PENJUALAN: {format_rp(total_revenue)}
{'='*70}
"""
            self._print_report_dialog(report_text, f"Laporan_Produk_Terlaris_{datetime.now().strftime('%Y%m%d')}")
        
        print_btn = ttk.Button(header_frame, text="🖨️ Cetak Laporan", command=print_bestselling)
        print_btn.pack(side='left', padx=5)
        
        scrollbar = ttk.Scrollbar(parent, orient='vertical', command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        tree.pack(fill='both', expand=True, padx=10, pady=10)
    
    def _create_stock_info_tab(self, parent):
        """Create stock info tab."""
        stok_list = self.report_generator.get_stok_summary()
        
        # Header frame with print button
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill='x', padx=10, pady=10)
        
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
        
        def print_stock_info():
            """Print laporan informasi stok."""
            report_text = f"""
{'='*70}
LAPORAN INFORMASI STOK PRODUK
{'='*70}
Tanggal: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{'─'*70}
"""
            habis_count = 0
            minim_count = 0
            normal_count = 0
            total_stok = 0
            
            for i, item in enumerate(stok_list, 1):
                stok = item['stok']
                total_stok += stok
                
                if stok == 0:
                    habis_count += 1
                    status = "⚠️ HABIS"
                elif stok < 5:
                    minim_count += 1
                    status = "⚡ MINIM"
                else:
                    normal_count += 1
                    status = "✅ NORMAL"
                
                report_text += f"""
{i}. [{item['kode']}] {item['nama']}
   Stok: {stok} pcs | Status: {status}
"""
            
            report_text += f"""
{'─'*70}
RINGKASAN:
├─ Total Produk      : {len(stok_list)}
├─ Status Normal     : {normal_count}
├─ Status Minim      : {minim_count}
├─ Status Habis      : {habis_count}
└─ Total Stok        : {total_stok} pcs
{'='*70}
"""
            self._print_report_dialog(report_text, f"Laporan_Stok_{datetime.now().strftime('%Y%m%d')}")
        
        print_btn = ttk.Button(header_frame, text="🖨️ Cetak Laporan", command=print_stock_info)
        print_btn.pack(side='left', padx=5)
        
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
        
        # Load config manager
        from telegram_bot import TelegramConfigManager
        config_manager = TelegramConfigManager()
        
        # Create scrollable canvas for telegram content
        canvas = tk.Canvas(self.content_area, bg=COLORS['bg_main'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.content_area, orient='vertical', command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Bind mousewheel for scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Header
        header = ttk.Label(
            scrollable_frame,
            text="🤖 Manajemen Telegram Bot",
            font=FONTS['title'],
            foreground=COLORS['primary']
        )
        header.pack(pady=10)
        
        # Status info
        status_frame = ttk.LabelFrame(scrollable_frame, text="Status Bot", padding=10)
        status_frame.pack(fill='x', padx=10, pady=10)
        
        if self.telegram_bot and self.telegram_bot.available:
            status_text = "✅ Bot siap digunakan"
            status_color = COLORS['success']
        else:
            status_text = "⚠️ Bot belum dikonfigurasi" if not config_manager.is_enabled() else "❌ Konfigurasi tidak lengkap"
            status_color = COLORS['warning'] if not config_manager.is_enabled() else COLORS['danger']
        
        status_label = tk.Label(
            status_frame,
            text=status_text,
            font=FONTS['heading'],
            bg=COLORS['bg_card'],
            fg=status_color
        )
        status_label.pack(pady=10)
        
        # Device Token & Settings
        config_frame = ttk.LabelFrame(scrollable_frame, text="⚙️ Konfigurasi", padding=10)
        config_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(config_frame, text="Bot Token:", font=FONTS['normal']).pack(anchor='w', pady=5)
        token_entry = ttk.Entry(config_frame, width=50, show='*')
        token_entry.insert(0, config_manager.config.get('bot_token', ''))
        token_entry.pack(fill='x', pady=5)
        
        ttk.Label(config_frame, text="Admin Chat ID:", font=FONTS['normal']).pack(anchor='w', pady=5)
        admin_id_entry = ttk.Entry(config_frame, width=50)
        admin_id_entry.insert(0, str(config_manager.config.get('admin_chat_id', '')))
        admin_id_entry.pack(fill='x', pady=5)
        
        # Status toggles
        notify_frame = ttk.LabelFrame(config_frame, text="📢 Notifikasi", padding=5)
        notify_frame.pack(fill='x', pady=10)
        
        enabled_var = tk.BooleanVar(value=config_manager.config.get('enabled', False))
        ttk.Checkbutton(
            notify_frame,
            text="Aktifkan Bot",
            variable=enabled_var
        ).pack(anchor='w', pady=5)
        
        notify_trans_var = tk.BooleanVar(value=config_manager.config.get('notify_transaction', True))
        ttk.Checkbutton(
            notify_frame,
            text="Notifikasi Transaksi",
            variable=notify_trans_var
        ).pack(anchor='w', pady=5)
        
        notify_stock_var = tk.BooleanVar(value=config_manager.config.get('notify_low_stock', True))
        ttk.Checkbutton(
            notify_frame,
            text="Notifikasi Stok Minim",
            variable=notify_stock_var
        ).pack(anchor='w', pady=5)
        
        ttk.Label(notify_frame, text="Batas Stok Minim:", font=FONTS['small']).pack(anchor='w', pady=5)
        stock_threshold_entry = ttk.Entry(notify_frame, width=20)
        stock_threshold_entry.insert(0, str(config_manager.config.get('low_stock_threshold', 20)))
        stock_threshold_entry.pack(anchor='w', pady=5)
        
        # Buttons
        btn_frame = ttk.Frame(config_frame)
        btn_frame.pack(fill='x', pady=15)
        
        def save_config():
            """Save Telegram configuration."""
            try:
                token = token_entry.get().strip()
                admin_id_str = admin_id_entry.get().strip()
                
                if not token:
                    messagebox.showerror("Error", "Bot Token tidak boleh kosong!")
                    return
                
                if not admin_id_str:
                    messagebox.showerror("Error", "Admin Chat ID tidak boleh kosong!")
                    return
                
                try:
                    admin_id = int(admin_id_str)
                except ValueError:
                    messagebox.showerror("Error", "Admin Chat ID harus berupa angka!")
                    return
                
                # Validate threshold
                try:
                    threshold = int(stock_threshold_entry.get().strip())
                    if threshold < 1:
                        messagebox.showerror("Error", "Batas stok harus lebih besar dari 0!")
                        return
                except ValueError:
                    messagebox.showerror("Error", "Batas stok harus berupa angka!")
                    return
                
                # Update config
                config_manager.config['bot_token'] = token
                config_manager.config['admin_chat_id'] = admin_id
                config_manager.config['enabled'] = enabled_var.get()
                config_manager.config['notify_transaction'] = notify_trans_var.get()
                config_manager.config['notify_low_stock'] = notify_stock_var.get()
                config_manager.config['low_stock_threshold'] = threshold
                
                if admin_id not in config_manager.config.get('allowed_chat_ids', []):
                    if 'allowed_chat_ids' not in config_manager.config:
                        config_manager.config['allowed_chat_ids'] = []
                    config_manager.config['allowed_chat_ids'].append(admin_id)
                
                # Save config
                config_manager.save_config()
                messagebox.showinfo("Sukses", "✅ Konfigurasi berhasil disimpan!")
                logger.info("Telegram configuration saved from GUI")
                
            except Exception as e:
                messagebox.showerror("Error", f"Gagal menyimpan konfigurasi:\n{str(e)}")
                logger.error(f"Error saving telegram config: {e}")
        
        def test_connection():
            """Test Telegram bot connection."""
            try:
                token = token_entry.get().strip()
                
                if not token:
                    messagebox.showerror("Error", "Bot Token tidak boleh kosong!")
                    return
                
                import requests
                
                # Test token with Telegram API
                url = f"https://api.telegram.org/bot{token}/getMe"
                
                try:
                    response = requests.get(url, timeout=5)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('ok'):
                            bot_info = data.get('result', {})
                            bot_name = bot_info.get('first_name', 'Unknown')
                            bot_username = bot_info.get('username', 'Unknown')
                            
                            messagebox.showinfo(
                                "✅ Sukses",
                                f"Bot berhasil terhubung!\n\n"
                                f"Bot Name: {bot_name}\n"
                                f"Username: @{bot_username}\n\n"
                                f"Bot siap menerima command."
                            )
                            logger.info(f"Telegram bot test successful: {bot_name}")
                        else:
                            error_msg = data.get('description', 'Unknown error')
                            messagebox.showerror("Error", f"❌ Error dari Telegram API:\n{error_msg}")
                            logger.error(f"Telegram API error: {error_msg}")
                    else:
                        messagebox.showerror("Error", f"❌ Gagal terhubung ke Telegram API\nStatus Code: {response.status_code}")
                        logger.error(f"Telegram API connection failed: {response.status_code}")
                        
                except requests.exceptions.Timeout:
                    messagebox.showerror("Error", "❌ Connection timeout.\nPeriksa koneksi internet Anda.")
                    logger.error("Telegram API connection timeout")
                except requests.exceptions.ConnectionError:
                    messagebox.showerror("Error", "❌ Gagal terhubung ke internet.\nPastikan koneksi internet aktif.")
                    logger.error("Telegram API connection error")
                except Exception as e:
                    messagebox.showerror("Error", f"❌ Error: {str(e)}")
                    logger.error(f"Error in test_connection: {e}")
                    
            except Exception as e:
                messagebox.showerror("Error", f"❌ Error menguji koneksi:\n{str(e)}")
                logger.error(f"Error testing telegram connection: {e}")
        
        save_btn = ttk.Button(
            btn_frame,
            text="💾 Simpan Konfigurasi",
            command=save_config
        )
        save_btn.pack(side='left', padx=5)
        
        test_btn = ttk.Button(
            btn_frame,
            text="🧪 Test Koneksi",
            command=test_connection
        )
        test_btn.pack(side='left', padx=5)
    
    # ========================================================================
    # PHASE 4-5: TRANSACTION HISTORY & RESTOCK DASHBOARD
    # ========================================================================
    
    def show_transaction_history(self):
        """Show transaction history viewer (Phase 5)."""
        if not PHASE_45_AVAILABLE or not self.gui_services:
            messagebox.showwarning(
                "Fitur Tidak Tersedia",
                "Modul Phase 4-5 tidak tersedia. Gunakan laporan standar."
            )
            return
        
        if not self.gui_services.check_permission('view_reports'):
            messagebox.showerror("Akses Ditolak", "Anda tidak memiliki akses ke fitur ini")
            return
        
        self._clear_content()
        
        # Header
        header = ttk.Label(
            self.content_area,
            text="📜 Riwayat Transaksi",
            font=FONTS['title'],
            foreground=COLORS['primary']
        )
        header.pack(pady=10)
        
        try:
            # Import TransactionViewer
            from app.gui_components import TransactionViewer
            
            # Create viewer
            viewer = TransactionViewer(
                parent=self.content_area,
                transaction_service=self.gui_services.transaction_service
            )
            
            logger.info("Transaction history viewer displayed")
            
        except Exception as e:
            logger.error(f"Error showing transaction history: {e}", exc_info=True)
            error_label = ttk.Label(
                self.content_area,
                text=f"❌ Gagal membuka transaction viewer: {e}",
                foreground=COLORS['danger']
            )
            error_label.pack(pady=20)
    
    def show_restock_dashboard(self):
        """Show restock recommendations dashboard (Phase 5)."""
        if not PHASE_45_AVAILABLE or not self.gui_services:
            messagebox.showwarning(
                "Fitur Tidak Tersedia",
                "Modul Phase 4-5 tidak tersedia. Gunakan stok opname standar."
            )
            return
        
        if not self.gui_services.check_permission('view_inventory'):
            messagebox.showerror("Akses Ditolak", "Anda tidak memiliki akses ke fitur ini")
            return
        
        self._clear_content()
        
        # Header
        header = ttk.Label(
            self.content_area,
            text="📋 Restock Rekomendasi",
            font=FONTS['title'],
            foreground=COLORS['primary']
        )
        header.pack(pady=10)
        
        try:
            # Import RestockDashboard
            from app.gui_components import RestockDashboard
            
            # Create dashboard
            dashboard = RestockDashboard(
                parent=self.content_area,
                product_service=self.gui_services.product_service,
                restock_service=self.gui_services.restock_service
            )
            
            logger.info("Restock dashboard displayed")
            
        except Exception as e:
            logger.error(f"Error showing restock dashboard: {e}", exc_info=True)
            error_label = ttk.Label(
                self.content_area,
                text=f"❌ Gagal membuka restock dashboard: {e}",
                foreground=COLORS['danger']
            )
            error_label.pack(pady=20)
    
    # ========================================================================
    # SETTINGS PAGE
    # ========================================================================
    
    def show_settings(self):
        """Show settings page (admin only)."""
        # Check role
        if self.current_user['role'] != 'admin':
            messagebox.showerror("Akses Ditolak", "Hanya admin yang dapat mengakses Settings!")
            return
        
        self._clear_content()
        
        # Header
        header = ttk.Label(
            self.content_area,
            text="⚙️ Pengaturan & Utility",
            font=FONTS['title'],
            foreground=COLORS['primary']
        )
        header.pack(pady=10)
        
        # Store Info Section
        store_frame = ttk.LabelFrame(self.content_area, text="🏪 Informasi Toko", padding=15)
        store_frame.pack(fill='x', padx=10, pady=10)
        
        store_config = self._load_store_config()
        store_info = store_config.get('store', {})
        
        # Store name
        ttk.Label(store_frame, text="Nama Toko:", font=FONTS['normal']).grid(row=0, column=0, sticky='w', pady=5, padx=5)
        store_name_entry = ttk.Entry(store_frame, width=50)
        store_name_entry.insert(0, store_info.get('name', ''))
        store_name_entry.grid(row=0, column=1, sticky='ew', pady=5, padx=5)
        
        # Store address
        ttk.Label(store_frame, text="Alamat Toko:", font=FONTS['normal']).grid(row=1, column=0, sticky='w', pady=5, padx=5)
        store_addr_entry = ttk.Entry(store_frame, width=50)
        store_addr_entry.insert(0, store_info.get('address', ''))
        store_addr_entry.grid(row=1, column=1, sticky='ew', pady=5, padx=5)
        
        # Store phone
        ttk.Label(store_frame, text="Nomor Telepon:", font=FONTS['normal']).grid(row=2, column=0, sticky='w', pady=5, padx=5)
        store_phone_entry = ttk.Entry(store_frame, width=50)
        store_phone_entry.insert(0, store_info.get('phone', ''))
        store_phone_entry.grid(row=2, column=1, sticky='ew', pady=5, padx=5)
        
        # Receipt width setting
        ttk.Label(store_frame, text="Lebar Receipt (karakter):", font=FONTS['normal']).grid(row=3, column=0, sticky='w', pady=5, padx=5)
        receipt_width_var = tk.IntVar(value=store_config.get('receipt', {}).get('width', 40))
        receipt_width_spinbox = ttk.Spinbox(store_frame, from_=30, to=80, textvariable=receipt_width_var, width=10)
        receipt_width_spinbox.grid(row=3, column=1, sticky='w', pady=5, padx=5)
        
        # Save store settings button
        def save_store_settings():
            """Save store configuration."""
            import json
            config = {
                'store': {
                    'name': store_name_entry.get(),
                    'address': store_addr_entry.get(),
                    'phone': store_phone_entry.get(),
                    'owner': store_info.get('owner', 'PT. G-LIES')
                },
                'receipt': {
                    'width': receipt_width_var.get(),
                    'show_phone': True,
                    'show_timestamp': True
                }
            }
            
            try:
                config_path = os.path.join(os.path.dirname(__file__), 'store_config.json')
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                messagebox.showinfo("Sukses", "Pengaturan toko berhasil disimpan!")
                logger.info("Store settings updated")
            except Exception as e:
                messagebox.showerror("Error", f"Gagal menyimpan pengaturan: {e}")
                logger.error(f"Failed to save store settings: {e}")
        
        store_save_btn = ttk.Button(
            store_frame,
            text="💾 Simpan Pengaturan Toko",
            command=save_store_settings
        )
        store_save_btn.grid(row=4, column=0, columnspan=2, sticky='ew', pady=15, padx=5)
        
        # ========== USER MANAGEMENT SECTION ==========
        user_mgmt_frame = ttk.LabelFrame(self.content_area, text="👥 Manajemen User", padding=10)
        user_mgmt_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # User list table
        user_list_frame = ttk.Frame(user_mgmt_frame)
        user_list_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Columns
        columns = ('ID', 'Username', 'Role', 'Status', 'Bergabung')
        user_tree = ttk.Treeview(user_list_frame, columns=columns, height=8, show='headings')
        
        # Define column headings and widths
        user_tree.heading('ID', text='ID')
        user_tree.column('ID', width=40, anchor='center')
        user_tree.heading('Username', text='Username')
        user_tree.column('Username', width=120)
        user_tree.heading('Role', text='Role')
        user_tree.column('Role', width=80, anchor='center')
        user_tree.heading('Status', text='Status')
        user_tree.column('Status', width=100, anchor='center')
        user_tree.heading('Bergabung', text='Bergabung')
        user_tree.column('Bergabung', width=150)
        
        user_tree.pack(fill='both', expand=True, side='left')
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(user_list_frame, orient='vertical', command=user_tree.yview)
        scrollbar.pack(side='right', fill='y')
        user_tree.configure(yscroll=scrollbar.set)
        
        # Load users into tree
        def refresh_user_list():
            """Refresh user list display."""
            for item in user_tree.get_children():
                user_tree.delete(item)
            
            users = self.db.get_all_users()
            for user in users:
                status = "✅ Aktif" if user['is_active'] else "❌ Nonaktif"
                created_at = user['created_at'][:10] if user['created_at'] else "N/A"
                user_tree.insert('', 'end', values=(
                    user['id'],
                    user['username'],
                    user['role'].upper(),
                    status,
                    created_at
                ))
        
        refresh_user_list()
        
        # Buttons frame
        user_btn_frame = ttk.Frame(user_mgmt_frame)
        user_btn_frame.pack(fill='x', padx=5, pady=10)
        
        def add_new_user():
            """Open dialog to add new user."""
            add_window = tk.Toplevel(self)
            add_window.title("Tambah User Baru")
            add_window.geometry("300x250")
            add_window.resizable(False, False)
            
            ttk.Label(add_window, text="Username:", font=FONTS['normal']).pack(anchor='w', padx=10, pady=(10, 0))
            username_entry = ttk.Entry(add_window, width=30)
            username_entry.pack(padx=10, pady=(0, 10), fill='x')
            username_entry.focus()
            
            ttk.Label(add_window, text="Password:", font=FONTS['normal']).pack(anchor='w', padx=10, pady=(0, 0))
            password_entry = ttk.Entry(add_window, width=30, show='*')
            password_entry.pack(padx=10, pady=(0, 10), fill='x')
            
            ttk.Label(add_window, text="Role:", font=FONTS['normal']).pack(anchor='w', padx=10, pady=(0, 0))
            role_var = tk.StringVar(value='cashier')
            role_combo = ttk.Combobox(add_window, textvariable=role_var, values=['admin', 'cashier'], state='readonly', width=28)
            role_combo.pack(padx=10, pady=(0, 15), fill='x')
            
            def save_new_user():
                username = username_entry.get().strip()
                password = password_entry.get().strip()
                role = role_var.get()
                
                if not username or not password:
                    messagebox.showwarning("Validasi", "Username dan password harus diisi!")
                    return
                
                if self.db.create_user(username, password, role):
                    messagebox.showinfo("Sukses", f"User '{username}' berhasil ditambahkan!")
                    refresh_user_list()
                    add_window.destroy()
                else:
                    messagebox.showerror("Error", f"Username '{username}' sudah ada atau terjadi error!")
            
            save_btn = ttk.Button(add_window, text="💾 Simpan", command=save_new_user)
            save_btn.pack(padx=10, pady=(0, 10), fill='x')
        
        def edit_user():
            """Edit selected user."""
            selection = user_tree.selection()
            if not selection:
                messagebox.showwarning("Peringatan", "Pilih user yang ingin diedit!")
                return
            
            item = selection[0]
            values = user_tree.item(item, 'values')
            user_id = int(values[0])
            username = values[1]
            current_role = values[2].lower()
            
            edit_window = tk.Toplevel(self)
            edit_window.title(f"Edit User: {username}")
            edit_window.geometry("300x250")
            edit_window.resizable(False, False)
            
            ttk.Label(edit_window, text=f"Username: {username}", font=FONTS['normal']).pack(anchor='w', padx=10, pady=(10, 15))
            
            ttk.Label(edit_window, text="Password Baru (kosongkan jika tidak diubah):", font=FONTS['normal']).pack(anchor='w', padx=10, pady=(0, 0))
            password_entry = ttk.Entry(edit_window, width=30, show='*')
            password_entry.pack(padx=10, pady=(0, 10), fill='x')
            
            ttk.Label(edit_window, text="Role:", font=FONTS['normal']).pack(anchor='w', padx=10, pady=(0, 0))
            role_var = tk.StringVar(value=current_role)
            role_combo = ttk.Combobox(edit_window, textvariable=role_var, values=['admin', 'cashier'], state='readonly', width=28)
            role_combo.pack(padx=10, pady=(0, 15), fill='x')
            
            def save_edited_user():
                password = password_entry.get().strip()
                new_role = role_var.get()
                
                update_data = {'role': new_role}
                if password:
                    update_data['password'] = password
                
                if self.db.update_user(user_id, **update_data):
                    messagebox.showinfo("Sukses", f"User '{username}' berhasil diupdate!")
                    refresh_user_list()
                    edit_window.destroy()
                else:
                    messagebox.showerror("Error", "Gagal mengupdate user!")
            
            save_btn = ttk.Button(edit_window, text="💾 Simpan", command=save_edited_user)
            save_btn.pack(padx=10, pady=(0, 10), fill='x')
        
        def delete_user():
            """Delete selected user."""
            selection = user_tree.selection()
            if not selection:
                messagebox.showwarning("Peringatan", "Pilih user yang ingin dihapus!")
                return
            
            item = selection[0]
            values = user_tree.item(item, 'values')
            user_id = int(values[0])
            username = values[1]
            
            # Prevent deleting the current logged-in user
            if user_id == self.current_user.get('id'):
                messagebox.showerror("Error", "Tidak dapat menghapus user yang sedang login!")
                return
            
            if messagebox.askyesno("Konfirmasi", f"Hapus user '{username}'?\n\nTindakan ini tidak dapat dibatalkan!"):
                if self.db.delete_user(user_id):
                    messagebox.showinfo("Sukses", f"User '{username}' berhasil dihapus!")
                    refresh_user_list()
                else:
                    messagebox.showerror("Error", "Gagal menghapus user!")
        
        def toggle_user_status():
            """Deactivate/Activate selected user."""
            selection = user_tree.selection()
            if not selection:
                messagebox.showwarning("Peringatan", "Pilih user yang ingin diubah statusnya!")
                return
            
            item = selection[0]
            values = user_tree.item(item, 'values')
            user_id = int(values[0])
            username = values[1]
            is_active = "Nonaktif" not in values[3]
            
            # Prevent deactivating the current logged-in user
            if user_id == self.current_user.get('id'):
                messagebox.showerror("Error", "Tidak dapat menonaktifkan user yang sedang login!")
                return
            
            new_status = not is_active
            action = "Nonaktifkan" if is_active else "Aktifkan"
            
            if messagebox.askyesno("Konfirmasi", f"{action} user '{username}'?"):
                if self.db.update_user(user_id, is_active=new_status):
                    messagebox.showinfo("Sukses", f"User '{username}' berhasil diupdate!")
                    refresh_user_list()
                else:
                    messagebox.showerror("Error", "Gagal mengupdate user!")
        
        # Action buttons
        add_btn = ttk.Button(user_btn_frame, text="➕ Tambah User", command=add_new_user)
        add_btn.pack(side='left', padx=5)
        
        edit_btn = ttk.Button(user_btn_frame, text="✏️ Edit User", command=edit_user)
        edit_btn.pack(side='left', padx=5)
        
        toggle_btn = ttk.Button(user_btn_frame, text="🔄 Toggle Status", command=toggle_user_status)
        toggle_btn.pack(side='left', padx=5)
        
        delete_btn = ttk.Button(user_btn_frame, text="🗑️ Hapus User", command=delete_user)
        delete_btn.pack(side='left', padx=5)
        
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
    
    # ========================================================================
    # STOK OPNAME PAGE
    # ========================================================================
    
    def show_stok_opname(self):
        """Show stok opname (inventory count) page."""
        self._clear_content()
        
        # Header
        header = ttk.Label(
            self.content_area,
            text="📋 Stok Opname",
            font=FONTS['title'],
            foreground=COLORS['primary']
        )
        header.pack(pady=10)
        
        # Create notebook tabs
        notebook = ttk.Notebook(self.content_area)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Tab 1: Active Session
        active_frame = ttk.Frame(notebook)
        notebook.add(active_frame, text="📊 Session Aktif")
        self._create_active_session_tab(active_frame)
        
        # Tab 2: Create New Session
        new_session_frame = ttk.Frame(notebook)
        notebook.add(new_session_frame, text="➕ Session Baru")
        self._create_new_session_tab(new_session_frame)
        
        # Tab 3: Session History
        history_frame = ttk.Frame(notebook)
        notebook.add(history_frame, text="📜 Riwayat")
        self._create_session_history_tab(history_frame)
    
    def _create_new_session_tab(self, parent):
        """Create tab untuk membuat session stok opname baru."""
        # Form frame
        form_frame = ttk.LabelFrame(parent, text="Buat Session Stok Opname Baru", padding=15)
        form_frame.pack(fill='x', padx=10, pady=10)
        
        # Date picker
        ttk.Label(form_frame, text="Tanggal Opname:", font=FONTS['normal']).pack(anchor='w', pady=5)
        from tkcalendar import DateEntry
        date_entry = DateEntry(form_frame, width=20)
        date_entry.pack(anchor='w', pady=5, fill='x')
        
        # Keterangan/Notes
        ttk.Label(form_frame, text="Keterangan:", font=FONTS['normal']).pack(anchor='w', pady=(15, 5))
        keterangan_text = tk.Text(form_frame, height=5, width=50)
        keterangan_text.pack(fill='both', expand=True, pady=5)
        
        # Buttons
        btn_frame = ttk.Frame(form_frame)
        btn_frame.pack(fill='x', pady=15)
        
        def create_session():
            """Create a new stok opname session."""
            try:
                tanggal = date_entry.get_date().strftime('%Y-%m-%d')
                keterangan = keterangan_text.get('1.0', 'end').strip()
                created_by = self.current_user['username']
                
                session_id = self.stok_opname_service.create_session(tanggal, keterangan, created_by)
                
                messagebox.showinfo(
                    "✅ Sukses",
                    f"Session stok opname berhasil dibuat!\n\n"
                    f"ID Session: {session_id}\n"
                    f"Tanggal: {tanggal}\n\n"
                    f"Session siap digunakan."
                )
                
                logger.info(f"New stok opname session created: ID={session_id}")
                self.show_stok_opname()
                
            except Exception as e:
                messagebox.showerror("Error", f"Gagal membuat session:\n{str(e)}")
                logger.error(f"Error creating stok opname session: {e}", exc_info=True)
        
        create_btn = ttk.Button(
            btn_frame,
            text="✅ Buat Session",
            command=create_session
        )
        create_btn.pack(side='left', padx=5)
    
    def _create_active_session_tab(self, parent):
        """Create tab untuk active session stok opname."""
        try:
            # Create scrollable container
            canvas = tk.Canvas(parent, highlightthickness=0, bg=COLORS['bg_main'])
            scrollbar = ttk.Scrollbar(parent, orient='vertical', command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            # Bind mousewheel for scrolling
            def _on_mousewheel(event):
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            
            # Pack canvas and scrollbar
            canvas.pack(side='left', fill='both', expand=True)
            scrollbar.pack(side='right', fill='y')
            
            # Get active sessions (status='active')
            all_sessions = self.stok_opname_service.list_sessions(limit=100)
            active_sessions = [s for s in all_sessions if s.status == 'active']
            
            if not active_sessions:
                empty_label = ttk.Label(
                    scrollable_frame,
                    text="Tidak ada session aktif. Buat session baru di tab 'Session Baru'",
                    font=FONTS['normal'],
                    foreground=COLORS['text_secondary']
                )
                empty_label.pack(pady=20)
                return
            
            # Session selector
            selector_frame = ttk.LabelFrame(scrollable_frame, text="Pilih Session", padding=10)
            selector_frame.pack(fill='x', padx=10, pady=10)
            
            session_var = tk.StringVar()
            session_options = [f"Session {s.id} - {s.tanggal}" for s in active_sessions]
            session_combo = ttk.Combobox(
                selector_frame,
                textvariable=session_var,
                values=session_options,
                state='readonly',
                width=50
            )
            session_combo.pack(fill='x', pady=5)
            session_combo.set(session_options[0])
            
            # Item input frame
            input_frame = ttk.LabelFrame(scrollable_frame, text="Input Stok Fisik", padding=15)
            input_frame.pack(fill='x', padx=10, pady=10)
            
            ttk.Label(input_frame, text="Cari Produk (Kode/Nama):", font=FONTS['normal']).pack(anchor='w', pady=5)
            search_var = tk.StringVar()
            
            # Get all products for dropdown
            all_products_opname = self.product_manager.list_products()
            all_product_options = [f"{p.kode} - {p.nama}" for p in all_products_opname]
            
            search_combo = ttk.Combobox(input_frame, textvariable=search_var, values=all_product_options, width=50)
            search_combo.pack(fill='x', pady=5)
            
            # Autocomplete function
            def on_search_change(*args):
                """Filter product suggestions as user types."""
                search_text = search_var.get().lower().strip()
                
                if not search_text:
                    # Show all if empty
                    search_combo['values'] = all_product_options
                else:
                    # Filter products by kode or nama
                    filtered = [p for p in all_product_options if search_text in p.lower()]
                    search_combo['values'] = filtered if filtered else all_product_options
            
            search_var.trace('w', on_search_change)
            
            ttk.Label(input_frame, text="Stok Fisik (yang dihitung):", font=FONTS['normal']).pack(anchor='w', pady=(15, 5))
            stok_fisik_var = tk.StringVar()
            stok_fisik_entry = ttk.Entry(input_frame, textvariable=stok_fisik_var, width=20)
            stok_fisik_entry.pack(anchor='w', pady=5)
            
            ttk.Label(input_frame, text="Catatan (opsional):", font=FONTS['normal']).pack(anchor='w', pady=(15, 5))
            catatan_text = tk.Text(input_frame, height=3, width=50)
            catatan_text.pack(fill='both', expand=True, pady=5)
            
            # Items display frame
            items_frame = ttk.LabelFrame(scrollable_frame, text="Item dalam Session", padding=10)
            items_frame.pack(fill='both', expand=True, padx=10, pady=10)
            
            columns = ('No', 'Kode', 'Produk', 'Stok Sistem', 'Stok Fisik', 'Selisih', 'Status')
            items_tree = ttk.Treeview(items_frame, columns=columns, height=12, show='headings')
            
            items_tree.heading('No', text='No')
            items_tree.column('No', width=30, anchor='center')
            items_tree.heading('Kode', text='Kode')
            items_tree.column('Kode', width=80)
            items_tree.heading('Produk', text='Produk')
            items_tree.column('Produk', width=150)
            items_tree.heading('Stok Sistem', text='Stok Sistem')
            items_tree.column('Stok Sistem', width=80, anchor='center')
            items_tree.heading('Stok Fisik', text='Stok Fisik')
            items_tree.column('Stok Fisik', width=80, anchor='center')
            items_tree.heading('Selisih', text='Selisih')
            items_tree.column('Selisih', width=80, anchor='center')
            items_tree.heading('Status', text='Status')
            items_tree.column('Status', width=80, anchor='center')
            
            scrollbar = ttk.Scrollbar(items_frame, orient='vertical', command=items_tree.yview)
            items_tree.configure(yscroll=scrollbar.set)
            scrollbar.pack(side='right', fill='y')
            items_tree.pack(fill='both', expand=True)
            
            def refresh_items():
                """Refresh items display for selected session."""
                session_text = session_var.get()
                if not session_text:
                    return
                
                session_id = int(session_text.split()[1]) 
                
                # Clear tree
                for item in items_tree.get_children():
                    items_tree.delete(item)
                
                # Get items
                items = self.stok_opname_service.get_session_items(session_id)
                
                for i, item in enumerate(items, 1):
                    status_display = item.status
                    if item.status == 'pending':
                        status_display = "⏳ Pending"
                    elif item.status == 'counted':
                        status_display = "✅ Counted"
                    elif item.status == 'verified':
                        status_display = "✔️ Verified"
                    
                    selisih_display = str(item.selisih)
                    if item.selisih > 0:
                        selisih_display = f"+{item.selisih}"
                    elif item.selisih < 0:
                        selisih_display = f"{item.selisih}"
                    
                    items_tree.insert('', 'end', values=(
                        str(i),
                        item.kode_produk,
                        item.nama_produk,
                        item.stok_sistem,
                        item.stok_fisik if item.stok_fisik > 0 else "—",
                        selisih_display,
                        status_display
                    ))
            
            refresh_items()
            
            def add_item_count():
                """Add counted item to session."""
                try:
                    session_text = session_var.get()
                    if not session_text:
                        messagebox.showwarning("Peringatan", "Pilih session terlebih dahulu!")
                        return
                    
                    search_term = search_var.get().strip()
                    if not search_term:
                        messagebox.showwarning("Peringatan", "Cari produk terlebih dahulu!")
                        return
                    
                    stok_fisik_str = stok_fisik_var.get().strip()
                    if not stok_fisik_str:
                        messagebox.showwarning("Peringatan", "Masukkan stok fisik!")
                        return
                    
                    try:
                        stok_fisik = int(stok_fisik_str)
                    except ValueError:
                        messagebox.showerror("Error", "Stok fisik harus berupa angka!")
                        return
                    
                    if stok_fisik < 0:
                        messagebox.showerror("Error", "Stok fisik tidak boleh negatif!")
                        return
                    
                    # Extract kode from dropdown selection (format: "KODE - NAMA")
                    if ' - ' not in search_term:
                        messagebox.showerror("Error", "Pilih produk dari dropdown!")
                        return
                    
                    kode = search_term.split(' - ')[0].strip()
                    found_product = self.product_manager.get_product(kode)
                    
                    if not found_product:
                        messagebox.showerror("Error", "Produk tidak ditemukan!")
                        return
                    
                    session_id = int(session_text.split()[1])
                    items = self.stok_opname_service.get_session_items(session_id)
                    
                    # Find the item in session
                    item_in_session = None
                    for item in items:
                        if item.product_id == found_product.id:
                            item_in_session = item
                            break
                    
                    if not item_in_session:
                        messagebox.showerror("Error", "Produk tidak ada dalam session ini!")
                        return
                    
                    # Update item
                    catatan = catatan_text.get('1.0', 'end').strip()
                    
                    if self.stok_opname_service.update_item(item_in_session.id, stok_fisik, catatan, 'counted'):
                        messagebox.showinfo("✅ Sukses", f"Stok untuk {found_product.nama} berhasil diinput!")
                        
                        # Clear inputs
                        search_var.set("")
                        stok_fisik_var.set("")
                        catatan_text.delete('1.0', 'end')
                        search_combo.focus()
                        
                        # Refresh items
                        refresh_items()
                    else:
                        messagebox.showerror("Error", "Gagal menyimpan data!")
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Terjadi kesalahan:\n{str(e)}")
                    logger.error(f"Error adding item count: {e}", exc_info=True)
            
            def complete_session():
                """Complete the stok opname session."""
                session_text = session_var.get()
                if not session_text:
                    messagebox.showwarning("Peringatan", "Pilih session terlebih dahulu!")
                    return
                
                session_id = int(session_text.split()[1])
                items = self.stok_opname_service.get_session_items(session_id)
                
                # Check if all items are counted
                pending_items = [i for i in items if i.status == 'pending']
                if pending_items:
                    count = len(pending_items)
                    result = messagebox.askyesnocancel(
                        "Peringatan",
                        f"Masih ada {count} item yang belum dihitung.\n\n"
                        f"Apakah Anda ingin menyelesaikan session sekarang?\n\n"
                        f"Item yang belum dihitung akan tetap menggunakan stok sistem."
                    )
                    if result is None:
                        return
                    elif result is False:
                        return
                
                # Show summary
                items_with_diff = self.stok_opname_service.get_items_with_differences(session_id)
                
                summary_msg = f"""
RINGKASAN STOK OPNAME

Session ID: {session_id}
Total Item: {len(items)}
Item Berbeda: {len(items_with_diff)}

Apakah Anda ingin menyelesaikan session ini?
Stok produk akan diperbarui berdasarkan hasil opname.
"""
                
                if messagebox.askyesno("Konfirmasi", summary_msg):
                    if self.stok_opname_service.complete_session(session_id):
                        messagebox.showinfo("✅ Sukses", "Session stok opname selesai!\nStok produk telah diperbarui.")
                        logger.info(f"Stok opname session completed: {session_id}")
                        self.show_stok_opname()
                    else:
                        messagebox.showerror("Error", "Gagal menyelesaikan session!")
            
            # Action buttons
            action_frame = ttk.Frame(input_frame)
            action_frame.pack(fill='x', pady=15)
            
            add_btn = ttk.Button(
                action_frame,
                text="➕ Tambah Item",
                command=add_item_count
            )
            add_btn.pack(side='left', padx=5)
            
            complete_btn = ttk.Button(
                action_frame,
                text="✅ Selesaikan Session",
                command=complete_session
            )
            complete_btn.pack(side='left', padx=5)
            
            refresh_btn = ttk.Button(
                action_frame,
                text="🔄 Refresh",
                command=refresh_items
            )
            refresh_btn.pack(side='left', padx=5)
            
        except Exception as e:
            error_label = ttk.Label(
                parent,
                text=f"⚠️ Error: {str(e)}",
                font=FONTS['normal'],
                foreground=COLORS['danger']
            )
            error_label.pack(pady=20)
            logger.error(f"Error in active session tab: {e}", exc_info=True)
    
    def _create_session_history_tab(self, parent):
        """Create tab untuk history stok opname sessions."""
        try:
            # Get all sessions
            all_sessions = self.stok_opname_service.list_sessions(limit=100)
            
            if not all_sessions:
                empty_label = ttk.Label(
                    parent,
                    text="Belum ada history stok opname",
                    font=FONTS['normal'],
                    foreground=COLORS['text_secondary']
                )
                empty_label.pack(pady=20)
                return
            
            # Sessions table
            columns = ('No', 'ID', 'Tanggal', 'Status', 'Keterangan', 'Dibuat Oleh')
            sessions_tree = ttk.Treeview(parent, columns=columns, height=15, show='headings')
            
            sessions_tree.heading('No', text='No')
            sessions_tree.column('No', width=30, anchor='center')
            sessions_tree.heading('ID', text='ID')
            sessions_tree.column('ID', width=50, anchor='center')
            sessions_tree.heading('Tanggal', text='Tanggal')
            sessions_tree.column('Tanggal', width=100)
            sessions_tree.heading('Status', text='Status')
            sessions_tree.column('Status', width=100, anchor='center')
            sessions_tree.heading('Keterangan', text='Keterangan')
            sessions_tree.column('Keterangan', width=200)
            sessions_tree.heading('Dibuat Oleh', text='Dibuat Oleh')
            sessions_tree.column('Dibuat Oleh', width=100)
            
            scrollbar = ttk.Scrollbar(parent, orient='vertical', command=sessions_tree.yview)
            sessions_tree.configure(yscroll=scrollbar.set)
            scrollbar.pack(side='right', fill='y')
            sessions_tree.pack(fill='both', expand=True, padx=10, pady=10)
            
            for i, session in enumerate(all_sessions, 1):
                status_display = "✅ Selesai" if session.status == 'completed' else "⏳ Aktif" if session.status == 'active' else "❌ Dibatalkan"
                
                sessions_tree.insert('', 'end', values=(
                    str(i),
                    session.id,
                    session.tanggal,
                    status_display,
                    session.keterangan or "—",
                    session.created_by
                ))
            
            # Action buttons
            btn_frame = ttk.Frame(parent)
            btn_frame.pack(fill='x', padx=10, pady=10)
            
            def view_detail():
                """View detail of selected session."""
                selection = sessions_tree.selection()
                if not selection:
                    messagebox.showwarning("Peringatan", "Pilih session terlebih dahulu!")
                    return
                
                item = sessions_tree.item(selection[0])
                values = item['values']
                session_id = int(values[1])
                
                report = self.stok_opname_service.get_session_report(session_id)
                if not report:
                    messagebox.showerror("Error", "Laporan tidak ditemukan!")
                    return
                
                # Create report window
                report_window = tk.Toplevel(self)
                report_window.title(f"Detail Stok Opname - Session {session_id}")
                report_window.geometry("700x600")
                
                # Report content
                report_text = tk.Text(report_window, font=FONTS['mono'], height=30, width=90)
                report_text.pack(fill='both', expand=True, padx=10, pady=10)
                
                # Generate report text
                content = f"""
{'='*80}
LAPORAN STOK OPNAME
{'='*80}

Session ID       : {report.session_id}
Tanggal          : {report.tanggal}
Total Item       : {report.total_items}
Item Terhitung   : {report.items_counted}
Item Berbeda     : {report.total_selisih}
Total Qty Beda   : {report.total_selisih_qty}

{'-'*80}
DETAIL ITEM:
{'-'*80}
"""
                
                for detail in report.items_details:
                    selisih_str = f"+{detail['selisih']}" if detail['selisih'] > 0 else str(detail['selisih'])
                    content += f"""
{detail['kode']} - {detail['nama']}
  Stok Sistem : {detail['stok_sistem']} {detail['satuan']}
  Stok Fisik  : {detail['stok_fisik']} {detail['satuan']}
  Selisih     : {selisih_str} {detail['satuan']}
  Status      : {detail['status']}
  Catatan     : {detail['catatan'] or '—'}
"""
                
                content += f"\n{'='*80}\n"
                
                report_text.insert('1.0', content)
                report_text.config(state='disabled')
                
                # Close button
                close_btn = ttk.Button(report_window, text="Tutup", command=report_window.destroy)
                close_btn.pack(pady=10)
            
            view_btn = ttk.Button(btn_frame, text="👁️ Lihat Detail", command=view_detail)
            view_btn.pack(side='left', padx=5)
            
            def print_report():
                """Print laporan stok opname ke printer."""
                selection = sessions_tree.selection()
                if not selection:
                    messagebox.showwarning("Peringatan", "Pilih session terlebih dahulu!")
                    return
                
                item = sessions_tree.item(selection[0])
                values = item['values']
                session_id = int(values[1])
                
                report = self.stok_opname_service.get_session_report(session_id)
                if not report:
                    messagebox.showerror("Error", "Laporan tidak ditemukan!")
                    return
                
                try:
                    # Generate report content
                    content = f"""
{'='*80}
LAPORAN STOK OPNAME
{'='*80}

Session ID       : {report.session_id}
Tanggal          : {report.tanggal}
Total Item       : {report.total_items}
Item Terhitung   : {report.items_counted}
Item Berbeda     : {report.total_selisih}
Total Qty Beda   : {report.total_selisih_qty}

{'-'*80}
DETAIL ITEM:
{'-'*80}
"""
                    
                    for detail in report.items_details:
                        selisih_str = f"+{detail['selisih']}" if detail['selisih'] > 0 else str(detail['selisih'])
                        content += f"""
{detail['kode']} - {detail['nama']}
  Stok Sistem : {detail['stok_sistem']} {detail['satuan']}
  Stok Fisik  : {detail['stok_fisik']} {detail['satuan']}
  Selisih     : {selisih_str} {detail['satuan']}
  Status      : {detail['status']}
  Catatan     : {detail['catatan'] or '—'}
"""
                    
                    content += f"\n{'='*80}\n"
                    content += f"Dicetak pada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    
                    # Save to temporary file
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                        f.write(content)
                        temp_file = f.name
                    
                    # Print using Windows print dialog
                    import subprocess
                    import os
                    
                    try:
                        # Use notepad to print (Windows)
                        subprocess.Popen(['notepad', '/p', temp_file])
                        messagebox.showinfo("Sukses", "Laporan dikirim ke printer!")
                        logger.info(f"Stok opname report printed: session_id={session_id}")
                        
                        # Clean up temp file after a delay
                        import threading
                        def cleanup():
                            import time
                            time.sleep(3)
                            try:
                                os.remove(temp_file)
                            except:
                                pass
                        threading.Thread(daemon=True, target=cleanup).start()
                    except Exception as e:
                        messagebox.showerror("Error", f"Gagal print: {str(e)}")
                        logger.error(f"Print error: {e}")
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Terjadi kesalahan:\n{str(e)}")
                    logger.error(f"Error printing report: {e}", exc_info=True)
            
            print_btn = ttk.Button(btn_frame, text="🖨️ Print", command=print_report)
            print_btn.pack(side='left', padx=5)
            
        except Exception as e:
            error_label = ttk.Label(
                parent,
                text=f"⚠️ Error: {str(e)}",
                font=FONTS['normal'],
                foreground=COLORS['danger']
            )
            error_label.pack(pady=20)
            logger.error(f"Error in session history tab: {e}", exc_info=True)
    
    def _reset_database(self):
        """Reset database with enhanced safety (admin only)."""
        # Check role
        if self.current_user['role'] != 'admin':
            messagebox.showerror("Akses Ditolak", "Hanya admin yang dapat mereset database!")
            return
        
        # First warning dialog
        warning_result = messagebox.showwarning(
            "⚠️ PERINGATAN BERBAHAYA",
            "ANDA AKAN MENGHAPUS SEMUA DATA DATABASE!\n\n"
            "Ini akan menghapus:\n"
            "  • Semua produk\n"
            "  • Semua transaksi\n"
            "  • Semua riwayat penjualan\n"
            "  • TIDAK DAPAT DIPULIHKAN\n\n"
            "Lanjutkan ke langkah konfirmasi?"
        )
        
        # If user clicks "No" or closes dialog, return
        if warning_result == 'cancel':
            messagebox.showinfo("Dibatalkan", "Reset database dibatalkan.")
            return
        
        # Second confirmation: ask user to type "RESET"
        confirm_dialog = tk.Toplevel(self)
        confirm_dialog.title("🔐 Konfirmasi Final - Ketik RESET")
        confirm_dialog.geometry("500x250")
        confirm_dialog.resizable(False, False)
        confirm_dialog.configure(bg=COLORS['bg_main'])
        
        # Make dialog modal
        confirm_dialog.transient(self)
        confirm_dialog.grab_set()
        
        # Warning label
        warning_label = tk.Label(
            confirm_dialog,
            text="⚠️ KONFIRMASI FINAL",
            font=FONTS['heading'],
            bg=COLORS['danger'],
            fg='white',
            padx=15,
            pady=10
        )
        warning_label.pack(fill='x')
        
        # Instructions
        instructions = tk.Label(
            confirm_dialog,
            text="Ketik 'RESET' di bawah untuk mengonfirmasi penghapusan database.\n\nTindakan ini TIDAK DAPAT DIBATALKAN!",
            font=FONTS['normal'],
            bg=COLORS['bg_main'],
            fg=COLORS['text_primary'],
            justify='center',
            padx=15,
            pady=15
        )
        instructions.pack(fill='x')
        
        # Entry field
        entry_frame = tk.Frame(confirm_dialog, bg=COLORS['bg_main'])
        entry_frame.pack(fill='x', padx=20, pady=10)
        
        entry_label = tk.Label(
            entry_frame,
            text="Ketik konfirmasi:",
            font=FONTS['normal'],
            bg=COLORS['bg_main'],
            fg=COLORS['text_primary']
        )
        entry_label.pack(anchor='w', pady=(0, 5))
        
        confirm_entry = tk.Entry(
            entry_frame,
            font=FONTS['mono'],
            width=30,
            show='*'  # Show dots instead of text for security
        )
        confirm_entry.pack(fill='x')
        confirm_entry.focus()
        
        # Status label
        status_label = tk.Label(
            confirm_dialog,
            text="",
            font=FONTS['small'],
            bg=COLORS['bg_main'],
            fg=COLORS['danger']
        )
        status_label.pack()
        
        # Buttons
        button_frame = tk.Frame(confirm_dialog, bg=COLORS['bg_main'])
        button_frame.pack(fill='x', padx=15, pady=15)
        
        def on_confirm():
            """Process confirmation."""
            input_text = confirm_entry.get()
            
            if input_text != "RESET":
                status_label.config(
                    text=f"❌ Input salah! Anda mengetik: '{input_text}' (harus 'RESET')",
                    fg=COLORS['danger']
                )
                confirm_entry.delete(0, 'end')
                confirm_entry.focus()
                return
            
            # Create backup before reset
            try:
                logger.info("Creating backup before database reset...")
                if self.db.backup_database():
                    logger.info("Backup created successfully before reset")
                    backup_msg = "✓ Backup database dibuat sebelum reset"
                else:
                    backup_msg = "⚠️ Backup tidak dibuat (kemungkinan sudah ada backup hari ini)"
            except Exception as e:
                backup_msg = f"⚠️ Gagal membuat backup: {e}"
                logger.warning(f"Backup creation failed: {e}")
            
            # Clear the database
            try:
                self.db.clear_database()
                logger.info("Database cleared successfully")
                
                confirm_dialog.destroy()
                messagebox.showinfo(
                    "✓ Sukses",
                    f"Database berhasil direset!\n\n{backup_msg}\n\n"
                    f"Pemulihan: Gunakan backup dari folder 'backup/' jika diperlukan"
                )
                self.show_settings()
            except Exception as e:
                logger.error(f"Database reset failed: {e}")
                messagebox.showerror("Error", f"Gagal mereset database: {e}")
                confirm_dialog.destroy()
        
        def on_cancel():
            """Cancel the reset."""
            confirm_dialog.destroy()
            messagebox.showinfo("Dibatalkan", "Reset database dibatalkan.")
        
        confirm_btn = ttk.Button(
            button_frame,
            text="🚨 RESET SEKARANG",
            command=on_confirm
        )
        confirm_btn.pack(side='left', padx=5)
        
        cancel_btn = ttk.Button(
            button_frame,
            text="❌ Batal",
            command=on_cancel
        )
        cancel_btn.pack(side='left', padx=5)
        
        # Allow Enter key to submit
        confirm_entry.bind('<Return>', lambda e: on_confirm())
        
        # Center dialog on window
        confirm_dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 500) // 2
        y = self.winfo_y() + (self.winfo_height() - 250) // 2
        confirm_dialog.geometry(f"+{x}+{y}")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point with login system."""
    logger.info("Application initialization started")
    
    # Loop untuk multiple login/logout sessions
    while True:
        # Create root window for login
        root = tk.Tk()
        root.withdraw()  # Hide root window temporarily
        
        # Ensure root is properly initialized
        root.update_idletasks()
        
        # Initialize database
        db = DatabaseManager()
        logger.info("Database initialized")
        
        # Create default admin user if no users exist
        if not db.user_exists():
            logger.info("Creating default users on first run")
            db.create_user("admin", "admin123", "admin")
            db.create_user("cashier", "cashier123", "cashier")
            logger.info("Default users created: admin and cashier")
        
        logger.info("Showing login window")
        
        try:
            # Show login window
            login_window = LoginWindow(root, db)
            root.wait_window(login_window)
            
            # Get logged-in user
            user = login_window.get_user()
            
            # If login failed or user clicked exit
            if not user:
                logger.warning("User cancelled login, exiting application")
                root.destroy()
                return  # Exit application completely
            
            # Destroy temporary root
            root.destroy()
            
            # Create main application with logged-in user
            logger.info(f"Launching main application for user {user['username']}")
            app = POSGUIApplication(user=user)
            app.mainloop()
            
            logger.info(f"User {user['username']} logged out - returning to login")
            # Loop akan repeat, menampilkan login window lagi
            
        except Exception as e:
            logger.error(f"Error in main: {e}", exc_info=True)
            root.destroy()
            raise


if __name__ == "__main__":
    main()
