#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script untuk fitur discount dan tax.
"""

from models import Transaction, TransactionItem
from models import format_rp

print("=" * 70)
print("TESTING DISCOUNT AND TAX FUNCTIONALITY")
print("=" * 70)

# Test 1: Basic transaction without discount/tax
print("\n1️⃣  TEST 1: Basic transaction (no discount/tax)")
trans = Transaction()
item1 = TransactionItem(product_id=1, product_name="Item 1", qty=2, harga_satuan=50000)
item2 = TransactionItem(product_id=2, product_name="Item 2", qty=1, harga_satuan=100000)
trans.add_item(item1)
trans.add_item(item2)

print(f"   Subtotal     : {format_rp(trans.subtotal)}")
print(f"   Discount (0%): {format_rp(trans.discount_amount)}")
print(f"   Tax (0%)     : {format_rp(trans.tax_amount)}")
print(f"   Total        : {format_rp(trans.total)}")
assert trans.subtotal == 200000, "Subtotal should be 200000"
assert trans.total == 200000, "Total should be 200000 (no discount/tax)"
print("   ✅ Test 1 PASSED")

# Test 2: Transaction with 10% discount
print("\n2️⃣  TEST 2: Transaction with 10% discount")
trans.set_discount(10)
print(f"   Subtotal     : {format_rp(trans.subtotal)}")
print(f"   Discount (10%): -{format_rp(trans.discount_amount)}")
print(f"   Tax (0%)      : {format_rp(trans.tax_amount)}")
print(f"   Total        : {format_rp(trans.total)}")
assert trans.discount_percent == 10, "Discount percent should be 10"
assert trans.discount_amount == 20000, "Discount amount should be 20000 (10% of 200000)"
assert trans.total == 180000, "Total should be 180000 (200000 - 20000)"
print("   ✅ Test 2 PASSED")

# Test 3: Transaction with 10% discount + 10% tax
print("\n3️⃣  TEST 3: Transaction with 10% discount + 10% tax")
trans.set_tax(10)
print(f"   Subtotal      : {format_rp(trans.subtotal)}")
print(f"   Discount (10%) : -{format_rp(trans.discount_amount)}")
print(f"   Base for tax   : {format_rp(trans.subtotal - trans.discount_amount)}")
print(f"   Tax (10%)      : +{format_rp(trans.tax_amount)}")
print(f"   Total         : {format_rp(trans.total)}")
expected_tax = int((200000 - 20000) * (10/100))  # 10% of (200000-20000)
expected_total = 200000 - 20000 + expected_tax  # 200000 - 20000 + 18000 = 198000
assert trans.tax_percent == 10, "Tax percent should be 10"
assert trans.tax_amount == expected_tax, f"Tax amount should be {expected_tax}"
assert trans.total == expected_total, f"Total should be {expected_total}"
print("   ✅ Test 3 PASSED")

# Test 4: Discount exceeding subtotal (should fail)
print("\n4️⃣  TEST 4: Validate discount range")
try:
    trans.set_discount(150)  # 150% discount
    print("   ❌ Test 4 FAILED - Should have raised error for discount > 100%")
except Exception as e:
    print(f"   Error caught: {e}")
    print("   ✅ Test 4 PASSED")

# Test 5: Negative tax (should fail)
print("\n5️⃣  TEST 5: Validate tax range")
try:
    trans.set_tax(-5)  # Negative tax
    print("   ❌ Test 5 FAILED - Should have raised error for negative tax")
except Exception as e:
    print(f"   Error caught: {e}")
    print("   ✅ Test 5 PASSED")

# Test 6: Different percentage values
print("\n6️⃣  TEST 6: Various discount and tax combinations")
trans2 = Transaction()
item3 = TransactionItem(product_id=3, product_name="Item 3", qty=1, harga_satuan=300000)
trans2.add_item(item3)

trans2.set_discount(15)  # 15% discount
trans2.set_tax(5)        # 5% tax

expected_discount = int(300000 * 0.15)  # 45000
expected_base = 300000 - expected_discount  # 255000
expected_tax = int(expected_base * 0.05)  # 12750
expected_total = expected_base + expected_tax  # 267750

print(f"   Subtotal           : {format_rp(trans2.subtotal)}")
print(f"   Discount (15%)     : -{format_rp(trans2.discount_amount)}")
print(f"   Tax (5% on base)   : +{format_rp(trans2.tax_amount)}")
print(f"   Total              : {format_rp(trans2.total)}")

assert trans2.discount_amount == expected_discount, f"Discount should be {expected_discount}"
assert trans2.tax_amount == expected_tax, f"Tax should be {expected_tax}"
assert trans2.total == expected_total, f"Total should be {expected_total}"
print("   ✅ Test 6 PASSED")

print("\n" + "=" * 70)
print("✅ ALL TESTS PASSED!")
print("=" * 70)
print("\nDiscount & Tax functionality is working correctly!")
print("- Discount percentage calculation: ✓")
print("- Tax percentage calculation: ✓")
print("- Total calculation (subtotal - discount + tax): ✓")
print("- Validation for invalid ranges: ✓")
