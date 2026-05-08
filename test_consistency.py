#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Test script untuk verify konsistensi data termin

import sys
from database import DatabaseManager
from models import format_rp

def test_consistency():
    """Test consistency antara kedua view."""
    print("=" * 80)
    print("🧪 Testing Termin Payment Data Consistency")
    print("=" * 80)
    
    try:
        db = DatabaseManager('kasir_pos.db')
        
        # Test 1: Get all pending termin payments (method baru)
        print("\n📋 Test 1: Method baru - get_all_pending_termin_payments()")
        all_pending = db.get_all_pending_termin_payments()
        print(f"   Total: {len(all_pending)} pembayaran")
        
        customers = set()
        for payment in all_pending:
            customer = payment.get('customer_name', 'N/A')
            invoice = payment.get('invoice_number', 'N/A')
            amount = payment.get('payment_amount', 0)
            due_date = payment.get('due_date', 'N/A')
            customers.add(customer)
            print(f"   • {invoice} | {customer} | {format_rp(amount)} | {due_date}")
        
        print(f"   Total Customer Unik: {len(customers)}")
        print(f"   Customers: {', '.join(sorted(customers))}")
        
        # Test 2: Get overdue + upcoming (method lama)
        print("\n📋 Test 2: Method lama - get_overdue + get_upcoming_termin_payments()")
        overdue = db.get_overdue_termin_payments()
        upcoming = db.get_upcoming_termin_payments(days_ahead=365)
        combined = overdue + upcoming
        print(f"   Overdue: {len(overdue)}")
        print(f"   Upcoming: {len(upcoming)}")
        print(f"   Total: {len(combined)} pembayaran")
        
        customers_old = set()
        for payment in combined:
            customer = payment.get('customer_name', 'N/A')
            customers_old.add(customer)
        
        print(f"   Customers: {', '.join(sorted(customers_old))}")
        
        # Compare
        print("\n📊 Comparison:")
        print(f"   Method baru:  {len(all_pending)} items - Customers: {len(customers)}")
        print(f"   Method lama:  {len(combined)} items - Customers: {len(customers_old)}")
        
        if customers == customers_old:
            print(f"   ✅ KONSISTEN: Kedua method menampilkan customer yang sama")
        else:
            print(f"   ⚠️  BERBEDA: Method lama kehilangan customer: {customers - customers_old}")
        
        # Test 3: Verifikasi bahwa Hadi ada di both
        if 'Hadi' in customers and 'Hadi' in customers_old:
            print(f"\n✅ Hadi ada di KEDUA method - Data KONSISTEN")
        elif 'Hadi' in customers and 'Hadi' not in customers_old:
            print(f"\n❌ Hadi HANYA ada di method baru - Perlu update method lama")
        elif 'Hadi' not in customers and 'Hadi' in customers_old:
            print(f"\n❌ Hadi HANYA ada di method lama - Perlu check method baru")
        else:
            print(f"\n❓ Hadi tidak ada di keduanya - Perlu check database")
        
        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == '__main__':
    success = test_consistency()
    sys.exit(0 if success else 1)
