# ============================================================================
# ASYNC_MANAGER.PY - Threading & Async Operations Manager
# ============================================================================
# Fungsi: Manage background tasks, heavy operations tanpa blocking UI
# Responsibilitas: Thread pooling, task scheduling, progress tracking
# ============================================================================

import threading
import queue
from typing import Callable, Any, Dict, List, Optional
from functools import wraps
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, Future
import time
from logger_config import get_logger

logger = get_logger(__name__)


class AsyncTask:
    """Represent async task dengan metadata."""
    
    def __init__(self, task_id: str, name: str, func: Callable, args: tuple = (), kwargs: Dict = None):
        """
        Init async task.
        
        Args:
            task_id: Unique task identifier
            name: Readable task name
            func: Function to execute
            args: Positional arguments
            kwargs: Keyword arguments
        """
        self.task_id = task_id
        self.name = name
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self.status = 'pending'  # pending, running, completed, failed
        self.result = None
        self.error = None
        self.progress = 0  # 0-100
        self.start_time = None
        self.end_time = None
        self.future = None
    
    def get_duration(self) -> Optional[float]:
        """Get task duration dalam seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary untuk serialization."""
        return {
            'task_id': self.task_id,
            'name': self.name,
            'status': self.status,
            'progress': self.progress,
            'result': str(self.result) if self.result else None,
            'error': str(self.error) if self.error else None,
            'duration': self.get_duration(),
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None
        }


class AsyncManager:
    """
    Manager untuk background tasks & threading.
    
    Provide:
    - Thread pool untuk task execution
    - Task tracking & progress monitoring
    - Error handling & retry logic
    - Task scheduling
    """
    
    def __init__(self, max_workers: int = 5, queue_size: int = 100):
        """
        Init AsyncManager.
        
        Args:
            max_workers: Maximum concurrent threads
            queue_size: Maximum pending tasks
        """
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.tasks = {}  # task_id -> AsyncTask
        self.task_queue = queue.Queue(maxsize=queue_size)
        self.running = True
        logger.info(f"AsyncManager initialized: workers={max_workers}, queue_size={queue_size}")
    
    def submit_task(
        self,
        task_id: str,
        name: str,
        func: Callable,
        args: tuple = (),
        kwargs: Dict = None,
        callback: Optional[Callable] = None,
        error_callback: Optional[Callable] = None
    ) -> AsyncTask:
        """
        Submit task untuk background execution.
        
        Args:
            task_id: Unique task ID
            name: Readable task name
            func: Function to execute
            args: Positional arguments
            kwargs: Keyword arguments
            callback: Success callback function
            error_callback: Error callback function
            
        Returns:
            AsyncTask object
        """
        try:
            if task_id in self.tasks:
                raise ValueError(f"Task {task_id} sudah ada")
            
            task = AsyncTask(task_id, name, func, args, kwargs or {})
            task.status = 'pending'
            task.start_time = datetime.now()
            
            # Wrap function dengan progress tracking
            def task_wrapper():
                try:
                    task.status = 'running'
                    logger.info(f"Task started: {name} (ID={task_id})")
                    
                    result = func(*task.args, **task.kwargs)
                    
                    task.status = 'completed'
                    task.result = result
                    task.progress = 100
                    task.end_time = datetime.now()
                    
                    logger.info(f"Task completed: {name} (ID={task_id})")
                    
                    if callback:
                        try:
                            callback(result)
                        except Exception as e:
                            logger.error(f"Callback error untuk task {task_id}: {e}")
                    
                    return result
                
                except Exception as e:
                    task.status = 'failed'
                    task.error = str(e)
                    task.end_time = datetime.now()
                    
                    logger.error(f"Task failed: {name} (ID={task_id}): {e}")
                    
                    if error_callback:
                        try:
                            error_callback(e)
                        except Exception as cb_error:
                            logger.error(f"Error callback error untuk task {task_id}: {cb_error}")
                    
                    raise
            
            # Submit ke thread pool
            future = self.executor.submit(task_wrapper)
            task.future = future
            self.tasks[task_id] = task
            
            logger.info(f"Task submitted: {name} (ID={task_id})")
            return task
        
        except Exception as e:
            logger.error(f"Error submitting task {task_id}: {e}")
            raise
    
    def get_task(self, task_id: str) -> Optional[AsyncTask]:
        """Get task status & result."""
        return self.tasks.get(task_id)
    
    def get_task_result(self, task_id: str, timeout: float = None) -> Any:
        """
        Get task result, blocking sampai selesai.
        
        Args:
            task_id: Task ID
            timeout: Timeout dalam seconds
            
        Returns:
            Task result
            
        Raises:
            TimeoutError: Jika timeout
            Exception: Jika task failed
        """
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} tidak ditemukan")
        
        try:
            result = task.future.result(timeout=timeout)
            return result
        except Exception as e:
            logger.error(f"Error getting result untuk task {task_id}: {e}")
            raise
    
    def get_all_tasks(self) -> List[AsyncTask]:
        """Get semua tasks dengan status."""
        return list(self.tasks.values())
    
    def get_running_tasks(self) -> List[AsyncTask]:
        """Get hanya running tasks."""
        return [t for t in self.tasks.values() if t.status == 'running']
    
    def get_pending_tasks(self) -> List[AsyncTask]:
        """Get hanya pending tasks."""
        return [t for t in self.tasks.values() if t.status == 'pending']
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel task jika belum started."""
        task = self.get_task(task_id)
        if not task:
            return False
        
        if task.future.cancel():
            task.status = 'cancelled'
            logger.info(f"Task cancelled: {task_id}")
            return True
        
        return False
    
    def wait_all(self, timeout: float = None) -> Dict[str, Dict]:
        """
        Wait untuk semua tasks selesai.
        
        Args:
            timeout: Timeout dalam seconds
            
        Returns:
            Dictionary dengan task results/errors
        """
        results = {}
        
        for task_id, task in self.tasks.items():
            try:
                result = self.get_task_result(task_id, timeout=timeout)
                results[task_id] = {'status': 'completed', 'result': result}
            except Exception as e:
                results[task_id] = {'status': 'failed', 'error': str(e)}
        
        return results
    
    def schedule_periodic(
        self,
        task_id: str,
        name: str,
        func: Callable,
        interval_seconds: int,
        args: tuple = (),
        kwargs: Dict = None
    ) -> threading.Thread:
        """
        Schedule task untuk run periodically.
        
        Args:
            task_id: Unique task ID
            name: Readable task name
            func: Function to execute
            interval_seconds: Interval antara executions
            args: Positional arguments
            kwargs: Keyword arguments
            
        Returns:
            Thread object
        """
        def periodic_runner():
            while self.running:
                try:
                    func(*args, **(kwargs or {}))
                except Exception as e:
                    logger.error(f"Periodic task {task_id} error: {e}")
                
                time.sleep(interval_seconds)
        
        thread = threading.Thread(target=periodic_runner, daemon=True, name=f"periodic-{task_id}")
        thread.start()
        
        logger.info(f"Periodic task scheduled: {name} (interval={interval_seconds}s)")
        return thread
    
    def shutdown(self, wait: bool = True, timeout: float = 30):
        """Shutdown async manager."""
        self.running = False
        self.executor.shutdown(wait=wait, timeout=timeout)
        logger.info("AsyncManager shutdown complete")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        total = len(self.tasks)
        running = len(self.get_running_tasks())
        pending = len(self.get_pending_tasks())
        completed = len([t for t in self.tasks.values() if t.status == 'completed'])
        failed = len([t for t in self.tasks.values() if t.status == 'failed'])
        
        return {
            'total_tasks': total,
            'running': running,
            'pending': pending,
            'completed': completed,
            'failed': failed,
            'max_workers': self.max_workers,
            'timestamp': datetime.now().isoformat()
        }


def run_async(task_id: str, name: str):
    """
    Decorator untuk run function async.
    
    Usage:
        @run_async('report_gen', 'Generate Report')
        def generate_report(date):
            # Long running operation
            return report_data
        
        task = generate_report('2024-01-01')
        result = task.future.result()
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from app.utils.async_manager import AsyncManager
            manager = AsyncManager()
            return manager.submit_task(
                task_id=task_id,
                name=name,
                func=func,
                args=args,
                kwargs=kwargs
            )
        return wrapper
    return decorator


# Global async manager instance
_async_manager = None

def get_async_manager(max_workers: int = 5) -> AsyncManager:
    """Get atau create global async manager."""
    global _async_manager
    if _async_manager is None:
        _async_manager = AsyncManager(max_workers=max_workers)
    return _async_manager
