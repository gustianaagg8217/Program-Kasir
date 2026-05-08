#!/usr/bin/env python
# Check cashflow table

from database import DatabaseManager

db = DatabaseManager()

try:
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Check cashflow table
        cursor.execute("SELECT id, type, amount, description, created_at FROM cashflow ORDER BY created_at DESC LIMIT 10")
        rows = cursor.fetchall()
        
        print("=== CASHFLOW TABLE (Last 10 entries) ===")
        if rows:
            for row in rows:
                print(f"ID: {row[0]}, Type: {row[1]}, Amount: Rp {row[2]:,}, Desc: {row[3]}, Date: {row[4]}")
        else:
            print("No entries found in cashflow table!")
        
        print("\n=== INCOME SUMMARY ===")
        cursor.execute("SELECT type, COUNT(*), SUM(amount) FROM cashflow GROUP BY type")
        summary = cursor.fetchall()
        for row in summary:
            cf_type = row[0]
            count = row[1]
            total = row[2]
            print(f"{cf_type}: {count} entries, Total: Rp {total:,}")
            
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
