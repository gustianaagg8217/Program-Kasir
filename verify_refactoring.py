#!/usr/bin/env python3
# ============================================================================
# VERIFY_REFACTORING.PY - Verify all refactoring components work
# ============================================================================

import sys
import os

print("=" * 70)
print("POS SYSTEM REFACTORING - VERIFICATION")
print("=" * 70)

# Test 1: Config Manager
print("\n✓ Testing Config Manager...")
try:
    from config_manager import get_config
    config = get_config()
    assert config.get_store_name() is not None, "Store name not found"
    assert config.get_currency() is not None, "Currency not found"
    print(f"  ✅ Config loaded successfully")
    print(f"     Store: {config.get_store_name()}")
    print(f"     Currency: {config.get_currency()}")
except Exception as e:
    print(f"  ❌ Config Manager error: {e}")
    sys.exit(1)

# Test 2: Auth Manager & Database
print("\n✓ Testing Auth Manager...")
try:
    from database import DatabaseManager
    from auth_manager import AuthManager
    
    db = DatabaseManager()
    auth = AuthManager(db)
    
    # Check user table
    assert hasattr(auth, 'current_user'), "Auth not initialized"
    print(f"  ✅ Auth Manager initialized")
    print(f"     Current user: {auth.get_username()}")
    print(f"     Is logged in: {auth.is_logged_in()}")
except Exception as e:
    print(f"  ❌ Auth Manager error: {e}")
    sys.exit(1)

# Test 3: Logger
print("\n✓ Testing Logger...")
try:
    from logger_config import setup_logging, get_logger
    setup_logging()
    logger = get_logger(__name__)
    logger.info("Test log message")
    assert os.path.exists("pos.log"), "Log file not created"
    print(f"  ✅ Logger initialized")
    print(f"     Log file: pos.log")
except Exception as e:
    print(f"  ❌ Logger error: {e}")
    sys.exit(1)

# Test 4: Main system imports
print("\n✓ Testing Main System Imports...")
try:
    from main import POSSystem
    print(f"  ✅ Main system imports OK")
except Exception as e:
    print(f"  ❌ Main system import error: {e}")
    sys.exit(1)

# Test 5: Database user functions
print("\n✓ Testing Database User Functions...")
try:
    db = DatabaseManager()
    
    # Test create user
    success = db.create_user("test_user", "password123", role="cashier")
    print(f"  ✅ User creation: OK")
    
    # Test verify login
    user = db.verify_user_login("test_user", "password123")
    assert user is not None, "User verification failed"
    print(f"  ✅ User verification: OK")
    
    # Clean up
    if success:
        db.delete_user(user['id'])
        print(f"  ✅ User cleanup: OK")
except Exception as e:
    print(f"  ❌ Database user functions error: {e}")
    sys.exit(1)

# Test 6: Permission system
print("\n✓ Testing Permission System...")
try:
    from auth_manager import User
    
    # Create mock users
    admin = User(1, "admin", "admin", True)
    cashier = User(2, "cashier", "cashier", True)
    
    assert admin.is_admin() == True, "Admin check failed"
    assert cashier.is_cashier() == True, "Cashier check failed"
    assert admin.has_permission("any.permission") == True, "Admin permission failed"
    assert cashier.has_permission("transaksi.create") == True, "Cashier permission failed"
    
    print(f"  ✅ Admin permissions: OK")
    print(f"  ✅ Cashier permissions: OK")
except Exception as e:
    print(f"  ❌ Permission system error: {e}")
    sys.exit(1)

print("\n" + "=" * 70)
print("✅ ALL TESTS PASSED - System ready to use!")
print("=" * 70)
print("\nNext steps:")
print("1. Run: python main.py")
print("2. Choose 'Demo Mode' for instant login")
print("3. Configure store details in config.json if needed")
print("\nFor detailed info, see: REFACTORING_SUMMARY.md")
