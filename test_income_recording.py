#!/usr/bin/env python
# Test income recording on transaction completion

from database import DatabaseManager
from transaction import TransactionHandler
from models import ProductManager

print("=" * 60)
print("TEST: Income Recording on Transaction Completion")
print("=" * 60)

try:
    # Initialize
    db = DatabaseManager()
    product_manager = ProductManager(db)
    transaction_handler = TransactionHandler(db)
    
    print(f"\n1. Transaction Handler initialized")
    print(f"   - accounting_service: {transaction_handler.accounting_service}")
    print(f"   - ACCOUNTING_AVAILABLE: {transaction_handler.accounting_service is not None}")
    
    # Start transaction
    transaction_handler.start_transaction()
    print(f"\n2. Transaction started")
    
    # Add item
    kode = "UBI001"  # Ubi Mentah
    qty = 2
    result = transaction_handler.add_item(kode, qty)
    print(f"\n3. Item added: {kode}, qty={qty}, success={result}")
    
    # Get current transaction
    trans = transaction_handler.transaction_service.get_current_transaction()
    if trans:
        print(f"\n4. Current transaction:")
        print(f"   - Total: Rp {trans.total:,}")
        print(f"   - Items: {len(trans.items)}")
    
    # Complete transaction
    bayar = trans.total if trans else 0
    print(f"\n5. Completing transaction (lunas):")
    print(f"   - Bayar: Rp {bayar:,}")
    print(f"   - is_termin: False")
    
    trans_id = transaction_handler.complete_transaction(bayar, is_termin=False)
    print(f"   - Result: trans_id={trans_id}")
    
    # Check cashflow table
    print(f"\n6. Checking cashflow table:")
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, type, amount, description FROM cashflow ORDER BY created_at DESC LIMIT 5")
        rows = cursor.fetchall()
        
        if rows:
            for row in rows:
                print(f"   - ID: {row[0]}, Type: {row[1]}, Amount: Rp {row[2]:,}, Desc: {row[3]}")
        else:
            print(f"   - No entries found!")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
