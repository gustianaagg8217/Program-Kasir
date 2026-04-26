# ============================================================================
# ASYNC_HELPER.PY - Tkinter Async/Threading Utility for Non-Blocking Operations
# ============================================================================
# Fungsi: Menyediakan helper functions untuk operasi async dan thread-safe UI updates
# Fitur: ThreadPoolExecutor wrapper, loading indicators, thread-safe UI callbacks
# ============================================================================

import tkinter as tk
from tkinter import ttk
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from typing import Callable, Any, Optional, Dict
import time

# ============================================================================
# ASYNC TASK MANAGER
# ============================================================================

class AsyncTaskManager:
    """
    Manager untuk menjalankan tugas berat di background thread dengan UI loading indicator.
    Provides thread-safe callback system untuk update UI dari background thread.
    """
    
    def __init__(self, max_workers: int = 3):
        """
        Initialize AsyncTaskManager.
        
        Args:
            max_workers: Maximum number of background threads
        """
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.active_tasks = {}  # {task_id: Future}
        self.task_lock = threading.Lock()
    
    def submit_task(self, func: Callable, *args, task_id: str = None, **kwargs) -> str:
        """
        Submit async task to background thread.
        
        Args:
            func: Function to execute
            *args: Function arguments
            task_id: Optional task identifier
            **kwargs: Function keyword arguments
            
        Returns:
            Task ID for tracking
        """
        if task_id is None:
            task_id = f"task_{int(time.time() * 1000)}"
        
        future = self.executor.submit(func, *args, **kwargs)
        
        with self.task_lock:
            self.active_tasks[task_id] = future
        
        return task_id
    
    def get_task_result(self, task_id: str, timeout: float = None) -> Any:
        """
        Get result from completed task.
        
        Args:
            task_id: Task identifier
            timeout: Timeout in seconds
            
        Returns:
            Task result or None if not ready
            
        Raises:
            TimeoutError if timeout exceeded
        """
        with self.task_lock:
            future = self.active_tasks.get(task_id)
        
        if future is None:
            return None
        
        return future.result(timeout=timeout)
    
    def is_task_done(self, task_id: str) -> bool:
        """Check if task is completed."""
        with self.task_lock:
            future = self.active_tasks.get(task_id)
        return future.done() if future else False
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel task if not yet started."""
        with self.task_lock:
            future = self.active_tasks.get(task_id)
        return future.cancel() if future else False
    
    def shutdown(self):
        """Shutdown executor and wait for all tasks."""
        self.executor.shutdown(wait=True)


# ============================================================================
# ASYNC OPERATION WRAPPER
# ============================================================================

class AsyncOperation:
    """
    Wrapper untuk single async operation dengan loading indicator support.
    Provides easy interface untuk background task dengan callback.
    """
    
    def __init__(self, parent: tk.Widget, task_func: Callable, 
                 on_complete: Callable = None, on_error: Callable = None,
                 show_loading: bool = True):
        """
        Initialize AsyncOperation.
        
        Args:
            parent: Parent Tkinter widget
            task_func: Function to execute in background
            on_complete: Callback when task completes (func(result))
            on_error: Callback on error (func(exception))
            show_loading: Whether to show loading indicator
        """
        self.parent = parent
        self.task_func = task_func
        self.on_complete = on_complete
        self.on_error = on_error
        self.show_loading = show_loading
        
        self.loading_frame = None
        self.task_manager = AsyncTaskManager(max_workers=1)
        self.task_id = None
    
    def start(self, *args, **kwargs):
        """Start async task with loading indicator."""
        # Show loading indicator
        if self.show_loading:
            self.loading_frame = self._create_loading_indicator()
        
        # Submit task
        self.task_id = self.task_manager.submit_task(self.task_func, *args, **kwargs)
        
        # Start polling for completion
        self._poll_task()
    
    def _poll_task(self):
        """Poll task status and call callbacks when done."""
        if self.task_manager.is_task_done(self.task_id):
            # Task completed
            try:
                result = self.task_manager.get_task_result(self.task_id, timeout=0)
                self._hide_loading_indicator()
                
                if self.on_complete:
                    self.on_complete(result)
            except Exception as e:
                self._hide_loading_indicator()
                if self.on_error:
                    self.on_error(e)
        else:
            # Still running, poll again
            self.parent.after(100, self._poll_task)
    
    def _create_loading_indicator(self) -> tk.Frame:
        """Create loading indicator overlay."""
        # Create semi-transparent overlay
        frame = tk.Frame(self.parent, bg='#00000080', highlightthickness=0)
        frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        # Center loading widget
        inner_frame = tk.Frame(frame, bg='white', relief='flat')
        inner_frame.place(relx=0.5, rely=0.5, anchor='center')
        
        # Loading spinner animation
        spinner_label = tk.Label(
            inner_frame,
            text="⏳ Loading...",
            font=('Segoe UI', 12, 'bold'),
            bg='white',
            fg='#2E86AB'
        )
        spinner_label.pack(padx=20, pady=15)
        
        # Animated dots
        self.spinner_dots = 0
        self._animate_spinner(spinner_label)
        
        frame.lift()
        self.parent.update_idletasks()
        return frame
    
    def _animate_spinner(self, label: tk.Label):
        """Animate spinner dots."""
        if self.loading_frame is None:
            return
        
        dots = '.' * (self.spinner_dots % 4)
        label.config(text=f"⏳ Loading{dots}")
        self.spinner_dots += 1
        label.after(300, lambda: self._animate_spinner(label))
    
    def _hide_loading_indicator(self):
        """Hide loading indicator."""
        if self.loading_frame:
            self.loading_frame.destroy()
            self.loading_frame = None


# ============================================================================
# THREAD-SAFE UI UPDATE HELPER
# ============================================================================

class UIThreadSafeUpdater:
    """
    Provides thread-safe methods for updating Tkinter UI from background threads.
    Use this to safely update widgets from background worker threads.
    """
    
    @staticmethod
    def safe_call(widget: tk.Widget, callback: Callable, *args, **kwargs):
        """
        Execute callback safely in main Tkinter thread.
        
        Args:
            widget: Any Tkinter widget (used to access main thread)
            callback: Function to execute in main thread
            *args: Callback arguments
            **kwargs: Callback keyword arguments
        """
        def _execute():
            try:
                callback(*args, **kwargs)
            except Exception as e:
                print(f"Error in safe_call: {e}")
        
        # Schedule callback in main thread
        widget.after(0, _execute)
    
    @staticmethod
    def update_label(label: ttk.Label, text: str):
        """Safely update label text."""
        UIThreadSafeUpdater.safe_call(label, label.config, text=text)
    
    @staticmethod
    def update_treeview(tree: ttk.Treeview, items: list):
        """Safely populate treeview with items."""
        def _populate():
            # Clear existing items
            for item in tree.get_children():
                tree.delete(item)
            
            # Add new items
            for item_data in items:
                tree.insert('', 'end', values=item_data)
        
        UIThreadSafeUpdater.safe_call(tree, _populate)
    
    @staticmethod
    def show_error(widget: tk.Widget, title: str, message: str):
        """Safely show error dialog."""
        from tkinter import messagebox
        UIThreadSafeUpdater.safe_call(
            widget, 
            messagebox.showerror, 
            title, 
            message
        )


# ============================================================================
# LOADING INDICATOR COMPONENT
# ============================================================================

class LoadingIndicator(tk.Frame):
    """
    Reusable loading indicator component for Tkinter.
    Shows spinner animation with status message.
    """
    
    def __init__(self, parent: tk.Widget, message: str = "Loading...", **kwargs):
        """
        Initialize LoadingIndicator.
        
        Args:
            parent: Parent Tkinter widget
            message: Status message to display
            **kwargs: Additional Frame kwargs
        """
        super().__init__(parent, **kwargs)
        
        self.message = message
        self.is_running = False
        self.animation_step = 0
        
        # Create UI
        self._create_ui()
    
    def _create_ui(self):
        """Create loading indicator UI."""
        # Spinner
        spinner_label = tk.Label(
            self,
            text="⏳",
            font=('Arial', 24),
            fg='#2E86AB'
        )
        spinner_label.pack(pady=10)
        self.spinner_label = spinner_label
        
        # Message
        msg_label = tk.Label(
            self,
            text=self.message,
            font=('Segoe UI', 11),
            fg='#2E86AB'
        )
        msg_label.pack(pady=5)
        self.msg_label = msg_label
    
    def start(self):
        """Start loading animation."""
        self.is_running = True
        self._animate()
    
    def stop(self):
        """Stop loading animation."""
        self.is_running = False
    
    def _animate(self):
        """Animate spinner."""
        if not self.is_running:
            return
        
        spinners = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.animation_step = (self.animation_step + 1) % len(spinners)
        self.spinner_label.config(text=spinners[self.animation_step])
        
        self.after(100, self._animate)
    
    def set_message(self, message: str):
        """Update message."""
        self.msg_label.config(text=message)


# ============================================================================
# BATCH ASYNC EXECUTOR
# ============================================================================

class BatchAsyncExecutor:
    """
    Execute multiple async tasks in parallel and wait for all to complete.
    Useful for loading multiple data sources simultaneously.
    """
    
    def __init__(self, max_workers: int = 5):
        """Initialize executor."""
        self.task_manager = AsyncTaskManager(max_workers=max_workers)
        self.tasks = {}
    
    def add_task(self, task_id: str, func: Callable, *args, **kwargs) -> str:
        """Add task to batch."""
        task_id = self.task_manager.submit_task(func, *args, task_id=task_id, **kwargs)
        self.tasks[task_id] = func
        return task_id
    
    def wait_all(self, timeout: float = None) -> Dict[str, Any]:
        """
        Wait for all tasks to complete.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Dictionary of {task_id: result}
        """
        results = {}
        for task_id in self.tasks:
            try:
                results[task_id] = self.task_manager.get_task_result(task_id, timeout=timeout)
            except Exception as e:
                results[task_id] = None
                print(f"Task {task_id} failed: {e}")
        
        return results
    
    def wait_any(self, timeout: float = None) -> tuple:
        """
        Wait for any task to complete.
        
        Returns:
            Tuple of (task_id, result) for first completed task
        """
        for task_id in self.tasks:
            if self.task_manager.is_task_done(task_id):
                result = self.task_manager.get_task_result(task_id, timeout=timeout)
                return (task_id, result)
        
        return (None, None)


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

# Global task manager (singleton)
_global_task_manager = None

def get_global_task_manager() -> AsyncTaskManager:
    """Get or create global AsyncTaskManager."""
    global _global_task_manager
    if _global_task_manager is None:
        _global_task_manager = AsyncTaskManager(max_workers=5)
    return _global_task_manager

def cleanup_global_task_manager():
    """Shutdown global task manager."""
    global _global_task_manager
    if _global_task_manager:
        _global_task_manager.shutdown()
        _global_task_manager = None
