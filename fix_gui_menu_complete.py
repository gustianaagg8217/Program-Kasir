#!/usr/bin/env python3
"""
Fix gui_main.py menu items - replaces corrupted emoji section with clean code
"""

# Read the entire file
with open('gui_main.py', 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

# Find the line numbers for the menu section (around line 407-414)
start_line = None
end_line = None

for i, line in enumerate(lines):
    if '# Menu buttons' in line and 'role-based' in line:
        start_line = i
    if start_line is not None and 'for label, command, visible in menu_items:' in line:
        end_line = i
        break

if start_line is None or end_line is None:
    print("❌ Could not find menu section in gui_main.py")
    print(f"start_line={start_line}, end_line={end_line}")
    exit(1)

print(f"Found menu section: lines {start_line+1} to {end_line+1}")

# Create the new menu section (with corrected emoji and role-based visibility)
new_menu_section = '''        # Menu buttons - dengan role-based visibility
        is_admin = self.current_user['role'] == 'admin'
        menu_items = [
            ("🏠 Dashboard", self.show_dashboard, True),  # visible for all
            ("📦 Produk", self.show_products, is_admin),  # admin only
            ("📦 Stok Opname", self.show_stok_opname, is_admin),  # admin only
            ("🛒 Transaksi", self.show_transaction, True),  # visible for all
            ("📊 Laporan", self.show_reports, True),  # visible for all
            ("🤖 Telegram Bot", self.show_telegram, is_admin),  # admin only
        ]
        
        # Add Phase 4-5 features if available
        if PHASE_45_AVAILABLE and self.gui_services:
            menu_items.extend([
                ("📜 Riwayat Transaksi", self.show_transaction_history, True),
                ("📋 Restock Rekomendasi", self.show_restock_dashboard, True),
            ])
        
        # Add Settings only for admin
        if is_admin:
            menu_items.append(("⚙️ Settings", self.show_settings, True))
        
        menu_items.append(("🚪 Logout", self._logout, True))
        
        '''

# Replace the old section with new one
new_lines = lines[:start_line] + [new_menu_section] + lines[end_line:]

# Write back
with open('gui_main.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✅ Successfully fixed menu section in gui_main.py")
print(f"   - Replaced lines {start_line+1}-{end_line+1}")
print(f"   - Fixed corrupted emoji characters")
print(f"   - Updated role-based visibility:")
print(f"     * Produk: admin only")
print(f"     * Stok Opname: admin only ✅ (FIXED)")
print(f"     * Telegram Bot: admin only")
