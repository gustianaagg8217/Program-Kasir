#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Python environment verification script for POS System setup
Called by setup.bat to verify all required modules
"""

import sys

print('Python version:', sys.version.split()[0])
print()

# Test built-in modules
modules_builtin = {
    'sqlite3': 'Database support',
    'json': 'JSON parsing',
    'csv': 'CSV file handling',
}

print('Built-in modules:')
for module_name, description in modules_builtin.items():
    try:
        __import__(module_name)
        print(f'  ✅ {module_name:<20} - {description}')
    except ImportError:
        print(f'  ❌ {module_name:<20} - {description}')

print()
print('Optional modules (for extended features):')

# Test optional modules
modules_optional = {
    'telegram': 'Telegram bot notifications',
    'requests': 'HTTP requests',
}

for module_name, description in modules_optional.items():
    try:
        __import__(module_name)
        print(f'  ✅ {module_name:<20} - {description}')
    except ImportError:
        print(f'  ⚠️  {module_name:<20} - {description}')

print()
print('Verification complete!')
