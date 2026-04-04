# Diskon & Pajak - Flow Diagram & Comparison

## Updated Transaction Flow

```
┌──────────────────────────────────────────────────────────────┐
│                    CHECKOUT PROCESS                           │
└──────────────────────────────────────────────────────────────┘

[Add Items to Cart]
        │
        ▼
   [Lihat Item]
        │
        ▼
   [Checkout] ◀─────────────────────────┐
        │                               │
        ▼                               │
   📊 Show Summary                      │
   • Total Item: 3                      │
   • Total Qty: 5                       │
   • Subtotal: Rp 500,000               │
        │                               │
        ▼                               │
   🏷️  ENTER DISCOUNT %                 │
   (State: DISKON) ◀─ NEW! ⭐           │
   Input: 10                            │
        │                               │
        ├─ Invalid? → Error + Retry ────┤
        │                               │
        ▼                               │
   💰 Apply Discount                    │
   • Discount: 10%                      │
   • Amount: Rp 50,000                  │
        │                               │
        ▼                               │
   💱 ENTER TAX %                       │
   (State: PAJAK) ◀─ NEW! ⭐           │
   Input: 10                            │
        │                               │
        ├─ Invalid? → Error + Retry ────┤
        │                               │
        ▼                               │
   💵 Apply Tax                         │
   • Tax: 10% (on discounted amount)    │
   • Amount: Rp 45,000                  │
        │                               │
        ▼                               │
   📋 SHOW BREAKDOWN                    │
   • Subtotal: Rp 500,000               │
   • Discount: -Rp 50,000               │
   • Tax: +Rp 45,000                    │
   • TOTAL: Rp 495,000                  │
        │                               │
        ▼                               │
   💳 ENTER PAYMENT                     │
   (State: PEMBAYARAN)                  │
   Input: 500,000                       │
        │                               │
        ├─ Insufficient? → Error ───────┤
        │                               │
        ▼                               │
   ✅ TRANSACTION SUCCESS               │
   • Show detailed receipt               │
   • Display change                      │
   • Clear transaction                   │
        │                               │
        ▼                               │
   [Start New Transaction] ─────────────┘
```

---

## Before vs After

### BEFORE (Old Flow)
```
Add Items → Checkout → [Direct to Payment Step]
                              ↓
                    Ask: "Berapa pembayaran?"
                              ↓
                    Enter: 500000
                              ↓
                    Calculate: Total = 500000
                              ↓
                    Receipt: Show only total
```

### AFTER (New Flow) ⭐
```
Add Items → Checkout → [Ask Discount %]
                              ↓
                        Enter: 10
                              ↓
                       [Ask Tax %]
                              ↓
                        Enter: 10
                              ↓
                    Show Complete Breakdown
                    • Subtotal: 500,000
                    • Discount: -50,000
                    • Tax: +45,000
                    • TOTAL: 495,000
                              ↓
                       [Ask Payment]
                              ↓
                        Enter: 500,000
                              ↓
         Receipt: Show all components with details
```

---

## State Diagram

### OLD States
```
5 States for Transaction:
- MAIN_MENU (0)
- TRANSAKSI_MENU (1)
- TAMBAH_ITEM_KODE (2)
- TAMBAH_ITEM_QTY (3)
- PEMBAYARAN (4) ← Directly to payment
```

### NEW States
```
7 States for Transaction:
- MAIN_MENU (0)
- TRANSAKSI_MENU (1)
- TAMBAH_ITEM_KODE (2)
- TAMBAH_ITEM_QTY (3)
- DISKON (5) ← NEW! Ask discount
- PAJAK (6) ← NEW! Ask tax
- PEMBAYARAN (4) ← After discount & tax
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      USER INPUT                              │
└─────────────────────────────────────────────────────────────┘
                    │                    │
                    ▼                    ▼
            [Discount Input]        [Tax Input]
                 10%                    10%
                    │                    │
                    ▼                    ▼
        Transaction Model    Transaction Model
        set_discount(10)      set_tax(10)
                    │                    │
                    └────────┬───────────┘
                             ▼
                  Calculate Total:
                  ╔═══════════════════════════════╗
                  ║ 1. subtotal = Rp 500,000      ║
                  ║ 2. discount = -Rp 50,000      ║
                  ║ 3. base = Rp 450,000          ║
                  ║ 4. tax = +Rp 45,000           ║
                  ║ 5. total = Rp 495,000         ║
                  ╚═══════════════════════════════╝
                             │
                             ▼
                   Transaction Summary
                   {
                     subtotal: 500000,
                     discount_percent: 10,
                     discount_amount: 50000,
                     tax_percent: 10,
                     tax_amount: 45000,
                     total: 495000
                   }
                             │
                             ▼
                    Payment Processing
                    (Compare payment vs total)
                             │
                             ▼
                    Transaction Success
                    Show Receipt with:
                    - Subtotal breakdown
                    - Discount details
                    - Tax details
                    - Final total
                    - Payment & change
```

---

## Conversation Handler Flow

```
ConversationHandler (transaksi_conv)
├─ Entry Points:
│  └─ CallbackQueryHandler("transaksi")
│
├─ States:
│  ├─ TRANSAKSI_MENU (1)
│  │  └─ transaksi_checkout() → triggers DISKON state
│  │
│  ├─ DISKON (5) ⭐ NEW
│  │  ├─ MessageHandler → handle_diskon()
│  │  ├─ Validate input (0-100)
│  │  ├─ Apply discount to transaction
│  │  └─ Transition → PAJAK state
│  │
│  ├─ PAJAK (6) ⭐ NEW
│  │  ├─ MessageHandler → handle_pajak()
│  │  ├─ Validate input (0-100)
│  │  ├─ Apply tax to transaction
│  │  ├─ Show breakdown
│  │  └─ Transition → PEMBAYARAN state
│  │
│  ├─ PEMBAYARAN (4)
│  │  ├─ MessageHandler → handle_pembayaran()
│  │  ├─ Validate payment
│  │  ├─ Complete transaction
│  │  └─ Show receipt with discount/tax
│  │
│  └─ Other states...
│
└─ Fallbacks:
   └─ /cancel → ConversationHandler.END
```

---

## Variable Storage in Context

### context.user_data Structure
```
context.user_data = {
    'current_product': {
        'kode': 'PROD001',
        'nama': 'COFFEE ARABICA',
        'harga': 25000,
        'stok': 50
    },
    
    'transaction_summary': {        ← Updated by both handle_diskon & handle_pajak
        'items_count': 3,
        'qty_total': 5,
        'total': 500000
    },
    
    'diskon_percent': 10,            ← NEW! Set in handle_diskon()
    
    'pajak_percent': 10,             ← NEW! Set in handle_pajak()
    
    'transaction_total': 495000      ← Updated to final total after tax
}
```

---

## Method Chaining

```
User Input (Discount)
        │
        ▼
handle_diskon()
        │
        ├─ Parse input
        ├─ Validate (0-100)
        ├─ trans.set_discount(percent)   ◀── Transaction Model
        │   ├─ Calculate discount_amount
        │   └─ Call calculate_total()
        ├─ Store in context
        └─ Transition to PAJAK


User Input (Tax)
        │
        ▼
handle_pajak()
        │
        ├─ Parse input
        ├─ Validate (0-100)
        ├─ trans.set_tax(percent)        ◀── Transaction Model
        │   ├─ Calculate tax_amount
        │   └─ Call calculate_total()
        ├─ Get final summary
        ├─ Store in context
        └─ Transition to PEMBAYARAN


User Input (Payment)
        │
        ▼
handle_pembayaran()
        │
        ├─ Parse payment amount
        ├─ Validate >= total
        ├─ trans_handler.complete_transaction()
        ├─ Build receipt with discount/tax
        ├─ Show message
        └─ Clear context
```

---

## Example Execution Trace

### Transaction with 10% Discount, 10% Tax

```
STEP 1: Checkout
  Items: 3
  Subtotal: Rp 500,000
  → Transition to DISKON state
  → Show: "Masukkan Diskon %"

STEP 2: Discount Input
  User enters: "10"
  handle_diskon():
    ├─ diskon_percent = 10
    ├─ trans.set_discount(10)
    │   ├─ discount_amount = 500,000 × 0.10 = Rp 50,000
    │   ├─ calculate_total()
    │   └─ total = 500,000 - 50,000 = Rp 450,000
    ├─ Store diskon_percent = 10 in context
    └─ → Transition to PAJAK state
  → Show: "Diskon Diterapkan, Masukkan Pajak %"

STEP 3: Tax Input
  User enters: "10"
  handle_pajak():
    ├─ pajak_percent = 10
    ├─ trans.set_tax(10)
    │   ├─ base = 500,000 - 50,000 = Rp 450,000
    │   ├─ tax_amount = 450,000 × 0.10 = Rp 45,000
    │   ├─ calculate_total()
    │   └─ total = 450,000 + 45,000 = Rp 495,000
    ├─ Store pajak_percent = 10 in context
    ├─ Store transaction_total = 495,000
    └─ → Transition to PEMBAYARAN state
  → Show: "Subtotal: 500k, Diskon: -50k, Pajak: +45k, Total: 495k"

STEP 4: Payment Input
  User enters: "500000"
  handle_pembayaran():
    ├─ bayar = 500,000
    ├─ total = 495,000
    ├─ Validate: 500,000 >= 495,000 ✅
    ├─ complete_transaction(500000)
    ├─ kembalian = 500,000 - 495,000 = Rp 5,000
    ├─ Build receipt:
    │   ├─ subtotal = 500,000
    │   ├─ diskon = -50,000 (10%)
    │   ├─ pajak = +45,000 (10%)
    │   ├─ total = 495,000
    │   ├─ bayar = 500,000
    │   └─ kembalian = 5,000
    └─ → ConversationHandler.END
  → Show success receipt with breakdown
  → Clear transaction from context
```

---

## Comparison Matrix

| Feature | Before | After |
|---------|--------|-------|
| **Ask Discount** | ❌ No | ✅ Yes |
| **Ask Tax** | ❌ No | ✅ Yes |
| **Automatic Calculation** | ❌ Manual | ✅ Automatic |
| **Discount Amount Shown** | ❌ No | ✅ Yes (Rp) |
| **Tax Amount Shown** | ❌ No | ✅ Yes (Rp) |
| **Breakdown in Receipt** | ❌ Single line | ✅ 4-line detailed |
| **States in Transaction** | 5 | 7 |
| **User Steps** | 2 (add items, pay) | 4 (add items, diskon, tax, pay) |
| **Calculation Accuracy** | 🟡 Manual error risk | ✅ 100% automatic |
| **Audit Trail** | ❌ No discount info | ✅ All logged |

---

## Code Statistics

| Metric | Count |
|--------|-------|
| New states added | 2 (DISKON, PAJAK) |
| New methods added | 2 (handle_diskon, handle_pajak) |
| Methods modified | 2 (transaksi_checkout, handle_pembayaran) |
| Lines of code added | ~150 |
| Documentation lines | 200+ |

---

**Implementation Date:** April 4, 2026  
**Status:** ✅ Complete  
**Syntax Check:** ✅ Passed  

