#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Debug script untuk melihat data transaksi di database."""

from database import DatabaseManager
from datetime import datetime

db = DatabaseManager()

# Check today's transactions
today = datetime.now().strftime('%Y-%m-%d')
print(f'Today date: {today}')

# Get all transactions dengan tanggal
with db.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute('SELECT id, tanggal, total FROM transactions ORDER BY id DESC LIMIT 5')
    rows = cursor.fetchall()
    print(f'\n5 Transaksi terakhir:')
    for row in rows:
        print(f'  ID: {row["id"]}, Tanggal: {row["tanggal"]}, Total: {row["total"]}')

    # Check today's transactions
    cursor.execute('SELECT COUNT(*) as count FROM transactions WHERE DATE(tanggal) = ?', (today,))
    count = cursor.fetchone()
    print(f'\nTransaksi hari ini ({today}): {count["count"]} transaksi')

# Check laporan harian
print(f'\nLaporan harian:')
laporan = db.get_laporan_harian(today)
print(f'  Total penjualan: {laporan["total_penjualan"]}')
print(f'  Total transaksi: {laporan["total_transaksi"]}')
