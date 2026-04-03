"""
Test LoginWindow specifically to ensure it displays properly
"""

import tkinter as tk
from tkinter import ttk
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Testing LoginWindow display...")
print("=" * 80)

try:
    print("[1/5] Importing database...")
    from database import DatabaseManager
    db = DatabaseManager()
    print("      [OK] Database imported")
    
    print("[2/5] Importing gui_main...")
    from gui_main import LoginWindow, FONTS, COLORS
    print("      [OK] gui_main imported")
    
    print("[3/5] Creating root window...")
    root = tk.Tk()
    root.withdraw()  # Hide root temporarily
    print("      [OK] Root window created and hidden")
    
    print("[4/5] Creating LoginWindow...")
    print("      [INFO] LoginWindow should appear NOW on screen")
    print("      [INFO] Login with: admin / admin123")
    print("      [INFO] Or close the window to exit test")
    print("-" * 80)
    
    login_window = LoginWindow(root, db)
    
    print("[5/5] Starting event loop...")
    root.wait_window(login_window)
    
    # Get user result
    user = login_window.get_user()
    
    if user:
        print("-" * 80)
        print(f"\n[SUCCESS] Login successful!")
        print(f"User: {user['username']}")
        print(f"Role: {user['role']}")
    else:
        print("-" * 80)
        print(f"\n[INFO] Login cancelled or window closed")
    
    root.destroy()
    print("\n[SUCCESS] LoginWindow test completed - WINDOW DISPLAY WORKS!")
    
except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
