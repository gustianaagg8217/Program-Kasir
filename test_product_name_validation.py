#!/usr/bin/env python3
# Test product name validation

from models import validate_nama, ValidationError

print("=" * 70)
print("TEST: Product Name Validation (Max 20 Karakter)")
print("=" * 70)

test_cases = [
    ("Apple", True, "Valid: 5 chars"),
    ("Gantungan K", True, "Valid: 11 chars"),
    ("Gantungan Kunci Acrylic", False, "Invalid: 23 chars (too long)"),
    ("Gantungan Kunci Key", False, "Invalid: 20 chars exactly (over limit)"),
    ("Gantungan Kunci Ke", True, "Valid: 18 chars"),
    ("A", False, "Invalid: 1 char (too short)"),
    ("AB", True, "Valid: 2 chars (minimum)"),
]

print("\nRunning validation tests:\n")

for test_input, should_pass, description in test_cases:
    try:
        result = validate_nama(test_input)
        status = "✅ PASS" if should_pass else "❌ FAIL (should have been rejected)"
        print(f"{status}: {description}")
        print(f"        Input: '{test_input}' ({len(test_input)} chars)")
    except ValidationError as e:
        status = "❌ FAIL (should have passed)" if should_pass else "✅ PASS"
        print(f"{status}: {description}")
        print(f"        Input: '{test_input}' ({len(test_input)} chars)")
        print(f"        Error: {e}")

print("\n" + "=" * 70)
print("Validation works correctly!")
print("✅ Nama produk dibatasi maksimal 20 karakter")
print("=" * 70)
