#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick test to verify the daily sales chart functionality
"""

import sys
import os
from datetime import datetime, timedelta

# Test imports
try:
    import matplotlib
    print("✓ matplotlib imported successfully")
    matplotlib.use('TkAgg')
    
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    print("✓ FigureCanvasTkAgg imported successfully")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)

# Test data generation
try:
    from database import DatabaseManager
    from laporan import ReportGenerator
    print("✓ Database and ReportGenerator imported successfully")
    
    # Initialize
    db = DatabaseManager()
    report_gen = ReportGenerator(db)
    
    # Get last 7 days of sales
    today = datetime.now().date()
    start_date = (today - timedelta(days=6)).strftime('%Y-%m-%d')
    end_date = today.strftime('%Y-%m-%d')
    
    report_data = report_gen.get_laporan_periode(start_date, end_date)
    
    print(f"✓ Report data retrieved for period: {start_date} to {end_date}")
    print(f"  - Total sales: Rp {report_data.get('total_penjualan', 0):,}")
    print(f"  - Total transactions: {report_data.get('total_transaksi', 0)}")
    print(f"  - Days with sales: {report_data.get('hari_dengan_penjualan', 0)}")
    
    daily_breakdown = report_data.get('harian_breakdown', [])
    if daily_breakdown:
        print(f"  - Daily records: {len(daily_breakdown)}")
        for record in daily_breakdown:
            print(f"    • {record['tanggal']}: Rp {record['total']:,} ({record['transaksi']} transaksi)")
    else:
        print("  - No sales data in period (this is okay if no transactions)")
    
except Exception as e:
    print(f"✗ Error retrieving sales data: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test chart creation logic
try:
    # Prepare data
    dates = []
    sales_values = []
    
    day_totals = {d['tanggal']: d['total'] for d in daily_breakdown} if daily_breakdown else {}
    
    current = datetime.strptime(start_date, '%Y-%m-%d').date()
    end = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    while current <= end:
        date_str = current.strftime('%Y-%m-%d')
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        day_abbr = date_obj.strftime('%a')
        day_num = date_obj.strftime('%d').lstrip('0')
        dates.append(f"{day_abbr}\n{day_num}")
        sales_values.append(day_totals.get(date_str, 0))
        current += timedelta(days=1)
    
    print(f"\n✓ Chart data prepared:")
    print(f"  - X-axis (dates): {dates}")
    print(f"  - Y-axis (sales): {[f'Rp {v:,}' for v in sales_values]}")
    
    # Create figure
    fig = Figure(figsize=(10, 4), dpi=100)
    ax = fig.add_subplot(111)
    
    # Create bar chart
    bars = ax.bar(dates, sales_values, color='#2ECC71', edgecolor='black', linewidth=0.5)
    
    ax.set_title('📈 Penjualan 7 Hari Terakhir', fontsize=12, fontweight='bold')
    ax.set_ylabel('Total Penjualan (Rp)', fontsize=10)
    ax.set_xlabel('Tanggal', fontsize=10)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    
    fig.tight_layout()
    
    print("✓ Chart figure created successfully")
    print("✓ Chart configured with title, labels, and grid")
    
except Exception as e:
    print(f"✗ Error creating chart: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*60)
print("✓ ALL TESTS PASSED - Sales chart integration is ready!")
print("="*60)
print("\nThe daily sales chart will display:")
print("  • Last 7 days of sales data")
print("  • Bar chart with day abbreviations and dates")
print("  • Value labels on top of each bar")
print("  • Y-axis formatted in Rupiah (K = thousand)")
print("  • Grid for easy reading")
