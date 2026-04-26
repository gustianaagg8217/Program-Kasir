#!/usr/bin/env python3
import re

# Read the file
with open('gui_main.py', 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

# Find and replace the Stok Opname line - match by pattern
# Pattern: any emoji + " Stok Opname" + True
pattern = r'(\(".\s*Stok Opname",\s*self\.show_stok_opname,\s*)True(\s*\))'
replacement = r'\1is_admin\2  # admin only'

content_new = re.sub(pattern, replacement, content)

if content_new != content:
    with open('gui_main.py', 'w', encoding='utf-8') as f:
        f.write(content_new)
    print("✅ Successfully updated Stok Opname menu item to use is_admin")
else:
    print("❌ No changes made - pattern not found")
    # Try to find what we have
    lines = content.split('\n')
    for i, line in enumerate(lines[405:420], 406):
        if 'Stok Opname' in line:
            print(f"Line {i}: {repr(line)}")
