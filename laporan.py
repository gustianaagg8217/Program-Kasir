# ============================================================================
# LAPORAN.PY - Sistem Laporan & Export CSV
# ============================================================================
# Fungsi: Generate laporan penjualan dengan berbagai filter dan statistik
# Export ke CSV untuk analisis lanjutan
# ============================================================================

import csv
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from database import DatabaseManager
from models import format_rp

# ============================================================================
# REPORT GENERATOR - Generate berbagai jenis laporan
# ============================================================================

class ReportGenerator:
    """
    Generate berbagai jenis laporan dari data transaksi.
    
    Laporan yang bisa dibuat:
    - Laporan penjualan harian
    - Laporan penjualan periode
    - Laporan produk terlaris
    - Laporan stok produk
    - Laporan summary dashboard
    
    Attributes:
        db (DatabaseManager): Database instance
        
    Methods:
        get_laporan_harian(): Laporan harian
        get_laporan_periode(): Laporan range tanggal
        get_produk_terlaris(): Top selling products
        get_stok_summary(): Product stock summary
    """
    
    def __init__(self, db: DatabaseManager):
        """
        Inisialisasi ReportGenerator.
        
        Args:
            db (DatabaseManager): Database instance
        """
        self.db = db
    
    # ========================================================================
    # LAPORAN PENJUALAN HARIAN
    # ========================================================================
    
    def get_laporan_harian(self, date_str: str = None) -> Dict:
        """
        Ambil laporan penjualan untuk satu hari.
        
        Args:
            date_str (str): Format 'YYYY-MM-DD' (default: hari ini)
            
        Returns:
            Dict:
            {
                'tanggal': str,
                'total_penjualan': int,
                'total_transaksi': int,
                'rata_rata_transaksi': float,
                'total_item': int,
                'rata_rata_item_per_transaksi': float,
                'produk_laris': List[Dict],
                'transactions': List[Dict]
            }
        """
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        report = self.db.get_laporan_harian(date_str)
        
        # Hitung rata-rata
        total_transaksi = report['total_transaksi']
        total_item = sum(len(self.db.get_transaction(t['id'])['items']) 
                        for t in report['transactions'])
        
        return {
            'tanggal': date_str,
            'total_penjualan': report['total_penjualan'],
            'total_transaksi': total_transaksi,
            'rata_rata_transaksi': (report['total_penjualan'] / total_transaksi 
                                   if total_transaksi > 0 else 0),
            'total_item': total_item,
            'rata_rata_item_per_transaksi': (total_item / total_transaksi 
                                             if total_transaksi > 0 else 0),
            'produk_laris': report['produk_laris'],
            'transactions': report['transactions']
        }
    
    def get_laporan_periode(self, start_date: str, end_date: str) -> Dict:
        """
        Ambil laporan penjualan untuk range tanggal tertentu.
        
        Args:
            start_date (str): Format 'YYYY-MM-DD'
            end_date (str): Format 'YYYY-MM-DD'
            
        Returns:
            Dict:
            {
                'start_date': str,
                'end_date': str,
                'total_hari': int,
                'total_penjualan': int,
                'total_transaksi': int,
                'rata_rata_penjualan_per_hari': float,
                'hari_dengan_penjualan': int,
                'harian_breakdown': List[Dict]
            }
        """
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            print("❌ Format tanggal salah (gunakan YYYY-MM-DD)")
            return None
        
        # Generate tanggal untuk setiap hari
        harian_breakdown = []
        current = start
        
        total_penjualan = 0
        total_transaksi = 0
        hari_dengan_penjualan = 0
        
        while current <= end:
            date_str = current.strftime('%Y-%m-%d')
            trans = self.db.get_transactions_by_date(date_str)
            
            if len(trans) > 0:
                day_total = sum(t['total'] for t in trans)
                total_penjualan += day_total
                total_transaksi += len(trans)
                hari_dengan_penjualan += 1
                
                harian_breakdown.append({
                    'tanggal': date_str,
                    'total': day_total,
                    'transaksi': len(trans)
                })
            
            current += timedelta(days=1)
        
        total_hari = (end - start).days + 1
        
        return {
            'start_date': start_date,
            'end_date': end_date,
            'total_hari': total_hari,
            'total_penjualan': total_penjualan,
            'total_transaksi': total_transaksi,
            'rata_rata_penjualan_per_hari': (total_penjualan / total_hari 
                                             if total_hari > 0 else 0),
            'hari_dengan_penjualan': hari_dengan_penjualan,
            'harian_breakdown': harian_breakdown
        }
    
    def get_produk_terlaris(self, limit: int = 10, date_str: str = None) -> List[Dict]:
        """
        Ambil daftar produk paling laris.
        
        Args:
            limit (int): Jumlah top produk (default: 10)
            date_str (str): Jika diberikan, filter hanya untuk hari tersebut
            
        Returns:
            List[Dict]: List produk dengan struktur:
            [
                {
                    'nama': str,
                    'total_qty': int,
                    'total_revenue': int,
                    'rank': int
                }
            ]
        """
        if date_str:
            # Filter by date
            transactions = self.db.get_transactions_by_date(date_str)
            if not transactions:
                return []
            
            produk_map = {}
            for trans in transactions:
                trans_full = self.db.get_transaction(trans['id'])
                if trans_full:
                    for item in trans_full['items']:
                        product_name = item['nama']
                        if product_name not in produk_map:
                            produk_map[product_name] = {
                                'nama': product_name,
                                'total_qty': 0,
                                'total_revenue': 0
                            }
                        produk_map[product_name]['total_qty'] += item['qty']
                        produk_map[product_name]['total_revenue'] += item['subtotal']
            
            produk_list = sorted(produk_map.values(), 
                                key=lambda x: x['total_qty'], 
                                reverse=True)[:limit]
        else:
            # All time
            produk_list = self.db.get_produk_paling_laris(limit)
        
        # Add ranking
        for i, produk in enumerate(produk_list, 1):
            produk['rank'] = i
        
        return produk_list
    
    def get_stok_summary(self) -> List[Dict]:
        """
        Ambil summary stok semua produk.
        
        Returns:
            List[Dict]: List produk dengan struktur:
            [
                {
                    'kode': str,
                    'nama': str,
                    'harga': int,
                    'stok': int,
                    'status': 'OK' | 'LOW' | 'EMPTY'
                }
            ]
            
        Status: 
            - OK: stok > 20
            - LOW: stok 1-20
            - EMPTY: stok 0
        """
        products = self.db.get_all_products()
        
        summary = []
        for prod in products:
            if prod['stok'] == 0:
                status = '🔴 KOSONG'
            elif prod['stok'] <= 20:
                status = '🟡 MINIM'
            else:
                status = '🟢 OK'
            
            summary.append({
                'kode': prod['kode'],
                'nama': prod['nama'],
                'harga': prod['harga'],
                'stok': prod['stok'],
                'status': status
            })
        
        return sorted(summary, key=lambda x: x['stok'])
    
    def get_dashboard_summary(self) -> Dict:
        """
        Ambil summary untuk dashboard (ringkasan lengkap).
        
        Returns:
            Dict:
            {
                'hari_ini': {
                    'total_penjualan': int,
                    'total_transaksi': int,
                    'rata_rata': float
                },
                'produk_terlaris': List[Dict],
                'stok_minim': List[Dict],
                'total_produk': int,
                'total_stok': int
            }
        """
        # Laporan hari ini
        laporan_hari_ini = self.get_laporan_harian()
        
        # Produk terlaris hari ini
        produk_terlaris = self.get_produk_terlaris(limit=5, 
                                                   date_str=datetime.now().strftime('%Y-%m-%d'))
        
        # Stok produk
        stok_summary = self.get_stok_summary()
        stok_minim = [p for p in stok_summary if p['stok'] <= 20]
        
        # Total produk & stok
        products = self.db.get_all_products()
        total_produk = len(products)
        total_stok = sum(p['stok'] for p in products)
        
        return {
            'hari_ini': {
                'total_penjualan': laporan_hari_ini['total_penjualan'],
                'total_transaksi': laporan_hari_ini['total_transaksi'],
                'rata_rata': laporan_hari_ini['rata_rata_transaksi']
            },
            'produk_terlaris': produk_terlaris,
            'stok_minim': stok_minim,
            'total_produk': total_produk,
            'total_stok': total_stok
        }

# ============================================================================
# REPORT FORMATTER - Format laporan dengan rapi untuk display
# ============================================================================

class ReportFormatter:
    """
    Format laporan untuk ditampilkan di terminal/console dengan rapi.
    
    Methods:
        format_laporan_harian(): Format laporan harian
        format_laporan_periode(): Format laporan periode
        format_produk_terlaris(): Format list produk
        format_stok_summary(): Format stok summary
        format_dashboard(): Format dashboard
    """
    
    @staticmethod
    def format_laporan_harian(laporan: Dict) -> str:
        """
        Format laporan harian menjadi string yang siap display.
        
        Args:
            laporan (Dict): Hasil dari get_laporan_harian()
            
        Returns:
            str: Formatted report
        """
        lines = []
        lines.append("=" * 70)
        lines.append(f"LAPORAN PENJUALAN HARIAN - {laporan['tanggal']}")
        lines.append("=" * 70)
        
        lines.append("\n📊 RINGKASAN:")
        lines.append(f"  Total Penjualan       : {format_rp(laporan['total_penjualan'])}")
        lines.append(f"  Total Transaksi       : {laporan['total_transaksi']} transaksi")
        lines.append(f"  Rata-rata Transaksi   : {format_rp(int(laporan['rata_rata_transaksi']))}")
        lines.append(f"  Total Item Terjual    : {laporan['total_item']} item")
        lines.append(f"  Rata-rata Item/Trans  : {laporan['rata_rata_item_per_transaksi']:.1f}")
        
        # Produk laris
        if laporan['produk_laris']:
            lines.append("\n🏆 PRODUK TERLARIS:")
            for i, prod in enumerate(laporan['produk_laris'], 1):
                lines.append(f"  {i}. {prod['nama']:<20} | {prod['total_qty']:>3} qty | "
                            f"{format_rp(prod['total_revenue'])}")
        
        lines.append("\n" + "=" * 70)
        return "\n".join(lines)
    
    @staticmethod
    def format_laporan_periode(laporan: Dict) -> str:
        """
        Format laporan periode.
        
        Args:
            laporan (Dict): Hasil dari get_laporan_periode()
            
        Returns:
            str: Formatted report
        """
        lines = []
        lines.append("=" * 70)
        lines.append(f"LAPORAN PENJUALAN PERIODE")
        lines.append(f"{laporan['start_date']} s/d {laporan['end_date']}")
        lines.append("=" * 70)
        
        lines.append("\n📊 RINGKASAN:")
        lines.append(f"  Periode               : {laporan['total_hari']} hari")
        lines.append(f"  Total Penjualan       : {format_rp(laporan['total_penjualan'])}")
        lines.append(f"  Total Transaksi       : {laporan['total_transaksi']} transaksi")
        lines.append(f"  Rata-rata/Hari       : {format_rp(int(laporan['rata_rata_penjualan_per_hari']))}")
        lines.append(f"  Hari Beroperasi       : {laporan['hari_dengan_penjualan']} hari")
        
        # Breakdown harian
        if laporan['harian_breakdown']:
            lines.append("\n📅 BREAKDOWN HARIAN:")
            lines.append("  Tanggal         | Penjualan       | Transaksi")
            lines.append("  " + "-" * 50)
            for day in laporan['harian_breakdown']:
                lines.append(f"  {day['tanggal']} | {format_rp(day['total']):<15} | "
                            f"{day['transaksi']} transaksi")
        
        lines.append("\n" + "=" * 70)
        return "\n".join(lines)
    
    @staticmethod
    def format_produk_terlaris(produk_list: List[Dict], title: str = "PRODUK TERLARIS") -> str:
        """
        Format list produk terlaris.
        
        Args:
            produk_list (List[Dict]): List produk dari get_produk_terlaris()
            title (str): Judul laporan
            
        Returns:
            str: Formatted list
        """
        lines = []
        lines.append("=" * 70)
        lines.append(title.center(70))
        lines.append("=" * 70)
        
        if not produk_list:
            lines.append("⚠️ Belum ada data penjualan")
        else:
            lines.append("No. | Nama Produk          | Qty  | Total Revenue")
            lines.append("-" * 70)
            for prod in produk_list:
                lines.append(f"{prod['rank']:>2}. | {prod['nama']:<20} | {prod['total_qty']:>4} | "
                            f"{format_rp(prod['total_revenue'])}")
        
        lines.append("=" * 70)
        return "\n".join(lines)
    
    @staticmethod
    def format_stok_summary(stok_list: List[Dict]) -> str:
        """
        Format stok summary.
        
        Args:
            stok_list (List[Dict]): List stok dari get_stok_summary()
            
        Returns:
            str: Formatted summary
        """
        lines = []
        lines.append("=" * 80)
        lines.append("SUMMARY STOK PRODUK".center(80))
        lines.append("=" * 80)
        
        lines.append("Kode       | Nama Produk          | Harga       | Stok | Status")
        lines.append("-" * 80)
        
        for prod in stok_list:
            lines.append(f"{prod['kode']:<10} | {prod['nama']:<20} | {format_rp(prod['harga']):<11} | "
                        f"{prod['stok']:>4} | {prod['status']}")
        
        lines.append("=" * 80)
        return "\n".join(lines)
    
    @staticmethod
    def format_dashboard(dashboard: Dict) -> str:
        """
        Format dashboard summary.
        
        Args:
            dashboard (Dict): Hasil dari get_dashboard_summary()
            
        Returns:
            str: Formatted dashboard
        """
        lines = []
        lines.append("╔" + "═" * 68 + "╗")
        lines.append("║" + "POS DASHBOARD - RINGKASAN HARI INI".center(68) + "║")
        lines.append("╠" + "═" * 68 + "╣")
        
        # Summary hari ini
        lines.append("║ 📊 PENJUALAN HARI INI:" + " " * 46 + "║")
        lines.append(f"║    Total: {format_rp(dashboard['hari_ini']['total_penjualan']):<20} | "
                    f"Transaksi: {dashboard['hari_ini']['total_transaksi']:<6} | "
                    f"Rata-rata: {format_rp(int(dashboard['hari_ini']['rata_rata'])):<12} ║")
        
        lines.append("║ " + "-" * 66 + " ║")
        
        # Produk terlaris
        lines.append("║ 🏆 TOP 5 PRODUK TERLARIS:" + " " * 41 + "║")
        for i, prod in enumerate(dashboard['produk_terlaris'][:5], 1):
            lines.append(f"║    {i}. {prod['nama']:<18} | {prod['total_qty']:>3} qty | "
                        f"{format_rp(prod['total_revenue']):<12} ║")
        
        lines.append("║ " + "-" * 66 + " ║")
        
        # Stok minim
        lines.append("║ ⚠️  STOK PRODUK MINIM:" + " " * 45 + "║")
        if dashboard['stok_minim']:
            for prod in dashboard['stok_minim'][:3]:
                lines.append(f"║    {prod['nama']:<20} | Stok: {prod['stok']:>3} {prod['status']:<8} ║")
        else:
            lines.append("║    Semua stok mencukupi ✅" + " " * 40 + "║")
        
        lines.append("║ " + "-" * 66 + " ║")
        
        # Inventory
        lines.append(f"║ 📦 INVENTORY: {dashboard['total_produk']} produk | "
                    f"Total Stok: {dashboard['total_stok']:<20} ║")
        
        lines.append("╚" + "═" * 68 + "╝")
        
        return "\n".join(lines)

# ============================================================================
# CSV EXPORTER - Export laporan ke CSV
# ============================================================================

class CSVExporter:
    """
    Export berbagai laporan ke format CSV untuk analisis lanjutan.
    
    Methods:
        export_produk_terlaris(): Export produk terlaris ke CSV
        export_stok_summary(): Export stok summary ke CSV
        export_transactions(): Export semua transaksi ke CSV
    """
    
    def __init__(self, export_dir: str = "exports"):
        """
        Inisialisasi CSVExporter.
        
        Args:
            export_dir (str): Directory untuk menyimpan CSV files
        """
        self.export_dir = export_dir
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)
            print(f"📁 Directory '{export_dir}' dibuat")
    
    def export_produk_terlaris(self, produk_list: List[Dict], 
                               filename: str = None) -> Optional[str]:
        """
        Export produk terlaris ke CSV.
        
        Args:
            produk_list (List[Dict]): List produk
            filename (str): Custom filename (default: produk_terlaris_TIMESTAMP.csv)
            
        Returns:
            str: Path file yang disimpan
            None: Jika gagal
        """
        try:
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"produk_terlaris_{timestamp}.csv"
            
            filepath = os.path.join(self.export_dir, filename)
            
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=['rank', 'nama', 'total_qty', 'total_revenue'])
                writer.writeheader()
                writer.writerows(produk_list)
            
            print(f"✅ File berhasil diekspor: {filepath}")
            return filepath
        except Exception as e:
            print(f"❌ Error saat export: {e}")
            return None
    
    def export_stok_summary(self, stok_list: List[Dict], 
                           filename: str = None) -> Optional[str]:
        """
        Export stok summary ke CSV.
        
        Args:
            stok_list (List[Dict]): List stok
            filename (str): Custom filename
            
        Returns:
            str: Path file
            None: Jika gagal
        """
        try:
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"stok_produk_{timestamp}.csv"
            
            filepath = os.path.join(self.export_dir, filename)
            
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=['kode', 'nama', 'harga', 'stok', 'status'])
                writer.writeheader()
                writer.writerows(stok_list)
            
            print(f"✅ File berhasil diekspor: {filepath}")
            return filepath
        except Exception as e:
            print(f"❌ Error saat export: {e}")
            return None
    
    def export_transactions(self, db: DatabaseManager, date_str: str = None, 
                           filename: str = None) -> Optional[str]:
        """
        Export transaksi harian ke CSV.
        
        Args:
            db (DatabaseManager): Database instance
            date_str (str): Tanggal (default: hari ini)
            filename (str): Custom filename
            
        Returns:
            str: Path file
            None: Jika gagal
        """
        try:
            if date_str is None:
                date_str = datetime.now().strftime('%Y-%m-%d')
            
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"transaksi_{date_str}_{timestamp}.csv"
            
            filepath = os.path.join(self.export_dir, filename)
            transactions = db.get_transactions_by_date(date_str)
            
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['ID', 'Tanggal', 'Total', 'Bayar', 'Kembalian'])
                
                for trans in transactions:
                    writer.writerow([
                        trans['id'],
                        trans['tanggal'],
                        trans['total'],
                        trans['bayar'],
                        trans['kembalian']
                    ])
            
            print(f"✅ File berhasil diekspor: {filepath}")
            return filepath
        except Exception as e:
            print(f"❌ Error saat export: {e}")
            return None

# ============================================================================
# TESTING - Jalankan jika file dijalankan standalone
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("POS REPORT SYSTEM - Testing")
    print("=" * 70)
    
    # Setup
    db = DatabaseManager()
    report_gen = ReportGenerator(db)
    formatter = ReportFormatter()
    exporter = CSVExporter()
    
    # Test laporan harian
    print("\n📊 Testing Laporan Harian...")
    laporan = report_gen.get_laporan_harian()
    print(formatter.format_laporan_harian(laporan))
    
    # Test produk terlaris
    print("\n🏆 Testing Produk Terlaris...")
    produk_laris = report_gen.get_produk_terlaris(limit=5)
    print(formatter.format_produk_terlaris(produk_laris))
    
    # Test stok summary
    print("\n📦 Testing Stok Summary...")
    stok = report_gen.get_stok_summary()
    print(formatter.format_stok_summary(stok))
    
    # Test dashboard
    print("\n🎨 Testing Dashboard...")
    dashboard = report_gen.get_dashboard_summary()
    print(formatter.format_dashboard(dashboard))
    
    # Test export CSV
    print("\n💾 Testing CSV Export...")
    exporter.export_produk_terlaris(produk_laris)
    exporter.export_stok_summary(stok)
    exporter.export_transactions(db)
    
    print("\n✅ Test selesai!")
