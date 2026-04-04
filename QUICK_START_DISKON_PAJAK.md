# Quick Start - Diskon & Pajak Feature

## What's New? 🎉

The Telegram POS bot now supports **discount and tax** calculations during checkout!

---

## How to Use (User Perspective)

### Step 1: Add Items to Cart
Click "➕ Tambah Item" and add products as normal.

### Step 2: Click "💳 Checkout"
You'll see a summary:
```
💳 KONFIRMASI CHECKOUT

📊 Ringkasan:
  Total Item: 3
  Total Qty: 5
  Subtotal: Rp 500,000

🏷️  MASUKKAN DISKON (%)
(Ketik angka 0-100 atau 0 untuk tanpa diskon)

Contoh: 10 (untuk diskon 10%)
```

### Step 3: Enter Discount (%)
- **Type:** `10` (for 10% discount)
- **Or type:** `0` (for no discount)
- **Or press:** `/cancel` (to abort)

### Step 4: System Shows Discount Applied
```
🏷️  DISKON DITERAPKAN
Diskon: 10%
Potongan: Rp 50,000

💰 MASUKKAN PAJAK (%)
(Ketik angka 0-100 atau 0 untuk tanpa pajak)

Contoh: 10 (untuk pajak 10% PPN)
```

### Step 5: Enter Tax/PPN (%)
- **Type:** `10` (for 10% tax)
- **Or type:** `0` (for no tax)
- **Or type:** `15` (for standard PPN rate)

### Step 6: Review Breakdown
```
📊 RINGKASAN BELANJA

Subtotal : Rp 500,000
Diskon   : -Rp 50,000 (10%)
Pajak    : +Rp 45,000 (10%)
───────────────────────
💵 TOTAL  : Rp 495,000

💳 MASUKKAN JUMLAH PEMBAYARAN
(Ketik nominal atau ketik 0 untuk membatalkan)

Minimum pembayaran: Rp 495,000
```

### Step 7: Enter Payment Amount
- **Type:** `500000` (to pay Rp 500,000)
- **Or type:** `495000` (exact amount, no change)

### Step 8: Success! ✅
```
✅ TRANSAKSI BERHASIL

📄 No. Invoice: 12345
━━━━━━━━━━━━━━━━━━━━━━━
Subtotal     : Rp 500,000
Diskon 10%   : -Rp 50,000
Pajak 10%    : +Rp 45,000
━━━━━━━━━━━━━━━━━━━━━━━
💰 Total    : Rp 495,000
💵 Pembayaran: Rp 500,000
🔄 Kembalian : Rp 5,000
⏰ Waktu     : 15:30:45

Terima kasih telah berbelanja! 🙏
```

---

## Common Use Cases

### Case 1: 10% Member Discount Only
```
Subtotal: Rp 1,000,000
Discount: 10% = -Rp 100,000

Steps:
1. Checkout → Type: 10
2. Tax input → Type: 0
3. Total: Rp 900,000
```

### Case 2: Standard Tax (15% PPN) Only
```
Subtotal: Rp 1,000,000
Tax: 15% = +Rp 150,000

Steps:
1. Checkout → Type: 0 (no discount)
2. Tax input → Type: 15
3. Total: Rp 1,150,000
```

### Case 3: Bulk Buy Discount (15%) + Tax (10%)
```
Subtotal: Rp 5,000,000
Discount: 15% = -Rp 750,000
After discount: Rp 4,250,000
Tax: 10% = +Rp 425,000
Total: Rp 4,675,000

Steps:
1. Checkout → Type: 15
2. Tax input → Type: 10
3. Total: Rp 4,675,000
```

---

## Calculation Formula

### Formula
```
discount_amount = subtotal × (discount_percent / 100)
tax_amount = (subtotal - discount_amount) × (tax_percent / 100)
TOTAL = subtotal - discount_amount + tax_amount
```

### Example: Rp 500,000 with 10% Discount & 10% Tax
```
Subtotal:           Rp 500,000
Discount Calc:      500,000 × (10÷100) = Rp 50,000
Base for Tax:       500,000 - 50,000 = Rp 450,000
Tax Calc:           450,000 × (10÷100) = Rp 45,000
TOTAL:              450,000 + 45,000 = Rp 495,000
```

---

## Tips & Tricks

### Tip 1: Type Just Numbers
```
✅ Type: 10
❌ Don't type: 10% or "10 percent"
```

### Tip 2: No Discount or Tax?
```
Type: 0 (zero)
Or just type: /cancel if you want to abort
```

### Tip 3: Decimal Discounts
```
✅ Type: 2.5 (for 2.5% discount)
✅ Type: 0.5 (for 0.5% discount)
```

### Tip 4: Quick Shortcuts
- **Member discount:** 5% (type: 5)
- **Bulk discount:** 10% (type: 10)
- **Clearance:** 25% (type: 25)
- **Standard PPN (Indonesia):** 10% or 15% (type: 10 or 15)

---

## Common Questions

### Q: What if I make a mistake?
A: Typing an invalid number will show an error, then you can try again. The process is completely reversible until you confirm payment.

### Q: Can I just skip discount/tax?
A: Yes! Type `0` for no discount or no tax.

### Q: What's the difference between discount and tax?
- **Discount:** Reduce the price (coming off subtotal)
- **Tax:** Add to the price (added to discounted amount)

### Q: Does a 10% discount then 10% tax equal 0% change?
A: No! The discount applies first, then tax applies to the DISCOUNTED amount.
```
Subtotal: Rp 1,000
Discount 10%: -Rp 100 (total: Rp 900)
Tax 10%: +Rp 90 (10% of Rp 900, not 1,000)
Final: Rp 990 (net: -1%, not 0%)
```

---

## Error Messages & Solutions

| Message | Meaning | Solution |
|---------|---------|----------|
| "Diskon harus antara 0-100%" | Discount invalid | Type a number between 0-100 |
| "Pajak harus antara 0-100%" | Tax invalid | Type a number between 0-100 |
| "Masukkan angka yang valid" | Not a number | Type only numbers (0-100) |
| "Uang Anda kurang Rp..." | Payment insufficient | Type a larger payment amount |

---

## Process Flow Chart

```
START
  │
  ├─ Add Items to Cart
  │
  ├─ Click [Checkout]
  │   ↓
  ├─ Enter Discount % (0-100)
  │   ├─ Invalid? → Show error, retry
  │   └─ Valid? → Confirm discount applied
  │
  ├─ Enter Tax % (0-100)
  │   ├─ Invalid? → Show error, retry
  │   └─ Valid? → Show complete breakdown
  │
  ├─ Review Summary (Subtotal - Discount + Tax = Total)
  │
  ├─ Enter Payment Amount
  │   ├─ Too low? → Show error, retry
  │   └─ Sufficient? → Process payment
  │
  ├─ [Success!]
  │   ├─ Show receipt with all details
  │   └─ Clear transaction
  │
  └─ END
```

---

## Integration Notes

### For Store Owners
- This feature works with existing **Telegram bot**
- **No additional setup** required
- **Works with all products** in your database
- **Automatic calculation** - no manual math needed

### For Admin/Manager
- All transactions logged with discount/tax info
- Can see discount patterns for analytics
- Future: Save discount/tax to database for reporting

---

## Future Features (Coming Soon)

- 🎟️ **Coupon codes** - Enter code instead of percentage
- 📊 **Pre-set rates** - Click buttons for common discounts/taxes
- 💾 **Save history** - View past transactions with discounts
- 📈 **Analytics** - See discount usage patterns
- 👥 **Member rates** - Auto-apply member discounts

---

## Support

**Issue:** Discount not applying correctly
- **Solution:** Make sure to type a number 0-100 in the first step

**Issue:** Tax calculation seems wrong
- **Solution:** Remember, tax is calculated on the DISCOUNTED amount, not original subtotal

**Issue:** Can't proceed past discount step
- **Solution:** Type a valid number or type `/cancel` to start over

---

**Version:** 1.0  
**Status:** ✅ Ready to Use  
**Date:** April 4, 2026  

