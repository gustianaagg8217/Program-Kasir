"""
Simple diagnostic tool to test if GUI window displays properly
"""

import tkinter as tk
from tkinter import ttk
import time

print("Testing simple Tkinter window display...")
print("=" * 80)

try:
    print("[1/3] Creating root window...")
    root = tk.Tk()
    root.title("Test Window")
    root.geometry("300x150")
    
    # Center on screen
    root.update_idletasks()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width // 2) - 150
    y = (screen_height // 2) - 75
    root.geometry(f"+{x}+{y}")
    
    # Add simple label
    label = ttk.Label(root, text="TEST: If you see this, GUI works!")
    label.pack(pady=20)
    
    # Simple button
    def on_close():
        print("[SUCCESS] Window closed properly - GUI WORKS!")
        root.destroy()
    
    btn = ttk.Button(root, text="Close Test", command=on_close)
    btn.pack(pady=10)
    
    print("      [OK] Root window created")
    
    print("[2/3] Bringing window to focus...")
    root.lift()
    root.focus_set()
    root.attributes('-topmost', True)
    root.attributes('-topmost', False)
    print("      [OK] Window focus set")
    
    print("[3/3] Starting event loop...")
    print("      [INFO] Window should appear now on screen")
    print("      [INFO] Close the window to complete test")
    print("=" * 80)
    
    # Run for max 10 seconds (auto-close if not interacted)
    root.after(10000, root.destroy)
    root.mainloop()
    
    print("\n[SUCCESS] Test completed - GUI display OK")
    
except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()
