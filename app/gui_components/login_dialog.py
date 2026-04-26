# ============================================================================
# LOGIN_DIALOG.PY - Login Dialog Component for Phase 5 GUI
# ============================================================================
# Fungsi: Tkinter login dialog dengan UserService integration
# Responsibilitas: User authentication, error handling, session creation
# ============================================================================

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable, Tuple
from app.services.user_service import UserService
from app.utils.session_manager import SessionManager, get_session_manager
from app.utils.error_handler import ValidationError
from logger_config import get_logger

logger = get_logger(__name__)


class LoginDialog:
    """
    Login dialog untuk user authentication.
    
    Integration dengan UserService & SessionManager.
    """
    
    def __init__(
        self,
        parent: tk.Widget,
        user_service: UserService,
        on_login_success: Optional[Callable] = None,
        on_login_fail: Optional[Callable] = None,
        session_manager: SessionManager = None
    ):
        """
        Init LoginDialog.
        
        Args:
            parent: Parent tkinter widget
            user_service: UserService instance
            on_login_success: Callback pada sukses
            on_login_fail: Callback pada gagal
            session_manager: SessionManager instance
        """
        self.user_service = user_service
        self.session_manager = session_manager or get_session_manager()
        self.on_login_success = on_login_success
        self.on_login_fail = on_login_fail
        
        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Login - Point of Sale System")
        self.dialog.geometry("400x300")
        self.dialog.resizable(False, False)
        self.dialog.grab_set()
        
        # Center window
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (300 // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        self._create_widgets()
        self.username_entry.focus()
        
        logger.info("LoginDialog initialized")
    
    def _create_widgets(self):
        """Create login form widgets."""
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.grid(row=0, column=0, sticky='nsew')
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="Login to POS System",
            font=("Arial", 16, "bold")
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=20)
        
        # Username
        ttk.Label(main_frame, text="Username:").grid(row=1, column=0, sticky='w', pady=5)
        self.username_entry = ttk.Entry(main_frame, width=30)
        self.username_entry.grid(row=1, column=1, sticky='ew', pady=5)
        self.username_entry.bind('<Return>', lambda e: self._on_login())
        
        # Password
        ttk.Label(main_frame, text="Password:").grid(row=2, column=0, sticky='w', pady=5)
        self.password_entry = ttk.Entry(main_frame, width=30, show='*')
        self.password_entry.grid(row=2, column=1, sticky='ew', pady=5)
        self.password_entry.bind('<Return>', lambda e: self._on_login())
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
        ttk.Button(
            button_frame,
            text="Login",
            command=self._on_login
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Cancel",
            command=self._on_cancel
        ).pack(side=tk.LEFT, padx=5)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="", foreground="red")
        self.status_label.grid(row=4, column=0, columnspan=2, pady=10)
        
        # Configure grid
        main_frame.columnconfigure(1, weight=1)
    
    def _on_login(self):
        """Handle login button click."""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        
        if not username or not password:
            self.status_label.config(text="Username dan password harus diisi")
            return
        
        try:
            # Authenticate user
            is_valid, user = self.user_service.authenticate(username, password)
            
            if not is_valid or not user:
                self.status_label.config(text="Username atau password salah")
                logger.warning(f"Login failed untuk username: {username}")
                
                if self.on_login_fail:
                    self.on_login_fail(username, "Authentication failed")
                return
            
            # Create session
            session = self.session_manager.create_session(user)
            
            logger.info(f"Login berhasil: {username} (role={user.role})")
            messagebox.showinfo("Sukses", f"Welcome, {username}!")
            
            if self.on_login_success:
                self.on_login_success(user)
            
            self.dialog.destroy()
        
        except ValidationError as e:
            self.status_label.config(text=str(e))
            logger.error(f"Validation error dalam login: {e}")
        
        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}")
            logger.error(f"Login error: {e}")
    
    def _on_cancel(self):
        """Handle cancel button click."""
        self.dialog.destroy()
        
        if self.on_login_fail:
            self.on_login_fail(None, "Login cancelled")


def show_login_dialog(
    parent: tk.Widget,
    user_service: UserService,
    on_success: Optional[Callable] = None,
    on_fail: Optional[Callable] = None
) -> Optional[Tuple]:
    """
    Show login dialog.
    
    Args:
        parent: Parent tkinter widget
        user_service: UserService instance
        on_success: Callback pada sukses
        on_fail: Callback pada gagal
        
    Returns:
        LoginDialog instance
    """
    return LoginDialog(
        parent=parent,
        user_service=user_service,
        on_login_success=on_success,
        on_login_fail=on_fail
    )
