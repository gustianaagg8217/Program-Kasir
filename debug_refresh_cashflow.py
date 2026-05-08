#!/usr/bin/env python
# Debug refresh_cashflow logic

from database import DatabaseManager
from accounting_service import AccountingService
from datetime import datetime

db = DatabaseManager()
accounting = AccountingService(db)

# Test date parsing like refresh_cashflow does
start_str = "4/28/26"  # DateEntry format
end_str = "4/28/26"

start_date = None
end_date = None
for fmt in ['%m/%d/%y', '%m/%d/%Y', '%Y-%m-%d', '%d-%m-%Y']:
    try:
        start_date = datetime.strptime(start_str, fmt).date()
        break
    except ValueError:
        continue

for fmt in ['%m/%d/%y', '%m/%d/%Y', '%Y-%m-%d', '%d-%m-%Y']:
    try:
        end_date = datetime.strptime(end_str, fmt).date()
        break
    except ValueError:
        continue

print("=" * 80)
print("DEBUG: refresh_cashflow logic")
print("=" * 80)
print(f"\nDate parsing:")
print(f"  Input: {start_str} - {end_str}")
print(f"  Parsed start: {start_date}")
print(f"  Parsed end: {end_date}")

# Get history like refresh_cashflow does
history = accounting.get_history(limit=1000, start_date=start_date, end_date=end_date)

print(f"\nHistory retrieved: {len(history)} entries")
for entry in history:
    print(f"  - {entry}")

# Calculate breakdown
sales_income = 0
other_income = 0
total_expense = 0

for entry in history:
    entry_type = entry.get('type', '')
    amount = entry.get('amount', 0)
    description = entry.get('description', '').lower()
    
    print(f"\nAnalyzing: {entry_type}, {amount}, {description}")
    
    if entry_type == 'income':
        if 'penjualan' in description or 'pembayaran termin' in description:
            sales_income += amount
            print(f"  -> Sales income: +{amount}")
        else:
            other_income += amount
            print(f"  -> Other income: +{amount}")
    elif entry_type == 'expense':
        total_expense += amount
        print(f"  -> Expense: +{amount}")

print(f"\nSummary:")
print(f"  Sales income: Rp {sales_income:,}")
print(f"  Other income: Rp {other_income:,}")
print(f"  Total income: Rp {sales_income + other_income:,}")
print(f"  Total expense: Rp {total_expense:,}")
print(f"  Profit: Rp {(sales_income + other_income - total_expense):,}")
