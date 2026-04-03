"""
Quick test to identify any import or initialization errors
"""

import sys
import traceback

print("Testing Program Kasir imports...")
print("=" * 80)

try:
    print("[1/5] Importing database module...")
    from database import DatabaseManager
    print("      [OK] database.py imported successfully")
except Exception as e:
    print(f"      [ERROR] database.py: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("[2/5] Importing models module...")
    from models import ProductManager, ValidationError, format_rp
    print("      [OK] models.py imported successfully")
except Exception as e:
    print(f"      [ERROR] models.py: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("[3/5] Importing transaction module...")
    from transaction import TransactionService, TransactionHandler, ReceiptManager
    print("      [OK] transaction.py imported successfully")
except Exception as e:
    print(f"      [ERROR] transaction.py: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("[4/5] Importing laporan (reports) module...")
    from laporan import ReportGenerator, ReportFormatter, CSVExporter
    print("      [OK] laporan.py imported successfully")
except Exception as e:
    print(f"      [ERROR] laporan.py: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("[5/5] Importing gui_main module...")
    import gui_main
    print("      [OK] gui_main.py imported successfully")
except Exception as e:
    print(f"      [ERROR] gui_main.py: {e}")
    traceback.print_exc()
    sys.exit(1)

print("=" * 80)
print("[SUCCESS] All imports successful - no blocking errors detected")
print("\nProgram should be able to start now.")
print("If still having issues, check:")
print("  1. Database file (trades.db) exists")
print("  2. All config files are in place")
print("  3. Run 'python gui_main.py' to start the application")
