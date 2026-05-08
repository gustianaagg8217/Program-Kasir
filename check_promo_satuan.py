#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Check promotion satuan/unit
"""

from database import DatabaseManager

db = DatabaseManager()

# Get active promotions
promos = db.get_active_promotions()

print("\n📋 PROMOSI AKTIF DI DATABASE:")
print("="*80)
for promo in promos:
    print(f"\nPromosi ID: {promo['id']}")
    print(f"  Nama: {promo['nama_promosi']}")
    print(f"  Satuan: {promo['satuan']}")
    print(f"  Min Qty: {promo['min_qty']}")
    print(f"  Tipe Diskon: {promo['tipe_diskon']}")
    print(f"  Nilai Diskon: {promo['nilai_diskon']}")
    print(f"  Berlaku Kelipatan: {promo.get('berlaku_kelipatan', 0)}")
    print(f"  Tanggal Mulai: {promo['tanggal_mulai']}")
    print(f"  Tanggal Selesai: {promo['tanggal_selesai']}")
