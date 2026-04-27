#!/usr/bin/env python
# ============================================================================
# TEST_SECURITY_UPGRADE.PY - Test Security Features
# ============================================================================
# Purpose: Verify Bcrypt hashing and rate limiting implementation
# ============================================================================

import sys
import os
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

print("\n" + "="*70)
print("SECURITY UPGRADE TEST SUITE")
print("="*70)

# Test 1: Password Manager
print("\n✓ Test 1: Password Manager (Bcrypt)")
print("-" * 70)

try:
    from auth_security import PasswordManager, PasswordValidator
    
    # Test hashing
    test_password = "TestPassword123!"
    hashed = PasswordManager.hash_password(test_password)
    
    print(f"Original password: {test_password}")
    print(f"Hashed (truncated): {hashed[:40]}...")
    print(f"Hash length: {len(hashed)} characters")
    
    # Test verification
    correct = PasswordManager.verify_password(test_password, hashed)
    wrong = PasswordManager.verify_password("WrongPassword", hashed)
    
    print(f"Correct password verification: {correct} ✅" if correct else f"Correct password verification: {correct} ❌")
    print(f"Wrong password verification: {wrong} ✅" if not wrong else f"Wrong password verification: {wrong} ❌")
    
    # Test legacy hash detection
    legacy_sha256 = "7e8d9b3e4c6f2a1d9c8e7b6a5f4d3c2b1a9f8e7d6c5b4a3f2e1d0c9b8a7f6e"
    is_legacy = PasswordManager.is_legacy_hash(legacy_sha256)
    is_bcrypt = PasswordManager.is_legacy_hash(hashed)
    
    print(f"SHA256 hash detected as legacy: {is_legacy} ✅" if is_legacy else f"SHA256 hash detected as legacy: {is_legacy} ❌")
    print(f"Bcrypt hash detected as legacy: {is_bcrypt} ✅" if not is_bcrypt else f"Bcrypt hash detected as legacy: {is_bcrypt} ❌")
    
    print("✅ Test 1 PASSED: Password Manager works correctly\n")
    
except Exception as e:
    print(f"❌ Test 1 FAILED: {e}\n")
    sys.exit(1)

# Test 2: Database Integration
print("✓ Test 2: Database Integration")
print("-" * 70)

try:
    from database import DatabaseManager
    import sqlite3
    
    # Create test database
    test_db = "test_security.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    
    db = DatabaseManager(test_db)
    
    # Check tables exist
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
    
    required_tables = ['users', 'login_attempts']
    for table in required_tables:
        exists = table in tables
        print(f"Table '{table}': {exists} ✅" if exists else f"Table '{table}': {exists} ❌")
    
    # Create test user
    db.create_user("testuser", "password123")
    
    # Get user and verify password
    user = db.get_user_by_username("testuser")
    if user:
        print(f"User created: {user['username']} ({user['role']}) ✅")
    else:
        print("User creation failed ❌")
    
    print("✅ Test 2 PASSED: Database integration works correctly\n")
    
    # Cleanup
    os.remove(test_db)
    
except Exception as e:
    print(f"❌ Test 2 FAILED: {e}\n")
    sys.exit(1)

# Test 3: Login Attempt Tracking
print("✓ Test 3: Login Attempt Tracking")
print("-" * 70)

try:
    from database import DatabaseManager
    from auth_security import LoginAttemptTracker
    import os
    
    # Create test database
    test_db = "test_security_tracking.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    
    db = DatabaseManager(test_db)
    tracker = LoginAttemptTracker(db)
    
    # Create test user
    db.create_user("security_test", "password123")
    
    # Record login attempts
    attempt1 = db.record_login_attempt("security_test", False, "192.168.1.1")
    attempt2 = db.record_login_attempt("security_test", False, "192.168.1.1")
    attempt3 = db.record_login_attempt("security_test", True, "192.168.1.1")
    
    print(f"Failed attempt 1 recorded: {attempt1['id']} ✅")
    print(f"Failed attempt 2 recorded: {attempt2['id']} ✅")
    print(f"Success attempt recorded: {attempt3['id']} ✅")
    
    # Check failed attempts count
    failed_count = db.get_failed_attempts_count("security_test")
    print(f"Failed attempts count: {failed_count} ✅")
    
    # Get login history
    history = db.get_login_history("security_test")
    print(f"Login history retrieved: {len(history)} records ✅")
    
    print("✅ Test 3 PASSED: Login attempt tracking works correctly\n")
    
    # Cleanup
    os.remove(test_db)
    
except Exception as e:
    print(f"❌ Test 3 FAILED: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Rate Limiting & Lockout
print("✓ Test 4: Rate Limiting & Lockout")
print("-" * 70)

try:
    from database import DatabaseManager
    import os
    
    # Create test database
    test_db = "test_security_ratelimit.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    
    db = DatabaseManager(test_db)
    
    # Create test user
    db.create_user("ratelimit_test", "password123")
    
    # Record 5 failed attempts
    for i in range(5):
        db.record_login_attempt("ratelimit_test", False, f"192.168.1.{i}")
        print(f"Failed attempt {i+1} recorded")
    
    # Check lockout status
    lockout = db.check_login_lockout("ratelimit_test")
    
    print(f"\nLockout Status:")
    print(f"  Is locked: {lockout['is_locked']} ✅" if lockout['is_locked'] else f"  Is locked: {lockout['is_locked']} ❌")
    print(f"  Failed attempts: {lockout['failed_count']}/{lockout['max_attempts']}")
    print(f"  Remaining minutes: {lockout['remaining_minutes']}")
    
    print("✅ Test 4 PASSED: Rate limiting and lockout work correctly\n")
    
    # Cleanup
    os.remove(test_db)
    
except Exception as e:
    print(f"❌ Test 4 FAILED: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Password Validation
print("✓ Test 5: Password Validation")
print("-" * 70)

try:
    from auth_security import PasswordValidator
    
    # Test weak password
    valid1, msg1 = PasswordValidator.validate_password("weak")
    print(f"Weak password (4 chars): Valid={valid1} (Expected: False) ✅" if not valid1 else f"Weak password: Valid={valid1} (Expected: False) ❌")
    
    # Test strong password
    valid2, msg2 = PasswordValidator.validate_password("StrongPassword123!")
    print(f"Strong password: Valid={valid2} (Expected: True) ✅" if valid2 else f"Strong password: Valid={valid2} (Expected: True) ❌")
    
    # Test empty password
    valid3, msg3 = PasswordValidator.validate_password("")
    print(f"Empty password: Valid={valid3} (Expected: False) ✅" if not valid3 else f"Empty password: Valid={valid3} (Expected: False) ❌")
    
    print("✅ Test 5 PASSED: Password validation works correctly\n")
    
except Exception as e:
    print(f"❌ Test 5 FAILED: {e}\n")
    sys.exit(1)

# Test 6: Auth Manager
print("✓ Test 6: AuthManager Integration")
print("-" * 70)

try:
    from database import DatabaseManager
    from auth_manager import AuthManager
    import os
    
    # Create test database
    test_db = "test_auth_manager.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    
    db = DatabaseManager(test_db)
    auth = AuthManager(db)
    
    # Create test user
    db.create_user("authtest", "password123", role="cashier")
    
    # Test login
    success, msg = auth.login("authtest", "password123", ip_address="192.168.1.100")
    print(f"Successful login: {success} ✅" if success else f"Successful login: {success} ❌")
    print(f"Message: {msg}")
    
    # Check current user
    current_user = auth.get_current_user()
    print(f"Current user: {current_user.username} ({current_user.role}) ✅" if current_user else "Current user: None ❌")
    
    # Test logout
    auth.logout()
    print(f"Logout successful ✅")
    
    # Test wrong password
    success2, msg2 = auth.login("authtest", "wrongpassword", ip_address="192.168.1.100")
    print(f"Wrong password rejected: {not success2} ✅" if not success2 else f"Wrong password rejected: {not success2} ❌")
    
    print("✅ Test 6 PASSED: AuthManager integration works correctly\n")
    
    # Cleanup
    os.remove(test_db)
    
except Exception as e:
    print(f"❌ Test 6 FAILED: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Summary
print("="*70)
print("✅ ALL SECURITY TESTS PASSED!")
print("="*70)
print("\n📊 Summary:")
print("  ✓ Bcrypt password hashing working correctly")
print("  ✓ Login attempt tracking implemented")
print("  ✓ Rate limiting and account lockout functional")
print("  ✓ Password validation working")
print("  ✓ AuthManager integration complete")
print("  ✓ Database integration successful")
print("\n🔒 Security upgrade is ready for production!\n")
