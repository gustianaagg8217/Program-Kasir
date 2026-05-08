#!/usr/bin/env python3
# ============================================================================
# DEBUG_KELIPATAN.PY - Helper script untuk debug fitur berlaku kelipatan
# ============================================================================

import sqlite3
from datetime import datetime
from models import format_rp

def check_promotions():
    """Check semua promosi dan nilai berlaku_kelipatan mereka."""
    db_path = "kasir_pos.db"
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        print("=" * 80)
        print("📊 STATUS PROMOSI - BERLAKU KELIPATAN CHECK")
        print("=" * 80)
        
        cursor.execute("""
            SELECT id, nama_promosi, tipe_diskon, nilai_diskon, min_qty, satuan,
                   berlaku_kelipatan, tanggal_mulai, tanggal_selesai, status
            FROM promotions
            ORDER BY id DESC
        """)
        
        promotions = cursor.fetchall()
        
        if not promotions:
            print("❌ Tidak ada promosi di database")
            return
        
        print(f"\n📋 Total Promosi: {len(promotions)}")
        print("-" * 80)
        
        for idx, promo in enumerate(promotions, 1):
            berlaku_kelipatan = bool(promo['berlaku_kelipatan'] or 0)
            
            print(f"\n{idx}. {promo['nama_promosi']}")
            print(f"   ID: {promo['id']}")
            print(f"   Tipe: {promo['tipe_diskon']}")
            print(f"   Nilai: Rp {promo['nilai_diskon']:,}" if promo['tipe_diskon'] == 'nominal' else f"   Nilai: {promo['nilai_diskon']}%")
            print(f"   Min Pembelian: {promo['min_qty']} {promo['satuan']}")
            print(f"   Berlaku Kelipatan: {'✓ YA' if berlaku_kelipatan else '✗ TIDAK'}")
            print(f"   Periode: {promo['tanggal_mulai']} s/d {promo['tanggal_selesai']}")
            print(f"   Status: {promo['status']}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

def enable_kelipatan_for_promotion(promo_id):
    """Enable berlaku_kelipatan untuk promosi tertentu."""
    db_path = "kasir_pos.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if promotion exists
        cursor.execute("SELECT nama_promosi FROM promotions WHERE id = ?", (promo_id,))
        result = cursor.fetchone()
        
        if not result:
            print(f"❌ Promosi dengan ID {promo_id} tidak ditemukan")
            conn.close()
            return
        
        promo_name = result[0]
        
        # Update berlaku_kelipatan
        cursor.execute("""
            UPDATE promotions
            SET berlaku_kelipatan = 1
            WHERE id = ?
        """, (promo_id,))
        
        conn.commit()
        print(f"✅ Promosi '{promo_name}' (ID {promo_id}) - Berlaku Kelipatan DIAKTIFKAN")
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

def disable_kelipatan_for_promotion(promo_id):
    """Disable berlaku_kelipatan untuk promosi tertentu."""
    db_path = "kasir_pos.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if promotion exists
        cursor.execute("SELECT nama_promosi FROM promotions WHERE id = ?", (promo_id,))
        result = cursor.fetchone()
        
        if not result:
            print(f"❌ Promosi dengan ID {promo_id} tidak ditemukan")
            conn.close()
            return
        
        promo_name = result[0]
        
        # Update berlaku_kelipatan
        cursor.execute("""
            UPDATE promotions
            SET berlaku_kelipatan = 0
            WHERE id = ?
        """, (promo_id,))
        
        conn.commit()
        print(f"✅ Promosi '{promo_name}' (ID {promo_id}) - Berlaku Kelipatan DINONAKTIFKAN")
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

def test_multiplier_calculation():
    """Test perhitungan multiplier untuk scenarios berbeda."""
    print("\n" + "=" * 80)
    print("🧪 TEST PERHITUNGAN MULTIPLIER")
    print("=" * 80)
    
    test_cases = [
        {"name": "Price-based dengan kelipatan", "amount": 440750, "min": 200000, "multiplier": 2},
        {"name": "Price-based Rp 200k", "amount": 200000, "min": 200000, "multiplier": 1},
        {"name": "Price-based Rp 600k", "amount": 600000, "min": 200000, "multiplier": 3},
        {"name": "Qty-based 10kg", "amount": 10, "min": 5, "multiplier": 2},
        {"name": "Qty-based 5kg", "amount": 5, "min": 5, "multiplier": 1},
    ]
    
    for test in test_cases:
        multiplier = int(test["amount"] / test["min"])
        status = "✓" if multiplier == test["multiplier"] else "✗"
        print(f"{status} {test['name']}: {test['amount']} / {test['min']} = {multiplier}x (expected {test['multiplier']}x)")

if __name__ == "__main__":
    import sys
    
    print("\n🔍 PROGRAM DEBUG BERLAKU KELIPATAN\n")
    print("Menu:")
    print("1. Check semua promosi")
    print("2. Enable berlaku kelipatan untuk promosi")
    print("3. Disable berlaku kelipatan untuk promosi")
    print("4. Test perhitungan multiplier")
    print("0. Exit\n")
    
    choice = input("Pilih menu (0-4): ").strip()
    
    if choice == "1":
        check_promotions()
    elif choice == "2":
        check_promotions()
        promo_id = input("\nMasukkan ID promosi untuk enable kelipatan: ").strip()
        if promo_id.isdigit():
            enable_kelipatan_for_promotion(int(promo_id))
        else:
            print("❌ ID harus berupa angka")
    elif choice == "3":
        check_promotions()
        promo_id = input("\nMasukkan ID promosi untuk disable kelipatan: ").strip()
        if promo_id.isdigit():
            disable_kelipatan_for_promotion(int(promo_id))
        else:
            print("❌ ID harus berupa angka")
    elif choice == "4":
        test_multiplier_calculation()
    elif choice == "0":
        print("Bye!")
    else:
        print("❌ Pilihan tidak valid")
