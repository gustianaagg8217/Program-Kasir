#!/usr/bin/env python3
# ============================================================================
# FIX_TERMIN_INVOICES.PY - Perbaiki invoices yang salah simpan payment_type
# ============================================================================
# Fungsi: Update invoices lama yang tidak memiliki payment_type atau salah
# ============================================================================

import sqlite3
from datetime import datetime
from database import DatabaseManager

def fix_termin_invoices():
    """
    Perbaiki semua invoices yang terkait dengan termin transactions.
    
    Workflow:
    1. Fetch semua termin transactions
    2. Untuk setiap transaction, update invoice payment_type ke 'termin'
    3. Hitung sisa hutang yang benar
    """
    
    db = DatabaseManager()
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            print("🔍 Scanning termin transactions...")
            
            # Get semua termin transactions
            cursor.execute("""
                SELECT t.id, t.transaction_number, t.total, t.bayar, t.kembalian
                FROM transactions t
                WHERE t.payment_type = 'termin'
                ORDER BY t.created_at DESC
            """)
            
            termin_trans = cursor.fetchall()
            print(f"Ditemukan {len(termin_trans)} termin transactions\n")
            
            if len(termin_trans) == 0:
                print("✅ Tidak ada termin transactions yang perlu diperbaiki")
                return
            
            # Update invoices untuk setiap termin transaction
            fixed_count = 0
            for trans_id, trans_number, total, bayar, kembalian in termin_trans:
                # Cari invoice yang terkait dengan transaction ini
                # (berdasarkan total dan waktu dibuat)
                cursor.execute("""
                    SELECT i.id, i.invoice_number, i.total, i.bayar, i.payment_type
                    FROM invoices i
                    WHERE i.total = ?
                    AND i.payment_type != 'termin'
                    ORDER BY i.created_at DESC
                    LIMIT 1
                """, (total,))
                
                invoice_row = cursor.fetchone()
                
                if invoice_row:
                    inv_id, inv_number, inv_total, inv_bayar, inv_type = invoice_row
                    
                    # Update payment_type ke 'termin'
                    sisa_hutang = total - bayar
                    
                    cursor.execute("""
                        UPDATE invoices
                        SET payment_type = 'termin', 
                            kembalian = ?
                        WHERE id = ?
                    """, (sisa_hutang, inv_id))
                    
                    fixed_count += 1
                    print(f"✅ Fixed: INV-{inv_number}")
                    print(f"   Transaction: {trans_number}")
                    print(f"   Total: Rp {total:,.0f}")
                    print(f"   DP: Rp {bayar:,.0f}")
                    print(f"   Sisa Hutang: Rp {sisa_hutang:,.0f}\n")
            
            conn.commit()
            print(f"\n🎉 Selesai! {fixed_count} invoices berhasil diperbaiki")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True


if __name__ == "__main__":
    print("=" * 70)
    print("FIX TERMIN INVOICES - Perbaiki Invoice Termin yang Salah")
    print("=" * 70)
    print()
    
    fix_termin_invoices()
