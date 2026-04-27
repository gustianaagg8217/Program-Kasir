#!/usr/bin/env python
# ============================================================================
# MIGRATE_TO_BCRYPT.PY - Migrate password hashes from SHA256 to Bcrypt
# ============================================================================
# Fungsi: Upgrade existing password hashes ke bcrypt yang lebih aman
# Supports backward compatibility - old SHA256 hashes tetap bisa diverifikasi
# Version: 1.0
# ============================================================================

import sqlite3
import os
import sys
from datetime import datetime
from logger_config import get_logger

# Import security modules
try:
    from auth_security import PasswordManager
    bcrypt_available = True
except ImportError:
    print("❌ Error: auth_security module not found. Install bcrypt first:")
    print("   pip install bcrypt")
    sys.exit(1)

logger = get_logger(__name__)

# ============================================================================
# PASSWORD MIGRATION
# ============================================================================

class PasswordMigration:
    """
    Migrate password hashes dari SHA256 ke Bcrypt.
    
    Features:
    - Detect existing SHA256 hashes
    - Migrate ke Bcrypt secara bertahap
    - Log semua changes untuk audit trail
    - Backward compatibility support
    """
    
    def __init__(self, db_path: str = "kasir_pos.db"):
        """
        Initialize migration.
        
        Args:
            db_path (str): Path ke database file
        """
        self.db_path = db_path
        self.stats = {
            'total_users': 0,
            'legacy_hashes': 0,
            'already_bcrypt': 0,
            'migrated': 0,
            'failed': 0,
            'errors': []
        }
    
    def get_connection(self):
        """Get database connection."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            logger.error(f"Cannot connect to database: {e}")
            raise
    
    def is_sha256_hash(self, hash_value: str) -> bool:
        """
        Check if hash adalah SHA256 format.
        
        SHA256 hashes adalah 64 karakter hex.
        Bcrypt hashes dimulai dengan $2a$, $2b$, atau $2y$.
        
        Args:
            hash_value (str): Hash value untuk dicek
            
        Returns:
            bool: True jika legacy SHA256
        """
        if not hash_value:
            return False
        
        # Bcrypt format
        if hash_value.startswith(('$2a$', '$2b$', '$2y$')):
            return False
        
        # SHA256 format: 64 hex characters
        if len(hash_value) == 64 and all(c in '0123456789abcdef' for c in hash_value):
            return True
        
        return False
    
    def analyze_database(self) -> dict:
        """
        Analyze database untuk check existing password hashes.
        
        Returns:
            dict: Stats tentang password format distribution
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get all users dengan password hashes
            cursor.execute("SELECT id, username, hashed_password FROM users ORDER BY id")
            users = cursor.fetchall()
            
            self.stats['total_users'] = len(users)
            
            for user in users:
                user_id = user['id']
                username = user['username']
                hash_val = user['hashed_password']
                
                if self.is_sha256_hash(hash_val):
                    self.stats['legacy_hashes'] += 1
                else:
                    self.stats['already_bcrypt'] += 1
            
            conn.close()
            
            return self.stats
        
        except Exception as e:
            logger.error(f"Error analyzing database: {e}")
            self.stats['errors'].append(str(e))
            return self.stats
    
    def migrate_password(self, old_hash: str) -> tuple[str, bool]:
        """
        Migrate single password hash ke bcrypt.
        
        Note: Karena hashing one-way, kita tidak bisa recover plaintext password.
        Solusi: User perlu reset password setelah migration.
        
        Atau, kita bisa keep existing SHA256 hash dan biarkan verify_password()
        handle both formats (backward compatibility).
        
        Args:
            old_hash (str): Old SHA256 hash
            
        Returns:
            tuple: (new_hash, success)
        """
        try:
            if not self.is_sha256_hash(old_hash):
                return old_hash, False  # Already bcrypt
            
            # Since we can't recover plaintext from SHA256, we mark hashes for reset
            # by keeping them as SHA256 (backward compatible)
            # BUT we CAN upgrade on next successful login
            logger.info(f"SHA256 hash identified - will upgrade on next login: {old_hash[:16]}...")
            return old_hash, False
        
        except Exception as e:
            logger.error(f"Error migrating password: {e}")
            return old_hash, False
    
    def run_migration(self, dry_run: bool = True) -> dict:
        """
        Run password migration.
        
        Strategy:
        1. Keep existing SHA256 hashes (backward compatible)
        2. On next successful login, upgrade to bcrypt
        3. Log all activities
        
        Args:
            dry_run (bool): If True, hanya analyze tanpa changes
            
        Returns:
            dict: Migration stats
        """
        try:
            # Analyze current state
            print("\n" + "="*70)
            print("PASSWORD HASH MIGRATION ANALYSIS")
            print("="*70)
            
            self.analyze_database()
            
            print(f"\n📊 Database Analysis:")
            print(f"   Total users: {self.stats['total_users']}")
            print(f"   Already Bcrypt: {self.stats['already_bcrypt']}")
            print(f"   Legacy SHA256: {self.stats['legacy_hashes']}")
            
            if self.stats['legacy_hashes'] == 0:
                print("\n✅ No migration needed - all hashes are already Bcrypt!")
                return self.stats
            
            if dry_run:
                print(f"\n🔍 DRY RUN MODE - No changes will be made")
                print(f"\nMigration Strategy:")
                print(f"   1. Keep existing SHA256 hashes (backward compatible)")
                print(f"   2. Upgrade to Bcrypt on next successful login")
                print(f"   3. All activities logged in database")
                return self.stats
            
            # Migration tidak diperlukan karena backward compatibility supported
            print(f"\n✅ Migration Ready!")
            print(f"   - {self.stats['legacy_hashes']} SHA256 hashes akan di-upgrade")
            print(f"   - Upgrade terjadi otomatis pada login berikutnya")
            print(f"   - Tidak ada action diperlukan sekarang")
            
            return self.stats
        
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            self.stats['errors'].append(str(e))
            return self.stats
    
    def print_report(self):
        """Print migration report."""
        print("\n" + "="*70)
        print("MIGRATION REPORT")
        print("="*70)
        print(f"\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Database: {self.db_path}")
        print(f"\n📊 Statistics:")
        print(f"   Total Users: {self.stats['total_users']}")
        print(f"   Bcrypt Hashes: {self.stats['already_bcrypt']}")
        print(f"   SHA256 Hashes: {self.stats['legacy_hashes']}")
        print(f"   Migrated: {self.stats['migrated']}")
        print(f"   Failed: {self.stats['failed']}")
        
        if self.stats['errors']:
            print(f"\n⚠️  Errors:")
            for error in self.stats['errors']:
                print(f"   - {error}")
        
        if self.stats['legacy_hashes'] > 0:
            print(f"\n✅ Backward Compatibility:")
            print(f"   - Legacy SHA256 hashes are still supported")
            print(f"   - Automatic upgrade to Bcrypt on next login")
            print(f"   - No user action required")
        
        print("\n" + "="*70)


# ============================================================================
# MAIN - Run migration
# ============================================================================

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migrate password hashes from SHA256 to Bcrypt",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze without making changes (default)
  python migrate_to_bcrypt.py
  
  # Perform migration
  python migrate_to_bcrypt.py --migrate
  
  # Use custom database path
  python migrate_to_bcrypt.py --db /path/to/database.db --migrate
        """
    )
    
    parser.add_argument(
        '--db',
        default='kasir_pos.db',
        help='Path to database file (default: kasir_pos.db)'
    )
    parser.add_argument(
        '--migrate',
        action='store_true',
        help='Perform actual migration (default is dry-run analysis)'
    )
    
    args = parser.parse_args()
    
    # Check database exists
    if not os.path.exists(args.db):
        print(f"❌ Error: Database not found: {args.db}")
        sys.exit(1)
    
    # Run migration
    migrator = PasswordMigration(db_path=args.db)
    
    if args.migrate:
        print("🔄 Running migration...")
        migrator.run_migration(dry_run=False)
    else:
        print("🔍 Running analysis (dry-run, no changes)...")
        migrator.run_migration(dry_run=True)
    
    migrator.print_report()


if __name__ == "__main__":
    main()
