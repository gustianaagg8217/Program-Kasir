# Diskon & Pajak Feature Documentation

## Overview
Added comprehensive **discount and tax** support to Telegram bot POS system. Users can now apply percentage-based discounts and taxes during checkout with real-time calculation and detailed receipt breakdown.

---

## Changes Made

### 1. Conversation States Added
```python
DISKON, PAJAK = range(5, 7)
```
- **DISKON**: State for discount input (0-100%)
- **PAJAK**: State for tax/PPN input (0-100%)

### 2. Updated Conversation Handler
Added two new states to the transaction ConversationHandler:
```python
DISKON: [
    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_diskon),
],
PAJAK: [
    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_pajak),
],
```

### 3. Methods Added/Modified

#### **transaksi_checkout()** - MODIFIED ✏️
**Before:**
- Directly showed subtotal and asked for payment amount

**After:**
- Shows confirmation with item summary
- Asks for discount percentage (0-100%)
- Transitions to DISKON state

```python
# New prompt
msg = (
    f"💳 *KONFIRMASI CHECKOUT*\n\n"
    f"📊 Ringkasan:\n"
    f"  Total Item: {summary['items_count']}\n"
    f"  Total Qty: {summary['qty_total']}\n"
    f"  Subtotal: {format_rp(summary['total'])}\n\n"
    f"🏷️  *MASUKKAN DISKON (%)*\n"
    f"(Ketik angka 0-100 atau 0 untuk tanpa diskon)"
)
```

#### **handle_diskon()** - NEW ⭐
Handles discount input and calculates discount amount:

**Flow:**
1. Accepts discount percentage (0-100)
2. Validates input
3. Applies discount to transaction using `trans.set_discount(diskon_percent)`
4. Calculates discount amount automatically
5. Shows discount applied message
6. Asks for tax percentage
7. Transitions to PAJAK state

**Logic:**
```python
# Validate input
if diskon_percent < 0 or diskon_percent > 100:
    raise ValidationError

# Apply to transaction
trans.set_discount(diskon_percent)
# Automatically calculates: 
# discount_amount = subtotal * (discount_percent / 100)
```

#### **handle_pajak()** - NEW ⭐
Handles tax/PPN input and shows final summary:

**Flow:**
1. Accepts tax percentage (0-100)
2. Validates input
3. Applies tax to transaction using `trans.set_tax(pajak_percent)`
4. Calculates tax amount on discounted subtotal
5. Shows complete breakdown:
   - Subtotal
   - Discount amount with percentage
   - Tax amount with percentage
   - **Total (with discount and tax)**
6. Asks for payment amount
7. Transitions to PEMBAYARAN state

**Logic:**
```python
# Tax calculated ON THE DISCOUNTED AMOUNT
# Formula: 
# tax_amount = (subtotal - discount_amount) * (tax_percent / 100)
# total = subtotal - discount_amount + tax_amount
```

#### **handle_pembayaran()** - MODIFIED ✏️
Enhanced to show detailed breakdown in success receipt:

**Before Success Message:**
```
✅ *TRANSAKSI BERHASIL*

📄 No. Invoice: 123
💰 Total: Rp 450,000
💵 Pembayaran: Rp 500,000
🔄 Kembalian: Rp 50,000
⏰ Waktu: 15:30:45
```

**After Success Message (with discount & tax):**
```
✅ *TRANSAKSI BERHASIL*

📄 No. Invoice: 123
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Subtotal     : Rp 500,000
Diskon 10%   : -Rp 50,000
Pajak 10%    : +Rp 45,000
━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 *Total    : Rp 495,000*
💵 Pembayaran: Rp 500,000
🔄 Kembalian : Rp 5,000
⏰ Waktu     : 15:30:45

Terima kasih telah berbelanja! 🙏
```

---

## User Flow

```
[Checkout Button]
    ↓
Ask Discount %
    ↓ User enters: 10
    ↓
Set discount (10%)
Show: "Diskon Diterapkan: Rp 50,000"
    ↓
Ask Tax/PPN %
    ↓ User enters: 10
    ↓
Set tax (10%)
Show Complete Breakdown:
  Subtotal: Rp 500,000
  Discount: -Rp 50,000
  Tax: +Rp 45,000
  Total: Rp 495,000
    ↓
Ask Payment Amount
    ↓ User enters: 500,000
    ↓
[Complete Transaction]
Show Receipt with all details
    ↓
[Finish]
```

---

## Calculation Examples

### Example 1: 10% Discount, No Tax
```
Subtotal:       Rp 500,000
Discount 10%:   -Rp 50,000
Tax 0%:         Rp 0
─────────────────────────
Total:          Rp 450,000
```

### Example 2: 10% Discount, 10% Tax
```
Subtotal:       Rp 500,000
Discount 10%:   -Rp 50,000  (Rp 500,000 × 10%)
At base:        Rp 450,000
Tax 10%:        +Rp 45,000  (Rp 450,000 × 10%)
─────────────────────────
Total:          Rp 495,000
```

### Example 3: No Discount, 15% Tax (PPN Standard)
```
Subtotal:       Rp 1,000,000
Discount 0%:    Rp 0
Tax 15%:        +Rp 150,000 (Rp 1,000,000 × 15%)
─────────────────────────
Total:          Rp 1,150,000
```

---

## Implementation Details

### Transaction Model Integration
The implementation leverages existing `Transaction` model methods:

```python
# From models.py - Transaction class
transaction.set_discount(discount_percent: float) -> bool
# Automatically calculates discount_amount
# Recalculates total

transaction.set_tax(tax_percent: float) -> bool
# Automatically calculates tax_amount
# Tax is calculated on (subtotal - discount)
# Recalculates total

transaction.calculate_total() -> int
# Formula: total = subtotal - discount_amount + tax_amount
```

### Data Flow
1. **Checkout** → Asks for discount
2. **Diskon Input** → Applies discount to transaction (trans.set_discount)
3. **Pajak Input** → Applies tax to transaction (trans.set_tax)
4. **Both applied** → Recalculation happens automatically
5. **Payment** → Uses calculated total with discount and tax
6. **Receipt** → Shows all components (subtotal, discount, tax, total)

### Database Storage
- Discount and tax info is **not stored yet** in database
- Currently calculated and displayed only
- Can be extended to save to database in future

---

## Testing Scenarios

### Scenario 1: No Discount, No Tax
```
User: 0 (discount)
User: 0 (tax)
Expected: Total remains unchanged
```

### Scenario 2: 10% Discount, 0% Tax
```
User: 10 (discount)
User: 0 (tax)
Expected: Total = subtotal - (subtotal × 10%)
```

### Scenario 3: 0% Discount, 15% Tax
```
User: 0 (discount)
User: 15 (tax)
Expected: Total = subtotal + (subtotal × 15%)
```

### Scenario 4: 15% Discount, 10% Tax
```
User: 15 (discount)
User: 10 (tax)
Expected: 
  discount_amount = subtotal × 15%
  tax_amount = (subtotal - discount_amount) × 10%
  total = subtotal - discount_amount + tax_amount
```

### Scenario 5: Invalid Inputs
```
Test: User enters -5 (discount)
Expected: Error - "Diskon harus antara 0-100%"

Test: User enters 150 (tax)
Expected: Error - "Pajak harus antara 0-100%"

Test: User enters "abc" (discount)
Expected: Error - "Masukkan angka yang valid (0-100)"
```

---

## Error Handling

| Error Scenario | Message |
|---|---|
| Invalid discount (negative) | "❌ Diskon harus antara 0-100%!" |
| Invalid discount (>100) | "❌ Diskon harus antara 0-100%!" |
| Non-numeric discount | "❌ Masukkan angka yang valid (0-100)!" |
| Invalid tax (negative) | "❌ Pajak harus antara 0-100%!" |
| Invalid tax (>100) | "❌ Pajak harus antara 0-100%!" |
| Non-numeric tax | "❌ Masukkan angka yang valid (0-100)!" |
| Insufficient payment | "❌ Uang Anda kurang Rp {amount}!" |

All errors show recovery message: "Silakan coba lagi atau ketik /cancel untuk batalkan."

---

## Logging

All discount and tax operations are logged:

```
Discount applied: 10% (Rp50,000) for user_id: 123456789
Tax applied: 10% (Rp45,000) for user_id: 123456789
Transaction completed: ID=789, subtotal=500000, diskon=50000, pajak=45000, total=495000, payment=500000, user_id=123456789
```

---

## Future Enhancements

1. **Save to Database**
   - Store discount_percent, discount_amount, tax_percent, tax_amount in transactions table
   - Track discount usage patterns

2. **Fixed Discounts**
   - Define fixed discount amounts (membership, bulk discount)
   - Apply pre-configured discounts via buttons

3. **Coupon Support**
   - Enter coupon code for automatic discount
   - Validate coupon availability and limits

4. **Tax Configuration**
   - Admin can set default tax rate per transaction
   - Different tax rates for different product categories

5. **Discount Rules**
   - Tiered discounts based on purchase amount
   - Time-based promotions
   - Member-exclusive discounts

6. **Tax Templates**
   - Pre-save common tax rates (0%, 10%, 15%)
   - Quick select buttons instead of typing

7. **Receipt Printer Integration**
   - Format discount/tax in printed receipt
   - Show on receipt printing

---

## Backward Compatibility

✅ **Fully backward compatible:**
- Existing transactions work without discount/tax
- Defaults to 0% discount and 0% tax
- No database changes required
- No breaking changes to existing code

---

## Files Modified

**File:** `d:\Program-Kasir\telegram_main.py`

**Changes:**
- Added DISKON and PAJAK conversation states (line ~57)
- Updated range definitions for other states (line ~57-60)
- Added DISKON and PAJAK to ConversationHandler (line ~147-152)
- Modified `transaksi_checkout()` method (line ~780-810)
- **Added `handle_diskon()` method (lines ~683-730)**
- **Added `handle_pajak()` method (lines ~732-800)**
- Modified `handle_pembayaran()` method (lines ~944-1021)

---

## Dependencies & Requirements

- ✅ `models.py` Transaction class with discount/tax methods (already exists)
- ✅ `transaction.py` TransactionHandler integration (already supports)
- ✅ `database.py` (no changes needed)
- ✅ Format_rp() for currency formatting

---

**Implementation Date:** April 4, 2026  
**Status:** ✅ Complete & Tested  
**Syntax Validation:** ✅ Passed  
**Version:** 1.0  

