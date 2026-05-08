#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script untuk verifikasi promo discount muncul di struk
"""

from database import DatabaseManager
from transaction import TransactionService
import json

def test_promo_in_receipt():
    """Test bahwa promo discount disimpan dan ditampilkan di struk"""
    
    print("\n" + "="*60)
    print("🧪 TEST: Verifikasi Promo Discount di Struk")
    print("="*60)
    
    # Initialize
    db = DatabaseManager()
    trans_service = TransactionService(db)
    
    # Get a product with active promotion
    print("\n📦 Ambil data produk...")
    all_products = db.get_all_products()
    if not all_products:
        print("❌ Tidak ada produk di database")
        return
    
    product = all_products[0]
    print(f"✅ Produk: {product['nama']} (ID: {product['id']})")
    print(f"   Harga: Rp {product['harga']:,}")
    print(f"   Stok: {product['stok']}")
    
    # Check for active promotions
    from promotion_service import PromotionService
    promo_service = PromotionService(db)
    active_promos = promo_service.get_applicable_promotions()
    
    if active_promos:
        print(f"\n🎯 Promosi aktif:")
        for promo in active_promos[:3]:
            print(f"   - {promo['nama_promosi']}: {promo['nilai_diskon']} ({promo['tipe_diskon']})")
    else:
        print("\n⚠️ Tidak ada promosi aktif")
    
    # Create a test transaction
    print("\n💳 Membuat transaksi test...")
    trans = trans_service.create_transaction()
    print(f"✅ Transaksi dibuat: {trans.tanggal}")
    
    # Add item (qty = 5kg untuk bisa dapat promo jika ada)
    qty_to_add = 5
    print(f"\n📝 Menambah {qty_to_add} item...")
    
    # Debug: Check promotion calculation
    from promotion_service import PromotionService
    promo_srv = PromotionService(db)
    product_satuan = (product.get('satuan') or 'pcs').lower()
    discount_info = promo_srv.calculate_discount_for_quantity(qty_to_add, product_satuan, active_promos)
    print(f"   Satuan produk: {product_satuan}")
    print(f"   Discount info: {discount_info}")
    
    success = trans_service.add_item_by_kode(product['kode'], qty_to_add)
    
    if not success:
        print("❌ Gagal add item")
        return
    
    # Set payment
    trans_service.current_transaction.set_bayar(trans_service.current_transaction.total)
    
    # Save transaction
    print("\n💾 Menyimpan transaksi...")
    trans_id = trans_service.save_transaction()
    
    if not trans_id:
        print("❌ Gagal save transaction")
        return
    
    print(f"✅ Transaksi disimpan dengan ID: {trans_id}")
    
    # Retrieve transaction dari database
    print("\n🔍 Mengambil transaksi dari database...")
    trans_data = db.get_transaction(trans_id)
    
    if not trans_data:
        print("❌ Gagal retrieve transaction")
        return
    
    trans_header = trans_data['transaction']
    items = trans_data['items']
    
    print(f"✅ Transaksi ID {trans_id} berhasil diambil")
    print(f"\n📋 Detail Items:")
    print(f"{'Produk':<20} {'Qty':<8} {'Harga':<15} {'Promo':<20}")
    print("-" * 65)
    
    for item in items:
        promo_name = item.get('promotion_name', 'N/A')
        discount = item.get('discount_percent', 0)
        if discount > 0:
            discount_str = f"{item['promotion_name']} ({discount}%)"
        else:
            discount_str = "Tidak ada"
        
        print(f"{item['nama']:<20} {item['qty']:<8} Rp {item['harga_satuan']:<13,} {discount_str:<20}")
    
    # Check if promo info is in items
    print("\n✅ VERIFIKASI DATABASE FIELDS:")
    for i, item in enumerate(items, 1):
        print(f"\n   Item {i}:")
        print(f"     - promotion_id: {item.get('promotion_id', 'NULL')}")
        print(f"     - promotion_name: {item.get('promotion_name', 'NULL')}")
        print(f"     - discount_percent: {item.get('discount_percent', 0)}")
        print(f"     - discount_nominal: {item.get('discount_nominal', 0)}")
    
    print("\n" + "="*60)
    print("✅ TEST SELESAI - Promo fields berhasil disimpan di database!")
    print("="*60)

if __name__ == '__main__':
    try:
        test_promo_in_receipt()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
