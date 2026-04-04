#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Database initialization script for POS System setup
Called by setup.bat during installation
"""

import sys
import os

try:
    # Add current directory to path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    from database import DatabaseManager
    
    print('Initializing database...')
    db = DatabaseManager()
    print('✅ Database initialized successfully')
    
    # Show stats
    stats = db.get_database_stats()
    print(f'   Products: {stats.get("total_products", 0)}')
    print(f'   Transactions: {stats.get("total_transaksi", 0)}')
    
    print('✅ Setup complete!')
    sys.exit(0)
    
except ImportError as e:
    print(f'❌ Import Error: {e}')
    print('   Make sure database.py exists in the current directory')
    sys.exit(1)
except Exception as e:
    print(f'❌ Database error: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
