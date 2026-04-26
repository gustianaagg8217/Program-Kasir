# ============================================================================
# CONFIG_LOADER.PY - Global Configuration Management
# ============================================================================
# Fungsi: Load & manage config.json globally dengan feature flags
# Fitur: Type-safe access, env override, default values
# ============================================================================

import json
import os
from typing import Any, Optional, Dict
from pathlib import Path
from logger_config import get_logger

logger = get_logger(__name__)

# ============================================================================
# CONFIG LOADER
# ============================================================================

class ConfigLoader:
    """Load & manage configuration dari config.json."""
    
    _instance = None
    _config: Dict[str, Any] = {}
    
    def __new__(cls):
        """Singleton pattern - hanya satu instance di memory."""
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize config dengan load dari file."""
        try:
            # Find config.json dari current directory atau parent
            config_path = self._find_config()
            
            if not config_path:
                logger.warning("config.json tidak ditemukan, gunakan default")
                self._config = self._get_default_config()
                return
            
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
            
            logger.info(f"Config loaded from: {config_path}")
            
        except Exception as e:
            logger.error(f"Error loading config: {e}, gunakan default")
            self._config = self._get_default_config()
    
    def _find_config(self) -> Optional[Path]:
        """Cari config.json di current dir atau parent."""
        paths = [
            Path("config.json"),
            Path(__file__).parent.parent.parent / "config.json",  # Root project
            Path.cwd() / "config.json"
        ]
        
        for path in paths:
            if path.exists():
                return path
        return None
    
    @staticmethod
    def _get_default_config() -> Dict[str, Any]:
        """Return default config jika file tidak ada."""
        return {
            "store": {
                "name": "POS SYSTEM",
                "address": "Address",
                "phone": "Phone",
                "email": "email@example.com"
            },
            "business": {
                "currency": "IDR",
                "tax_default": 0,
                "discount_default": 0,
                "timezone": "Asia/Jakarta"
            },
            "features": {
                "telegram": False,
                "ai": False,
                "stok_opname": True,
                "backup": True
            },
            "app": {
                "debug": False,
                "async_operations": True,
                "cache_enabled": True
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get config value dengan dot notation.
        
        Contoh:
            config.get("store.name")
            config.get("features.telegram", False)
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            
            if value is None:
                return default
        
        return value
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check apakah feature diaktifkan."""
        return self.get(f"features.{feature}", False)
    
    def get_store_info(self) -> Dict[str, str]:
        """Get semua store information."""
        return self.get("store", {})
    
    def reload(self):
        """Reload config dari file (untuk development)."""
        self._initialize()
        logger.info("Config reloaded")
    
    def dump(self) -> str:
        """Return config sebagai formatted JSON string."""
        return json.dumps(self._config, indent=2, ensure_ascii=False)


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

# Initialize global config instance
config = ConfigLoader()


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_config(key: str, default: Any = None) -> Any:
    """Convenience function untuk get config value."""
    return config.get(key, default)


def is_feature_enabled(feature: str) -> bool:
    """Convenience function untuk check feature status."""
    return config.is_feature_enabled(feature)


def get_store_name() -> str:
    """Get store name."""
    return config.get("store.name", "POS SYSTEM")


def get_currency() -> str:
    """Get currency code."""
    return config.get("business.currency", "IDR")


def is_debug_mode() -> bool:
    """Check apakah app dalam debug mode."""
    return config.get("app.debug", False)
