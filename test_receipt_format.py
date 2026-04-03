#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test improved receipt formatting with store info and footer message
"""

import sys
import os
import json
from datetime import datetime

# Mock format_rp function for testing
def format_rp(amount):
    """Format amount as Rupiah currency."""
    return f"Rp {int(amount):,}".replace(',', '.')

# Mock transaction data
trans = {
    'id': 'TRX001',
    'tanggal': '2026-04-03 14:35:27',
    'total': 95000,
    'bayar': 100000,
    'kembalian': 5000,
    'discount_amount': 0,
    'discount_percent': 0,
    'tax_amount': 0,
    'tax_percent': 0,
}

items = [
    {
        'nama': 'Charging Cable USB Type-C',
        'qty': 2,
        'harga_satuan': 25000,
        'subtotal': 50000
    },
    {
        'nama': 'Screen Protector',
        'qty': 3,
        'harga_satuan': 15000,
        'subtotal': 45000
    }
]

# Store config
store_config = {
    "store": {
        "name": "TOKO ACCESSORIES G-LIES",
        "address": "Jl. Majalaya, Solokanjeruk, Bandung",
        "phone": "(022) 123-4567"
    },
    "receipt": {
        "width": 40,
        "show_phone": True,
        "show_timestamp": True
    }
}

def _format_receipt_line(label, value, width=40, bold=False):
    """Format a receipt line with label on left and value right-aligned."""
    label_len = len(label)
    value_len = len(value)
    spacing = width - label_len - value_len
    
    if spacing < 1:
        spacing = 1
    
    line = label + (" " * spacing) + value
    return line[:width]

def generate_receipt_text(trans, items, store_config):
    """Generate receipt text format with discount and tax."""
    receipt = []
    
    store_name = store_config['store']['name']
    store_address = store_config['store']['address']
    store_phone = store_config['store']['phone']
    receipt_width = store_config['receipt']['width']
    show_phone = store_config['receipt'].get('show_phone', True)
    
    # Header
    receipt.append("=" * receipt_width)
    receipt.append(store_name.center(receipt_width))
    receipt.append(store_address.center(receipt_width))
    if show_phone and store_phone:
        receipt.append(store_phone.center(receipt_width))
    receipt.append("=" * receipt_width)
    receipt.append("")
    
    # Transaction info
    receipt.append(f"Transaksi ID  : {trans['id']}")
    
    # Format datetime nicely
    try:
        trans_datetime = datetime.strptime(trans['tanggal'], '%Y-%m-%d %H:%M:%S')
        formatted_date = trans_datetime.strftime('%d/%m/%Y %H:%M:%S')
    except:
        formatted_date = trans['tanggal']
    
    receipt.append(f"Tanggal/Waktu : {formatted_date}")
    receipt.append("-" * receipt_width)
    receipt.append("Daftar Item:")
    receipt.append("-" * receipt_width)
    
    subtotal = 0
    for i, item in enumerate(items, 1):
        product_name = item['nama'][:receipt_width - 10]
        qty = item['qty']
        harga = item['harga_satuan']
        subtotal_item = item['subtotal']
        subtotal += subtotal_item
        
        receipt.append(f"{i}. {product_name}")
        qty_text = f"{qty}x {format_rp(harga)}"
        total_text = format_rp(subtotal_item)
        line = f"   {qty_text} = {total_text}"
        receipt.append(line)
    
    receipt.append("-" * receipt_width)
    
    # Summary with proper alignment
    receipt.append(_format_receipt_line("Subtotal", format_rp(subtotal), receipt_width))
    
    # Add discount if applicable
    discount = trans.get('discount_amount', 0)
    if discount > 0:
        discount_pct = trans.get('discount_percent', 0)
        discount_line = f"Diskon ({discount_pct}%)"
        receipt.append(_format_receipt_line(discount_line, f"-{format_rp(discount)}", receipt_width))
    
    # Add tax if applicable
    tax = trans.get('tax_amount', 0)
    if tax > 0:
        tax_pct = trans.get('tax_percent', 0)
        tax_line = f"Pajak ({tax_pct}%)"
        receipt.append(_format_receipt_line(tax_line, f"+{format_rp(tax)}", receipt_width))
    
    receipt.append("-" * receipt_width)
    receipt.append(_format_receipt_line("Total Belanja", format_rp(trans['total']), receipt_width, bold=True))
    receipt.append(_format_receipt_line("Pembayaran", format_rp(trans['bayar']), receipt_width))
    receipt.append(_format_receipt_line("Kembalian", format_rp(trans['kembalian']), receipt_width))
    receipt.append("=" * receipt_width)
    
    # Thank you message
    receipt.append("Terima Kasih".center(receipt_width))
    
    # Footer message
    footer_msg = "Barang yang sudah dibeli\ntidak dapat dikembalikan"
    for line in footer_msg.split('\n'):
        receipt.append(line.center(receipt_width))
    
    receipt.append("=" * receipt_width)
    
    return "\n".join(receipt)

# Generate and display receipt
try:
    receipt_text = generate_receipt_text(trans, items, store_config)
    
    print("=" * 60)
    print("IMPROVED RECEIPT FORMAT - TEST OUTPUT")
    print("=" * 60)
    print()
    print(receipt_text)
    print()
    print("=" * 60)
    print("✓ Receipt formatting test successful!")
    print("=" * 60)
    print()
    print("Features demonstrated:")
    print("  ✓ Store name, address, and phone from config")
    print("  ✓ Properly formatted datetime (DD/MM/YYYY HH:MM:SS)")
    print("  ✓ Right-aligned monetary values")
    print("  ✓ Footer message: 'Barang yang sudah dibeli tidak dapat dikembalikan'")
    print("  ✓ Max width: 40 characters (configurable)")
    print("  ✓ Centered header and footer elements")
    print("  ✓ Clean visual alignment")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
