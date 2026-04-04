# ============================================================================
# SERVICE_FACTORY.PY - Central access point for all services
# ============================================================================
# Fungsi: Provide singleton instances of services untuk dependency injection
# Coord inate service dependencies
# ============================================================================

from ..repository import RepositoryFactory
from .base_service import ProductService
from .stock_service import StockService
from .transaction_service import TransactionService
from .auth_service import AuthenticationService


class ServiceFactory:
    \"\"\"
    Factory untuk create dan manage service instances.
    
    Features:
    - Singleton pattern untuk services
    - Manage dependencies between services
    - Dependency injection friendly
    
    Usage:
        factory = ServiceFactory()
        product_service = factory.product_service()
        transaction_service = factory.transaction_service()
    \"\"\"
    
    def __init__(self, db_path: str = \"kasir_pos.db\"):
        \"\"\"
        Initialize service factory.
        
        Args:
            db_path (str): Database file path
        \"\"\"
        self.db_path = db_path
        self.repository_factory = RepositoryFactory(db_path)
        
        # Singleton instances
        self._product_service: ProductService = None
        self._stock_service: StockService = None
        self._transaction_service: TransactionService = None
        self._auth_service: AuthenticationService = None
    
    def product_service(self) -> ProductService:
        \"\"\"Get product service (singleton).\"\"\"
        if self._product_service is None:
            self._product_service = ProductService(self.repository_factory)
        return self._product_service
    
    def stock_service(self) -> StockService:
        \"\"\"Get stock service (singleton).\"\"\"
        if self._stock_service is None:
            self._stock_service = StockService(self.repository_factory)
        return self._stock_service
    
    def transaction_service(self) -> TransactionService:
        \"\"\"Get transaction service (singleton).\"\"\"
        if self._transaction_service is None:
            self._transaction_service = TransactionService(self.repository_factory)
        return self._transaction_service
    
    def auth_service(self) -> AuthenticationService:
        \"\"\"Get authentication service (singleton).\"\"\"
        if self._auth_service is None:
            self._auth_service = AuthenticationService(self.repository_factory)
        return self._auth_service
    
    def get_all_services(self) -> dict:
        \"\"\"Get all service instances.\"\"\"
        return {
            'product': self.product_service(),
            'stock': self.stock_service(),
            'transaction': self.transaction_service(),
            'auth': self.auth_service()
        }
