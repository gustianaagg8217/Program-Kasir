#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ============================================================================
# TEST_TERMIN_DASHBOARD.PY - Test script untuk fitur Termin Payment Warning
# ============================================================================

import sys
from datetime import datetime, date, timedelta
from database import DatabaseManager
from models import format_rp

def test_termin_dashboard():
    """Test termin payment dashboard features."""
    print("=" * 80)
    print("🧪 Testing Termin Payment Dashboard Features")
    print("=" * 80)
    
    try:
        # Initialize database
        db = DatabaseManager('kasir_pos.db')
        print("✅ Database connected successfully")
        
        # Test 1: Get overdue termin payments
        print("\n📋 Test 1: Getting overdue termin payments...")
        overdue = db.get_overdue_termin_payments()
        print(f"   Found {len(overdue)} overdue payments")
        for payment in overdue[:3]:
            print(f"   - {payment.get('invoice_number')} | {payment.get('customer_name')} | "
                  f"{format_rp(payment.get('payment_amount', 0))} | Due: {payment.get('due_date')}")
        
        # Test 2: Get upcoming termin payments
        print("\n📋 Test 2: Getting upcoming termin payments (next 7 days)...")
        upcoming = db.get_upcoming_termin_payments(days_ahead=7)
        print(f"   Found {len(upcoming)} upcoming payments")
        for payment in upcoming[:3]:
            print(f"   - {payment.get('invoice_number')} | {payment.get('customer_name')} | "
                  f"{format_rp(payment.get('payment_amount', 0))} | Due: {payment.get('due_date')}")
        
        # Test 3: Get upcoming termin payments (30 days)
        print("\n📋 Test 3: Getting upcoming termin payments (next 30 days)...")
        upcoming_30 = db.get_upcoming_termin_payments(days_ahead=30)
        print(f"   Found {len(upcoming_30)} upcoming payments (30 days)")
        
        # Test 4: Calculate statistics
        print("\n📊 Test 4: Dashboard Statistics")
        total_overdue = sum(p.get('payment_amount', 0) for p in overdue)
        total_upcoming = sum(p.get('payment_amount', 0) for p in upcoming)
        
        print(f"   Overdue Payments:     {len(overdue)} cicilan | {format_rp(total_overdue)}")
        print(f"   Upcoming Payments:    {len(upcoming)} cicilan | {format_rp(total_upcoming)}")
        print(f"   Total Termin Piutang: {len(overdue) + len(upcoming)} cicilan | "
              f"{format_rp(total_overdue + total_upcoming)}")
        
        # Test 5: Verify day calculations
        print("\n⏱️  Test 5: Day calculations")
        if overdue:
            payment = overdue[0]
            due_date = datetime.strptime(payment.get('due_date'), '%Y-%m-%d').date()
            days_overdue = (date.today() - due_date).days
            print(f"   Sample overdue payment: {payment.get('invoice_number')}")
            print(f"   Due date: {payment.get('due_date')}")
            print(f"   Days overdue: {days_overdue} hari")
        
        if upcoming:
            payment = upcoming[0]
            due_date = datetime.strptime(payment.get('due_date'), '%Y-%m-%d').date()
            days_until = (due_date - date.today()).days
            print(f"   Sample upcoming payment: {payment.get('invoice_number')}")
            print(f"   Due date: {payment.get('due_date')}")
            print(f"   Days until due: {days_until} hari")
        
        print("\n" + "=" * 80)
        print("✅ All tests completed successfully!")
        print("=" * 80)
        
        # Summary
        print("\n📝 SUMMARY:")
        print(f"   • Overdue payments warning will show if {len(overdue)} > 0")
        print(f"   • Upcoming payments warning will show if {len(upcoming)} > 0")
        print(f"   • Dashboard will display both warnings if applicable")
        
        if len(overdue) > 0:
            print(f"\n⚠️  WARNING: {len(overdue)} overdue termin payments detected!")
            print(f"   Total amount: {format_rp(total_overdue)}")
        
        if len(upcoming) > 0:
            print(f"\n🔔 INFO: {len(upcoming)} termin payments due within 7 days")
            print(f"   Total amount: {format_rp(total_upcoming)}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_termin_dashboard()
    sys.exit(0 if success else 1)
