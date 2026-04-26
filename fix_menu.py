#!/usr/bin/env python3
# Quick fix script for menu items

with open('gui_main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace Stok Opname True with is_admin
content = content.replace(
    '("📦 Stok Opname", self.show_stok_opname, True),',
    '("📦 Stok Opname", self.show_stok_opname, is_admin),  # admin only'
)

with open('gui_main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Successfully updated Stok Opname menu item to use is_admin")
