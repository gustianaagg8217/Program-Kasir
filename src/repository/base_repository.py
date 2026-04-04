# ============================================================================
# BASE_REPOSITORY.PY - Abstract Base Repository (Repository Layer)
# ============================================================================
# Fungsi: Define interface untuk semua repository
# Provide common CRUD operations dan error handling
# ============================================================================

from abc import ABC, abstractmethod
from typing import List, Optional, Any, Dict
from datetime import datetime
import sqlite3
from contextlib import contextmanager

from ..core import DatabaseError, DataIntegrityError


class BaseRepository(ABC):
    """
    Abstract base repository untuk semua data access operations.
    
    Fitur:
    - Context manager untuk safe DB operations
    - Common CRUD methods
    - Error handling & logging
    - Transaction management
    """
    
    def __init__(self, db_path: str = "kasir_pos.db"):
        """
        Initialize repository.
        
        Args:
            db_path (str): Path ke database file
        """
        self.db_path = db_path
    
    def _get_connection(self):
        """Get database connection."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            raise DatabaseError(
                f"Gagal connect ke database: {str(e)}",
                "connection"
            )
    
    @contextmanager
    def get_db(self):
        """
        Context manager untuk database connection.
        
        Usage:
            with self.get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(...)
        """
        conn = None
        try:
            conn = self._get_connection()
            yield conn
            conn.commit()
        except sqlite3.IntegrityError as e:
            if conn:
                conn.rollback()
            raise DataIntegrityError(f"Data integrity error: {str(e)}")
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            raise DatabaseError(f"Database error: {str(e)}")
        finally:
            if conn:
                conn.close()
    
    @abstractmethod
    def create(self, **kwargs) -> Any:
        """Create new entity."""
        pass
    
    @abstractmethod
    def read(self, entity_id: int) -> Optional[Any]:
        """Read entity by ID."""
        pass
    
    @abstractmethod
    def update(self, entity_id: int, **kwargs) -> bool:
        """Update entity by ID."""
        pass
    
    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """Delete entity by ID."""
        pass
    
    @abstractmethod
    def list_all(self) -> List[Any]:
        """List all entities."""
        pass


class CacheableRepository(BaseRepository):
    """
    Repository dengan caching support untuk optimize queries.
    
    Attributes:
        cache (Dict): In-memory cache
        cache_ttl (int): Cache TTL in seconds
    """
    
    def __init__(self, db_path: str = "kasir_pos.db", cache_ttl: int = 300):
        """
        Initialize repository with caching.
        
        Args:
            db_path (str): Path ke database
            cache_ttl (int): Cache time-to-live in seconds (default: 5 mins)
        """
        super().__init__(db_path)
        self.cache: Dict[str, tuple] = {}  # {key: (value, timestamp)}
        self.cache_ttl = cache_ttl
    
    def _get_cache(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key in self.cache:
            value, timestamp = self.cache[key]
            if (datetime.now() - timestamp).seconds < self.cache_ttl:
                return value
            else:
                del self.cache[key]
        return None
    
    def _set_cache(self, key: str, value: Any) -> None:
        """Set value in cache."""
        self.cache[key] = (value, datetime.now())
    
    def _invalidate_cache(self, pattern: str = None) -> None:
        """
        Invalidate cache.
        
        Args:
            pattern (str): Only invalidate keys matching pattern (partial match)
        """
        if pattern is None:
            self.cache.clear()
        else:
            keys_to_delete = [k for k in self.cache.keys() if pattern in k]
            for key in keys_to_delete:
                del self.cache[key]
