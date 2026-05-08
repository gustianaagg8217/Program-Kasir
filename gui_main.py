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
from auth_manager import AuthManager
from models import ProductManager, ValidationError, Product, format_rp, format_satuan
from transaction import TransactionService, TransactionHandler, ReceiptManager
from laporan import ReportGenerator, ReportFormatter, CSVExporter
from telegram_bot import POSTelegramBot, TelegramConfigManager, TELEGRAM_AVAILABLE
from stok_opname import StokOpnameService
from logger_config import get_logger, log_user_login, log_user_logout, log_product_added, log_product_updated, log_product_deleted, log_transaction_completed

# Import invoice modules
from invoice.invoice_service import InvoiceService
from invoice.invoice_pdf import InvoicePDFGenerator

# Import payment service
from payment_service import PaymentService, TerminPaymentService

# Import promotion service
from promotion_service import PromotionService

# Import accounting service
try:
    from accounting_service import AccountingService
    ACCOUNTING_AVAILABLE = True
except ImportError:
    ACCOUNTING_AVAILABLE = False
    AccountingService = None

# Import Phase 4-5 Integration Services
try:
    from app.integration import init_gui_services, get_gui_services
    from app.gui_components import show_login_dialog
    PHASE_45_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Phase 4-5 modules not available: {e}")
    PHASE_45_AVAILABLE = False

# Import Async Helper for non-blocking operations
from async_helper import AsyncOperation, UIThreadSafeUpdater, get_global_task_manager, cleanup_global_task_manager, LoadingIndicator

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
# PAYMENT TYPE DIALOG - Dialog untuk memilih pembayaran lunas/termin
# ============================================================================

class PaymentTypeDialog(tk.Toplevel):
    """
    Dialog untuk memilih tipe pembayaran: Lunas atau Termin.
    """
    
    def __init__(self, parent, total_amount: int):
        """
        Initialize payment type dialog.
        
        Args:
            parent: Parent window
            total_amount (int): Total amount untuk transaksi
        """
        super().__init__(parent)
        self.title("Pilih Tipe Pembayaran")
        self.geometry("550x600")
        self.resizable(True, True)
        self.grab_set()
        
        self.total_amount = total_amount
        self.result = None
        self.payment_type = None
        self.termin_data = None
        
        self._create_widgets()
        self.transient(parent)
        self.wait_window()
    
    def _create_widgets(self):
        """Create dialog widgets with scrollable content."""
        # Create main container frame
        container = ttk.Frame(self)
        container.pack(side='top', fill='both', expand=True)
        
        # Create canvas with scrollbar
        canvas = tk.Canvas(container, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient='vertical', command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            '<Configure>',
            lambda e: canvas.configure(scrollregion=canvas.bbox('all'))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Enable mousewheel scrolling - bind to canvas only, not global
        def _on_mousewheel(event):
            try:
                if canvas.winfo_exists():
                    canvas.yview_scroll(int(-1*(event.delta/120)), 'units')
            except tk.TclError:
                pass
        
        canvas.bind('<MouseWheel>', _on_mousewheel)
        
        # Unbind on destroy
        def _on_destroy():
            try:
                canvas.unbind('<MouseWheel>')
            except:
                pass
        
        self.bind('<Destroy>', lambda e: _on_destroy() if e.widget == self else None)
        
        # Main frame for content
        main_frame = ttk.Frame(scrollable_frame, padding=20)
        main_frame.pack(fill='both', expand=True)
        
        # Title
        title = ttk.Label(
            main_frame,
            text="Pilih Tipe Pembayaran",
            font=FONTS['heading'],
            foreground=COLORS['primary']
        )
        title.pack(pady=10)
        
        # Total amount display
        amount_label = ttk.Label(
            main_frame,
            text=f"Total: {format_rp(self.total_amount)}",
            font=FONTS['normal']
        )
        amount_label.pack(pady=10)
        
        # Payment type selection
        self.payment_type_var = tk.StringVar(value="lunas")
        
        # Radio button frame
        radio_frame = ttk.LabelFrame(main_frame, text="Tipe Pembayaran", padding=10)
        radio_frame.pack(fill='x', pady=20)
        
        # Lunas option
        ttk.Radiobutton(
            radio_frame,
            text="💰 Lunas (Pembayaran Penuh)",
            variable=self.payment_type_var,
            value="lunas",
            command=self._on_payment_type_changed
        ).pack(anchor='w', pady=5)
        
        # Termin option
        ttk.Radiobutton(
            radio_frame,
            text="📅 Termin (Pembayaran Cicilan)",
            variable=self.payment_type_var,
            value="termin",
            command=self._on_payment_type_changed
        ).pack(anchor='w', pady=5)
        
        # Customer info frame (always visible)
        customer_frame = ttk.LabelFrame(main_frame, text="Informasi Customer", padding=10)
        customer_frame.pack(fill='x', pady=10)
        
        # Customer name (always visible for all payment types)
        ttk.Label(customer_frame, text="Nama Customer:").grid(row=0, column=0, sticky='w', pady=5)
        self.customer_name_var = tk.StringVar()
        ttk.Entry(customer_frame, textvariable=self.customer_name_var, width=30).grid(row=0, column=1, sticky='w', padx=5)
        
        # Phone number
        ttk.Label(customer_frame, text="Nomor Handphone:").grid(row=1, column=0, sticky='w', pady=5)
        self.customer_phone_var = tk.StringVar()
        ttk.Entry(customer_frame, textvariable=self.customer_phone_var, width=30).grid(row=1, column=1, sticky='w', padx=5)
        
        # Email address
        ttk.Label(customer_frame, text="Alamat Email:").grid(row=2, column=0, sticky='w', pady=5)
        self.customer_email_var = tk.StringVar()
        ttk.Entry(customer_frame, textvariable=self.customer_email_var, width=30).grid(row=2, column=1, sticky='w', padx=5)
        
        # Home address
        ttk.Label(customer_frame, text="Alamat Rumah:").grid(row=3, column=0, sticky='w', pady=5)
        self.customer_address_var = tk.StringVar()
        address_entry = tk.Text(customer_frame, height=3, width=30, font=FONTS['normal'])
        address_entry.grid(row=3, column=1, sticky='w', padx=5)
        
        def get_address_text():
            return address_entry.get("1.0", "end").strip()
        
        # Store reference to get address
        self._get_address = get_address_text
        
        # Termin details frame (initially hidden)
        self.termin_frame = ttk.LabelFrame(main_frame, text="Detail Termin", padding=10)
        self.termin_frame.pack(fill='x', pady=10)
        self.termin_frame.pack_forget()
        
        # Number of installments
        ttk.Label(self.termin_frame, text="Jumlah Cicilan:").grid(row=0, column=0, sticky='w', pady=5)
        self.installment_count_var = tk.StringVar(value="2")
        ttk.Spinbox(
            self.termin_frame,
            from_=2,
            to=12,
            textvariable=self.installment_count_var,
            width=10
        ).grid(row=0, column=1, sticky='w', padx=5)
        
        # First installment due date
        ttk.Label(self.termin_frame, text="Tanggal Termin Pertama:").grid(row=1, column=0, sticky='w', pady=5)
        self.first_due_date_var = tk.StringVar()
        self.first_due_date_entry = DateEntry(
            self.termin_frame,
            textvariable=self.first_due_date_var,
            width=15
        )
        self.first_due_date_entry.grid(row=1, column=1, sticky='w', padx=5)
        
        # Interval (days)
        ttk.Label(self.termin_frame, text="Interval (hari):").grid(row=2, column=0, sticky='w', pady=5)
        self.interval_var = tk.StringVar(value="30")
        ttk.Spinbox(
            self.termin_frame,
            from_=7,
            to=365,
            textvariable=self.interval_var,
            width=10
        ).grid(row=2, column=1, sticky='w', padx=5)
        
        # Spacer for scrollable area
        ttk.Frame(main_frame).pack(pady=20)
        
        # Button frame (placed after scrollable area)
        button_frame = ttk.Frame(self, padding=10)
        button_frame.pack(fill='x', side='bottom')
        
        ttk.Button(
            button_frame,
            text="✓ Lanjutkan",
            command=self._on_confirm
        ).pack(side='left', padx=5)
        
        ttk.Button(
            button_frame,
            text="✕ Batal",
            command=self.destroy
        ).pack(side='left', padx=5)
    
    def _on_payment_type_changed(self):
        """Handle payment type change."""
        if self.payment_type_var.get() == "termin":
            self.termin_frame.pack(fill='x', pady=10)
        else:
            self.termin_frame.pack_forget()
    
    def _on_confirm(self):
        """Handle confirm button."""
        payment_type = self.payment_type_var.get()
        
        if payment_type == "termin":
            # Validate customer name ONLY for termin payment
            if not self.customer_name_var.get().strip():
                messagebox.showwarning("Peringatan", "Nama customer harus diisi untuk pembayaran termin!")
                return
            
            # Validate termin inputs
            if not self.first_due_date_var.get():
                messagebox.showwarning("Peringatan", "Tanggal termin pertama harus diisi!")
                return
            
            try:
                installment_count = int(self.installment_count_var.get())
                interval = int(self.interval_var.get())
                
                if installment_count < 2 or installment_count > 12:
                    messagebox.showwarning("Peringatan", "Jumlah cicilan harus 2-12!")
                    return
                
                if interval < 7 or interval > 365:
                    messagebox.showwarning("Peringatan", "Interval harus 7-365 hari!")
                    return
            except ValueError:
                messagebox.showwarning("Peringatan", "Input harus berupa angka!")
                return
            
            # Calculate installment schedule
            from datetime import datetime, timedelta
            
            # Parse DateEntry format (MM/DD/YY)
            try:
                date_string = self.first_due_date_var.get()
                # Try multiple date formats
                first_due_date = None
                for date_format in ["%m/%d/%y", "%Y-%m-%d", "%d/%m/%Y"]:
                    try:
                        first_due_date = datetime.strptime(date_string, date_format).date()
                        break
                    except ValueError:
                        continue
                
                if first_due_date is None:
                    messagebox.showwarning("Peringatan", "Format tanggal tidak valid!")
                    return
            except Exception as e:
                messagebox.showwarning("Peringatan", f"Error parsing tanggal: {e}")
                return
            
            schedule = []
            
            # Sisa yang harus dicicil = total - DP
            # Tapi DP belum diketahui di sini, jadi untuk sekarang gunakan full total
            # DP akan ditanya di _process_payment() dan jadwal akan di-adjust
            amount_per_installment = self.total_amount // installment_count
            
            for i in range(installment_count):
                due_date = first_due_date + timedelta(days=interval * i)
                
                # Last installment gets the remainder
                if i == installment_count - 1:
                    amount = self.total_amount - (amount_per_installment * i)
                else:
                    amount = amount_per_installment
                
                schedule.append({
                    'amount': amount,
                    'due_date': due_date.isoformat(),
                    'notes': f'Cicilan ke-{i+1}'
                })
            
            self.termin_data = {
                'customer_name': self.customer_name_var.get(),
                'customer_phone': self.customer_phone_var.get(),
                'customer_email': self.customer_email_var.get(),
                'customer_address': self._get_address(),
                'installment_count': installment_count,
                'schedule': schedule,
                'total_amount': self.total_amount  # Simpan total asli
            }
        else:
            # For lunas payment, customer name is optional
            self.termin_data = {
                'customer_name': self.customer_name_var.get() if self.customer_name_var.get().strip() else None,
                'customer_phone': self.customer_phone_var.get(),
                'customer_email': self.customer_email_var.get(),
                'customer_address': self._get_address()
            }
        
        self.payment_type = payment_type
        self.result = (payment_type, self.termin_data)
        self.destroy()

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
        self.auth_manager = AuthManager(db)  # Initialize AuthManager untuk security
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
        """Process login dengan security features (rate limiting, attempt tracking)."""
        username = self.username_var.get().strip()
        password = self.password_var.get()
        
        if not username or not password:
            messagebox.showwarning("Peringatan", "Username dan password harus diisi!")
            logger.warning(f"Login attempt with empty credentials")
            return
        
        # Use AuthManager untuk security features (rate limiting, attempt tracking)
        success, message = self.auth_manager.login(username, password)
        
        if success:
            # Get user data untuk return
            user = self.db.get_user_by_username(username)
            self.result = user
            logger.info(f"User login successful: {username} (role: {user['role']})")
            self.destroy()
        else:
            # Show error message (includes rate limiting info)
            messagebox.showerror("Login Gagal", message)
            logger.warning(f"Failed login: {message}")
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
            
            # Initialize Invoice Service
            self.invoice_service = InvoiceService(self.db)
            self.invoice_pdf_generator = InvoicePDFGenerator(invoice_dir="invoices")
            logger.info("✅ Invoice service initialized")
            
            # Initialize Accounting Service untuk Pembukuan
            self.accounting_service = None
            if ACCOUNTING_AVAILABLE:
                try:
                    self.accounting_service = AccountingService(self.db)
                    logger.info("✅ Accounting service initialized")
                except Exception as e:
                    logger.warning(f"⚠️ Accounting service initialization failed: {e}")
            else:
                logger.warning("⚠️ Accounting service not available")
            
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
        
        # F2 → Focus to Diskon (%) field
        self.bind('<F2>', lambda e: self._focus_discount_field())
        
        # F3 → Process payment
        self.bind('<F3>', lambda e: self._process_payment())
        
        # Escape → Cancel transaction
        self.bind('<Escape>', lambda e: self._clear_transaction())
        
        logger.info("Keyboard shortcuts registered:")
        logger.info("  Enter → Add item")
        logger.info("  F1 → New transaction")
        logger.info("  F2 → Focus to Diskon (%) field")
        logger.info("  F3 → Process payment")
        logger.info("  Escape → Cancel transaction")
    
    def _on_enter_pressed(self, event):
        """Handle Enter key press - add item to transaction."""
        # Only process if transaction page is active and search field has focus or is empty
        try:
            # Check if product_listbox exists (means we're on transaction page)
            if hasattr(self, 'product_listbox'):
                # Check if focus is on qty_entry - let specific handler deal with it
                if hasattr(self, 'qty_entry') and self.focus_get() == self.qty_entry:
                    return 'break'  # Stop propagation, let qty_entry handler process it
                
                # Check if focus is on search_entry - let specific handler deal with it
                if hasattr(self, 'search_entry') and self.focus_get() == self.search_entry:
                    return 'break'  # Stop propagation, let search_entry handler process it
        except Exception as e:
            logger.debug(f"Enter key handler: {e}")
    
    def _focus_discount_field(self):
        """F2: Focus to Diskon (%) entry field and select all text."""
        try:
            if hasattr(self, 'discount_pct_entry'):
                self.discount_pct_entry.focus()
                self.discount_pct_entry.select_range(0, tk.END)
        except Exception as e:
            logger.debug(f"Focus discount field error: {e}")
    
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
        
        # Menu buttons - dengan role-based visibility
        is_admin = self.current_user['role'] == 'admin'
        menu_items = [
            ("🏠 Dashboard", self.show_dashboard, True),  # visible for all
            ("📦 Produk", self.show_products, is_admin),  # admin only
            ("📊 Stok Opname", self.show_stok_opname, is_admin),  # admin only
            ("🛒 Transaksi (F1)", self.show_transaction, True),
            ("📊 Laporan", self.show_reports, True),
            ("🧾 Invoice", self.show_invoices, True),  # Invoice menu - for all
            ("📚 Pembukuan", self.show_pembukuan, is_admin),  # Bookkeeping - admin only
            ("🎯 Promosi", self.show_promotions, is_admin),  # Promotions - admin only
            ("🤖 Telegram Bot", self.show_telegram, is_admin),  # admin only
        ]
        
        # Add Phase 4-5 features if available
        if PHASE_45_AVAILABLE and self.gui_services:
            menu_items.extend([
                ("📜 Riwayat Transaksi", self.show_transaction_history, True),
                ("📋 Restock Rekomendasi", self.show_restock_dashboard, True),
            ])
        
        # Add Settings only for admin
        if is_admin:
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
            # Cleanup async task manager
            try:
                cleanup_global_task_manager()
                logger.info("✅ Async task manager cleaned up")
            except Exception as e:
                logger.warning(f"⚠️ Error cleaning up task manager: {e}")
            
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
        """Show dashboard page with async loading."""
        self._clear_content()
        
        # Create scrollable content area with canvas and scrollbar
        canvas = tk.Canvas(self.content_area, bg=COLORS['bg_main'], highlightthickness=0, relief='flat', bd=0)
        scrollbar = ttk.Scrollbar(self.content_area, orient='vertical', command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        # Configure scrollbar appearance
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Create a window in the canvas
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        # Bind frame configure to update scroll region
        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # Make the frame width match canvas width
            canvas.itemconfig(canvas_window, width=canvas.winfo_width() if canvas.winfo_width() > 1 else 800)
        
        scrollable_frame.bind("<Configure>", _on_frame_configure)
        
        # Handle canvas configure to update frame width
        def _on_canvas_configure(event):
            if scrollable_frame.winfo_width() != event.width:
                canvas.itemconfig(canvas_window, width=event.width)
        
        canvas.bind("<Configure>", _on_canvas_configure)
        
        # Add mouse wheel scrolling support
        def _on_mousewheel(event):
            try:
                if canvas.winfo_exists():
                    scroll_units = int(-1*(event.delta/120))
                    canvas.yview_scroll(scroll_units, "units")
                    return "break"
            except (tk.TclError, AttributeError):
                pass
        
        # Bind mousewheel to canvas and scrollable_frame
        canvas.bind("<MouseWheel>", _on_mousewheel)
        scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
        
        # Add Page Up/Down keyboard scrolling support
        def _on_page_up(event):
            try:
                if canvas.winfo_exists():
                    canvas.yview_scroll(-10, "units")
                    return "break"
            except (tk.TclError, AttributeError):
                pass
        
        def _on_page_down(event):
            try:
                if canvas.winfo_exists():
                    canvas.yview_scroll(10, "units")
                    return "break"
            except (tk.TclError, AttributeError):
                pass
        
        canvas.bind("<Prior>", _on_page_up)   # Page Up
        canvas.bind("<Next>", _on_page_down)  # Page Down
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Header
        header = ttk.Label(
            scrollable_frame,
            text="📊 Dashboard",
            font=FONTS['title'],
            foreground=COLORS['primary']
        )
        header.pack(pady=10)
        
        # Stats cards container (will be filled asynchronously)
        stats_frame = ttk.Frame(scrollable_frame)
        stats_frame.pack(fill='x', pady=10)
        
        # Show loading indicator for stats
        loading_label = ttk.Label(
            stats_frame,
            text="⏳ Loading statistics...",
            font=FONTS['normal'],
            foreground=COLORS['info']
        )
        loading_label.pack(pady=20)
        
        # Load stats in background
        def load_stats():
            """Load dashboard stats in background thread."""
            try:
                stats = self.db.get_database_stats()
                dashboard_data = self.report_generator.get_dashboard_summary()
                return {
                    'stats': stats,
                    'dashboard_data': dashboard_data
                }
            except Exception as e:
                logger.error(f"Error loading dashboard stats: {e}")
                return None
        
        def on_stats_loaded(result):
            """Callback when stats are loaded."""
            if result is None:
                loading_label.config(text="❌ Error loading statistics")
                return
            
            loading_label.destroy()
            
            # Create stat cards
            stats = result['stats']
            dashboard_data = result['dashboard_data']
            
            cards_data = [
                ("📦 Total Produk", str(stats['total_products']), COLORS['info']),
                ("💰 Penjualan Hari Ini", format_rp(dashboard_data['hari_ini']['total_penjualan']), COLORS['success']),
                ("🔢 Transaksi Hari Ini", str(dashboard_data['hari_ini']['total_transaksi']), COLORS['warning']),
                ("📈 Rata-rata Transaksi", format_rp(int(dashboard_data['hari_ini']['rata_rata'])), COLORS['secondary']),
            ]
            
            for title, value, color in cards_data:
                self._create_stat_card(stats_frame, title, value, color)
            
            # Add termin payment warning section
            self._create_termin_warning_section(scrollable_frame)
            
            # Load chart section
            chart_frame = ttk.Frame(scrollable_frame)
            chart_frame.pack(fill='both', expand=True, pady=10)
            
            loading_chart_label = ttk.Label(
                chart_frame,
                text="⏳ Loading chart...",
                font=FONTS['normal'],
                foreground=COLORS['info']
            )
            loading_chart_label.pack(pady=20)
            
            # Load chart asynchronously
            def load_chart():
                try:
                    self._create_daily_sales_chart(chart_frame)
                    return True
                except Exception as e:
                    logger.error(f"Error loading chart: {e}")
                    return False
            
            def on_chart_loaded(success):
                if success:
                    loading_chart_label.destroy()
                    # Load AI recommendations asynchronously
                    load_recommendations()
                else:
                    loading_chart_label.config(text="❌ Error loading chart")
            
            # Execute chart loading
            chart_operation = AsyncOperation(
                scrollable_frame,
                load_chart,
                on_complete=on_chart_loaded,
                show_loading=False
            )
            chart_operation.start()
            
            # Load other sections
            self._create_ai_recommendations_section(scrollable_frame)
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
                btn.pack(pady=5)
        
        def load_recommendations():
            """Load recommendations asynchronously."""
            pass  # Can be implemented if needed
        
        # Start loading stats asynchronously
        stats_operation = AsyncOperation(
            scrollable_frame,
            load_stats,
            on_complete=on_stats_loaded,
            show_loading=False
        )
        stats_operation.start()
    
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
    
    def _create_termin_warning_section(self, parent):
        """Create termin payment warning section showing overdue and upcoming due dates."""
        try:
            # Get termin payment data
            overdue_payments = self.db.get_overdue_termin_payments()
            upcoming_payments = self.db.get_upcoming_termin_payments(days_ahead=5)
            
            # Only show warning section if there are overdue or upcoming payments
            if not overdue_payments and not upcoming_payments:
                return
            
            # Main warning frame
            warning_frame = tk.Frame(parent, bg=COLORS['bg_card'], relief='solid', bd=2)
            warning_frame.pack(fill='both', padx=10, pady=10)
            
            # Header with warning icon
            header_frame = tk.Frame(warning_frame, bg=COLORS['warning'], relief='flat', bd=0)
            header_frame.pack(fill='x')
            
            warning_title = tk.Label(
                header_frame,
                text="⚠️  PERINGATAN JATUH TEMPO PEMBAYARAN TERMIN",
                font=FONTS['subheading'],
                bg=COLORS['warning'],
                fg='white',
                pady=10
            )
            warning_title.pack()
            
            # Content frame with padding
            content_frame = tk.Frame(warning_frame, bg=COLORS['bg_card'])
            content_frame.pack(fill='both', expand=True, padx=10, pady=10)
            
            # Display overdue payments (red section)
            if overdue_payments:
                overdue_label = tk.Label(
                    content_frame,
                    text=f"🔴 TERLAMABAT ({len(overdue_payments)} pembayaran):",
                    font=FONTS['subheading'],
                    bg=COLORS['bg_card'],
                    fg=COLORS['danger'],
                    justify='left'
                )
                overdue_label.pack(fill='x', pady=(5, 10))
                
                for payment in overdue_payments[:5]:  # Show top 5
                    invoice_num = payment.get('invoice_number', 'N/A')
                    customer = payment.get('customer_name', 'N/A')
                    due_date = payment.get('due_date', 'N/A')
                    amount = payment.get('payment_amount', 0)
                    
                    # Calculate days overdue
                    from datetime import datetime, date
                    due_date_obj = datetime.strptime(due_date, '%Y-%m-%d').date()
                    days_overdue = (date.today() - due_date_obj).days
                    
                    info_text = f"  • {invoice_num} | {customer} | {format_rp(amount)} | Terlamabat {days_overdue} hari"
                    
                    info_label = tk.Label(
                        content_frame,
                        text=info_text,
                        font=FONTS['small'],
                        bg='#FFEBEE',  # Light red
                        fg=COLORS['danger'],
                        justify='left',
                        anchor='w'
                    )
                    info_label.pack(fill='x', pady=2)
                
                if len(overdue_payments) > 5:
                    more_label = tk.Label(
                        content_frame,
                        text=f"  ... dan {len(overdue_payments) - 5} pembayaran lainnya",
                        font=FONTS['small'],
                        bg=COLORS['bg_card'],
                        fg=COLORS['danger']
                    )
                    more_label.pack(fill='x', pady=2)
            
            # Display upcoming payments (yellow section)
            if upcoming_payments:
                if overdue_payments:
                    separator = tk.Frame(content_frame, bg=COLORS['border'], height=1)
                    separator.pack(fill='x', pady=10)
                
                upcoming_label = tk.Label(
                    content_frame,
                    text=f"🟡 AKAN JATUH TEMPO ({len(upcoming_payments)} pembayaran):",
                    font=FONTS['subheading'],
                    bg=COLORS['bg_card'],
                    fg=COLORS['warning'],
                    justify='left'
                )
                upcoming_label.pack(fill='x', pady=(5, 10))
                
                for payment in upcoming_payments[:5]:  # Show top 5
                    invoice_num = payment.get('invoice_number', 'N/A')
                    customer = payment.get('customer_name', 'N/A')
                    due_date = payment.get('due_date', 'N/A')
                    amount = payment.get('payment_amount', 0)
                    
                    # Calculate days until due
                    from datetime import datetime, date
                    due_date_obj = datetime.strptime(due_date, '%Y-%m-%d').date()
                    days_until_due = (due_date_obj - date.today()).days
                    
                    info_text = f"  • {invoice_num} | {customer} | {format_rp(amount)} | Jatuh tempo dalam {days_until_due} hari"
                    
                    info_label = tk.Label(
                        content_frame,
                        text=info_text,
                        font=FONTS['small'],
                        bg='#FFFBF0',  # Light yellow
                        fg='#D97706',  # Amber
                        justify='left',
                        anchor='w'
                    )
                    info_label.pack(fill='x', pady=2)
                
                if len(upcoming_payments) > 5:
                    more_label = tk.Label(
                        content_frame,
                        text=f"  ... dan {len(upcoming_payments) - 5} pembayaran lainnya",
                        font=FONTS['small'],
                        bg=COLORS['bg_card'],
                        fg=COLORS['warning']
                    )
                    more_label.pack(fill='x', pady=2)
            
            # Action button
            action_frame = tk.Frame(content_frame, bg=COLORS['bg_card'])
            action_frame.pack(fill='x', pady=10)
            
            action_btn = ttk.Button(
                action_frame,
                text="📋 Lihat Detail Termin",
                command=self.show_termin_payments
            )
            action_btn.pack()
            
        except Exception as e:
            logger.error(f"Error creating termin warning section: {e}")
    
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
        columns = ('No', 'Produk', 'Waktu', 'Total', 'Status Bayar')
        
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
            
            # Format status bayar based on payment type
            payment_type = trans.get('payment_type', 'lunas')
            if payment_type == 'termin':
                sisa_hutang = trans['total'] - trans['bayar']
                status_bayar = f"{format_rp(sisa_hutang)} (Hutang)"
            else:
                status_bayar = format_rp(trans['kembalian'])
            
            item_id = tree.insert('', 'end', values=(
                str(i),
                product_names,
                trans['tanggal'],
                format_rp(trans['total']),
                status_bayar
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
        
        # Tentukan label berdasarkan tipe pembayaran
        payment_type = trans.get('payment_type', 'lunas')
        
        if payment_type == 'termin':
            label_pembayaran = "DP (Down Payment)"
            sisa_hutang = trans['total'] - trans['bayar']
            label_kembalian = f"Sisa Hutang      "
            nilai_kembalian = sisa_hutang
        else:
            label_pembayaran = "Pembayaran       "
            label_kembalian = "Kembalian        "
            nilai_kembalian = trans['kembalian']
        
        summary_text = f"""
Total Belanja    : {format_rp(trans['total'])}
{label_pembayaran} : {format_rp(trans['bayar'])}
{label_kembalian} : {format_rp(nilai_kembalian)}
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
        """Generate receipt text format with discount and tax (dengan breakdown diskon)."""
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
            
            # Show per-item promotional discount if available
            if item.get('promotion_name'):
                discount_text = ""
                if item.get('discount_percent', 0) > 0:
                    discount_text = f"{item.get('discount_percent')}%"
                elif item.get('discount_nominal', 0) > 0:
                    discount_text = format_rp(item.get('discount_nominal', 0))
                
                if discount_text:
                    receipt.append(f"   └─ {item.get('promotion_name')}: -{discount_text}")
        
        receipt.append("-" * receipt_width)
        
        # Summary with proper alignment
        receipt.append(self._format_receipt_line("Subtotal", format_rp(subtotal), receipt_width))
        
        # Add promotional info if applicable
        promo_info = []
        try:
            # Collect promotional information from items dan format discount text
            for item in items:
                # Build discount text from discount_percent dan discount_nominal
                if item.get('promotion_name'):
                    discount_text = ""
                    
                    if item.get('discount_percent', 0) > 0:
                        discount_text = f"{item.get('discount_percent')}%"
                    elif item.get('discount_nominal', 0) > 0:
                        discount_text = format_rp(item.get('discount_nominal', 0))
                    
                    if discount_text:
                        promo_info.append({
                            'name': item.get('promotion_name'),
                            'discount': discount_text
                        })
            
            # Remove duplicates
            seen_promos = set()
            unique_promos = []
            for promo in promo_info:
                promo_key = f"{promo['name']}_{promo['discount']}"
                if promo_key not in seen_promos:
                    seen_promos.add(promo_key)
                    unique_promos.append(promo)
            
            # Display applied promotions
            if unique_promos:
                receipt.append("")
                receipt.append("🎯 PROMOSI BERLAKU:")
                receipt.append("-" * receipt_width)
                for i, promo in enumerate(unique_promos, 1):
                    promo_line = f"{i}. {promo['name']}: -{promo['discount']}"
                    receipt.append(promo_line)
                receipt.append("-" * receipt_width)
        except Exception as e:
            logger.debug(f"Error collecting promo info: {e}")
        
        # Add discount with breakdown if applicable
        discount = trans.get('discount_amount', 0) or 0
        if discount > 0:
            discount_pct = trans.get('discount_percent', 0) or 0
            
            # Show main discount line
            if discount_pct > 0:
                discount_line = f"Diskon ({discount_pct}%)"
            else:
                discount_line = "Diskon Manual"
            
            receipt.append(self._format_receipt_line(discount_line, f"-{format_rp(discount)}", receipt_width))
            
            # Tambahkan breakdown jika ada breakdown detail di trans
            # (Note: Breakdown detail mungkin tidak tersimpan di DB, akan ditampilkan dari current transaction)
            try:
                current_trans = self.transaction_handler.transaction_service.get_current_transaction()
                if current_trans:
                    breakdown = current_trans.get_discount_breakdown()
                    detail_lines = []
                    
                    promo_amount = breakdown.get('promo_amount', 0) or 0
                    if promo_amount > 0:
                        detail_lines.append(f"  Promo: {format_rp(promo_amount)}")
                    
                    manual_percent_amount = breakdown.get('manual_percent_amount', 0) or 0
                    if manual_percent_amount > 0:
                        detail_lines.append(f"  Manual %: {format_rp(manual_percent_amount)}")
                    
                    manual_fixed_amount = breakdown.get('manual_fixed_amount', 0) or 0
                    if manual_fixed_amount > 0:
                        detail_lines.append(f"  Manual Rp: {format_rp(manual_fixed_amount)}")
                    
                    for detail_line in detail_lines:
                        receipt.append(detail_line)
            except:
                pass  # Ignore if breakdown not available
        
        # Add tax if applicable
        tax = trans.get('tax_amount', 0) or 0
        if tax > 0:
            tax_pct = trans.get('tax_percent', 0) or 0
            tax_line = f"Pajak ({tax_pct}%)"
            receipt.append(self._format_receipt_line(tax_line, f"+{format_rp(tax)}", receipt_width))
        
        receipt.append("-" * receipt_width)
        receipt.append(self._format_receipt_line("Total Belanja", format_rp(trans['total']), receipt_width, bold=True))
        
        # Tentukan label berdasarkan tipe pembayaran
        payment_type = trans.get('payment_type', 'lunas')
        
        if payment_type == 'termin':
            receipt.append(self._format_receipt_line("DP (Down Payment)", format_rp(trans['bayar']), receipt_width))
            sisa_hutang = trans['total'] - trans['bayar']
            receipt.append(self._format_receipt_line("Sisa Hutang", format_rp(sisa_hutang), receipt_width))
        else:
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
        """Show products management page with async loading."""
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
        
        # Show loading indicator while fetching products
        loading_frame = ttk.Frame(self.content_area)
        loading_frame.pack(fill='both', expand=True, pady=50)
        
        loading_label = ttk.Label(
            loading_frame,
            text="⏳ Loading produk...",
            font=FONTS['normal'],
            foreground=COLORS['info']
        )
        loading_label.pack()
        
        # Load products in background thread
        def load_products():
            """Load products from database."""
            try:
                products = self.product_manager.list_products()
                return products
            except Exception as e:
                logger.error(f"Error loading products: {e}")
                return None
        
        def on_products_loaded(products):
            """Callback when products are loaded."""
            loading_frame.destroy()
            
            if products is None:
                error_label = ttk.Label(
                    self.content_area,
                    text="❌ Error loading products",
                    font=FONTS['normal'],
                    foreground=COLORS['danger']
                )
                error_label.pack(pady=20)
                return
            
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
                
                # Filter and display products
                filtered_products = []
                for p in products:
                    # Handle both dict and Product object
                    if isinstance(p, dict):
                        nama = (p.get('nama', '') or '').lower()
                        kode = (p.get('kode', '') or '').lower()
                    else:
                        # Product object
                        nama = (p.nama or '').lower()
                        kode = (p.kode or '').lower()
                    
                    if search_term in nama or search_term in kode:
                        filtered_products.append(p)
                
                # Add filtered products to table
                for i, product in enumerate(filtered_products, 1):
                    # Handle both dict and Product object
                    if isinstance(product, dict):
                        kode = product.get('kode', 'N/A')
                        nama = product.get('nama', 'N/A')
                        harga = product.get('harga', 0)
                        stok = product.get('stok', 0)
                        satuan = product.get('satuan', 'pcs')
                    else:
                        # Product object
                        kode = product.kode
                        nama = product.nama
                        harga = product.harga
                        stok = product.stok
                        satuan = product.satuan
                    
                    tree.insert('', 'end', values=(
                        str(i),
                        kode,
                        nama,
                        format_rp(harga),
                        f"{stok} {satuan}",
                        satuan,
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
        
        # Start async loading
        product_operation = AsyncOperation(
            self.content_area,
            load_products,
            on_complete=on_products_loaded,
            show_loading=False
        )
        product_operation.start()
    
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
            # Handle both dict and Product object
            if isinstance(prod, dict):
                prod_kode = str(prod.get('kode', '')).strip()
            else:
                prod_kode = str(prod.kode).strip()
            
            if prod_kode == product_kode:
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
        """Show transaction page with scrollable layout."""
        self._clear_content()
        
        # Create scrollable canvas for entire transaction page
        canvas = tk.Canvas(self.content_area, bg=COLORS['bg_main'], highlightthickness=0, relief='flat', bd=0)
        scrollbar = ttk.Scrollbar(self.content_area, orient='vertical', command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        # Configure scrollbar appearance
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Create a window in the canvas
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        # Bind frame configure to update scroll region
        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # Make the frame width match canvas width
            canvas.itemconfig(canvas_window, width=canvas.winfo_width() if canvas.winfo_width() > 1 else 800)
        
        scrollable_frame.bind("<Configure>", _on_frame_configure)
        
        # Handle canvas configure to update frame width
        def _on_canvas_configure(event):
            if scrollable_frame.winfo_width() != event.width:
                canvas.itemconfig(canvas_window, width=event.width)
        
        canvas.bind("<Configure>", _on_canvas_configure)
        
        # Add mouse wheel scrolling support - bind to canvas only (not bind_all)
        def _on_mousewheel(event):
            try:
                if canvas.winfo_exists():
                    scroll_units = int(-1*(event.delta/120))
                    canvas.yview_scroll(scroll_units, "units")
                    return "break"  # Prevent default behavior
            except (tk.TclError, AttributeError):
                pass
        
        # Bind mousewheel to canvas and scrollable_frame
        canvas.bind("<MouseWheel>", _on_mousewheel)
        scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
        
        # Add Page Up/Down keyboard scrolling support
        def _on_page_up(event):
            try:
                if canvas.winfo_exists():
                    canvas.yview_scroll(-10, "units")
                    return "break"
            except (tk.TclError, AttributeError):
                pass
        
        def _on_page_down(event):
            try:
                if canvas.winfo_exists():
                    canvas.yview_scroll(10, "units")
                    return "break"
            except (tk.TclError, AttributeError):
                pass
        
        canvas.bind("<Prior>", _on_page_up)   # Page Up
        canvas.bind("<Next>", _on_page_down)  # Page Down
        
        # Pack widgets with proper ordering
        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        
        # Header
        header = ttk.Label(
            scrollable_frame,
            text="🛒 Proses Transaksi",
            font=FONTS['title'],
            foreground=COLORS['primary']
        )
        header.pack(pady=10)
        
        # Main container with two columns
        main_frame = ttk.Frame(scrollable_frame)
        main_frame.pack(fill='both', expand=True, pady=10, padx=10)
        
        # Left side - Product search and add
        left_frame = ttk.LabelFrame(main_frame, text="📦 Tambah Item", padding=10)
        left_frame.pack(side='left', fill='both', expand=True, padx=5)
        
        ttk.Label(left_frame, text="Cari Produk (Kode/Nama):", font=FONTS['normal']).pack(anchor='w', pady=5)
        
        self.product_search_var = tk.StringVar()
        self.search_entry = ttk.Entry(
            left_frame,
            textvariable=self.product_search_var,
            width=30
        )
        self.search_entry.pack(fill='x', pady=5)
        self.search_entry.focus()
        
        # Bind KeyRelease event for dynamic filtering
        self.search_entry.bind('<KeyRelease>', lambda e: self._filter_product_list())
        self.search_entry.bind('<Down>', lambda e: self._focus_product_list())
        self.search_entry.bind('<Return>', self._on_product_search_enter)
        
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
        self.qty_entry = ttk.Entry(left_frame, textvariable=self.qty_var, width=30)
        self.qty_entry.pack(fill='x', pady=5)
        
        # Bind Enter key to add item and move focus back to search entry
        self.qty_entry.bind('<Return>', self._on_qty_enter)
        
        add_item_btn = ttk.Button(
            left_frame,
            text="➕ Tambah Item",
            command=self._add_transaction_item
        )
        add_item_btn.pack(fill='x', pady=10)
        
        # Right side - Cart summary
        right_frame = ttk.LabelFrame(main_frame, text="🛒 Keranjang Belanja", padding=10)
        right_frame.pack(side='right', fill='both', expand=True, padx=5)
        
        # Cart items display - Create frame for treeview with scrollbar
        cart_tree_frame = ttk.Frame(right_frame)
        cart_tree_frame.pack(fill='both', expand=True, pady=10)
        
        # Scrollbar for cart treeview
        cart_scrollbar = ttk.Scrollbar(cart_tree_frame, orient='vertical')
        cart_scrollbar.pack(side='right', fill='y')
        
        self.cart_tree = ttk.Treeview(
            cart_tree_frame,
            columns=('No', 'Produk', 'Qty', 'Harga', 'Diskon', 'Subtotal'),
            height=10,
            show='headings',
            yscrollcommand=cart_scrollbar.set
        )
        cart_scrollbar.config(command=self.cart_tree.yview)
        
        self.cart_tree.heading('No', text='No')
        self.cart_tree.heading('Produk', text='Produk')
        self.cart_tree.heading('Qty', text='Qty')
        self.cart_tree.heading('Harga', text='Harga')
        self.cart_tree.heading('Diskon', text='Diskon')
        self.cart_tree.heading('Subtotal', text='Subtotal')
        
        self.cart_tree.column('No', width=25)
        self.cart_tree.column('Produk', width=120)
        self.cart_tree.column('Qty', width=40)
        self.cart_tree.column('Harga', width=80)
        self.cart_tree.column('Diskon', width=90)
        self.cart_tree.column('Subtotal', width=80)
        
        self.cart_tree.pack(side='left', fill='both', expand=True)
        
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
        discount_payment_container = ttk.Frame(scrollable_frame)
        discount_payment_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Discount & Tax section (left side)
        discount_tax_frame = ttk.LabelFrame(discount_payment_container, text="💰 Diskon & Pajak", padding=10)
        discount_tax_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))
        
        # Discount section - Percentage
        discount_pct_inner = ttk.Frame(discount_tax_frame)
        discount_pct_inner.pack(side='left', padx=10)
        
        ttk.Label(discount_pct_inner, text="Diskon (%):", font=FONTS['normal']).pack(side='left', padx=5)
        self.discount_var = tk.StringVar(value="0")
        self.discount_pct_entry = ttk.Entry(discount_pct_inner, textvariable=self.discount_var, width=10)
        self.discount_pct_entry.pack(side='left', padx=5)
        self.discount_pct_entry.bind('<KeyRelease>', lambda e: self._update_discount())
        
        # Discount section - Fixed (Rupiah)
        discount_rp_inner = ttk.Frame(discount_tax_frame)
        discount_rp_inner.pack(side='left', padx=10)
        
        ttk.Label(discount_rp_inner, text="Diskon (Rp):", font=FONTS['normal']).pack(side='left', padx=5)
        self.discount_amount_var = tk.StringVar(value="0")
        discount_rp_entry = ttk.Entry(discount_rp_inner, textvariable=self.discount_amount_var, width=15)
        discount_rp_entry.pack(side='left', padx=5)
        discount_rp_entry.bind('<KeyRelease>', lambda e: self._update_discount_amount())
        
        # Tax section
        tax_inner = ttk.Frame(discount_tax_frame)
        tax_inner.pack(side='left', padx=10)
        
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
        payment_entry.pack(side='left', padx=2)
        
        # Buttons (in payment frame, right side)
        process_btn = ttk.Button(
            payment_frame,
            text="✅ Proses Pembayaran",
            command=self._process_payment
        )
        process_btn.pack(side='left', padx=2)
        
        clear_btn = ttk.Button(
            payment_frame,
            text="❌ Batalkan",
            command=self._clear_transaction
        )
        clear_btn.pack(side='left', padx=2)
        
        # Start a new transaction
        self.transaction_handler.start_transaction()
        self.discount_var.set("0")
        self.discount_amount_var.set("0")
        self.tax_var.set("0")
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
    
    def _on_product_search_enter(self, event):
        """Handle Enter key press in product search field - select product and move to quantity field."""
        try:
            # First, try to select from listbox if a product is highlighted
            selection = self.product_listbox.curselection()
            if selection:
                self._select_from_list()
            else:
                # If no selection, select the first item if available
                if self.product_listbox.size() > 0:
                    self.product_listbox.selection_set(0)
                    self._select_from_list()
                else:
                    messagebox.showwarning("Peringatan", "Produk tidak ditemukan!")
                    return 'break'
            
            # Move focus to quantity entry
            self.qty_entry.focus()
            self.qty_entry.select_range(0, tk.END)  # Select all text in qty field
            return 'break'  # Stop event propagation
        except Exception as e:
            logger.debug(f"Error in product search enter handler: {e}")
            return 'break'
    
    def _on_qty_enter(self, event):
        """Handle Enter key press in quantity field - add item to transaction."""
        try:
            # Add the transaction item
            self._add_transaction_item()
            
            # Move focus back to search entry for next product
            self.search_entry.focus()
            self.search_entry.select_range(0, tk.END)  # Select all text
            return 'break'  # Stop event propagation
        except Exception as e:
            logger.debug(f"Error in quantity enter handler: {e}")
            return 'break'
    
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
        """Update cart display with discount and tax calculations (dengan breakdown diskon terakumulasi)."""
        # Clear existing items
        for item in self.cart_tree.get_children():
            self.cart_tree.delete(item)
        
        # Get transaction
        trans = self.transaction_handler.transaction_service.get_current_transaction()
        
        if trans and trans.get_item_count() > 0:
            items = self.transaction_handler.get_items()
            if items:  # Check if items is not None
                for i, item in enumerate(items, 1):
                    # Format diskon per item
                    discount_display = ""
                    if item['discount_text']:
                        discount_display = f"-{item['discount_text']}"
                    
                    self.cart_tree.insert('', 'end', values=(
                        str(i),
                        item['nama'],
                        str(item['qty']),
                        format_rp(item['harga_satuan']),
                        discount_display,  # Tampilkan diskon per item
                        format_rp(item['subtotal'])
                    ))
            
            # Update subtotal, discount breakdown, tax, and total
            self.subtotal_label.config(text=format_rp(trans.subtotal))
            
            # Build discount display dengan breakdown LENGKAP
            breakdown = trans.get_discount_breakdown()
            discount_amount = trans.discount_amount or 0
            discount_text = f"-Rp {discount_amount:,}"
            
            # Tambahkan breakdown detail jika ada diskon dari berbagai sumber
            details = []
            
            # 1. Manual percentage discount
            manual_percent_amount = breakdown.get('manual_percent_amount', 0) or 0
            if manual_percent_amount > 0:
                details.append(f"Manual %: {trans.manual_discount_percent}% = Rp {manual_percent_amount:,}")
            
            # 2. Manual fixed amount discount
            manual_fixed_amount = breakdown.get('manual_fixed_amount', 0) or 0
            if manual_fixed_amount > 0:
                details.append(f"Manual Rp: Rp {manual_fixed_amount:,}")
            
            # 3. Promotional discounts (dari item-item dengan promo)
            promo_amount = breakdown.get('promo_amount', 0) or 0
            if promo_amount > 0:
                details.append(f"Promo: Rp {promo_amount:,}")
            
            # 4. Transaction-wide promotional discount
            trans_promo_discount = trans.promo_discount or 0
            if trans_promo_discount > 0:
                details.append(f"Promo Transaksi: Rp {trans_promo_discount:,}")
            
            if details:
                discount_text += "\n  Terakumulasi dari:\n  • " + "\n  • ".join(details)
            
            self.discount_label.config(text=discount_text)
            tax_amount = trans.tax_amount or 0
            self.tax_label.config(text=f"+Rp {tax_amount:,}")
            self.total_label.config(text=format_rp(trans.total))
        else:
            self.subtotal_label.config(text="Rp 0")
            self.discount_label.config(text="Rp 0")
            self.tax_label.config(text="Rp 0")
            self.total_label.config(text="Rp 0")
    
    def _update_discount(self):
        """Update discount percentage dan recalculate total (dapat dikombinasikan dengan diskon Rp)."""
        try:
            discount_percent = float(self.discount_var.get() or "0")
            
            # Validasi
            if discount_percent < 0 or discount_percent > 100:
                messagebox.showwarning("Peringatan", "Diskon harus antara 0-100%")
                self.discount_var.set("0")
                return
            
            # Set diskon percentage (NOT reset diskon fixed)
            trans = self.transaction_handler.transaction_service.get_current_transaction()
            if trans:
                trans.set_manual_discount_percent(discount_percent)
                self._update_cart_display()
                logger.info(f"Diskon manual % diupdate: {discount_percent}%")
        except ValueError:
            messagebox.showwarning("Peringatan", "Diskon harus berupa angka!")
            self.discount_var.set("0")
    
    def _update_discount_amount(self):
        """Update discount fixed amount dan recalculate total (dapat dikombinasikan dengan diskon %)."""
        try:
            discount_text = self.discount_amount_var.get().strip()
            
            if not discount_text or discount_text == "0":
                # Reset ke diskon fixed 0 jika kosong
                trans = self.transaction_handler.transaction_service.get_current_transaction()
                if trans:
                    trans.set_manual_discount_fixed(0)
                    self._update_cart_display()
                return
            
            discount_amount = int(discount_text)
            
            # Validasi
            if discount_amount < 0:
                messagebox.showwarning("Peringatan", "Diskon tidak boleh negatif!")
                self.discount_amount_var.set("0")
                return
            
            # Set diskon fixed (NOT reset diskon percentage)
            trans = self.transaction_handler.transaction_service.get_current_transaction()
            if trans:
                trans.set_manual_discount_fixed(discount_amount)
                self._update_cart_display()
                logger.info(f"Diskon manual Rp diupdate: Rp{discount_amount:,}")
        except ValueError:
            messagebox.showwarning("Peringatan", "Diskon harus berupa angka!")
            self.discount_amount_var.set("0")
    
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
        """Process payment dengan opsi lunas atau termin."""
        summary = self.transaction_handler.get_transaction_summary()
        
        if not summary or summary['items_count'] == 0:
            messagebox.showwarning("Peringatan", "Keranjang belanja kosong!")
            return
        
        try:
            # ================================================================
            # STEP 0: Apply transaction-wide promotions (berdasarkan total)
            # ================================================================
            promo_result = self.transaction_handler.apply_transaction_promotions()
            
            if promo_result['applied']:
                # Show promotion info dialog
                promo_msg = f"🎯 Promosi Berhasil Diterapkan!\n\n"
                promo_msg += f"Promosi: {promo_result['promotion_name']}\n"
                promo_msg += f"Total Sebelum: {format_rp(promo_result['total_before'])}\n"
                
                # Tambah info kelipatan jika ada
                multiplier = promo_result.get('multiplier', 1)
                if multiplier > 1:
                    promo_msg += f"Kelipatan: {multiplier}x\n"
                
                promo_msg += f"Diskon: {format_rp(promo_result['discount_amount'])}\n"
                promo_msg += f"Total Sesudah: {format_rp(promo_result['total_after'])}\n"
                messagebox.showinfo("Promosi Diterapkan", promo_msg)
                
                # Update summary dengan total yang sudah di-diskon
                summary = self.transaction_handler.get_transaction_summary()
                self._update_cart_display()  # Refresh display untuk update total
            
            # ================================================================
            # STEP 1: Show payment type dialog
            # ================================================================
            dialog = PaymentTypeDialog(self, summary['total'])
            
            if not dialog.result:
                # User cancelled
                return
            
            payment_type, termin_data = dialog.result
            
            if payment_type == "lunas":
                # ============================================================
                # PEMBAYARAN LUNAS (Normal payment flow)
                # ============================================================
                bayar = int(self.payment_var.get())
                
                if bayar < summary['total']:
                    messagebox.showwarning("Peringatan", f"Pembayaran kurang! (Total: {format_rp(summary['total'])})")
                    return
                
                try:
                    # Complete transaction as normal
                    trans_id = self.transaction_handler.complete_transaction(
                        bayar,
                        store_name="TOKO UBI BAROKAH IBU AWANG",
                        store_address="Jl. Desa Mekarbakti, pertigaan Cilembu."
                    )
                    logger.info(f"Lunas transaction completed: trans_id={trans_id}, bayar={bayar}")
                except Exception as e:
                    logger.error(f"Error completing lunas transaction: {e}", exc_info=True)
                    messagebox.showerror("Error", f"Gagal memproses transaksi: {str(e)}")
                    return
                
                if trans_id:
                    kembalian = bayar - summary['total']
                    
                    # Auto-save receipt
                    self.transaction_handler.print_receipt(
                        store_name="TOKO UBI BAROKAH IBU AWANG",
                        store_address="Jl. Desa Mekarbakti, pertigaan Cilembu."
                    )
                    
                    # Create invoice
                    self._create_invoice_and_display(trans_id, summary, kembalian)
                    
                    # Reset cart
                    self.transaction_handler.cancel_transaction()
                    self._update_cart_display()
                else:
                    messagebox.showerror("Error", "Gagal memproses transaksi: ID transaksi tidak tergenerate!")
            
            elif payment_type == "termin":
                # ============================================================
                # PEMBAYARAN TERMIN (Installment payment)
                # ============================================================
                # Create termin payment service
                termin_service = TerminPaymentService(self.db)
                
                # Bayar DP (Down Payment) atau lunas DP?
                dp_choice = messagebox.askyesno(
                    "Down Payment",
                    f"Masukkan Down Payment?\n\nTotal: {format_rp(summary['total'])}\nHitung berapa DP?"
                )
                
                if dp_choice:
                    try:
                        dp_amount_str = simpledialog.askstring(
                            "Down Payment",
                            f"Masukkan jumlah DP (Rp):\n\nTotal: {format_rp(summary['total'])}"
                        )
                        
                        if not dp_amount_str:
                            messagebox.showwarning("Batalkan", "DP harus dimasukkan untuk termin!")
                            return
                        
                        dp_amount = int(dp_amount_str)
                        
                        if dp_amount <= 0 or dp_amount > summary['total']:
                            messagebox.showwarning("Peringatan", f"DP harus 1 sampai {format_rp(summary['total'])}!")
                            return
                    except ValueError:
                        messagebox.showerror("Error", "DP harus berupa angka!")
                        return
                else:
                    dp_amount = summary['total']  # Bayar semua dulu jika tidak ada DP
                
                # Complete transaction terlebih dahulu
                try:
                    trans_id = self.transaction_handler.complete_transaction(
                        dp_amount,
                        store_name="TOKO UBI BAROKAH IBU AWANG",
                        store_address="Jl. Desa Mekarbakti, pertigaan Cilembu.",
                        is_termin=True
                    )
                    logger.info(f"Termin transaction completed: trans_id={trans_id}, dp_amount={dp_amount}")
                except Exception as e:
                    logger.error(f"Error completing termin transaction: {e}", exc_info=True)
                    messagebox.showerror("Error", f"Gagal memproses transaksi: {str(e)}")
                    return
                
                if trans_id:
                    try:
                        # Auto-save receipt
                        self.transaction_handler.print_receipt(
                            store_name="TOKO UBI BAROKAH IBU AWANG",
                            store_address="Jl. Desa Mekarbakti, pertigaan Cilembu."
                        )
                        
                        # Create termin invoice
                        if 'schedule' in termin_data and termin_data['schedule']:
                            # Hitung ulang jadwal cicilan setelah dikurangi DP
                            remaining_amount = summary['total'] - dp_amount
                            adjusted_schedule = self._adjust_termin_schedule(
                                termin_data,
                                dp_amount,
                                remaining_amount
                            )
                            
                            success, msg, invoice_id = termin_service.create_termin_invoice(
                                trans_id,
                                termin_data['customer_name'],
                                adjusted_schedule,
                                customer_phone=termin_data.get('customer_phone'),
                                customer_email=termin_data.get('customer_email'),
                                customer_address=termin_data.get('customer_address')
                            )
                        else:
                            logger.warning("No termin schedule found in termin_data")
                            messagebox.showerror("Error", "Data jadwal termin tidak lengkap!")
                            return
                        
                        logger.info(f"Termin invoice creation result: success={success}, invoice_id={invoice_id}, msg={msg}")
                        
                        if success:
                            # Hitung ulang jadwal untuk display
                            remaining_amount = summary['total'] - dp_amount
                            adjusted_schedule = self._adjust_termin_schedule(
                                termin_data,
                                dp_amount,
                                remaining_amount
                            )
                            
                            # Display termin schedule
                            schedule_text = f"✅ Invoice Termin Berhasil Dibuat!\n\n"
                            schedule_text += f"Invoice ID: {invoice_id}\n"
                            schedule_text += f"Customer: {termin_data['customer_name']}\n"
                            schedule_text += f"Total: {format_rp(summary['total'])}\n"
                            schedule_text += f"DP: {format_rp(dp_amount)}\n"
                            schedule_text += f"Sisa Cicilan: {format_rp(remaining_amount)}\n"
                            schedule_text += f"\n📅 Jadwal Pembayaran:\n"
                            schedule_text += "="*50 + "\n"
                            
                            for idx, payment in enumerate(adjusted_schedule, 1):
                                schedule_text += f"{idx}. Rp {payment['amount']:,} - {payment['due_date']}\n"
                            
                            schedule_text += "="*50 + "\n"
                            
                            # Jangan buat invoice lagi (sudah dibuat di create_termin_invoice)
                            # Hanya tampilkan pesan sukses
                            messagebox.showinfo("Termin Invoice", schedule_text)
                            
                            # Reset cart
                            self.transaction_handler.cancel_transaction()
                            self._update_cart_display()
                        else:
                            messagebox.showerror("Error", f"Gagal membuat invoice termin: {msg}")
                    except Exception as e:
                        logger.error(f"Error in termin payment process: {e}", exc_info=True)
                        messagebox.showerror("Error", f"Error dalam proses termin: {str(e)}")
                else:
                    messagebox.showerror("Error", "Gagal memproses transaksi: ID transaksi tidak tergenerate!")
            
        except ValueError as e:
            logger.error(f"ValueError in payment process: {e}", exc_info=True)
            messagebox.showerror("Error", "Jumlah pembayaran harus berupa angka!")
        except Exception as e:
            logger.error(f"Unexpected error in payment process: {e}", exc_info=True)
            messagebox.showerror("Error", f"Error yang tidak terduga: {str(e)}")
    
    def _create_invoice_and_display(self, trans_id: int, summary: dict, kembalian: int = 0, is_termin: bool = False):
        """
        Helper method untuk create invoice dan tampilkan.
        
        Args:
            trans_id (int): Transaction ID
            summary (dict): Transaction summary
            kembalian (int): Kembalian untuk pembayaran lunas
            is_termin (bool): Apakah ini termin invoice
        """
        try:
            invoice_id = self.invoice_service.create_invoice_from_transaction(trans_id)
            
            if invoice_id:
                # Get invoice detail untuk PDF generation
                invoice_detail = self.db.get_invoice_detail(invoice_id)
                
                if invoice_detail:
                    invoice_data = invoice_detail['invoice']
                    invoice_data['items'] = invoice_detail.get('items', [])
                    
                    # Generate PDF invoice
                    pdf_filepath = self.invoice_pdf_generator.generate_invoice_pdf(
                        invoice_data,
                        store_name="TOKO UBI BAROKAH IBU AWANG",
                        store_address="Jl. Desa Mekarbakti, pertigaan Cilembu.",
                        store_phone=None,
                        db=self.db
                    )
                    
                    if pdf_filepath:
                        logger.info(f"✅ Invoice PDF generated: {pdf_filepath}")
                    else:
                        logger.warning("⚠️ PDF generation skipped (reportlab not available)")
            else:
                logger.warning(f"⚠️ Failed to create invoice for transaction {trans_id}")
        except Exception as e:
            logger.error(f"⚠️ Invoice creation error: {e}")
        
        # Ask to view receipt
        if is_termin:
            lihat_resi = messagebox.askyesno(
                "Transaksi Termin Selesai",
                f"✅ Invoice Termin berhasil dibuat!\n\nID: {trans_id}\nTotal: {format_rp(summary['total'])}\n\n📄 Lihat resi?"
            )
        else:
            lihat_resi = messagebox.askyesno(
                "Transaksi Selesai",
                f"✅ Transaksi berhasil!\n\nID: {trans_id}\nTotal: {format_rp(summary['total'])}\nKembalian: {format_rp(kembalian)}\n\n📄 Lihat resi?"
            )
        
        if lihat_resi:
            # Get transaction detail for viewing
            transaction = self.db.get_transaction(trans_id)
            if transaction:
                trans_data = transaction.get('transaction', transaction)
                items = transaction.get('items', [])
                receipt_text = self._generate_receipt_text(trans_data, items)
                self._print_report_dialog(receipt_text, f"resi_{trans_id}")
        
        messagebox.showinfo("Sukses", f"✅ Resi berhasil disimpan!\n📁 Lokasi: receipts/receipt_{trans_id}.txt")
        self.show_transaction()
    
    def _clear_transaction(self):
        """Clear transaction."""
        if messagebox.askyesno("Konfirmasi", "Batalkan transaksi?"):
            self.transaction_handler.cancel_transaction()
            self.show_transaction()
    
    def _adjust_termin_schedule(self, termin_data: dict, dp_amount: int, remaining_amount: int) -> list:
        """
        Adjust termin payment schedule setelah dikurangi DP.
        
        Args:
            termin_data (dict): Original termin data dengan schedule
            dp_amount (int): Jumlah DP yang dibayarkan
            remaining_amount (int): Sisa yang harus dicicil (total - dp)
        
        Returns:
            list: Adjusted schedule dengan total = remaining_amount
        """
        if not termin_data or 'schedule' not in termin_data:
            return []
        
        original_schedule = termin_data['schedule']
        if not original_schedule:
            return []
        
        # Hitung berapa banyak cicilan
        installment_count = len(original_schedule)
        
        # Hitung jumlah per cicilan dari remaining_amount
        amount_per_installment = remaining_amount // installment_count
        
        # Buat adjusted schedule
        adjusted_schedule = []
        for i in range(installment_count):
            # Last installment gets the remainder
            if i == installment_count - 1:
                amount = remaining_amount - (amount_per_installment * i)
            else:
                amount = amount_per_installment
            
            adjusted_schedule.append({
                'amount': amount,
                'due_date': original_schedule[i]['due_date'],
                'notes': original_schedule[i].get('notes', f'Cicilan ke-{i+1}')
            })
        
        logger.info(f"✅ Termin schedule adjusted: installments={installment_count}, remaining={remaining_amount}, per_installment={amount_per_installment}")
        return adjusted_schedule
    
    # ========================================================================
    # REPORTS PAGE
    # ========================================================================
    
    def show_reports(self):
        """Show reports page with lazy loading for tabs."""
        self._clear_content()
        
        # Header
        header = ttk.Label(
            self.content_area,
            text="📊 Laporan & Analisis",
            font=FONTS['title'],
            foreground=COLORS['primary']
        )
        header.pack(pady=10)
        
        # Tabs for different reports (with lazy loading)
        notebook = ttk.Notebook(self.content_area)
        notebook.pack(fill='both', expand=True, pady=10, padx=10)
        
        # Store frames for lazy loading
        tab_frames = {}
        tab_loaded = {}
        
        # Create tab frames (initially empty)
        tab_configs = [
            ("📅 Laporan Harian", "daily", self._create_daily_report_tab),
            ("📆 Laporan Periode", "period", self._create_period_report_tab),
            ("🏆 Produk Terlaris", "bestselling", self._create_bestselling_tab),
            ("📦 Informasi Stok", "stock", self._create_stock_info_tab),
            ("💳 Pembayaran Termin", "termin", self._create_termin_report_tab),
        ]
        
        for tab_label, tab_id, tab_func in tab_configs:
            frame = ttk.Frame(notebook)
            notebook.add(frame, text=tab_label)
            tab_frames[tab_id] = frame
            tab_loaded[tab_id] = False
        
        def on_tab_changed(event):
            """Load tab content when tab is selected."""
            selected_tab_id = notebook.tabs()[notebook.index(notebook.select())]
            selected_tab_name = notebook.tab(selected_tab_id, "text")
            
            # Find which tab was selected
            for tab_label, tab_id, tab_func in tab_configs:
                if tab_label == selected_tab_name and not tab_loaded[tab_id]:
                    # Load this tab asynchronously
                    frame = tab_frames[tab_id]
                    
                    loading_label = ttk.Label(
                        frame,
                        text="⏳ Loading...",
                        font=FONTS['normal'],
                        foreground=COLORS['info']
                    )
                    loading_label.pack(pady=50)
                    
                    def load_tab_data():
                        try:
                            return True
                        except Exception as e:
                            logger.error(f"Error loading tab {tab_id}: {e}")
                            return False
                    
                    def on_tab_data_loaded(success):
                        if success:
                            loading_label.destroy()
                            # Call the tab creation function
                            try:
                                tab_func(frame)
                                tab_loaded[tab_id] = True
                            except Exception as e:
                                error_label = ttk.Label(
                                    frame,
                                    text=f"❌ Error: {str(e)}",
                                    font=FONTS['normal'],
                                    foreground=COLORS['danger']
                                )
                                error_label.pack(pady=20)
                        else:
                            loading_label.config(text="❌ Error loading data")
                    
                    # Load asynchronously
                    tab_operation = AsyncOperation(
                        frame,
                        load_tab_data,
                        on_complete=on_tab_data_loaded,
                        show_loading=False
                    )
                    tab_operation.start()
        
        # Bind tab change event
        notebook.bind("<<NotebookTabChanged>>", on_tab_changed)
        
        # Load first tab automatically
        if tab_configs:
            first_frame = tab_frames[tab_configs[0][1]]
            try:
                tab_configs[0][2](first_frame)
                tab_loaded[tab_configs[0][1]] = True
            except Exception as e:
                logger.error(f"Error loading first tab: {e}")
                error_label = ttk.Label(
                    first_frame,
                    text=f"❌ Error: {str(e)}",
                    font=FONTS['normal'],
                    foreground=COLORS['danger']
                )
                error_label.pack(pady=20)
    
    def _create_daily_report_tab(self, parent):
        """Create daily report tab."""
        laporan = self.report_generator.get_laporan_harian()
        
        # Create canvas with scrollbar for entire tab
        canvas = tk.Canvas(parent, bg=COLORS['bg_main'], highlightthickness=0, relief='flat', bd=0)
        scrollbar = ttk.Scrollbar(parent, orient='vertical', command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        # Configure scrollbar appearance
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Create a window in the canvas
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        # Bind frame configure to update scroll region
        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # Make the frame width match canvas width
            canvas.itemconfig(canvas_window, width=canvas.winfo_width() if canvas.winfo_width() > 1 else 800)
        
        scrollable_frame.bind("<Configure>", _on_frame_configure)
        
        # Handle canvas configure to update frame width
        def _on_canvas_configure(event):
            if scrollable_frame.winfo_width() != event.width:
                canvas.itemconfig(canvas_window, width=event.width)
        
        canvas.bind("<Configure>", _on_canvas_configure)
        
        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            try:
                if canvas.winfo_exists():
                    scroll_units = int(-1*(event.delta/120))
                    canvas.yview_scroll(scroll_units, "units")
                    return "break"
            except (tk.TclError, AttributeError):
                pass
        
        canvas.bind("<MouseWheel>", _on_mousewheel)
        scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
        
        # Add Page Up/Down keyboard scrolling support
        def _on_page_up(event):
            try:
                if canvas.winfo_exists():
                    canvas.yview_scroll(-10, "units")
                    return "break"
            except (tk.TclError, AttributeError):
                pass
        
        def _on_page_down(event):
            try:
                if canvas.winfo_exists():
                    canvas.yview_scroll(10, "units")
                    return "break"
            except (tk.TclError, AttributeError):
                pass
        
        canvas.bind("<Prior>", _on_page_up)   # Page Up
        canvas.bind("<Next>", _on_page_down)  # Page Down
        
        # Pack canvas and scrollbar
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Summary
        summary_frame = ttk.LabelFrame(scrollable_frame, text="📊 Summary", padding=10)
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
        trans_frame = ttk.LabelFrame(scrollable_frame, text="📋 Daftar Transaksi", padding=10)
        trans_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        columns = ('No', 'ID', 'Produk', 'Total', 'Pembayaran', 'Status')
        tree = ttk.Treeview(trans_frame, columns=columns, height=15, show='headings')
        
        tree.heading('No', text='No')
        tree.heading('ID', text='ID')
        tree.heading('Produk', text='Produk')
        tree.heading('Total', text='Total')
        tree.heading('Pembayaran', text='Pembayaran')
        tree.heading('Status', text='Kembalian/Hutang')
        
        tree.column('No', width=30)
        tree.column('ID', width=60)
        tree.column('Produk', width=250)
        tree.column('Total', width=100)
        tree.column('Pembayaran', width=100)
        tree.column('Status', width=120)
        
        for i, trans in enumerate(laporan.get('transactions', []), 1):
            # Format status bayar based on payment type
            payment_type = trans.get('payment_type', 'lunas')
            if payment_type == 'termin':
                sisa_hutang = trans['total'] - trans['bayar']
                status_bayar = f"{format_rp(sisa_hutang)} (Hutang)"
            else:
                status_bayar = format_rp(trans['kembalian'])
            
            tree.insert('', 'end', values=(
                str(i),
                trans['id'],
                trans.get('product_names', ''),
                format_rp(trans['total']),
                format_rp(trans['bayar']),
                status_bayar
            ))
        
        scrollbar = ttk.Scrollbar(trans_frame, orient='vertical', command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        tree.pack(fill='both', expand=True)
        
        # Print button
        btn_frame = ttk.Frame(scrollable_frame)
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
        # Create canvas with scrollbar for entire tab
        canvas = tk.Canvas(parent, bg=COLORS['bg_main'], highlightthickness=0, relief='flat', bd=0)
        scrollbar = ttk.Scrollbar(parent, orient='vertical', command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        # Configure scrollbar appearance
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Create a window in the canvas
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        # Bind frame configure to update scroll region
        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # Make the frame width match canvas width
            canvas.itemconfig(canvas_window, width=canvas.winfo_width() if canvas.winfo_width() > 1 else 800)
        
        scrollable_frame.bind("<Configure>", _on_frame_configure)
        
        # Handle canvas configure to update frame width
        def _on_canvas_configure(event):
            if scrollable_frame.winfo_width() != event.width:
                canvas.itemconfig(canvas_window, width=event.width)
        
        canvas.bind("<Configure>", _on_canvas_configure)
        
        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            try:
                if canvas.winfo_exists():
                    scroll_units = int(-1*(event.delta/120))
                    canvas.yview_scroll(scroll_units, "units")
                    return "break"
            except (tk.TclError, AttributeError):
                pass
        
        canvas.bind("<MouseWheel>", _on_mousewheel)
        scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
        
        # Add Page Up/Down keyboard scrolling support
        def _on_page_up(event):
            try:
                if canvas.winfo_exists():
                    canvas.yview_scroll(-10, "units")
                    return "break"
            except (tk.TclError, AttributeError):
                pass
        
        def _on_page_down(event):
            try:
                if canvas.winfo_exists():
                    canvas.yview_scroll(10, "units")
                    return "break"
            except (tk.TclError, AttributeError):
                pass
        
        canvas.bind("<Prior>", _on_page_up)   # Page Up
        canvas.bind("<Next>", _on_page_down)  # Page Down
        
        # Pack canvas and scrollbar
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Date range selector
        selector_frame = ttk.LabelFrame(scrollable_frame, text="Pilih Periode", padding=10)
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
    
    def _create_termin_report_tab(self, parent):
        """Create termin payment tracking tab - unified view of all pending termin payments."""
        # Get all pending termin payments from termin_payments table (consistent with detail page)
        all_termin_payments = self.db.get_all_pending_termin_payments()
        
        # Create canvas with scrollbar for the entire tab content
        canvas = tk.Canvas(parent, bg=COLORS['bg_main'], highlightthickness=0, relief='flat', bd=0)
        scrollbar = ttk.Scrollbar(parent, orient='vertical', command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style='TFrame')
        
        # Configure scrollbar appearance
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Create a window in the canvas
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        # Bind frame configure to update scroll region
        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # Make the frame width match canvas width
            canvas.itemconfig(canvas_window, width=canvas.winfo_width() if canvas.winfo_width() > 1 else 800)
        
        scrollable_frame.bind("<Configure>", _on_frame_configure)
        
        # Handle canvas configure to update frame width
        def _on_canvas_configure(event):
            if scrollable_frame.winfo_width() != event.width:
                canvas.itemconfig(canvas_window, width=event.width)
        
        canvas.bind("<Configure>", _on_canvas_configure)
        
        # Bind mousewheel to canvas only (not global)
        def _on_mousewheel(event):
            try:
                if canvas.winfo_exists():
                    scroll_units = int(-1*(event.delta/120))
                    canvas.yview_scroll(scroll_units, "units")
                    return "break"
            except (tk.TclError, AttributeError):
                pass
        
        canvas.bind("<MouseWheel>", _on_mousewheel)
        scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
        
        # Add Page Up/Down keyboard scrolling support
        def _on_page_up(event):
            try:
                if canvas.winfo_exists():
                    canvas.yview_scroll(-10, "units")
                    return "break"
            except (tk.TclError, AttributeError):
                pass
        
        def _on_page_down(event):
            try:
                if canvas.winfo_exists():
                    canvas.yview_scroll(10, "units")
                    return "break"
            except (tk.TclError, AttributeError):
                pass
        
        canvas.bind("<Prior>", _on_page_up)   # Page Up
        canvas.bind("<Next>", _on_page_down)  # Page Down
        
        # Pack canvas and scrollbar
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        canvas.bind("<MouseWheel>", _on_mousewheel)
        
        # Header
        header_frame = ttk.Frame(scrollable_frame)
        header_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(
            header_frame,
            text="💳 Tracking Pembayaran Termin",
            font=FONTS['heading'],
            foreground=COLORS['primary']
        ).pack(side='left')
        
        # Summary
        summary_frame = ttk.LabelFrame(scrollable_frame, text="📊 Summary Termin", padding=10)
        summary_frame.pack(fill='x', padx=10, pady=10)
        
        # Calculate summary from termin_payments
        total_pending = len(all_termin_payments)
        total_amount = sum(item.get('payment_amount', 0) for item in all_termin_payments)
        
        from datetime import date
        today = date.today()
        overdue_count = 0
        for item in all_termin_payments:
            due_date_str = item.get('due_date', '')
            if due_date_str:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                if due_date < today:
                    overdue_count += 1
        
        summary_text = f"""
Total Pembayaran Pending     : {total_pending} cicilan
Total Jumlah Pembayaran      : {format_rp(total_amount)}
Pembayaran Terlamabat        : {overdue_count} cicilan
Pembayaran Akan Jatuh Tempo  : {total_pending - overdue_count} cicilan
        """
        
        summary_label = tk.Label(
            summary_frame,
            text=summary_text,
            font=FONTS['mono'],
            justify='left',
            bg=COLORS['bg_card']
        )
        summary_label.pack(anchor='w')
        
        # Check if there are pending termin payments
        if not all_termin_payments:
            # Show "no data" message instead of empty list
            empty_frame = ttk.Frame(scrollable_frame)
            empty_frame.pack(fill='both', expand=True, padx=10, pady=10)
            
            empty_label = ttk.Label(
                empty_frame,
                text="📭 Tidak ada pembayaran termin yang tertunda",
                font=FONTS['heading'],
                foreground=COLORS['text_secondary']
            )
            empty_label.pack(pady=50)
            return
        
        # Termin payments list
        list_frame = ttk.LabelFrame(scrollable_frame, text="📋 Daftar Pembayaran Termin Pending", padding=10)
        list_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        columns = ('No', 'Invoice', 'Customer', 'Jatuh Tempo', 'Jumlah', 'Status Hari')
        tree = ttk.Treeview(list_frame, columns=columns, height=15, show='headings')
        
        tree.heading('No', text='No')
        tree.heading('Invoice', text='Invoice')
        tree.heading('Customer', text='Customer')
        tree.heading('Jatuh Tempo', text='Jatuh Tempo')
        tree.heading('Jumlah', text='Jumlah')
        tree.heading('Status Hari', text='Status Hari')
        
        tree.column('No', width=30)
        tree.column('Invoice', width=120)
        tree.column('Customer', width=100)
        tree.column('Jatuh Tempo', width=100)
        tree.column('Jumlah', width=120)
        tree.column('Status Hari', width=120)
        
        for i, payment in enumerate(all_termin_payments, 1):
            invoice_num = payment.get('invoice_number', 'N/A')
            customer = payment.get('customer_name', 'N/A')
            due_date = payment.get('due_date', '')
            amount = payment.get('payment_amount', 0)
            
            # Calculate days status
            from datetime import date
            due_date_obj = datetime.strptime(due_date, '%Y-%m-%d').date()
            if due_date_obj < date.today():
                days_info = f"Terlamabat {(date.today() - due_date_obj).days} hari"
            else:
                days_info = f"Dalam {(due_date_obj - date.today()).days} hari"
            
            tree.insert('', 'end', values=(
                str(i),
                invoice_num,
                customer,
                due_date,
                format_rp(amount),
                days_info
            ))
        
        scrollbar_tree = ttk.Scrollbar(list_frame, orient='vertical', command=tree.yview)
        tree.configure(yscroll=scrollbar_tree.set)
        scrollbar_tree.pack(side='right', fill='y')
        tree.pack(fill='both', expand=True)
        
        # Right-click context menu for termin details
        def on_right_click(event):
            """Show context menu on right-click."""
            item = tree.selection()
            if not item:
                return
            
            # Create context menu
            context_menu = tk.Menu(self, tearoff=False)
            context_menu.add_command(
                label="📋 Lihat Detail Termin",
                command=lambda: on_show_detail(tree.item(item[0])['values'])
            )
            context_menu.add_command(
                label="💳 Bayar Cicilan",
                command=on_bayar_cicilan
            )
            context_menu.add_command(
                label="✅ Pelunasan Sisa Hutang",
                command=on_pelunasan
            )
            
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()
        
        def on_show_detail(values):
            """Show detail termin dialog."""
            if len(values) < 2:
                return
            
            invoice_num = values[1]
            customer = values[2]
            due_date = values[3]
            amount = values[4]
            
            # Find invoice_id from invoice_number
            invoice_id = None
            for payment in all_termin_payments:
                if payment.get('invoice_number') == invoice_num:
                    invoice_id = payment.get('invoice_id')
                    break
            
            if not invoice_id:
                messagebox.showerror("Error", "Invoice tidak ditemukan")
                return
            
            # Show detail dialog
            self._show_termin_detail_dialog(invoice_id, invoice_num, customer, due_date, amount)
        
        tree.bind('<Button-3>', on_right_click)
        
        # Action buttons for termin payments
        action_frame = ttk.Frame(scrollable_frame)
        action_frame.pack(fill='x', padx=10, pady=15)
        
        def on_bayar_cicilan():
            """Handle bayar cicilan action."""
            selected_items = tree.selection()
            if not selected_items:
                messagebox.showwarning("Peringatan", "Pilih pembayaran termin yang akan dibayar")
                return
            
            selected_item = selected_items[0]
            values = tree.item(selected_item)['values']
            
            # values: (No, Invoice, Customer, Jatuh Tempo, Jumlah, Status Hari)
            if len(values) < 2:
                return
            
            invoice_num = values[1]
            customer = values[2]
            cicilan_amount = values[4]  # Jumlah cicilan
            
            # Find invoice_id from invoice_number
            invoice_id = None
            for payment in all_termin_payments:
                if payment.get('invoice_number') == invoice_num:
                    invoice_id = payment.get('invoice_id')
                    break
            
            if not invoice_id:
                messagebox.showerror("Error", "Invoice tidak ditemukan")
                return
            
            # Show payment dialog
            self._show_termin_payment_dialog(invoice_id, invoice_num, customer, cicilan_amount)
        
        def on_pelunasan():
            """Handle pelunasan (full payment) action."""
            selected_items = tree.selection()
            if not selected_items:
                messagebox.showwarning("Peringatan", "Pilih pembayaran termin untuk pelunasan")
                return
            
            selected_item = selected_items[0]
            values = tree.item(selected_item)['values']
            
            # values: (No, Invoice, Customer, Jatuh Tempo, Jumlah, Status Hari)
            if len(values) < 2:
                return
            
            invoice_num = values[1]
            customer = values[2]
            
            # Find invoice_id and total sisa hutang
            invoice_id = None
            for payment in all_termin_payments:
                if payment.get('invoice_number') == invoice_num:
                    invoice_id = payment.get('invoice_id')
                    break
            
            if not invoice_id:
                messagebox.showerror("Error", "Invoice tidak ditemukan")
                return
            
            # Get invoice data to calculate sisa hutang
            invoice_detail = self.db.get_invoice_detail(invoice_id)
            if not invoice_detail:
                messagebox.showerror("Error", "Data invoice tidak ditemukan")
                return
            
            invoice = invoice_detail['invoice']
            dp_amount = invoice.get('bayar', 0)
            completed_payments = self.db.calculate_total_paid_termin(invoice_id)
            total_paid = dp_amount + completed_payments
            sisa_hutang = invoice['total'] - total_paid
            
            if sisa_hutang <= 0:
                messagebox.showinfo("Info", "Pembayaran termin sudah lunas")
                return
            
            # Show pelunasan dialog
            self._show_termin_pelunasan_dialog(invoice_id, invoice_num, customer, sisa_hutang)
        
        ttk.Button(
            action_frame,
            text="💳 Bayar Cicilan",
            command=on_bayar_cicilan
        ).pack(side='left', padx=5)
        
        ttk.Button(
            action_frame,
            text="✅ Pelunasan Sisa Hutang",
            command=on_pelunasan
        ).pack(side='left', padx=5)
        
        def on_refresh():
            """Refresh termin data."""
            # Clear tree
            for item in tree.get_children():
                tree.delete(item)
            
            # Reload data
            all_termin_payments_refresh = self.db.get_all_pending_termin_payments()
            
            # Update summary
            total_pending = len(all_termin_payments_refresh)
            total_amount = sum(item.get('payment_amount', 0) for item in all_termin_payments_refresh)
            
            from datetime import date
            today = date.today()
            overdue_count = 0
            for item in all_termin_payments_refresh:
                due_date_str = item.get('due_date', '')
                if due_date_str:
                    due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                    if due_date < today:
                        overdue_count += 1
            
            summary_text = f"""
Total Pembayaran Pending     : {total_pending} cicilan
Total Jumlah Pembayaran      : {format_rp(total_amount)}
Pembayaran Terlamabat        : {overdue_count} cicilan
Pembayaran Akan Jatuh Tempo  : {total_pending - overdue_count} cicilan
            """
            
            summary_label.config(text=summary_text.strip())
            
            # Repopulate tree
            for i, payment in enumerate(all_termin_payments_refresh, 1):
                invoice_num = payment.get('invoice_number', 'N/A')
                customer = payment.get('customer_name', 'N/A')
                due_date = payment.get('due_date', '')
                amount = payment.get('payment_amount', 0)
                
                # Calculate days status
                from datetime import date
                due_date_obj = datetime.strptime(due_date, '%Y-%m-%d').date()
                if due_date_obj < date.today():
                    days_info = f"Terlamabat {(date.today() - due_date_obj).days} hari"
                else:
                    days_info = f"Dalam {(due_date_obj - date.today()).days} hari"
                
                tree.insert('', 'end', values=(
                    str(i),
                    invoice_num,
                    customer,
                    due_date,
                    format_rp(amount),
                    days_info
                ))
            
            messagebox.showinfo("Berhasil", "Data pembayaran termin diperbarui!")
        
        ttk.Button(
            action_frame,
            text="🔄 Refresh",
            command=on_refresh
        ).pack(side='left', padx=5)
    
    # ========================================================================
    # INVOICE PAGE
    # ========================================================================
    
    def show_invoices(self):
        """Show invoices list page."""
        self._clear_content()
        
        # Header with action buttons
        header_frame = ttk.Frame(self.content_area)
        header_frame.pack(fill='x', pady=10)
        
        header_label = ttk.Label(
            header_frame,
            text="🧾 Daftar Invoice",
            font=FONTS['title'],
            foreground=COLORS['primary']
        )
        header_label.pack(side='left')
        
        # Show loading indicator
        loading_frame = ttk.Frame(self.content_area)
        loading_frame.pack(fill='both', expand=True, pady=50)
        
        loading_label = ttk.Label(
            loading_frame,
            text="⏳ Loading invoices...",
            font=FONTS['normal'],
            foreground=COLORS['info']
        )
        loading_label.pack()
        
        # Load invoices in background
        def load_invoices():
            try:
                invoices = self.db.get_all_invoices(limit=100)
                return invoices
            except Exception as e:
                logger.error(f"Error loading invoices: {e}")
                return None
        
        def on_invoices_loaded(invoices):
            loading_frame.destroy()
            
            if invoices is None:
                error_label = ttk.Label(
                    self.content_area,
                    text="❌ Error loading invoices",
                    font=FONTS['normal'],
                    foreground=COLORS['danger']
                )
                error_label.pack(pady=20)
                return
            
            if not invoices:
                empty_frame = ttk.Frame(self.content_area)
                empty_frame.pack(fill='both', expand=True, pady=50)
                
                empty_icon = tk.Label(
                    empty_frame,
                    text="📭",
                    font=("Arial", 48),
                    fg=COLORS['text_secondary']
                )
                empty_icon.pack(pady=10)
                
                empty_label = ttk.Label(
                    empty_frame,
                    text="Belum ada invoice",
                    font=FONTS['heading'],
                    foreground=COLORS['text_secondary']
                )
                empty_label.pack(pady=5)
                
                instruction_label = ttk.Label(
                    empty_frame,
                    text="Lakukan transaksi terlebih dahulu untuk membuat invoice",
                    font=FONTS['small'],
                    foreground=COLORS['text_secondary']
                )
                instruction_label.pack(pady=10)
                
                create_trans_btn = ttk.Button(
                    empty_frame,
                    text="🛒 Buat Transaksi Baru",
                    command=self.show_transaction
                )
                create_trans_btn.pack(pady=10)
                return
            
            # Search bar
            search_frame = ttk.Frame(self.content_area)
            search_frame.pack(fill='x', pady=10, padx=5)
            
            search_label = ttk.Label(search_frame, text="🔍 Cari Invoice:", font=FONTS['normal'])
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
            
            columns = ('No', 'Invoice Number', 'Tanggal', 'Total', 'Pembayaran')
            tree = ttk.Treeview(tree_frame, columns=columns, height=15, show='headings')
            
            # Define column headings
            tree.heading('No', text='No')
            tree.heading('Invoice Number', text='Nomor Invoice')
            tree.heading('Tanggal', text='Tanggal/Waktu')
            tree.heading('Total', text='Total')
            tree.heading('Pembayaran', text='Pembayaran')
            
            tree.column('No', width=30)
            tree.column('Invoice Number', width=150)
            tree.column('Tanggal', width=180)
            tree.column('Total', width=100)
            tree.column('Pembayaran', width=100)
            
            # Add scrollbar
            scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
            tree.configure(yscroll=scrollbar.set)
            scrollbar.pack(side='right', fill='y')
            tree.pack(fill='both', expand=True)
            
            # Store original invoices
            self._invoices_list = invoices
            self._invoice_tree = tree
            
            def update_invoice_list(*args):
                """Filter invoices based on search."""
                search_text = search_var.get().lower()
                
                # Clear tree
                for item in tree.get_children():
                    tree.delete(item)
                
                # Add filtered invoices
                filtered = [inv for inv in invoices 
                           if search_text in inv.get('invoice_number', '').lower()]
                
                for idx, inv in enumerate(filtered, 1):
                    inv_number = inv.get('invoice_number', 'N/A')
                    created_at = inv.get('created_at', 'N/A')
                    # Format datetime
                    if isinstance(created_at, str) and 'T' in created_at:
                        try:
                            dt = datetime.fromisoformat(created_at)
                            created_at = dt.strftime('%d/%m/%Y %H:%M:%S')
                        except:
                            pass
                    total = inv.get('total', 0)
                    bayar = inv.get('bayar', 0)
                    
                    tree.insert('', 'end', values=(
                        str(idx),
                        inv_number,
                        created_at,
                        format_rp(total),
                        format_rp(bayar)
                    ))
                
                self._current_filtered_invoices = filtered
            
            # Bind search input
            search_var.trace('w', update_invoice_list)
            
            # Initial population
            self._current_filtered_invoices = invoices
            update_invoice_list()
            
            # Add double-click handler
            tree.bind('<Double-1>', lambda e: self._show_invoice_detail_dialog(tree))
            
            # Action buttons
            btn_frame = ttk.Frame(self.content_area)
            btn_frame.pack(fill='x', pady=10)
            
            def open_selected_invoice():
                selection = tree.selection()
                if not selection:
                    messagebox.showwarning("Peringatan", "Pilih invoice terlebih dahulu")
                    return
                
                item_idx = tree.index(selection[0])
                if item_idx < len(self._current_filtered_invoices):
                    selected_inv = self._current_filtered_invoices[item_idx]
                    self._show_invoice_detail_dialog_by_id(selected_inv['id'])
            
            view_btn = ttk.Button(
                btn_frame,
                text="👁️ Lihat Detail",
                command=open_selected_invoice
            )
            view_btn.pack(side='left', padx=5)
            
            def export_pdf():
                selection = tree.selection()
                if not selection:
                    messagebox.showwarning("Peringatan", "Pilih invoice terlebih dahulu")
                    return
                
                item_idx = tree.index(selection[0])
                if item_idx < len(self._current_filtered_invoices):
                    selected_inv = self._current_filtered_invoices[item_idx]
                    invoice_detail = self.db.get_invoice_detail(selected_inv['id'])
                    
                    if invoice_detail:
                        invoice_data = invoice_detail['invoice']
                        invoice_data['items'] = invoice_detail.get('items', [])
                        pdf_filepath = self.invoice_pdf_generator.generate_invoice_pdf(
                            invoice_data,
                            store_name="TOKO UBI BAROKAH IBU AWANG",
                            store_address="Jl. Desa Mekarbakti, pertigaan Cilembu.",
                            store_phone=None,
                            db=self.db
                        )
                        
                        if pdf_filepath:
                            messagebox.showinfo("Sukses", f"✅ PDF berhasil digenerate:\n{pdf_filepath}")
                            # Optionally open the PDF
                            try:
                                os.startfile(pdf_filepath)
                            except:
                                pass
                        else:
                            messagebox.showerror("Error", "Gagal generate PDF")
            
            export_btn = ttk.Button(
                btn_frame,
                text="📄 Export PDF",
                command=export_pdf
            )
            export_btn.pack(side='left', padx=5)
            
            # Hint
            hint_label = ttk.Label(
                self.content_area,
                text="💡 Double-click untuk melihat detail invoice",
                font=FONTS['small'],
                foreground=COLORS['text_secondary']
            )
            hint_label.pack(anchor='w', pady=5)
        
        # Start async loading
        invoice_operation = AsyncOperation(
            self.content_area,
            load_invoices,
            on_complete=on_invoices_loaded,
            show_loading=False
        )
        invoice_operation.start()
    
    def _show_invoice_detail_dialog(self, tree):
        """Show invoice detail when double-clicked."""
        selection = tree.selection()
        if not selection:
            return
        
        item_idx = tree.index(selection[0])
        if item_idx < len(self._current_filtered_invoices):
            selected_inv = self._current_filtered_invoices[item_idx]
            self._show_invoice_detail_dialog_by_id(selected_inv['id'])
    
    def _show_invoice_detail_dialog_by_id(self, invoice_id: int):
        """Show invoice detail dialog."""
        invoice_detail = self.db.get_invoice_detail(invoice_id)
        
        if not invoice_detail:
            messagebox.showerror("Error", "Invoice tidak ditemukan")
            return
        
        inv = invoice_detail['invoice']
        items = invoice_detail['items']
        
        # Create detail dialog
        dialog = tk.Toplevel(self)
        dialog.title(f"📝 Detail Invoice - {inv['invoice_number']}")
        dialog.geometry("700x600")
        dialog.configure(bg=COLORS['bg_main'])
        
        # Header
        header = tk.Label(
            dialog,
            text=f"Invoice: {inv['invoice_number']}",
            font=FONTS['heading'],
            bg=COLORS['bg_main'],
            fg=COLORS['primary']
        )
        header.pack(pady=10)
        
        # Info section
        info_frame = tk.Frame(dialog, bg=COLORS['bg_card'], relief='flat', bd=1)
        info_frame.pack(fill='x', padx=10, pady=5)
        
        created_at = inv.get('created_at', 'N/A')
        if isinstance(created_at, str) and 'T' in created_at:
            try:
                dt = datetime.fromisoformat(created_at)
                created_at = dt.strftime('%d %B %Y %H:%M:%S')
            except:
                pass
        
        info_text = f"Tanggal/Waktu: {created_at}"
        info_label = tk.Label(
            info_frame,
            text=info_text,
            font=FONTS['normal'],
            bg=COLORS['bg_card'],
            justify='left'
        )
        info_label.pack(anchor='w', padx=10, pady=10)
        
        # Items section
        items_frame = ttk.LabelFrame(dialog, text="📦 Item Invoice", padding=10)
        items_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        columns = ('No', 'Produk', 'Qty', 'Harga', 'Subtotal')
        items_tree = ttk.Treeview(items_frame, columns=columns, height=12, show='headings')
        
        items_tree.heading('No', text='No')
        items_tree.heading('Produk', text='Produk')
        items_tree.heading('Qty', text='Qty')
        items_tree.heading('Harga', text='Harga Satuan')
        items_tree.heading('Subtotal', text='Subtotal')
        
        items_tree.column('No', width=30)
        items_tree.column('Produk', width=200)
        items_tree.column('Qty', width=50)
        items_tree.column('Harga', width=120)
        items_tree.column('Subtotal', width=120)
        
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
        
        summary_lines = []
        summary_lines.append(f"Subtotal          : {format_rp(inv['total'] + inv['discount_amount'] - inv['tax_amount'])}")
        
        if inv.get('discount_amount', 0) > 0:
            summary_lines.append(f"Diskon ({inv.get('discount_percent', 0)}%)    : -{format_rp(inv['discount_amount'])}")
        
        if inv.get('tax_amount', 0) > 0:
            summary_lines.append(f"Pajak ({inv.get('tax_percent', 0)}%)      : +{format_rp(inv['tax_amount'])}")
        
        summary_lines.append(f"{'─' * 50}")
        summary_lines.append(f"Total Belanja      : {format_rp(inv['total'])}")
        
        # Tentukan label berdasarkan tipe pembayaran
        payment_type = inv.get('payment_type', 'lunas')
        
        if payment_type == 'termin':
            # Hitung total yang sudah dibayar (DP + cicilan terbayar)
            total_cicilan_paid = self.db.calculate_total_paid_termin(invoice_id)
            total_paid = inv['bayar'] + total_cicilan_paid
            sisa_hutang = inv['total'] - total_paid
            
            summary_lines.append(f"DP (Down Payment) : {format_rp(inv['bayar'])}")
            
            if total_cicilan_paid > 0:
                summary_lines.append(f"Cicilan Terbayar  : {format_rp(total_cicilan_paid)}")
            
            # Check jika sudah lunas
            if sisa_hutang <= 0:
                summary_lines.append(f"Status            : ✅ LUNAS")
            else:
                summary_lines.append(f"Sisa Hutang       : {format_rp(sisa_hutang)}")
        else:
            summary_lines.append(f"Pembayaran        : {format_rp(inv['bayar'])}")
            summary_lines.append(f"Kembalian         : {format_rp(inv['kembalian'])}")
        
        summary_text = "\n".join(summary_lines)
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
        
        def export_pdf():
            inv['items'] = items
            pdf_filepath = self.invoice_pdf_generator.generate_invoice_pdf(
                inv,
                store_name="TOKO UBI BAROKAH IBU AWANG",
                store_address="Jl. Desa Mekarbakti, pertigaan Cilembu.",
                store_phone=None,
                db=self.db
            )
            
            if pdf_filepath:
                messagebox.showinfo("Sukses", f"✅ PDF berhasil digenerate:\n{pdf_filepath}")
                try:
                    os.startfile(pdf_filepath)
                except:
                    pass
            else:
                messagebox.showerror("Error", "Gagal generate PDF")
        
        export_btn = ttk.Button(
            btn_frame,
            text="📄 Export PDF",
            command=export_pdf
        )
        export_btn.pack(side='left', padx=5)
        
        close_btn = ttk.Button(btn_frame, text="Tutup", command=dialog.destroy)
        close_btn.pack(side='left', padx=5)
    
    # ========================================================================
    # PEMBUKUAN PAGE (Bookkeeping / Accounting) - ADMIN ONLY
    # ========================================================================
    
    def show_pembukuan(self):
        """Show cashflow/accounting page (admin only)."""
        self._clear_content()
        
        # Check if accounting service is available
        if not self.accounting_service:
            header = ttk.Label(
                self.content_area,
                text="❌ Sistem Pembukuan Tidak Tersedia",
                font=FONTS['title'],
                foreground=COLORS['danger']
            )
            header.pack(pady=20)
            
            msg = ttk.Label(
                self.content_area,
                text="Module accounting_service tidak ditemukan.\nSistem pembukuan tidak bisa diakses.",
                font=FONTS['normal']
            )
            msg.pack(pady=20)
            return
        
        # Header
        header = ttk.Label(
            self.content_area,
            text="Pembukuan & Cashflow (Accounting)",
            font=FONTS['title'],
            foreground=COLORS['primary']
        )
        header.pack(pady=10)
        
        # Create scrollable content
        canvas = tk.Canvas(self.content_area, bg=COLORS['bg_main'], highlightthickness=0, relief='flat', bd=0)
        scrollbar = ttk.Scrollbar(self.content_area, orient='vertical', command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        # Configure scrollbar appearance
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Create a window in the canvas
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        # Bind frame configure to update scroll region
        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # Make the frame width match canvas width
            canvas.itemconfig(canvas_window, width=canvas.winfo_width() if canvas.winfo_width() > 1 else 800)
        
        scrollable_frame.bind("<Configure>", _on_frame_configure)
        
        # Handle canvas configure to update frame width
        def _on_canvas_configure(event):
            if scrollable_frame.winfo_width() != event.width:
                canvas.itemconfig(canvas_window, width=event.width)
        
        canvas.bind("<Configure>", _on_canvas_configure)
        
        # Add mouse wheel scrolling support
        def _on_mousewheel(event):
            try:
                if canvas.winfo_exists():
                    scroll_units = int(-1*(event.delta/120))
                    canvas.yview_scroll(scroll_units, "units")
                    return "break"
            except (tk.TclError, AttributeError):
                pass
        
        # Bind mousewheel to canvas and scrollable_frame
        canvas.bind("<MouseWheel>", _on_mousewheel)
        scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
        
        # Add Page Up/Down keyboard scrolling support
        def _on_page_up(event):
            try:
                if canvas.winfo_exists():
                    canvas.yview_scroll(-10, "units")
                    return "break"
            except (tk.TclError, AttributeError):
                pass
        
        def _on_page_down(event):
            try:
                if canvas.winfo_exists():
                    canvas.yview_scroll(10, "units")
                    return "break"
            except (tk.TclError, AttributeError):
                pass
        
        canvas.bind("<Prior>", _on_page_up)   # Page Up
        canvas.bind("<Next>", _on_page_down)  # Page Down
        
        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        
        # ================================================================
        # SUMMARY SECTION - Income, Expense, Profit
        # ================================================================
        
        summary_frame = ttk.LabelFrame(scrollable_frame, text="Ringkasan Cashflow", padding=15)
        summary_frame.pack(fill='x', padx=10, pady=10)
        
        # Date range selector
        date_frame = ttk.Frame(summary_frame)
        date_frame.pack(fill='x', pady=10)
        
        ttk.Label(date_frame, text="Periode:", font=FONTS['normal']).pack(side='left', padx=5)
        
        start_date_var = tk.StringVar(
            value=(datetime.now().replace(day=1)).strftime('%Y-%m-%d')
        )
        end_date_var = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        
        ttk.Label(date_frame, text="Dari:", font=FONTS['small']).pack(side='left', padx=5)
        start_date_entry = DateEntry(
            date_frame,
            textvariable=start_date_var,
            background='darkblue',
            foreground='white',
            borderwidth=2,
            width=12
        )
        start_date_entry.pack(side='left', padx=5)
        
        ttk.Label(date_frame, text="Hingga:", font=FONTS['small']).pack(side='left', padx=5)
        end_date_entry = DateEntry(
            date_frame,
            textvariable=end_date_var,
            background='darkblue',
            foreground='white',
            borderwidth=2,
            width=12
        )
        end_date_entry.pack(side='left', padx=5)
        
        # Summary cards - with income breakdown
        summary_cards = ttk.Frame(summary_frame)
        summary_cards.pack(fill='x', pady=15)
        
        card_labels = {}
        
        # Top row: income breakdown
        income_row = ttk.Frame(summary_cards)
        income_row.pack(fill='x', pady=5)
        
        card_data_row1 = [
            ('Penjualan', 'sales_income', COLORS['success']),
            ('Pemasukan Lain', 'other_income', '#10B981'),  # Lighter green
            ('[+] Total Pemasukan', 'total_income', COLORS['primary']),
        ]
        
        for label_text, key, color in card_data_row1:
            card = tk.Frame(income_row, bg=color, relief='solid', bd=1, height=80)
            card.pack(side='left', expand=True, fill='both', padx=3, pady=5)
            
            title = tk.Label(card, text=label_text, bg=color, fg='white', font=FONTS['small'])
            title.pack(anchor='w', padx=8, pady=(8, 3))
            
            value = tk.Label(card, text='Rp 0', bg=color, fg='white', font=FONTS['heading'])
            value.pack(anchor='w', padx=8, pady=(3, 8))
            
            card_labels[key] = value
        
        # Bottom row: expense and profit
        expense_row = ttk.Frame(summary_cards)
        expense_row.pack(fill='x', pady=5)
        
        card_data_row2 = [
            ('[-] Total Pengeluaran', 'total_expense', COLORS['danger']),
            ('Keuntungan Bersih', 'profit', COLORS['primary']),
        ]
        
        for label_text, key, color in card_data_row2:
            card = tk.Frame(expense_row, bg=color, relief='solid', bd=1, height=80)
            card.pack(side='left', expand=True, fill='both', padx=3, pady=5)
            
            title = tk.Label(card, text=label_text, bg=color, fg='white', font=FONTS['small'])
            title.pack(anchor='w', padx=8, pady=(8, 3))
            
            value = tk.Label(card, text='Rp 0', bg=color, fg='white', font=FONTS['heading'])
            value.pack(anchor='w', padx=8, pady=(3, 8))
            
            card_labels[key] = value
        
        # ================================================================
        # CASHFLOW HISTORY TABLE
        # ================================================================
        
        history_frame = ttk.LabelFrame(scrollable_frame, text="Riwayat Cashflow", padding=10)
        history_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create treeview for cashflow history
        cols = ('Tanggal', 'Tipe', 'Deskripsi', 'Jumlah', 'Transaksi ID')
        history_tree = ttk.Treeview(history_frame, columns=cols, height=10, show='headings')
        
        history_tree.column('Tanggal', width=150, anchor='center')
        history_tree.column('Tipe', width=80, anchor='center')
        history_tree.column('Deskripsi', width=250, anchor='w')
        history_tree.column('Jumlah', width=120, anchor='e')
        history_tree.column('Transaksi ID', width=100, anchor='center')
        
        history_tree.heading('Tanggal', text='Tanggal')
        history_tree.heading('Tipe', text='Tipe')
        history_tree.heading('Deskripsi', text='Deskripsi')
        history_tree.heading('Jumlah', text='Jumlah')
        history_tree.heading('Transaksi ID', text='Transaksi')
        
        history_tree.pack(fill='both', expand=True)
        
        scrollbar_history = ttk.Scrollbar(history_frame, orient='vertical', command=history_tree.yview)
        scrollbar_history.pack(side='right', fill='y')
        history_tree.config(yscrollcommand=scrollbar_history.set)
        
        # ================================================================
        # ACTION BUTTONS
        # ================================================================
        
        button_frame = ttk.Frame(summary_frame)
        button_frame.pack(fill='x', pady=10)
        
        def refresh_cashflow():
            """Refresh cashflow summary and history with income breakdown."""
            try:
                from datetime import date
                # Parse DateEntry format (M/D/YY or M/D/YYYY)
                start_str = start_date_var.get().strip()
                end_str = end_date_var.get().strip()
                
                # Try different date formats
                start_date = None
                end_date = None
                for fmt in ['%m/%d/%y', '%m/%d/%Y', '%Y-%m-%d', '%d-%m-%Y']:
                    try:
                        start_date = datetime.strptime(start_str, fmt).date()
                        break
                    except ValueError:
                        continue
                
                for fmt in ['%m/%d/%y', '%m/%d/%Y', '%Y-%m-%d', '%d-%m-%Y']:
                    try:
                        end_date = datetime.strptime(end_str, fmt).date()
                        break
                    except ValueError:
                        continue
                
                if not start_date or not end_date:
                    raise ValueError(f"Format tanggal tidak valid. Gunakan M/D/YY atau YYYY-MM-DD")
                
                start = start_date
                end = end_date
                
                # Get history for income breakdown calculation
                history = self.accounting_service.get_history(
                    limit=1000,  # Get more entries to analyze
                    start_date=start,
                    end_date=end
                )
                
                # Calculate income breakdown
                sales_income = 0
                other_income = 0
                total_expense = 0
                
                for entry in history:
                    entry_type = entry.get('type', '')
                    amount = entry.get('amount', 0)
                    description = entry.get('description', '').lower()
                    
                    if entry_type == 'income':
                        # Sales income: contains "penjualan" or "pembayaran termin"
                        if 'penjualan' in description or 'pembayaran termin' in description:
                            sales_income += amount
                        else:
                            # Other income
                            other_income += amount
                    elif entry_type == 'expense':
                        total_expense += amount
                
                total_income = sales_income + other_income
                profit = total_income - total_expense
                
                # Update cards
                card_labels['sales_income'].config(text=format_rp(sales_income))
                card_labels['other_income'].config(text=format_rp(other_income))
                card_labels['total_income'].config(text=format_rp(total_income))
                card_labels['total_expense'].config(text=format_rp(total_expense))
                
                # Profit color based on value
                profit_color = COLORS['success'] if profit >= 0 else COLORS['danger']
                profit_card = card_labels['profit'].master
                profit_card.config(bg=profit_color)
                card_labels['profit'].config(
                    text=f"Rp {abs(profit):,}",
                    bg=profit_color
                )
                for widget in profit_card.winfo_children():
                    if isinstance(widget, tk.Label):
                        widget.config(bg=profit_card['bg'])
                
                # Update history table
                for item in history_tree.get_children():
                    history_tree.delete(item)
                
                for entry in history:
                    entry_type = entry.get('type', 'unknown')
                    type_icon = '[+] Pemasukan' if entry_type == 'income' else '[-] Pengeluaran'
                    
                    # Color based on type
                    tag = 'income' if entry_type == 'income' else 'expense'
                    
                    history_tree.insert('', 'end', values=(
                        entry.get('created_at', ''),
                        type_icon,
                        entry.get('description', ''),
                        format_rp(entry.get('amount', 0)),
                        entry.get('related_transaction_id', '-') or '-'
                    ), tags=(tag,))
                
                # Configure tags for colors
                history_tree.tag_configure('income', foreground=COLORS['success'])
                history_tree.tag_configure('expense', foreground=COLORS['danger'])
                
            except Exception as e:
                logger.error(f"Error refreshing cashflow: {e}")
                messagebox.showerror("Error", f"Gagal refresh data: {e}")
        
        def show_add_expense_dialog():
            """Show dialog to add new expense."""
            dialog = tk.Toplevel(self)
            dialog.title("Tambah Pengeluaran")
            dialog.geometry("400x300")
            
            ttk.Label(dialog, text="Deskripsi Pengeluaran:", font=FONTS['normal']).pack(
                anchor='w', padx=10, pady=(10, 5)
            )
            
            desc_entry = ttk.Entry(dialog, width=50)
            desc_entry.pack(fill='x', padx=10, pady=5)
            desc_entry.focus()
            
            ttk.Label(dialog, text="Jumlah Pengeluaran (Rp):", font=FONTS['normal']).pack(
                anchor='w', padx=10, pady=(10, 5)
            )
            
            amount_entry = ttk.Entry(dialog, width=50)
            amount_entry.pack(fill='x', padx=10, pady=5)
            
            def save_expense():
                try:
                    description = desc_entry.get().strip()
                    amount_str = amount_entry.get().strip()
                    
                    if not description:
                        messagebox.showwarning("Warning", "Deskripsi harus diisi!")
                        return
                    
                    if not amount_str:
                        messagebox.showwarning("Warning", "Jumlah harus diisi!")
                        return
                    
                    # Parse amount (remove Rp and dots)
                    amount_str = amount_str.replace('Rp', '').replace('.', '').replace(' ', '')
                    amount = int(amount_str)
                    
                    if amount <= 0:
                        messagebox.showwarning("Warning", "Jumlah harus lebih dari 0!")
                        return
                    
                    # Record expense
                    cf_id = self.accounting_service.record_expense(amount, description)
                    
                    if cf_id:
                        messagebox.showinfo("Sukses", f"Pengeluaran berhasil dicatat:\n{description}\nRp {amount:,}")
                        refresh_cashflow()
                        dialog.destroy()
                    else:
                        messagebox.showerror("Error", "Gagal menyimpan pengeluaran")
                
                except ValueError:
                    messagebox.showerror("Error", "Jumlah harus berupa angka!")
                except Exception as e:
                    messagebox.showerror("Error", f"Error: {e}")
            
            # Buttons
            btn_frame = ttk.Frame(dialog)
            btn_frame.pack(fill='x', padx=10, pady=15)
            
            save_btn = ttk.Button(btn_frame, text="Simpan", command=save_expense)
            save_btn.pack(side='left', padx=5)
            
            cancel_btn = ttk.Button(btn_frame, text="Batal", command=dialog.destroy)
            cancel_btn.pack(side='left', padx=5)
        
        def show_add_other_income_dialog():
            """Show dialog to add other income."""
            dialog = tk.Toplevel(self)
            dialog.title("Tambah Pemasukan Lain")
            dialog.geometry("400x300")
            
            ttk.Label(dialog, text="Deskripsi Pemasukan:", font=FONTS['normal']).pack(
                anchor='w', padx=10, pady=(10, 5)
            )
            
            desc_entry = ttk.Entry(dialog, width=50)
            desc_entry.pack(fill='x', padx=10, pady=5)
            desc_entry.focus()
            
            ttk.Label(dialog, text="Jumlah Pemasukan (Rp):", font=FONTS['normal']).pack(
                anchor='w', padx=10, pady=(10, 5)
            )
            
            amount_entry = ttk.Entry(dialog, width=50)
            amount_entry.pack(fill='x', padx=10, pady=5)
            
            def save_other_income():
                try:
                    description = desc_entry.get().strip()
                    amount_str = amount_entry.get().strip()
                    
                    if not description:
                        messagebox.showwarning("Warning", "Deskripsi harus diisi!")
                        return
                    
                    if not amount_str:
                        messagebox.showwarning("Warning", "Jumlah harus diisi!")
                        return
                    
                    # Parse amount (remove Rp and dots)
                    amount_str = amount_str.replace('Rp', '').replace('.', '').replace(' ', '')
                    amount = int(amount_str)
                    
                    if amount <= 0:
                        messagebox.showwarning("Warning", "Jumlah harus lebih dari 0!")
                        return
                    
                    # Record other income
                    cf_id = self.accounting_service.record_income(
                        transaction_id=None,
                        amount=amount,
                        description=description
                    )
                    
                    if cf_id:
                        messagebox.showinfo("Sukses", f"Pemasukan berhasil dicatat:\n{description}\nRp {amount:,}")
                        refresh_cashflow()
                        dialog.destroy()
                    else:
                        messagebox.showerror("Error", "Gagal menyimpan pemasukan")
                
                except ValueError:
                    messagebox.showerror("Error", "Jumlah harus berupa angka!")
                except Exception as e:
                    messagebox.showerror("Error", f"Error: {e}")
            
            # Buttons
            btn_frame = ttk.Frame(dialog)
            btn_frame.pack(fill='x', padx=10, pady=15)
            
            save_btn = ttk.Button(btn_frame, text="Simpan", command=save_other_income)
            save_btn.pack(side='left', padx=5)
            
            cancel_btn = ttk.Button(btn_frame, text="Batal", command=dialog.destroy)
            cancel_btn.pack(side='left', padx=5)
        
        # Buttons
        refresh_btn = ttk.Button(button_frame, text="Refresh", command=refresh_cashflow)
        refresh_btn.pack(side='left', padx=5)
        
        add_expense_btn = ttk.Button(
            button_frame,
            text="Tambah Pengeluaran",
            command=show_add_expense_dialog
        )
        add_expense_btn.pack(side='left', padx=5)
        
        add_income_btn = ttk.Button(
            button_frame,
            text="Tambah Pemasukan Lain",
            command=show_add_other_income_dialog
        )
        add_income_btn.pack(side='left', padx=5)
        
        # Initial load
        refresh_cashflow()
    
    # ========================================================================
    # PROMOTION MANAGEMENT PAGE - ADMIN ONLY
    # ========================================================================
    
    def show_promotions(self):
        """Show promotion management page (admin only)."""
        self._clear_content()
        
        # Header
        header_frame = ttk.Frame(self.content_area)
        header_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(
            header_frame,
            text="🎯 Manajemen Promosi",
            font=FONTS['title'],
            foreground=COLORS['primary']
        ).pack(side='left')
        
        # Create notebook with tabs
        notebook = ttk.Notebook(self.content_area)
        notebook.pack(fill='both', expand=True, pady=10, padx=10)
        
        # Tab 1: Daftar Promosi
        promo_list_frame = ttk.Frame(notebook)
        notebook.add(promo_list_frame, text="📋 Daftar Promosi")
        self._create_promotion_list_tab(promo_list_frame)
        
        # Tab 2: Tambah/Edit Promosi
        promo_form_frame = ttk.Frame(notebook)
        notebook.add(promo_form_frame, text="➕ Tambah Promosi")
        self._create_promotion_form_tab(promo_form_frame)
    
    def _create_promotion_list_tab(self, parent):
        """Create promotion list tab."""
        # Get all promotions
        promo_service = PromotionService(self.db)
        all_promotions = self.db.get_all_promotions()
        
        # Search bar
        search_frame = ttk.Frame(parent)
        search_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(search_frame, text="🔍 Cari Promosi:", font=FONTS['normal']).pack(side='left', padx=5)
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, width=40)
        search_entry.pack(side='left', padx=5, fill='x', expand=True)
        
        # Filter status
        status_var = tk.StringVar(value="semua")
        ttk.Label(search_frame, text="Status:", font=FONTS['normal']).pack(side='left', padx=5)
        status_combo = ttk.Combobox(search_frame, textvariable=status_var, 
                                    values=["semua", "aktif", "nonaktif", "berakhir"], width=15, state='readonly')
        status_combo.pack(side='left', padx=5)
        
        # Create treeview for promotions
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        columns = ('No', 'Nama', 'Tipe', 'Nilai', 'Min Pembelian', 'Kelipatan', 'Mulai', 'Selesai', 'Status')
        tree = ttk.Treeview(tree_frame, columns=columns, height=15, show='headings')
        
        tree.heading('No', text='No')
        tree.heading('Nama', text='Nama Promosi')
        tree.heading('Tipe', text='Tipe')
        tree.heading('Nilai', text='Nilai')
        tree.heading('Min Pembelian', text='Min Pembelian (Rp)')
        tree.heading('Kelipatan', text='Kelipatan')
        tree.heading('Mulai', text='Tanggal Mulai')
        tree.heading('Selesai', text='Tanggal Selesai')
        tree.heading('Status', text='Status')
        
        tree.column('No', width=30)
        tree.column('Nama', width=120)
        tree.column('Tipe', width=70)
        tree.column('Nilai', width=60)
        tree.column('Min Pembelian', width=90)
        tree.column('Kelipatan', width=60)
        tree.column('Mulai', width=80)
        tree.column('Selesai', width=80)
        tree.column('Status', width=70)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        tree.pack(fill='both', expand=True)
        
        # Mapping untuk menyimpan promotion ID berdasarkan tree item
        promo_id_map = {}
        
        def refresh_promo_list(*args):
            """Refresh promotion list dengan filter."""
            from datetime import datetime
            
            for item in tree.get_children():
                tree.delete(item)
            
            promo_id_map.clear()
            
            search_text = search_var.get().lower()
            status_filter = status_var.get()
            
            promotions = self.db.get_all_promotions()
            today = datetime.now().date()
            
            display_count = 0
            for promo in promotions:
                # Filter berdasarkan search text
                if search_text and search_text not in promo['nama_promosi'].lower():
                    continue
                
                # Determine actual status based on dates
                actual_status = promo['status']
                try:
                    tanggal_selesai = datetime.strptime(promo['tanggal_selesai'], '%Y-%m-%d').date()
                    if tanggal_selesai < today:
                        actual_status = 'berakhir'
                except (ValueError, TypeError):
                    pass
                
                # Filter berdasarkan status
                if status_filter != "semua" and actual_status != status_filter:
                    continue
                
                display_count += 1
                nilai = f"{promo['nilai_diskon']}{'%' if promo['tipe_diskon'] == 'persentase' else 'Rp'}"
                min_qty = f"Rp {int(promo['min_qty']):,.0f}" if promo['min_qty'] else "Rp 0"
                kelipatan_status = "✓ Ya" if bool(promo.get('berlaku_kelipatan', 0)) else "✗ Tidak"
                
                tree_item = tree.insert('', 'end', values=(
                    str(display_count),
                    promo['nama_promosi'],
                    promo['tipe_diskon'],
                    nilai,
                    min_qty,
                    kelipatan_status,
                    promo['tanggal_mulai'],
                    promo['tanggal_selesai'],
                    actual_status
                ))
                
                # Store promotion ID in map
                promo_id_map[tree_item] = promo['id']
        
        search_var.trace('w', refresh_promo_list)
        status_var.trace('w', refresh_promo_list)
        
        # Button actions
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill='x', padx=10, pady=10)
        
        def edit_promotion():
            """Edit selected promotion."""
            from datetime import datetime
            
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Peringatan", "Pilih promosi terlebih dahulu!")
                return
            
            tree_item = selection[0]
            if tree_item in promo_id_map:
                promo_id = promo_id_map[tree_item]
                promo = self.db.get_promotion_by_id(promo_id)
                if promo:
                    # Check if promotion has ended
                    try:
                        today = datetime.now().date()
                        tanggal_selesai = datetime.strptime(promo['tanggal_selesai'], '%Y-%m-%d').date()
                        if tanggal_selesai < today:
                            messagebox.showwarning("Peringatan", "Tidak bisa mengedit promosi yang sudah berakhir!")
                            return
                    except (ValueError, TypeError):
                        pass
                    
                    self._show_promotion_edit_dialog(promo)
                    refresh_promo_list()
                else:
                    messagebox.showerror("Error", "Promosi tidak ditemukan!")
            else:
                messagebox.showerror("Error", "Error mengambil data promosi!")
        
        def delete_promotion():
            """Delete selected promotion."""
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Peringatan", "Pilih promosi terlebih dahulu!")
                return
            
            tree_item = selection[0]
            if tree_item in promo_id_map:
                if messagebox.askyesno("Konfirmasi", "Yakin ingin menghapus promosi ini?"):
                    promo_id = promo_id_map[tree_item]
                    success, msg = self.db.delete_promotion(promo_id)
                    messagebox.showinfo("Sukses", msg) if success else messagebox.showerror("Error", msg)
                    refresh_promo_list()
        
        def toggle_status():
            """Toggle promotion status."""
            from datetime import datetime
            
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Peringatan", "Pilih promosi terlebih dahulu!")
                return
            
            tree_item = selection[0]
            if tree_item in promo_id_map:
                promo_id = promo_id_map[tree_item]
                promo = self.db.get_promotion_by_id(promo_id)
                if promo:
                    # Check if promotion has ended
                    try:
                        today = datetime.now().date()
                        tanggal_selesai = datetime.strptime(promo['tanggal_selesai'], '%Y-%m-%d').date()
                        if tanggal_selesai < today:
                            messagebox.showwarning("Peringatan", "Tidak bisa mengubah status promosi yang sudah berakhir!")
                            return
                    except (ValueError, TypeError):
                        pass
                    
                    new_status = 'nonaktif' if promo['status'] == 'aktif' else 'aktif'
                    success, msg = self.db.update_promotion(promo_id, status=new_status)
                    messagebox.showinfo("Sukses", msg) if success else messagebox.showerror("Error", msg)
                    refresh_promo_list()
        
        ttk.Button(action_frame, text="✏️ Edit", command=edit_promotion).pack(side='left', padx=5)
        ttk.Button(action_frame, text="🔄 Toggle Status", command=toggle_status).pack(side='left', padx=5)
        ttk.Button(action_frame, text="🗑️ Hapus", command=delete_promotion).pack(side='left', padx=5)
        
        # Initial load
        refresh_promo_list()
    
    def _create_promotion_form_tab(self, parent):
        """Create promotion form tab for adding/editing."""
        # Form frame
        form_frame = ttk.LabelFrame(parent, text="Form Promosi", padding=15)
        form_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Nama Promosi
        ttk.Label(form_frame, text="Nama Promosi:", font=FONTS['normal']).grid(row=0, column=0, sticky='w', pady=5)
        nama_entry = ttk.Entry(form_frame, width=40)
        nama_entry.grid(row=0, column=1, sticky='w', pady=5, padx=5)
        
        # Deskripsi
        ttk.Label(form_frame, text="Deskripsi/Keterangan:", font=FONTS['normal']).grid(row=1, column=0, sticky='nw', pady=5)
        deskripsi_text = tk.Text(form_frame, height=3, width=40, font=FONTS['small'])
        deskripsi_text.grid(row=1, column=1, sticky='w', pady=5, padx=5)
        
        # Tipe Diskon
        ttk.Label(form_frame, text="Tipe Diskon:", font=FONTS['normal']).grid(row=2, column=0, sticky='w', pady=5)
        tipe_var = tk.StringVar(value="persentase")
        tipe_combo = ttk.Combobox(form_frame, textvariable=tipe_var, 
                                 values=["persentase", "nominal"], width=20, state='readonly')
        tipe_combo.grid(row=2, column=1, sticky='w', pady=5, padx=5)
        
        # Nilai Diskon
        ttk.Label(form_frame, text="Nilai Diskon:", font=FONTS['normal']).grid(row=3, column=0, sticky='w', pady=5)
        nilai_frame = ttk.Frame(form_frame)
        nilai_frame.grid(row=3, column=1, sticky='w', pady=5, padx=5)
        
        nilai_entry = ttk.Entry(nilai_frame, width=15)
        nilai_entry.pack(side='left', padx=5)
        
        nilai_label = ttk.Label(nilai_frame, text="%", font=FONTS['normal'])
        nilai_label.pack(side='left', padx=2)
        
        def on_tipe_change(*args):
            """Update label saat tipe berubah."""
            if tipe_var.get() == "persentase":
                nilai_label.config(text="%")
            else:
                nilai_label.config(text="Rp")
        
        tipe_var.trace('w', on_tipe_change)
        
        # Minimum Pembelian (Rp)
        ttk.Label(form_frame, text="Minimum Pembelian (Rp):", font=FONTS['normal']).grid(row=4, column=0, sticky='w', pady=5)
        qty_frame = ttk.Frame(form_frame)
        qty_frame.grid(row=4, column=1, sticky='w', pady=5, padx=5)
        
        qty_entry = ttk.Entry(qty_frame, width=15)
        qty_entry.pack(side='left', padx=5)
        
        ttk.Label(qty_frame, text="Rp", font=FONTS['normal']).pack(side='left', padx=5)
        
        satuan_var = tk.StringVar(value="Rp")
        
        # Tanggal Mulai
        ttk.Label(form_frame, text="Tanggal Mulai:", font=FONTS['normal']).grid(row=5, column=0, sticky='w', pady=5)
        mulai_date = DateEntry(form_frame, width=20)
        mulai_date.grid(row=5, column=1, sticky='w', pady=5, padx=5)
        
        # Tanggal Selesai
        ttk.Label(form_frame, text="Tanggal Selesai:", font=FONTS['normal']).grid(row=6, column=0, sticky='w', pady=5)
        selesai_date = DateEntry(form_frame, width=20)
        selesai_date.grid(row=6, column=1, sticky='w', pady=5, padx=5)
        
        # Berlaku Kelipatan - Checkbox untuk mode kelipatan
        berlaku_kelipatan_var = tk.BooleanVar(value=False)
        berlaku_kelipatan_check = ttk.Checkbutton(
            form_frame, 
            text="Berlaku Kelipatan (diskon dikalikan per kelipatan minimum pembelian)",
            variable=berlaku_kelipatan_var
        )
        berlaku_kelipatan_check.grid(row=7, column=0, columnspan=2, sticky='w', pady=10)
        
        # Submit button
        def save_promotion():
            """Save promotion ke database."""
            nama = nama_entry.get().strip()
            deskripsi = deskripsi_text.get("1.0", tk.END).strip()
            tipe_diskon = tipe_var.get()
            
            try:
                nilai_diskon = int(nilai_entry.get())
                min_qty = float(qty_entry.get())
            except ValueError:
                messagebox.showerror("Error", "Nilai dan Minimum Pembelian harus berupa angka!")
                return
            
            satuan = satuan_var.get()
            tanggal_mulai = mulai_date.get_date().isoformat()
            tanggal_selesai = selesai_date.get_date().isoformat()
            berlaku_kelipatan = berlaku_kelipatan_var.get()
            
            # Validasi
            promo_service = PromotionService(self.db)
            is_valid_data, msg_data = promo_service.validate_promotion_data(nama, tipe_diskon, nilai_diskon, min_qty)
            is_valid_period, msg_period = promo_service.validate_promotion_period(tanggal_mulai, tanggal_selesai)
            
            if not is_valid_data:
                messagebox.showerror("Error", msg_data)
                return
            
            if not is_valid_period:
                messagebox.showerror("Error", msg_period)
                return
            
            # Save to database
            success, msg, promo_id = self.db.add_promotion(
                nama, tipe_diskon, nilai_diskon, min_qty, satuan, 
                tanggal_mulai, tanggal_selesai, deskripsi, berlaku_kelipatan
            )
            
            if success:
                messagebox.showinfo("Sukses", msg)
                # Clear form
                nama_entry.delete(0, tk.END)
                deskripsi_text.delete("1.0", tk.END)
                nilai_entry.delete(0, tk.END)
                qty_entry.delete(0, tk.END)
            else:
                messagebox.showerror("Error", msg)
        
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=8, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="💾 Simpan Promosi", command=save_promotion).pack(side='left', padx=5)
        ttk.Button(button_frame, text="🔄 Reset", 
                   command=lambda: (nama_entry.delete(0, tk.END), deskripsi_text.delete("1.0", tk.END), 
                                   nilai_entry.delete(0, tk.END), qty_entry.delete(0, tk.END))).pack(side='left', padx=5)
    
    def _show_promotion_edit_dialog(self, promo):
        """Show dialog to edit promotion."""
        dialog = tk.Toplevel(self)
        dialog.title(f"Edit Promosi: {promo['nama_promosi']}")
        dialog.geometry("500x400")
        dialog.resizable(False, False)
        
        # Center dialog
        dialog.transient(self)
        dialog.grab_set()
        
        # Form
        form_frame = ttk.Frame(dialog, padding=15)
        form_frame.pack(fill='both', expand=True)
        
        # Nama Promosi
        ttk.Label(form_frame, text="Nama Promosi:", font=FONTS['normal']).grid(row=0, column=0, sticky='w', pady=5)
        nama_entry = ttk.Entry(form_frame, width=40)
        nama_entry.insert(0, promo['nama_promosi'])
        nama_entry.grid(row=0, column=1, sticky='w', pady=5, padx=5)
        
        # Nilai Diskon
        ttk.Label(form_frame, text="Nilai Diskon:", font=FONTS['normal']).grid(row=1, column=0, sticky='w', pady=5)
        nilai_entry = ttk.Entry(form_frame, width=40)
        nilai_entry.insert(0, str(promo['nilai_diskon']))
        nilai_entry.grid(row=1, column=1, sticky='w', pady=5, padx=5)
        
        # Min Pembelian (Rp)
        ttk.Label(form_frame, text="Minimum Pembelian (Rp):", font=FONTS['normal']).grid(row=2, column=0, sticky='w', pady=5)
        qty_entry = ttk.Entry(form_frame, width=40)
        qty_entry.insert(0, str(promo['min_qty']))
        qty_entry.grid(row=2, column=1, sticky='w', pady=5, padx=5)
        
        # Tanggal Mulai
        ttk.Label(form_frame, text="Tanggal Mulai:", font=FONTS['normal']).grid(row=3, column=0, sticky='w', pady=5)
        mulai_date = DateEntry(form_frame, width=20)
        mulai_date.set_date(datetime.fromisoformat(promo['tanggal_mulai']).date())
        mulai_date.grid(row=3, column=1, sticky='w', pady=5, padx=5)
        
        # Tanggal Selesai
        ttk.Label(form_frame, text="Tanggal Selesai:", font=FONTS['normal']).grid(row=4, column=0, sticky='w', pady=5)
        selesai_date = DateEntry(form_frame, width=20)
        selesai_date.set_date(datetime.fromisoformat(promo['tanggal_selesai']).date())
        selesai_date.grid(row=4, column=1, sticky='w', pady=5, padx=5)
        
        # Status
        ttk.Label(form_frame, text="Status:", font=FONTS['normal']).grid(row=5, column=0, sticky='w', pady=5)
        status_var = tk.StringVar(value=promo['status'])
        status_combo = ttk.Combobox(form_frame, textvariable=status_var, 
                                   values=["aktif", "nonaktif"], width=20, state='readonly')
        status_combo.grid(row=5, column=1, sticky='w', pady=5, padx=5)
        
        # Berlaku Kelipatan - Checkbox untuk mode kelipatan
        berlaku_kelipatan_var = tk.BooleanVar(value=promo.get('berlaku_kelipatan', False))
        berlaku_kelipatan_check = ttk.Checkbutton(
            form_frame, 
            text="Berlaku Kelipatan (diskon dikalikan per kelipatan minimum pembelian)",
            variable=berlaku_kelipatan_var
        )
        berlaku_kelipatan_check.grid(row=6, column=0, columnspan=2, sticky='w', pady=10)
        
        # Save button
        def save_changes():
            try:
                nilai_diskon = int(nilai_entry.get())
                min_qty = float(qty_entry.get())
            except ValueError:
                messagebox.showerror("Error", "Nilai dan Minimum Pembelian harus berupa angka!")
                return
            
            success, msg = self.db.update_promotion(
                promo['id'],
                nama_promosi=nama_entry.get(),
                nilai_diskon=nilai_diskon,
                min_qty=min_qty,
                tanggal_mulai=mulai_date.get_date().isoformat(),
                tanggal_selesai=selesai_date.get_date().isoformat(),
                status=status_var.get(),
                berlaku_kelipatan=berlaku_kelipatan_var.get()
            )
            
            messagebox.showinfo("Sukses", msg) if success else messagebox.showerror("Error", msg)
            dialog.destroy()
        
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=7, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="💾 Simpan", command=save_changes).pack(side='left', padx=5)
        ttk.Button(button_frame, text="❌ Batal", command=dialog.destroy).pack(side='left', padx=5)
    
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
        canvas = tk.Canvas(self.content_area, bg=COLORS['bg_main'], highlightthickness=0, relief='flat', bd=0)
        scrollbar = ttk.Scrollbar(self.content_area, orient='vertical', command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        # Configure scrollbar appearance
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Create a window in the canvas
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        # Bind frame configure to update scroll region
        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # Make the frame width match canvas width
            canvas.itemconfig(canvas_window, width=canvas.winfo_width() if canvas.winfo_width() > 1 else 800)
        
        scrollable_frame.bind("<Configure>", _on_frame_configure)
        
        # Handle canvas configure to update frame width
        def _on_canvas_configure(event):
            if scrollable_frame.winfo_width() != event.width:
                canvas.itemconfig(canvas_window, width=event.width)
        
        canvas.bind("<Configure>", _on_canvas_configure)
        
        # Bind mousewheel for scrolling
        def _on_mousewheel(event):
            try:
                if canvas.winfo_exists():
                    scroll_units = int(-1*(event.delta/120))
                    canvas.yview_scroll(scroll_units, "units")
                    return "break"
            except (tk.TclError, AttributeError):
                pass
        
        canvas.bind("<MouseWheel>", _on_mousewheel)
        scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
        
        # Add Page Up/Down keyboard scrolling support
        def _on_page_up(event):
            try:
                if canvas.winfo_exists():
                    canvas.yview_scroll(-10, "units")
                    return "break"
            except (tk.TclError, AttributeError):
                pass
        
        def _on_page_down(event):
            try:
                if canvas.winfo_exists():
                    canvas.yview_scroll(10, "units")
                    return "break"
            except (tk.TclError, AttributeError):
                pass
        
        canvas.bind("<Prior>", _on_page_up)   # Page Up
        canvas.bind("<Next>", _on_page_down)  # Page Down
        
        # Pack canvas and scrollbar
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
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
    # TERMIN PAYMENT MANAGEMENT
    # ========================================================================
    
    def show_termin_payments(self):
        """Show termin payments details with overdue and upcoming payments."""
        self._clear_content()
        
        # Header
        header = ttk.Label(
            self.content_area,
            text="💳 Detail Pembayaran Termin",
            font=FONTS['title'],
            foreground=COLORS['primary']
        )
        header.pack(pady=10)
        
        # Create scrollable area
        canvas = tk.Canvas(self.content_area, bg=COLORS['bg_main'], highlightthickness=0, relief='flat', bd=0)
        scrollbar = ttk.Scrollbar(self.content_area, orient='vertical', command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        # Configure scrollbar appearance
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Create a window in the canvas
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        # Bind frame configure to update scroll region
        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # Make the frame width match canvas width
            canvas.itemconfig(canvas_window, width=canvas.winfo_width() if canvas.winfo_width() > 1 else 800)
        
        scrollable_frame.bind("<Configure>", _on_frame_configure)
        
        # Handle canvas configure to update frame width
        def _on_canvas_configure(event):
            if scrollable_frame.winfo_width() != event.width:
                canvas.itemconfig(canvas_window, width=event.width)
        
        canvas.bind("<Configure>", _on_canvas_configure)
        
        # Add mouse wheel scrolling support
        def _on_mousewheel(event):
            try:
                if canvas.winfo_exists():
                    scroll_units = int(-1*(event.delta/120))
                    canvas.yview_scroll(scroll_units, "units")
                    return "break"
            except (tk.TclError, AttributeError):
                pass
        
        canvas.bind("<MouseWheel>", _on_mousewheel)
        scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
        
        # Add Page Up/Down keyboard scrolling support
        def _on_page_up(event):
            try:
                if canvas.winfo_exists():
                    canvas.yview_scroll(-10, "units")
                    return "break"
            except (tk.TclError, AttributeError):
                pass
        
        def _on_page_down(event):
            try:
                if canvas.winfo_exists():
                    canvas.yview_scroll(10, "units")
                    return "break"
            except (tk.TclError, AttributeError):
                pass
        
        canvas.bind("<Prior>", _on_page_up)   # Page Up
        canvas.bind("<Next>", _on_page_down)  # Page Down
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        try:
            # Get all termin payment data
            overdue_payments = self.db.get_overdue_termin_payments()
            upcoming_payments = self.db.get_upcoming_termin_payments(days_ahead=30)
            
            # Section 1: Overdue Payments
            if overdue_payments:
                self._create_termin_section(
                    scrollable_frame,
                    "🔴 Pembayaran Terlamabat",
                    overdue_payments,
                    section_type='overdue'
                )
            else:
                no_overdue = tk.Label(
                    scrollable_frame,
                    text="✅ Tidak ada pembayaran yang terlamabat",
                    font=FONTS['normal'],
                    bg=COLORS['success'],
                    fg='white',
                    pady=10
                )
                no_overdue.pack(fill='x', padx=10, pady=10)
            
            # Separator
            if overdue_payments and upcoming_payments:
                separator = ttk.Separator(scrollable_frame, orient='horizontal')
                separator.pack(fill='x', pady=10)
            
            # Section 2: Upcoming Payments
            if upcoming_payments:
                self._create_termin_section(
                    scrollable_frame,
                    "🟡 Pembayaran yang Akan Jatuh Tempo (30 Hari ke Depan)",
                    upcoming_payments,
                    section_type='upcoming'
                )
            elif not overdue_payments:
                no_upcoming = tk.Label(
                    scrollable_frame,
                    text="✅ Tidak ada pembayaran yang akan jatuh tempo",
                    font=FONTS['normal'],
                    bg=COLORS['success'],
                    fg='white',
                    pady=10
                )
                no_upcoming.pack(fill='x', padx=10, pady=10)
            
            # Summary statistics
            total_overdue = sum(p.get('payment_amount', 0) for p in overdue_payments)
            total_upcoming = sum(p.get('payment_amount', 0) for p in upcoming_payments)
            
            summary_frame = tk.Frame(scrollable_frame, bg=COLORS['bg_card'], relief='solid', bd=1)
            summary_frame.pack(fill='x', padx=10, pady=20)
            
            summary_label = tk.Label(
                summary_frame,
                text="📊 RINGKASAN",
                font=FONTS['subheading'],
                bg=COLORS['primary'],
                fg='white',
                pady=5
            )
            summary_label.pack(fill='x')
            
            summary_content = tk.Frame(summary_frame, bg=COLORS['bg_card'])
            summary_content.pack(fill='both', expand=True, padx=10, pady=10)
            
            stats_text = f"""
Pembayaran Terlamabat:      {len(overdue_payments)} cicilan | {format_rp(total_overdue)}
Pembayaran akan Jatuh Tempo: {len(upcoming_payments)} cicilan | {format_rp(total_upcoming)}
Total Piutang Termin:        {len(overdue_payments) + len(upcoming_payments)} cicilan | {format_rp(total_overdue + total_upcoming)}
            """
            
            stats_label = tk.Label(
                summary_content,
                text=stats_text.strip(),
                font=FONTS['mono'],
                bg=COLORS['bg_card'],
                justify='left',
                anchor='w'
            )
            stats_label.pack(fill='x')
            
        except Exception as e:
            logger.error(f"Error showing termin payments: {e}")
            error_label = tk.Label(
                scrollable_frame,
                text=f"❌ Error: {str(e)}",
                font=FONTS['normal'],
                fg=COLORS['danger']
            )
            error_label.pack(pady=10)
    
    def _create_termin_section(self, parent, title, payments, section_type='upcoming'):
        """Create a termin payment section with table."""
        section_frame = tk.Frame(parent, bg=COLORS['bg_card'], relief='solid', bd=1)
        section_frame.pack(fill='x', padx=10, pady=10)
        
        # Section header
        header_bg = COLORS['danger'] if section_type == 'overdue' else COLORS['warning']
        header = tk.Label(
            section_frame,
            text=title,
            font=FONTS['subheading'],
            bg=header_bg,
            fg='white',
            pady=5
        )
        header.pack(fill='x')
        
        # Table header
        table_header_frame = tk.Frame(section_frame, bg='#E0E0E0')
        table_header_frame.pack(fill='x')
        
        headers = ['No', 'Invoice', 'Customer', 'Jatuh Tempo', 'Jumlah', 'Status Hari']
        col_widths = [5, 20, 20, 15, 20, 20]
        
        for i, header_text in enumerate(headers):
            header_label = tk.Label(
                table_header_frame,
                text=header_text,
                font=FONTS['small'],
                bg='#E0E0E0',
                anchor='w',
                width=col_widths[i]
            )
            header_label.pack(side='left', padx=2, pady=5)
        
        # Table rows
        table_frame = tk.Frame(section_frame, bg=COLORS['bg_card'])
        table_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        for idx, payment in enumerate(payments, 1):
            # Alternate row colors
            row_bg = '#F5F5F5' if idx % 2 == 0 else 'white'
            
            # Calculate days
            from datetime import datetime, date
            due_date_str = payment.get('due_date', '')
            due_date_obj = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            
            if section_type == 'overdue':
                days_info = f"{(date.today() - due_date_obj).days} hari lalu"
                text_color = COLORS['danger']
            else:
                days_info = f"dalam {(due_date_obj - date.today()).days} hari"
                text_color = '#D97706'
            
            row_frame = tk.Frame(table_frame, bg=row_bg)
            row_frame.pack(fill='x', pady=2)
            
            # Row data
            row_data = [
                str(idx),
                payment.get('invoice_number', 'N/A'),
                payment.get('customer_name', 'N/A'),
                due_date_str,
                format_rp(payment.get('payment_amount', 0)),
                days_info
            ]
            
            for i, data in enumerate(row_data):
                data_label = tk.Label(
                    row_frame,
                    text=data,
                    font=FONTS['small'],
                    bg=row_bg,
                    fg=text_color if i == len(row_data) - 1 else COLORS['text_primary'],
                    anchor='w',
                    width=col_widths[i]
                )
                data_label.pack(side='left', padx=2, pady=5)
    
    def _show_termin_detail_dialog(self, invoice_id: int, invoice_num: str, customer_name: str, due_date: str, cicilan_amount: str):
        """Show dialog untuk detail termin pembayaran."""
        dialog = tk.Toplevel(self)
        dialog.title(f"📋 Detail Termin - {invoice_num}")
        dialog.geometry("700x600")
        dialog.configure(bg=COLORS['bg_main'])
        dialog.grab_set()
        
        try:
            # Header
            header = tk.Label(
                dialog,
                text=f"Detail Pembayaran Termin",
                font=FONTS['heading'],
                bg=COLORS['primary'],
                fg='white',
                pady=10
            )
            header.pack(fill='x')
            
            # Info frame
            info_frame = tk.Frame(dialog, bg=COLORS['bg_card'], relief='flat', bd=1)
            info_frame.pack(fill='x', padx=10, pady=10)
            
            # Get invoice detail
            invoice_detail = self.db.get_invoice_detail(invoice_id)
            if invoice_detail:
                invoice = invoice_detail['invoice']
                items = invoice_detail['items']
                
                info_text = f"""
Invoice        : {invoice_num}
Customer       : {customer_name}
Tanggal        : {invoice.get('created_at', 'N/A')}
Jatuh Tempo    : {due_date}
Cicilan Amount : {cicilan_amount}
                """
            else:
                info_text = f"""
Invoice        : {invoice_num}
Customer       : {customer_name}
Jatuh Tempo    : {due_date}
Cicilan Amount : {cicilan_amount}
                """
            
            info_label = tk.Label(
                info_frame,
                text=info_text.strip(),
                font=FONTS['normal'],
                bg=COLORS['bg_card'],
                justify='left',
                anchor='w'
            )
            info_label.pack(anchor='w', padx=10, pady=10)
            
            # Items section (if available)
            if invoice_detail and items:
                items_frame = ttk.LabelFrame(dialog, text="📦 Item Invoice", padding=10)
                items_frame.pack(fill='both', expand=True, padx=10, pady=10)
                
                columns = ('No', 'Produk', 'Qty', 'Harga', 'Subtotal')
                items_tree = ttk.Treeview(items_frame, columns=columns, height=10, show='headings')
                
                items_tree.heading('No', text='No')
                items_tree.heading('Produk', text='Produk')
                items_tree.heading('Qty', text='Qty')
                items_tree.heading('Harga', text='Harga Satuan')
                items_tree.heading('Subtotal', text='Subtotal')
                
                items_tree.column('No', width=30)
                items_tree.column('Produk', width=250)
                items_tree.column('Qty', width=50)
                items_tree.column('Harga', width=100)
                items_tree.column('Subtotal', width=100)
                
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
            
            # Termin payments schedule
            if invoice_id:
                schedule_frame = ttk.LabelFrame(dialog, text="📅 Jadwal Pembayaran Termin", padding=10)
                schedule_frame.pack(fill='both', expand=True, padx=10, pady=10)
                
                termin_payments = self.db.get_termin_payments_by_invoice(invoice_id)
                
                if termin_payments:
                    columns = ('No', 'Jatuh Tempo', 'Jumlah', 'Status')
                    schedule_tree = ttk.Treeview(schedule_frame, columns=columns, height=8, show='headings')
                    
                    schedule_tree.heading('No', text='No')
                    schedule_tree.heading('Jatuh Tempo', text='Jatuh Tempo')
                    schedule_tree.heading('Jumlah', text='Jumlah')
                    schedule_tree.heading('Status', text='Status')
                    
                    schedule_tree.column('No', width=30)
                    schedule_tree.column('Jatuh Tempo', width=150)
                    schedule_tree.column('Jumlah', width=150)
                    schedule_tree.column('Status', width=100)
                    
                    for idx, payment in enumerate(termin_payments, 1):
                        status_display = "✅ Lunas" if payment['status'] == 'completed' else "⏳ Pending"
                        status_color = COLORS['success'] if payment['status'] == 'completed' else COLORS['warning']
                        
                        schedule_tree.insert('', 'end', values=(
                            str(idx),
                            payment['due_date'],
                            format_rp(payment['payment_amount']),
                            status_display
                        ))
                    
                    scrollbar = ttk.Scrollbar(schedule_frame, orient='vertical', command=schedule_tree.yview)
                    schedule_tree.configure(yscroll=scrollbar.set)
                    scrollbar.pack(side='right', fill='y')
                    schedule_tree.pack(fill='both', expand=True)
                else:
                    empty_label = ttk.Label(
                        schedule_frame,
                        text="Tidak ada jadwal pembayaran termin",
                        font=FONTS['normal']
                    )
                    empty_label.pack(pady=20)
            
            # Close button
            button_frame = ttk.Frame(dialog)
            button_frame.pack(fill='x', padx=10, pady=10)
            
            ttk.Button(
                button_frame,
                text="❌ Tutup",
                command=dialog.destroy
            ).pack(side='left')
        
        except Exception as e:
            logger.error(f"Error showing termin detail dialog: {e}")
            messagebox.showerror("Error", f"Error: {str(e)}")
    
    def _show_termin_payment_dialog(self, invoice_id: int, invoice_num: str, customer_name: str, cicilan_amount: str):
        """Show dialog untuk pembayaran cicilan termin."""
        dialog = tk.Toplevel(self)
        dialog.title(f"💳 Pembayaran Cicilan - {invoice_num}")
        dialog.geometry("500x400")
        dialog.configure(bg=COLORS['bg_main'])
        dialog.grab_set()
        
        try:
            # Header
            header = tk.Label(
                dialog,
                text=f"Pembayaran Cicilan Termin",
                font=FONTS['heading'],
                bg=COLORS['primary'],
                fg='white',
                pady=10
            )
            header.pack(fill='x')
            
            # Info frame
            info_frame = tk.Frame(dialog, bg=COLORS['bg_card'], relief='flat', bd=1)
            info_frame.pack(fill='x', padx=10, pady=10)
            
            info_text = f"""
Invoice    : {invoice_num}
Customer   : {customer_name}
Cicilan    : {cicilan_amount}
            """
            
            info_label = tk.Label(
                info_frame,
                text=info_text.strip(),
                font=FONTS['normal'],
                bg=COLORS['bg_card'],
                justify='left',
                anchor='w'
            )
            info_label.pack(anchor='w', padx=10, pady=10)
            
            # Payment input frame
            input_frame = ttk.LabelFrame(dialog, text="📝 Input Pembayaran", padding=10)
            input_frame.pack(fill='x', padx=10, pady=10)
            
            # Amount input
            ttk.Label(input_frame, text="Jumlah Pembayaran:").pack(anchor='w')
            amount_entry = ttk.Entry(input_frame, font=FONTS['normal'])
            amount_entry.pack(fill='x', pady=5)
            amount_entry.focus()
            
            # Notes input
            ttk.Label(input_frame, text="Catatan (opsional):").pack(anchor='w', pady=(10, 0))
            notes_text = tk.Text(input_frame, height=4, font=FONTS['small'])
            notes_text.pack(fill='both', expand=True, pady=5)
            
            # Button frame
            button_frame = ttk.Frame(dialog)
            button_frame.pack(fill='x', padx=10, pady=10)
            
            def on_submit():
                try:
                    payment_amount = int(amount_entry.get().strip().replace('.', '').replace(',', ''))
                    if payment_amount <= 0:
                        messagebox.showwarning("Peringatan", "Jumlah pembayaran harus lebih dari 0")
                        return
                    
                    notes = notes_text.get("1.0", "end").strip() or None
                    
                    # Process pembayaran
                    termin_service = TerminPaymentService(self.db)
                    success, msg = termin_service.record_termin_payment(invoice_id, payment_amount, notes)
                    
                    if success:
                        messagebox.showinfo("Berhasil", f"Pembayaran berhasil dicatat!\n\n{msg}")
                        dialog.destroy()
                        # Refresh tab
                        self.show_laporan()
                    else:
                        messagebox.showerror("Error", f"Pembayaran gagal:\n{msg}")
                
                except ValueError:
                    messagebox.showerror("Error", "Masukkan jumlah pembayaran yang valid")
            
            ttk.Button(
                button_frame,
                text="✅ Bayar",
                command=on_submit
            ).pack(side='left', padx=5)
            
            ttk.Button(
                button_frame,
                text="❌ Batal",
                command=dialog.destroy
            ).pack(side='left', padx=5)
        
        except Exception as e:
            logger.error(f"Error showing termin payment dialog: {e}")
            messagebox.showerror("Error", f"Error: {str(e)}")
    
    def _show_termin_pelunasan_dialog(self, invoice_id: int, invoice_num: str, customer_name: str, sisa_hutang: int):
        """Show dialog untuk pelunasan sisa hutang termin."""
        dialog = tk.Toplevel(self)
        dialog.title(f"✅ Pelunasan - {invoice_num}")
        dialog.geometry("500x400")
        dialog.configure(bg=COLORS['bg_main'])
        dialog.grab_set()
        
        try:
            # Header
            header = tk.Label(
                dialog,
                text=f"Pelunasan Sisa Hutang Termin",
                font=FONTS['heading'],
                bg=COLORS['success'],
                fg='white',
                pady=10
            )
            header.pack(fill='x')
            
            # Info frame
            info_frame = tk.Frame(dialog, bg=COLORS['bg_card'], relief='flat', bd=1)
            info_frame.pack(fill='x', padx=10, pady=10)
            
            info_text = f"""
Invoice         : {invoice_num}
Customer        : {customer_name}
Sisa Hutang     : {format_rp(sisa_hutang)}
            """
            
            info_label = tk.Label(
                info_frame,
                text=info_text.strip(),
                font=FONTS['normal'],
                bg=COLORS['bg_card'],
                justify='left',
                anchor='w'
            )
            info_label.pack(anchor='w', padx=10, pady=10)
            
            # Payment input frame
            input_frame = ttk.LabelFrame(dialog, text="📝 Input Pelunasan", padding=10)
            input_frame.pack(fill='x', padx=10, pady=10)
            
            # Amount input with default value
            ttk.Label(input_frame, text="Jumlah Pelunasan:").pack(anchor='w')
            amount_entry = ttk.Entry(input_frame, font=FONTS['normal'])
            amount_entry.insert(0, format_rp(sisa_hutang))
            amount_entry.pack(fill='x', pady=5)
            amount_entry.select_range(0, len(amount_entry.get()))
            amount_entry.focus()
            
            # Notes input
            ttk.Label(input_frame, text="Catatan (opsional):").pack(anchor='w', pady=(10, 0))
            notes_text = tk.Text(input_frame, height=4, font=FONTS['small'])
            notes_text.pack(fill='both', expand=True, pady=5)
            
            # Button frame
            button_frame = ttk.Frame(dialog)
            button_frame.pack(fill='x', padx=10, pady=10)
            
            def on_submit():
                try:
                    payment_amount = int(amount_entry.get().strip().replace('.', '').replace(',', '').replace('Rp', '').strip())
                    if payment_amount <= 0:
                        messagebox.showwarning("Peringatan", "Jumlah pelunasan harus lebih dari 0")
                        return
                    
                    if payment_amount > sisa_hutang:
                        messagebox.showwarning("Peringatan", f"Pelunasan tidak boleh melebihi sisa hutang: {format_rp(sisa_hutang)}")
                        return
                    
                    notes = notes_text.get("1.0", "end").strip() or f"Pelunasan sisa hutang - {format_rp(payment_amount)}"
                    
                    # Process pembayaran
                    termin_service = TerminPaymentService(self.db)
                    success, msg = termin_service.record_termin_payment(invoice_id, payment_amount, notes)
                    
                    if success:
                        messagebox.showinfo("Berhasil", f"Pelunasan berhasil dicatat!\n\n{msg}")
                        dialog.destroy()
                        # Refresh tab
                        self.show_laporan()
                    else:
                        messagebox.showerror("Error", f"Pelunasan gagal:\n{msg}")
                
                except ValueError:
                    messagebox.showerror("Error", "Masukkan jumlah pelunasan yang valid")
            
            ttk.Button(
                button_frame,
                text="✅ Lunasi",
                command=on_submit
            ).pack(side='left', padx=5)
            
            ttk.Button(
                button_frame,
                text="❌ Batal",
                command=dialog.destroy
            ).pack(side='left', padx=5)
        
        except Exception as e:
            logger.error(f"Error showing termin pelunasan dialog: {e}")
            messagebox.showerror("Error", f"Error: {str(e)}")
    
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
        
        # Create Canvas with Scrollbar for scrollable content
        canvas_frame = ttk.Frame(self.content_area)
        canvas_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        canvas = tk.Canvas(canvas_frame, bg=COLORS['bg_main'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient='vertical', command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style=None)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Bind mouse wheel for scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Store Info Section
        store_frame = ttk.LabelFrame(scrollable_frame, text="🏪 Informasi Toko", padding=15)
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
                    'owner': store_info.get('owner', 'PT. AVENTA INTELLIGENT POWER')
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
        user_mgmt_frame = ttk.LabelFrame(scrollable_frame, text="👥 Manajemen User", padding=10)
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
        
        user_tree.grid(row=0, column=0, sticky='nsew')
        
        # Vertical Scrollbar
        vsb = ttk.Scrollbar(user_list_frame, orient='vertical', command=user_tree.yview)
        vsb.grid(row=0, column=1, sticky='ns')
        
        # Horizontal Scrollbar
        hsb = ttk.Scrollbar(user_list_frame, orient='horizontal', command=user_tree.xview)
        hsb.grid(row=1, column=0, sticky='ew')
        
        user_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Configure grid weights
        user_list_frame.grid_rowconfigure(0, weight=1)
        user_list_frame.grid_columnconfigure(0, weight=1)
        
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
        stats_frame = ttk.LabelFrame(scrollable_frame, text="📊 Database Info", padding=10)
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
        about_frame = ttk.LabelFrame(scrollable_frame, text="ℹ️  Tentang Sistem", padding=10)
        about_frame.pack(fill='x', padx=10, pady=10)
        
        about_text = """
🛒 SISTEM POS - Toko
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
        danger_frame = ttk.LabelFrame(scrollable_frame, text="⚠️ Zone Berbahaya", padding=10)
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
            
            # Configure scrollbar appearance
            canvas.configure(yscrollcommand=scrollbar.set)
            
            # Create a window in the canvas
            canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            
            # Bind frame configure to update scroll region
            def _on_frame_configure(event):
                canvas.configure(scrollregion=canvas.bbox("all"))
                # Make the frame width match canvas width
                canvas.itemconfig(canvas_window, width=canvas.winfo_width() if canvas.winfo_width() > 1 else 800)
            
            scrollable_frame.bind("<Configure>", _on_frame_configure)
            
            # Handle canvas configure to update frame width
            def _on_canvas_configure(event):
                if scrollable_frame.winfo_width() != event.width:
                    canvas.itemconfig(canvas_window, width=event.width)
            
            canvas.bind("<Configure>", _on_canvas_configure)
            
            # Bind mousewheel for scrolling
            def _on_mousewheel(event):
                try:
                    if canvas.winfo_exists():
                        scroll_units = int(-1*(event.delta/120))
                        canvas.yview_scroll(scroll_units, "units")
                        return "break"
                except (tk.TclError, AttributeError):
                    pass
            
            canvas.bind("<MouseWheel>", _on_mousewheel)
            scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
            
            # Add Page Up/Down keyboard scrolling support
            def _on_page_up(event):
                try:
                    if canvas.winfo_exists():
                        canvas.yview_scroll(-10, "units")
                        return "break"
                except (tk.TclError, AttributeError):
                    pass
            
            def _on_page_down(event):
                try:
                    if canvas.winfo_exists():
                        canvas.yview_scroll(10, "units")
                        return "break"
                except (tk.TclError, AttributeError):
                    pass
            
            canvas.bind("<Prior>", _on_page_up)   # Page Up
            canvas.bind("<Next>", _on_page_down)  # Page Down
            
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
