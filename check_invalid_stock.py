import sqlite3

conn = sqlite3.connect('kasir_pos.db')
cursor = conn.cursor()
cursor.execute('SELECT id, kode, nama, stok FROM products WHERE stok IS NULL OR stok <= 0')
rows = cursor.fetchall()
print(f"Found {len(rows)} products with 0 or negative stock:")
for row in rows:
    print(f"  ID: {row[0]}, Kode: {row[1]}, Nama: {row[2]}, Stok: {row[3]}")

conn.close()
