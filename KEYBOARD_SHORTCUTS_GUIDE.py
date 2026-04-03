"""
KEYBOARD SHORTCUTS - Quick Reference & Testing Guide
For faster POS cashier operation
"""

SHORTCUTS = """
╔════════════════════════════════════════════════════════════════════════════╗
║                         KEYBOARD SHORTCUTS                                ║
╚════════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────┐
│ KEY        │ ACTION                    │ CONDITION                     │
├─────────────────────────────────────────────────────────────────────────┤
│ Enter      │ Add selected product      │ On Transaction page with      │
│            │ to cart                   │ product selected              │
│            │                           │                               │
│ F1         │ Start new transaction     │ Works from any page           │
│            │ (show Transaction page)   │                               │
│            │                           │                               │
│ F2         │ Process payment           │ On Transaction page with      │
│            │ (complete transaction)    │ items in cart                 │
│            │                           │                               │
│ Escape     │ Cancel transaction        │ On Transaction page           │
│            │ (clear cart & start over) │                               │
└─────────────────────────────────────────────────────────────────────────┘
"""

USAGE_FLOW = """
╔════════════════════════════════════════════════════════════════════════════╗
║                        TYPICAL CASHIER WORKFLOW                            ║
╚════════════════════════════════════════════════════════════════════════════╝

SCENARIO 1: Quick Transaction (Without Shortcuts)
──────────────────────────────────────────────────
1. User clicks "Transaksi" button
2. Types product code/name
3. Clicks "Tambah Item" button
4. Repeats for each item
5. Enters payment amount  
6. Clicks "Proses Pembayaran"
7. Prints receipt

└─ Requires: Multiple mouse clicks (5-10 per transaction)


SCENARIO 2: Fast Transaction (With Shortcuts)
──────────────────────────────────────────────
1. Press F1 → Opens Transaction page instantly
2. Type "COFFEE"
3. Press Enter → Item added ⚡
4. Type "TEA"
5. Press Enter → Item added ⚡
6. Enter payment amount
7. Press F2 → Payment processed ⚡
8. Prints receipt

└─ Benefit: Fewer mouse clicks, faster workflow, higher throughput


SCENARIO 3: Cancel & Retry
──────────────────────────
1. Added items to cart
2. Realized wrong items selected
3. Press Escape → Cart cleared instantly ⚡
4. F1 → Fresh transaction
5. Continue as normal

└─ Benefit: Undo actions instantly without clicking
"""

DETAILED_USAGE = """
╔════════════════════════════════════════════════════════════════════════════╗
║                       DETAILED USAGE GUIDE                                ║
╚════════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────┐
│ Enter Key - Add Item                                                    │
├─────────────────────────────────────────────────────────────────────────┤
│
│ Prerequisites:
│   • Must be on Transaction page
│   • Product must be selected in search field or listbox
│
│ Usage Steps:
│   1. Type product code or name in "Cari Produk" field
│   2. Product list filters automatically
│   3. Click product or press Down arrow to select
│   4. Press Enter
│   5. ✅ Product added to cart instantly
│
│ Example Workflow:
│   Type: "CO" → Listbox shows "COFFEE - Kopi Hitam"
│   Press: Down ↓ → Selects "COFFEE - Kopi Hitam"
│   Press: Enter → ✅ Added! Qty=1 in cart
│
│ Note: If item is already selected, pressing Enter multiple times
│       will add multiple quantities
│
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ F1 Key - New Transaction                                                │
├─────────────────────────────────────────────────────────────────────────┤
│
│ Functionality:
│   • Opens/shows Transaction page
│   • Clears previous search field
│   • Starts fresh transaction
│   • Sets focus to search field
│
│ Keyboard Accessibility:
│   • Press F1 from ANY page (Dashboard, Products, Reports, etc.)
│   • No need to click the sidebar button
│   • Instant navigation
│
│ Usage Examples:
│   Dashboard + F1 → Jump to Transaction page
│   Reports + F1 → Quickly switch transactions
│   Payment processing + F1 → Start new transaction after completion
│
│ Benefit: Fastest way to reach transaction page
│          Great for high-frequency operations
│
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ F2 Key - Process Payment                                                │
├─────────────────────────────────────────────────────────────────────────┤
│
│ Prerequisites:
│   • Must be on Transaction page
│   • Cart must have items
│   • Payment amount must be entered
│
│ Workflow:
│   1. Add all items to cart using Enter key or mouse
│   2. Enter payment amount in "Jumlah Pembayaran" field
│   3. Press F2
│   4. ✅ Payment processed instantly
│   5. Receipt dialog appears
│   6. Select print or skip
│
│ Example:
│   Cart items: 2 items, Total: Rp 50,000
│   Payment field: 50000
│   Press: F2 → ✅ Transaksi berhasil!
│           → Receipt dialog shown
│           → New transaction ready
│
│ Benefit: No mouse clicking needed to complete payment
│          Faster completion for high-volume transactions
│
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ Escape Key - Cancel Transaction                                         │
├─────────────────────────────────────────────────────────────────────────┤
│
│ Functionality:
│   • Clears all items from cart
│   • Resets discount/tax fields to 0%
│   • Clears payment amount field
│   • Clears product search field
│   • Shows confirmation dialog
│
│ Usage Scenarios:
│   Scenario 1: Wrong Items Added
│     → Customer says "Wait, wrong items!"
│     → Press Escape
│     → Cart cleared, start fresh
│
│   Scenario 2: Customer Changes Mind
│     → Halfway through transaction
│     → Press Escape to cancel
│     → Confirmation dialog prevents accidental cancel
│
│   Scenario 3: System Error or Mistake
│     → Need to restart transaction
│     → Press Escape
│     → Instant undo
│
│ Safety Feature:
│   Pressing Escape shows confirmation dialog:
│   "Batalkan transaksi?"
│   → Yes = Clear cart & reset
│   → No = Continue with current transaction
│
│ Benefit: Instant undo without looking for buttons
│          Prevents data loss with confirmation
│
└─────────────────────────────────────────────────────────────────────────┘
"""

PERFORMANCE_TIPS = """
╔════════════════════════════════════════════════════════════════════════════╗
║                  PERFORMANCE TIPS FOR CASHIERS                             ║
╚════════════════════════════════════════════════════════════════════════════╝

🚀 SPEED OPTIMIZATION:

1. Use F1 to Open Transaction Page
   • Faster than clicking sidebar button
   • Works from anywhere in app
   • Direct keyboard shortcut = faster access

2. Use Enter Key for Adding Items
   • No mouse movement to "Tambah Item" button
   • Just type product name/code and press Enter
   • Average: 0.5 sec → Instant

3. Use F2 for Payment Processing  
   • No need to move mouse to "Proses Pembayaran" button
   • Already have payment amount entered
   • One key press = completed payment

4. Use Escape to Undo Mistakes
   • Instant undo if wrong items selected
   • Faster than clicking "Batalkan" button
   • Confirmation prevents accidental presses

💡 RECOMMENDED WORKFLOW FOR HIGH VOLUME:

1. Start of Shift:
   • F1 → Ready for first transaction

2. For Each Customer:
   • Type product code (e.g., "COFFEE")
   • Enter key → Add to cart
   • Repeat for each item
   • Enter payment amount
   • F2 → Process payment
   • Confirm print & repeat

3. Multi-Item Transaction (3 items):
   • Previous method: ~15-20 clicks
   • With shortcuts: ~3 Enter presses + 1 F2 = ~4 key presses
   • Reduction: 75-80% fewer actions!

4. Cancellation Handling:
   • Old way: Click "Batalkan" button
   • New way: Press Escape
   • Time saved: 2-3 seconds per transaction

📊 EFFICIENCY METRICS:

Transaction Without Shortcuts:
├─ Click "Transaksi" button: 1 click
├─ Type first product: 1 action
├─ Click "Tambah Item": 1 click
├─ Repeat ×N items: N × 2 clicks = 2N clicks
├─ Click payment field: 1 click
├─ Type payment: 1 action
├─ Click "Proses Pembayaran": 1 click
└─ Total: 3 + 2N clicks + 2 type actions

Transaction With Shortcuts:
├─ Press F1: 1 key press
├─ Type first product: 1 action
├─ Press Enter: 1 key press
├─ Repeat ×N items: N × 2 key presses = 2N key presses
├─ Type payment (in field): 1 action
├─ Press F2: 1 key press
└─ Total: 2 + 2N key presses + 2 type actions

SAVINGS: ~50% reduction in manual input for N≥2 items
TIME SAVED: ~2-5 seconds per transaction
MULTIPLIER: 100 transactions/day × 3 sec = 5+ minutes saved daily!
"""

TROUBLESHOOTING = """
╔════════════════════════════════════════════════════════════════════════════╗
║                    KEYBOARD SHORTCUTS TROUBLESHOOTING                      ║
╚════════════════════════════════════════════════════════════════════════════╝

ISSUE: Enter key not adding items
───────────────────────────────────
Solution:
  1. Make sure you're on Transaction page (not Dashboard/Products/Reports)
  2. Make sure you've selected a product from the listbox
  3. Check if product_search field has product code/name
  4. Try clicking "Tambah Item" button to verify
  → If button works, may need to restart app

ISSUE: F1 not opening Transaction page
──────────────────────────────────────
Solution:
  1. F1 is system global in application
  2. Verify app window has focus (not minimized)
  3. Try clicking any app area first, then F1
  4. Check if F1 is bound to another app (some games/apps override)
  → Restart POS application

ISSUE: F2 not processing payment
────────────────────────────────
Solution:
  1. Must be on Transaction page
  2. Cart must have items (at least 1 product)
  3. Payment amount must be entered
  4. Payment amount must be ≥ total amount
  → Check cart has items, check payment field filled

ISSUE: Escape key not canceling
───────────────────────────────
Solution:
  1. Escape must be executed on Transaction page
  2. Confirmation dialog appears - must click "Ya" to confirm
  3. If no dialog shows, try clicking in transaction area first
  → Click somewhere in transaction page, then press Escape

ISSUE: Shortcuts work sometimes, not always
────────────────────────────────────────────
Solution:
  1. Keyboard focus might be in text field
  2. Some field might be intercepting the keys
  3. Try clicking main application area first
  4. Restart application if issue persists
  → Tested with focus on search field, should work

SOLUTION: Restart Application
──────────────────────────────
If shortcuts stop working:
  1. Close POS application completely
  2. Wait 2 seconds
  3. Re-open application with: python gui_main.py
  4. Try shortcut again
  → Check pos.log for any error messages
"""

LOGGING_INFO = """
╔════════════════════════════════════════════════════════════════════════════╗
║                    SHORTCUTS IN LOG FILES                                 ║
╚════════════════════════════════════════════════════════════════════════════╝

All keyboard shortcut actions are logged to pos.log:

INITIALIZATION:
2026-04-03 10:15:22 - INFO - __main__ - Keyboard shortcuts registered:
2026-04-03 10:15:22 - INFO - __main__   - Enter → Add item
2026-04-03 10:15:22 - INFO - __main__   - F1 → New transaction
2026-04-03 10:15:22 - INFO - __main__   - F2 → Process payment
2026-04-03 10:15:22 - INFO - __main__   - Escape → Cancel transaction

USAGE (when keys are pressed):
2026-04-03 10:15:45 - INFO - __main__ - Product search: 'coffee' - Found 1 products
2026-04-03 10:15:46 - INFO - __main__ - Product selected: COFFEE - Kopi Hitam
[Enter key pressed → Item added]
2026-04-03 10:15:47 - INFO - __main__ - Discount updated: 0%
[F2 key pressed → Payment processed]
2026-04-03 10:15:50 - INFO - __main__ - User admin logged out

Use logs to:
- Verify shortcuts are working
- Track usage patterns
- Debug issues with specific key presses
- Audit high-frequency operations
"""

if __name__ == "__main__":
    print(SHORTCUTS)
    print("\n" + "="*80 + "\n")
    print(USAGE_FLOW)
    print("\n" + "="*80 + "\n")
    print(DETAILED_USAGE)
    print("\n" + "="*80 + "\n")
    print(PERFORMANCE_TIPS)
    print("\n" + "="*80 + "\n")
    print(TROUBLESHOOTING)
    print("\n" + "="*80 + "\n")
    print(LOGGING_INFO)
