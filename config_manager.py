# ============================================================================
# CONFIG_MANAGER.PY - Configuration Management System
# ============================================================================
# Fungsi: Load, manage, dan provide access ke aplikasi config
# Menggantikan semua hardcoded values dengan dynamic configuration
# ============================================================================

import json
import os
from typing import Any, Optional
from logger_config import get_logger

logger = get_logger(__name__)

# ============================================================================
# CONFIG MANAGER - Single source of truth untuk semua configuration
# ============================================================================

class ConfigManager:
    """
    Centralized configuration manager untuk POS System.
    
    Fitur:
    - Load config dari config.json
    - Provide access ke config values
    - Fallback ke default values jika tidak ada
    - Support untuk override via environment variables
    
    Attributes:
        config (dict): Configuration dictionary
        config_file (str): Path ke config.json
        
    Methods:
        load(): Load config dari file
        get(): Ambil config value
        save(): Simpan config ke file
    """
    
    DEFAULT_CONFIG = {
        "store": {
            "name": "TOKO POS",
            "address": "Alamat Toko",
            "phone": "+62 XXX XXXX XXXX",
            "email": "info@toko.com"
        },
        "business": {
            "currency": "IDR",
            "tax_default": 0,
            "discount_default": 0,
            "timezone": "Asia/Jakarta"
        },
        "receipt": {
            "width": 50,
            "show_footer": True,
            "auto_print": False
        },
        "backup": {
            "auto_backup": True,
            "backup_interval_hours": 24,
            "keep_backups": 7
        },
        "logging": {
            "level": "INFO",
            "file": "pos.log",
            "max_size_mb": 5,
            "backup_count": 5
        },
        "telegram": {
            "enabled": False,
            "send_daily_report": False,
            "send_low_stock_alert": True,
            "report_time": "18:00"
        }
    }
    
    def __init__(self, config_file: str = "config.json"):
        """
        Inisialisasi ConfigManager.
        
        Args:
            config_file (str): Path ke config file (default: config.json)
        """
        self.config_file = config_file
        self.config = {}
        self.load()
    
    # ========================================================================
    # CONFIG LOADING & SAVING
    # ========================================================================
    
    def load(self) -> bool:
        """
        Load configuration dari file.
        
        Jika file tidak ada, gunakan DEFAULT_CONFIG.
        Jika file ada tapi invalid JSON, use DEFAULT_CONFIG dengan warning.
        
        Returns:
            bool: True jika load berhasil
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # Merge dengan default config untuk ensure all keys exist
                    self.config = self._merge_config(self.DEFAULT_CONFIG, loaded_config)
                    logger.info(f"Config loaded from {self.config_file}")
            else:
                # File tidak ada, create dengan default
                self.config = self.DEFAULT_CONFIG.copy()
                self.save()
                logger.info(f"Created default config at {self.config_file}")
            
            return True
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in config file: {e}. Using default config.")
            self.config = self.DEFAULT_CONFIG.copy()
            return False
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            self.config = self.DEFAULT_CONFIG.copy()
            return False
    
    def save(self) -> bool:
        """
        Simpan configuration ke file.
        
        Returns:
            bool: True jika save berhasil
        """
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logger.info(f"Config saved to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            return False
    
    def _merge_config(self, default: dict, override: dict) -> dict:
        """
        Merge default config dengan override config.
        Ensure semua keys dari default ada di final config.
        
        Args:
            default (dict): Default configuration
            override (dict): Override configuration
            
        Returns:
            dict: Merged configuration
        """
        result = default.copy()
        for key, value in override.items():
            if isinstance(value, dict) and key in default:
                result[key] = self._merge_config(default[key], value)
            else:
                result[key] = value
        return result
    
    # ========================================================================
    # CONFIG ACCESS
    # ========================================================================
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Ambil config value menggunakan dot notation.
        
        Args:
            key (str): Config key dengan dot notation
                      Contoh: "store.name", "business.currency"
            default: Default value jika key tidak ditemukan
            
        Returns:
            Any: Config value atau default
            
        Contoh:
            store_name = config.get("store.name")
            currency = config.get("business.currency", "IDR")
        """
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            logger.warning(f"Config key not found: {key}")
            return default
    
    def set(self, key: str, value: Any) -> bool:
        """
        Set config value menggunakan dot notation.
        
        Args:
            key (str): Config key dengan dot notation
            value: Nilai yang akan diset
            
        Returns:
            bool: True jika berhasil
            
        Contoh:
            config.set("store.name", "Toko Baru")
        """
        keys = key.split('.')
        config = self.config
        
        try:
            # Navigate to parent dict
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            
            # Set value
            config[keys[-1]] = value
            logger.info(f"Config updated: {key} = {value}")
            return True
        except Exception as e:
            logger.error(f"Error setting config: {e}")
            return False
    
    # ========================================================================
    # CONVENIENCE METHODS - Shortcut untuk common configs
    # ========================================================================
    
    def get_store_name(self) -> str:
        """Get nama toko."""
        return self.get("store.name", "TOKO POS")
    
    def get_store_address(self) -> str:
        """Get alamat toko."""
        return self.get("store.address", "Alamat Toko")
    
    def get_currency(self) -> str:
        """Get currency."""
        return self.get("business.currency", "IDR")
    
    def get_default_tax(self) -> float:
        """Get default tax percentage."""
        return float(self.get("business.tax_default", 0))
    
    def get_default_discount(self) -> float:
        """Get default discount percentage."""
        return float(self.get("business.discount_default", 0))
    
    def get_receipt_width(self) -> int:
        """Get receipt width untuk formatting."""
        return int(self.get("receipt.width", 50))
    
    def is_telegram_enabled(self) -> bool:
        """Check apakah Telegram bot enabled."""
        return bool(self.get("telegram.enabled", False))
    
    def is_auto_backup_enabled(self) -> bool:
        """Check apakah auto backup enabled."""
        return bool(self.get("backup.auto_backup", True))
    
    # ========================================================================
    # CONFIG INFO
    # ========================================================================
    
    def get_all(self) -> dict:
        """Get semua config sebagai dictionary."""
        return self.config.copy()
    
    def print_config(self):
        """Print semua config ke console (untuk debugging)."""
        logger.info("Current Configuration:")
        logger.info(json.dumps(self.config, indent=2))


# ============================================================================
# SINGLETON PATTERN - Global config instance
# ============================================================================

_config_instance = None

def get_config() -> ConfigManager:
    """
    Get singleton instance dari ConfigManager.
    
    Returns:
        ConfigManager: Global config instance
        
    Contoh:
        config = get_config()
        store_name = config.get_store_name()
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigManager()
    return _config_instance


# ============================================================================
# TESTING - Jalankan jika file dijalankan standalone
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("CONFIG MANAGER - Testing")
    print("=" * 70)
    
    # Get singleton instance
    config = get_config()
    
    # Test accessing config values
    print("\n✅ Testing config access:")
    print(f"Store Name: {config.get_store_name()}")
    print(f"Store Address: {config.get_store_address()}")
    print(f"Currency: {config.get_currency()}")
    print(f"Default Tax: {config.get_default_tax()}%")
    print(f"Receipt Width: {config.get_receipt_width()}")
    
    # Print all config
    print("\n✅ All Configuration:")
    config.print_config()
