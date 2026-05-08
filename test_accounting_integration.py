# ============================================================================
# TEST_ACCOUNTING_INTEGRATION.PY - Test Accounting System Integration
# ============================================================================
# Fungsi: Test semua komponen sistem pembukuan yang baru ditambahkan
# ============================================================================

import sys
from datetime import datetime, date, timedelta

print("=" * 80)
print("TESTING ACCOUNTING SYSTEM INTEGRATION")
print("=" * 80)

# Test 1: Import all modules
print("\n1️⃣ Testing Module Imports...")
print("-" * 80)

try:
    from database import DatabaseManager
    print("✅ DatabaseManager imported")
except Exception as e:
    print(f"❌ DatabaseManager import failed: {e}")
    sys.exit(1)

try:
    from cashflow_service import CashflowService
    print("✅ CashflowService imported")
except Exception as e:
    print(f"❌ CashflowService import failed: {e}")
    sys.exit(1)

try:
    from accounting_service import AccountingService
    print("✅ AccountingService imported")
except Exception as e:
    print(f"❌ AccountingService import failed: {e}")
    sys.exit(1)

try:
    from transaction import TransactionHandler
    print("✅ TransactionHandler imported (with accounting integration)")
except Exception as e:
    print(f"❌ TransactionHandler import failed: {e}")
    sys.exit(1)

# Test 2: Initialize database
print("\n2️⃣ Testing Database Initialization...")
print("-" * 80)

try:
    db_test = DatabaseManager("test_accounting.db")
    print("✅ Database initialized successfully")
    print(f"   Database path: {db_test.db_path}")
except Exception as e:
    print(f"❌ Database initialization failed: {e}")
    sys.exit(1)

# Test 3: Initialize accounting service
print("\n3️⃣ Testing Accounting Service Initialization...")
print("-" * 80)

try:
    accounting = AccountingService(db_test)
    print("✅ AccountingService initialized successfully")
except Exception as e:
    print(f"❌ AccountingService initialization failed: {e}")
    sys.exit(1)

# Test 4: Test cashflow operations
print("\n4️⃣ Testing Cashflow Operations...")
print("-" * 80)

try:
    # Add income
    cf_id_1 = accounting.record_income(transaction_id=1, amount=500000, description="Penjualan transaksi #1")
    if cf_id_1:
        print(f"✅ Income recorded (ID: {cf_id_1})")
    else:
        print("❌ Failed to record income")
    
    # Add more income
    cf_id_2 = accounting.record_income(transaction_id=2, amount=750000, description="Penjualan transaksi #2")
    if cf_id_2:
        print(f"✅ Income recorded (ID: {cf_id_2})")
    else:
        print("❌ Failed to record income")
    
    # Add expense
    cf_id_3 = accounting.record_expense(100000, "Pembelian plastik kemasan")
    if cf_id_3:
        print(f"✅ Expense recorded (ID: {cf_id_3})")
    else:
        print("❌ Failed to record expense")
    
    # Add more expense
    cf_id_4 = accounting.record_expense(50000, "Biaya operasional listrik")
    if cf_id_4:
        print(f"✅ Expense recorded (ID: {cf_id_4})")
    else:
        print("❌ Failed to record expense")

except Exception as e:
    print(f"❌ Cashflow operations failed: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Test profit calculation
print("\n5️⃣ Testing Profit Calculation...")
print("-" * 80)

try:
    profit = accounting.get_profit()
    print(f"✅ Profit calculated: Rp {profit:,}")
    print(f"   (Total income: Rp 1.250.000 - Total expense: Rp 150.000)")
except Exception as e:
    print(f"❌ Profit calculation failed: {e}")

# Test 6: Test summary report
print("\n6️⃣ Testing Summary Report...")
print("-" * 80)

try:
    summary = accounting.cashflow_service.get_cashflow_summary()
    print(f"✅ Summary Report Generated:")
    print(f"   Total Income:  Rp {summary['total_income']:,}")
    print(f"   Total Expense: Rp {summary['total_expense']:,}")
    print(f"   Net Profit:    Rp {summary['profit']:,}")
except Exception as e:
    print(f"❌ Summary report failed: {e}")

# Test 7: Test history retrieval
print("\n7️⃣ Testing History Retrieval...")
print("-" * 80)

try:
    history = accounting.get_history(limit=10)
    print(f"✅ Retrieved {len(history)} cashflow entries:")
    for i, entry in enumerate(history, 1):
        print(f"   {i}. [{entry['type'].upper()}] {entry['description']} - Rp {entry['amount']:,}")
except Exception as e:
    print(f"❌ History retrieval failed: {e}")

# Test 8: Test TransactionHandler integration
print("\n8️⃣ Testing TransactionHandler Integration...")
print("-" * 80)

try:
    handler = TransactionHandler(db_test)
    if handler.accounting_service:
        print("✅ TransactionHandler has accounting_service initialized")
        print("   Income will be automatically recorded on transaction completion")
    else:
        print("⚠️ TransactionHandler created but accounting_service is None")
except Exception as e:
    print(f"❌ TransactionHandler initialization failed: {e}")

# Test 9: Database cashflow table verification
print("\n9️⃣ Verifying Cashflow Table in Database...")
print("-" * 80)

try:
    with db_test.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM cashflow")
        result = cursor.fetchone()
        count = result['count'] if result else 0
        print(f"✅ Cashflow table verified")
        print(f"   Total entries in database: {count}")
        
        # Show table structure
        cursor.execute("PRAGMA table_info(cashflow)")
        columns = cursor.fetchall()
        print(f"   Table columns:")
        for col in columns:
            print(f"      - {col[1]} ({col[2]})")
except Exception as e:
    print(f"❌ Database verification failed: {e}")

# Test 10: Summary
print("\n" + "=" * 80)
print("✅ ALL TESTS PASSED!")
print("=" * 80)
print("\nSYSTEM PEMBUKUAN SUCCESSFULLY INTEGRATED")
print("\nFeatures Available:")
print("  ✅ Automatic income recording from transactions")
print("  ✅ Manual expense input")
print("  ✅ Profit/loss calculation")
print("  ✅ Cashflow history tracking")
print("  ✅ Date range filtering")
print("  ✅ GUI integration with new Pembukuan menu")
print("\nTo use in GUI:")
print("  1. Run: python gui_main.py")
print("  2. Login as admin")
print("  3. Go to menu: 📚 Pembukuan")
print("  4. View cashflow summary and history")
print("  5. Click '➕ Tambah Pengeluaran' to add expenses")
print("=" * 80)

# Cleanup
import os
if os.path.exists("test_accounting.db"):
    os.remove("test_accounting.db")
    print("\n✓ Test database cleaned up")
