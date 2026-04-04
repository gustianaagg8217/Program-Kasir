# ============================================================================
# REPOSITORY_FACTORY.PY - Central access point for all repositories
# ============================================================================
# Fungsi: Provide single instance of each repository untuk dependency injection
# ============================================================================

from .base_repository import BaseRepository
from .product_repository import ProductRepository, InventoryRepository
from .transaction_repository import TransactionRepository
from .user_repository import UserRepository


class RepositoryFactory:
    """
    Factory untuk create dan manage repository instances.
    
    Providing:
    - Singleton pattern untuk repositories
    - Dependency injection friendly
    - Easy to swap implementations for testing
    
    Usage:
        factory = RepositoryFactory()
        product_repo = factory.product_repository()
        transaction_repo = factory.transaction_repository()
    """
    
    def __init__(self, db_path: str = "kasir_pos.db"):
        """
        Initialize repository factory.
        
        Args:
            db_path (str): Database file path
        """
        self.db_path = db_path
        
        # Singleton instances
        self._product_repo: ProductRepository = None
        self._inventory_repo: InventoryRepository = None
        self._transaction_repo: TransactionRepository = None
        self._user_repo: UserRepository = None
    
    def product_repository(self) -> ProductRepository:
        """Get product repository (singleton)."""
        if self._product_repo is None:
            self._product_repo = ProductRepository(self.db_path)
        return self._product_repo
    
    def inventory_repository(self) -> InventoryRepository:
        """Get inventory repository (singleton)."""
        if self._inventory_repo is None:
            self._inventory_repo = InventoryRepository(self.db_path)
        return self._inventory_repo
    
    def transaction_repository(self) -> TransactionRepository:
        """Get transaction repository (singleton)."""
        if self._transaction_repo is None:
            self._transaction_repo = TransactionRepository(self.db_path)
        return self._transaction_repo
    
    def user_repository(self) -> UserRepository:
        """Get user repository (singleton)."""
        if self._user_repo is None:
            self._user_repo = UserRepository(self.db_path)
        return self._user_repo
    
    def get_all_repositories(self) -> dict:
        """Get all repository instances."""
        return {
            'product': self.product_repository(),
            'inventory': self.inventory_repository(),
            'transaction': self.transaction_repository(),
            'user': self.user_repository()
        }
