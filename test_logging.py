#!/usr/bin/env python3
# ============================================================================
# TEST_LOGGING.PY - Test logging functionality
# ============================================================================

from database import DatabaseManager
from logger_config import get_logger

logger = get_logger(__name__)

def main():
    """Test logging in various operations."""
    logger.info("=== TESTING LOGGING FUNCTIONALITY ===")
    
    # Initialize database
    db = DatabaseManager()
    logger.info("Database initialized successfully")
    
    # Check existing users
    user_exists = db.user_exists()
    logger.info(f"Users exist in database: {user_exists}")
    
    # Test product operations
    logger.info("Testing product operations...")
    
    # Add a test product
    result = db.add_product("TEST001", "Test Product", 50000, 100)
    logger.info(f"Product addition result: {result}")
    
    # Get product
    product = db.get_product_by_kode("TEST001")
    if product:
        logger.info(f"Retrieved product: {product['nama']} - Rp{product['harga']:,}")
    
    # Update product
    result = db.update_product("TEST001", stok=150)
    logger.info(f"Product stock updated: {result}")
    
    # Test transaction creation
    logger.info("Testing transaction creation...")
    trans_id = db.add_transaction(total=50000, bayar=100000, kembalian=50000)
    if trans_id:
        logger.info(f"Transaction created with ID: {trans_id}")
        
        # Add transaction item
        item_result = db.add_transaction_item(trans_id, 1, 1, 50000, 50000)
        logger.info(f"Transaction item added: {item_result}")
    
    # Reduce stock
    stock_result = db.reduce_stock(1, 5)
    logger.info(f"Stock reduced: {stock_result}")
    
    # Log end of testing
    logger.info("=== LOGGING TESTS COMPLETED ===")
    print("\n✅ Logging tests completed!")
    print(f"📝 Log file: D:\\Program_Kasir\\pos.log")
    print("\nOpen pos.log to see all logged events")

if __name__ == "__main__":
    main()
