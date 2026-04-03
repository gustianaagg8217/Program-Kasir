# 💰 Discount & Tax Feature Documentation

## Overview
The POS system now supports comprehensive discount and tax (PPN) management with real-time calculations and validation.

## Features

### 1. **Discount Support**
- Apply percentage-based discount to transactions
- Discount range: 0-100%
- Calculated as: `discount_amount = subtotal × (discount_percent / 100)`
- Tax is calculated on the discounted amount (subtotal - discount)

### 2. **Tax Support (PPN)**
- Apply percentage-based tax (Pajak Pertambahan Nilai)
- Tax range: 0-100%
- Calculated as: `tax_amount = (subtotal - discount) × (tax_percent / 100)`
- Tax applied AFTER discount

### 3. **Calculation Formula**
```
Total = Subtotal - Discount + Tax
      = Subtotal - (Subtotal × D%) + ((Subtotal - (Subtotal × D%)) × T%)

Example:
Subtotal = Rp 200.000
Discount = 10% → Rp 20.000
Base for tax = Rp 180.000
Tax = 5% → Rp 9.000
Total = Rp 189.000
```

## UI Components

### Discount & Tax Input Section
Located in the transaction page, below the cart summary:

```
╔═══════════════════════════════════════════╗
║         Diskon & Pajak                    ║
║                                           ║
║  Diskon (%): [____]  Pajak - PPN (%): [__]║
║                                           ║
╚═══════════════════════════════════════════╝
```

### Cart Summary Display
Enhanced to show breakdown:

```
Subtotal       : Rp 200.000
Diskon (10%)   : -Rp 20.000
Pajak (5%)     : +Rp 9.000
─────────────────────────────
Total          : Rp 189.000
```

## Usage Flow

### Step 1: Add Items to Cart
- Select products and quantities as normal
- Subtotal is calculated automatically

### Step 2: Apply Discount (Optional)
- Enter discount percentage in the "Diskon (%)" field
- Press Tab or click elsewhere to apply
- Discount amount is calculated and cart updates

### Step 3: Apply Tax (Optional)
- Enter tax percentage in the "Pajak - PPN (%)" field
- Press Tab or click elsewhere to apply
- Tax is calculated on (subtotal - discount)
- Total is updated

### Step 4: Process Payment
- Total now includes applied discount and tax
- Payment validation uses the updated total
- Receipt shows detailed breakdown

## Database Schema

### Transactions Table Updates
Added 4 new columns:

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `discount_percent` | REAL | 0 | Discount percentage |
| `discount_amount` | INTEGER | 0 | Discount in Rupiah |
| `tax_percent` | REAL | 0 | Tax percentage (PPN) |
| `tax_amount` | INTEGER | 0 | Tax in Rupiah |

**Migration**: Columns are auto-added if missing during app startup.

## Receipt Format

Receipts now include discount and tax breakdown:

```
════════════════════════════════════════════
TOKO ACCESSORIES G-LIES
Jl. Majalaya, Solokanjeruk, Bandung
════════════════════════════════════════════
Transaksi ID  : 15
Tanggal/Waktu : 2026-04-03 14:30:45
────────────────────────────────────────────
1. Produk A
   2x Rp 50.000 = Rp 100.000
2. Produk B
   1x Rp 100.000 = Rp 100.000
────────────────────────────────────────────
Subtotal      : Rp 200.000
Diskon (10%)  : -Rp 20.000
Pajak (5%)    : +Rp 9.000
────────────────────────────────────────────
Total Belanja  : Rp 189.000
Pembayaran     : Rp 200.000
Kembalian      : Rp 11.000
════════════════════════════════════════════
Terima Kasih
════════════════════════════════════════════
```

## Validation Rules

### Discount Validation
- ✅ Must be between 0-100%
- ✅ Cannot be negative
- ✅ Cannot exceed 100%
- ✅ Accepts decimal values (e.g., 5.5%)

### Tax Validation
- ✅ Must be between 0-100%
- ✅ Cannot be negative
- ✅ Cannot exceed 100%
- ✅ Accepts decimal values (e.g., 10.5%)

### Error Messages
- "Diskon harus antara 0-100%" - Discount out of range
- "Pajak harus antara 0-100%" - Tax out of range
- "Diskon harus berupa angka!" - Non-numeric discount value
- "Pajak harus berupa angka!" - Non-numeric tax value

## Logging

All discount and tax operations are logged:

```
[INFO] Discount set: 10% (amount: Rp20,000)
[INFO] Tax set: 5% (amount: Rp9,500)
[INFO] Transaction completed: ID=15, total=Rp189,500, items=2, payment=Rp200,000
```

## Transaction Model API

### Setting Discount
```python
transaction = handler.transaction_service.get_current_transaction()
transaction.set_discount(10)  # 10% discount
# transaction.discount_percent = 10
# transaction.discount_amount = auto-calculated
# transaction.total = auto-updated
```

### Setting Tax
```python
transaction.set_tax(5)  # 5% tax
# transaction.tax_percent = 5
# transaction.tax_amount = auto-calculated
# transaction.total = auto-updated
```

### Calculating Total
```python
# Automatically called when:
# - Adding items
# - Removing items
# - Setting discount
# - Setting tax
total = transaction.calculate_total()
```

## Examples

### Example 1: Coffee Shop (No Tax, 5% Member Discount)
```
Items:
- Kopi Cappuccino ×2 @ Rp 25.000 = Rp 50.000
- Pastry ×1 @ Rp 30.000 = Rp 30.000

Subtotal     : Rp 80.000
Discount 5%  : -Rp 4.000
Pajak 0%     : ±Rp 0
───────────────────────
Total        : Rp 76.000
```

### Example 2: Retail Store (10% Discount + 10% Tax/PPN)
```
Items:
- Keyboard USB ×1 @ Rp 150.000 = Rp 150.000
- Mouse Logitech ×1 @ Rp 200.000 = Rp 200.000

Subtotal        : Rp 350.000
Discount 10%    : -Rp 35.000
Base for tax    : Rp 315.000
Pajak 10% (PPN) : +Rp 31.500
───────────────────────
Total           : Rp 346.500
```

### Example 3: Bulk Purchase (15% Volume Discount + 5% Tax)
```
Items:
- Cables ×100 @ Rp 10.000 = Rp 1.000.000
- Connectors ×50 @ Rp 5.000 = Rp 250.000

Subtotal        : Rp 1.250.000
Discount 15%    : -Rp 187.500
Base for tax    : Rp 1.062.500
Pajak 5% (PPN)  : +Rp 53.125
──────────────────────────
Total           : Rp 1.115.625
```

## Testing

Run the test suite:
```bash
python test_discount_tax.py
```

All calculations verified:
- ✅ Basic transaction (no discount/tax)
- ✅ Transaction with discount only
- ✅ Transaction with discount + tax
- ✅ Validation of ranges
- ✅ Various percentage combinations

## Technical Files Modified

1. **models.py**
   - Updated `Transaction` dataclass with discount/tax fields
   - Added `set_discount()` method
   - Added `set_tax()` method
   - Updated `calculate_total()` logic

2. **database.py**
   - Updated transaction table schema
   - Added migration support for new columns
   - Updated `add_transaction()` method signature

3. **gui_main.py**
   - Added discount/tax input fields
   - Added `_update_discount()` method
   - Added `_update_tax()` method
   - Enhanced `_update_cart_display()` to show discount/tax
   - Updated `_generate_receipt_text()` to include discount/tax

4. **transaction.py**
   - Updated `save_transaction()` to save discount/tax data

## Best Practices

1. **Member Discounts**
   - Ask customer if they have member card
   - Apply member discount % automatically
   - Can be combined with promotional discounts

2. **Tax Compliance**
   - Always ensure tax % matches local regulations
   - In Indonesia: PPN standard is 10%
   - Store tax settings in configuration

3. **User Communication**
   - Always display discount amount in Rupiah
   - Show tax amount separately
   - Make total clear and visible
   - Include full breakdown in receipts

4. **Validation**
   - Warn if discount > 80% (unusual)
   - Warn if tax > 15% (unusual for standard PPN)
   - Confirm large transactions

## Future Enhancements

Possible future additions:
- Multiple discount types (member, promotional, seasonal)
- Discount per item (not just total)
- Fixed amount discounts (e.g., Rp 50.000 off)
- Tax-exempt items/categories
- Automatic discount based on total amount
- Loyalty points integration

---

## FAQ

**Q: Can I change discount/tax after payment?**
A: No, once payment is processed, the transaction is locked. The discount/tax must be set before payment.

**Q: Does tax apply to the discount or original price?**
A: Tax is applied to the discounted amount: (subtotal - discount) × tax%

**Q: Can I use both discount and tax together?**
A: Yes! They work together as intended in the formula.

**Q: What if I enter 0% discount?**
A: No discount will be applied. Discount amount will be Rp 0.

**Q: Are there any restrictions on percentage values?**
A: Only 0-100% range is allowed. Negative or >100% will show an error.

---

For more information, see the main README.md or contact support.
