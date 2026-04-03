# ============================================================================
# LOGGER_CONFIG.PY - Centralized Logging Configuration
# ============================================================================
# Fungsi: Setup Python logging dengan file dan console handlers
# Fitur: Timestamp, log levels (INFO, WARNING, ERROR), structured format
# ============================================================================

import logging
import logging.handlers
import os
from datetime import datetime

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

LOG_FILE = "pos.log"
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s - %(levelname)-8s - %(name)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(log_file=LOG_FILE, log_level=LOG_LEVEL):
    """
    Setup logging configuration dengan file dan console handlers.
    
    Args:
        log_file (str): Path ke file log (default: pos.log)
        log_level (int): Logging level (default: INFO)
        
    Returns:
        bool: True jika setup berhasil
        
    Fitur:
    - File handler: Tulis ke pos.log dengan rotation (5MB max)
    - Console handler: Display ke terminal
    - Format: Timestamp, level, logger name, message
    """
    
    try:
        # Create root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # Create formatter
        formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
        
        # ================================================================
        # FILE HANDLER - Write log ke file dengan rotation
        # ================================================================
        
        # Check jika file sudah ada
        file_exists = os.path.exists(log_file)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=5  # Keep 5 backup files
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        
        # ================================================================
        # CONSOLE HANDLER - Display log ke terminal
        # ================================================================
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)  # Only show INFO and above di console
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # Log file info
        logger = logging.getLogger(__name__)
        
        if not file_exists:
            logger.info("=" * 70)
            logger.info("SISTEM POS - Application Started")
            logger.info("=" * 70)
            logger.info(f"Log file: {os.path.abspath(log_file)}")
            logger.info(f"Log level: {logging.getLevelName(log_level)}")
        else:
            logger.info("=" * 70)
            logger.info("SISTEM POS - Application Restarted")
            logger.info("=" * 70)
        
        logger.info(f"Logging initialized at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error setting up logging: {e}")
        return False


def get_logger(name: str):
    """
    Get logger instance dengan nama specific.
    
    Args:
        name (str): Logger name (biasanya __name__)
        
    Returns:
        logging.Logger: Logger instance
        
    Contoh:
        logger = get_logger(__name__)
        logger.info("Produk ditambahkan")
    """
    return logging.getLogger(name)


# ============================================================================
# LOGGING LEVELS
# ============================================================================

def log_info(name: str, message: str):
    """Log INFO level message."""
    get_logger(name).info(message)


def log_warning(name: str, message: str):
    """Log WARNING level message."""
    get_logger(name).warning(message)


def log_error(name: str, message: str, exc_info=False):
    """
    Log ERROR level message.
    
    Args:
        name (str): Logger name
        message (str): Error message
        exc_info (bool): Include exception info (True untuk exception details)
    """
    get_logger(name).error(message, exc_info=exc_info)


def log_exception(name: str, message: str):
    """Log exception dengan full traceback."""
    get_logger(name).exception(message)


# ============================================================================
# COMMON LOG MESSAGES - Helper functions
# ============================================================================

def log_startup():
    """Log application startup."""
    logger = get_logger(__name__)
    logger.info("Application startup initiated")
    logger.info("All modules loaded successfully")


def log_product_added(kode: str, nama: str):
    """Log produk ditambahkan."""
    get_logger(__name__).info(f"Product added: {kode} = {nama}")


def log_product_updated(kode: str, nama: str):
    """Log produk diupdate."""
    get_logger(__name__).info(f"Product updated: {kode} = {nama}")


def log_product_deleted(kode: str, nama: str):
    """Log produk dihapus."""
    get_logger(__name__).warning(f"Product deleted: {kode} = {nama}")


def log_transaction_completed(trans_id: int, total: int, items_count: int):
    """Log transaksi selesai."""
    get_logger(__name__).info(f"Transaction completed: ID={trans_id}, Total=Rp{total:,}, Items={items_count}")


def log_user_login(username: str, role: str):
    """Log user login."""
    get_logger(__name__).info(f"User login: {username} ({role})")


def log_user_logout(username: str):
    """Log user logout."""
    get_logger(__name__).info(f"User logout: {username}")


def log_database_error(operation: str, error: str):
    """Log database error."""
    get_logger(__name__).error(f"Database error during {operation}: {error}")


# ============================================================================
# INITIALIZE LOGGING ON MODULE LOAD
# ============================================================================

# Setup logging ketika module diimport
setup_logging()
