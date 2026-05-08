#!/usr/bin/env python
# Check cashflow data in detail

from database import DatabaseManager
from datetime import datetime

db = DatabaseManager()

with db.get_connection() as conn:
    cursor = conn.cursor()
    
    print("=" * 80)
    print("CASHFLOW TABLE - DETAILED VIEW")
    print("=" * 80)
    
    cursor.execute("""
        SELECT id, type, amount, description, related_transaction_id, created_at 
        FROM cashflow 
        ORDER BY created_at DESC
    """)
    rows = cursor.fetchall()
    
    for row in rows:
        cf_id, cf_type, amount, description, trans_id, created_at = row
        desc_lower = description.lower()
        is_penjualan = 'penjualan' in desc_lower
        is_termin = 'pembayaran termin' in desc_lower
        
        print(f"\nID: {cf_id}")
        print(f"  Type: {cf_type}")
        print(f"  Amount: Rp {amount:,}")
        print(f"  Description: {description}")
        print(f"  Description (lower): {desc_lower}")
        print(f"  Is Penjualan: {is_penjualan}")
        print(f"  Is Termin: {is_termin}")
        print(f"  Trans ID: {trans_id}")
        print(f"  Created: {created_at}")
    
    print("\n" + "=" * 80)
    print("TODAY'S DATE RANGE")
    print("=" * 80)
    today = datetime.now().date()
    print(f"Today: {today}")
    print(f"Today start: {today} 00:00:00")
    print(f"Today end: {today} 23:59:59")
    
    cursor.execute("""
        SELECT type, COUNT(*), SUM(amount) 
        FROM cashflow 
        WHERE DATE(created_at) = DATE(?)
        GROUP BY type
    """, (str(today),))
    today_data = cursor.fetchall()
    
    print(f"\nToday's cashflow:")
    for row in today_data:
        cf_type, count, total = row
        print(f"  {cf_type}: {count} entries, Total: Rp {total:,}")
