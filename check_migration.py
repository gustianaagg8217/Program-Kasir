#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Migration script untuk fix tanggal transaksi yang masih UTC."""

from database import DatabaseManager
from datetime import datetime, timedelta

db = DatabaseManager()

# Get all transactions
with db.get_connection() as conn:
    cursor = conn.cursor()
    
    # Check transactions dengan tanggal
    cursor.execute('SELECT COUNT(*) as count FROM transactions')
    total = cursor.fetchone()['count']
    print(f'Total transaksi: {total}')
    
    # Check transaksi dengan tanggal UTC (2026-04-27 lebih pagi)
    cursor.execute("""
        SELECT id, tanggal FROM transactions 
        WHERE tanggal IS NOT NULL
        ORDER BY id
    """)
    transactions = cursor.fetchall()
    print(f'\nTransaksi dengan tanggal:')
    for t in transactions:
        print(f'  ID: {t["id"]}, Tanggal: {t["tanggal"]}')
    
    # Get latest transaction to check format
    cursor.execute("SELECT id, tanggal FROM transactions ORDER BY id DESC LIMIT 1")
    latest = cursor.fetchone()
    if latest and latest['tanggal']:
        print(f'\nTransaksi terbaru: {latest["tanggal"]}')
        try:
            parsed = datetime.fromisoformat(latest['tanggal'].replace('Z', '+00:00'))
            print(f'  Parsed as: {parsed}')
            print(f'  Timezone aware: {parsed.tzinfo}')
        except:
            pass

print('\n✅ Silakan buat transaksi baru untuk test fix!')
