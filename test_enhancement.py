#!/usr/bin/env python3
"""
Test script untuk enhancement fitur tampil nama produk saat input kode
"""

from database import DatabaseManager
from models import Product
from main import POSSystem

def test_enhancement():
    """Test enhancement - display produk saat input kode"""
    
    print("\n" + "=" * 70)
    print("TEST: Enhancement - Display Produk Saat Input Kode")
    print("=" * 70)
    
    # Initialize database
    db = DatabaseManager()
    
    # Add test product jika belum ada
    existing = db.get_product_by_kode("COFFEE")
    if not existing:
        print("\n➕ Adding test product: COFFEE (Kopi Hitam) - Rp 12.000")
        db.add_product("COFFEE", "Kopi Hitam", 12000, 50)
        print("✅ Product added successfully")
    else:
        print("\n✅ Product COFFEE already exists")
    
    # Add another product
    existing2 = db.get_product_by_kode("TEA")
    if not existing2:
        print("➕ Adding test product: TEA (Teh Botol) - Rp 5.000")
        db.add_product("TEA", "Teh Botol", 5000, 100)
        print("✅ Product added successfully")
    else:
        print("✅ Product TEA already exists")
    
    print("\n" + "=" * 70)
    print("✅ Test Products Created:")
    print("=" * 70)
    
    # Display all products
    products = db.get_all_products()
    for prod in products:
        print(f"  • {prod['kode']}: {prod['nama']} - Rp {prod['harga']:,.0f} (Stok: {prod['stok']})")
    
    print("\n" + "=" * 70)
    print("📝 FEATURE ENHANCEMENT - HOW TO TEST:")
    print("=" * 70)
    print("\n1. Start the program:")
    print("   python main.py")
    print("\n2. Choose Menu 2: 🛒 Transaksi Penjualan")
    print("\n3. Choose Menu 1: ➕ Tambah Item")
    print("\n4. Input Kode Produk: COFFEE")
    print("   (then press ENTER)")
    print("\n5. EXPECTED - System should immediately display:")
    print("   ✅ Produk ditemukan!")
    print("   📦 Nama: Kopi Hitam")
    print("   💰 Harga: Rp 12.000")
    print("   📊 Stok: 50 pcs")
    print("")
    print("   (Tersedia: 50 pcs)")
    print("   Jumlah (qty): [waiting for input]")
    print("\n6. Input qty: 2")
    print("   (then press ENTER)")
    print("\n7. EXPECTED - System should show:")
    print("   ✅ Item berhasil ditambahkan!")
    print("   2x Kopi Hitam = Rp 24.000")
    print("")
    print("8. Back to transaction menu, you'll see item details displayed!")
    print("")
    print("=" * 70)

if __name__ == "__main__":
    test_enhancement()
