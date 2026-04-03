# ============================================================================
# BACKUP_MANAGER.PY - Database Backup Management
# ============================================================================
# Fungsi: Mengelola automatic backup database harian dengan retention policy
# Fitur: Daily backup, retention (keep 7 backups), auto-cleanup, logging
# ============================================================================

import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from logger_config import get_logger

logger = get_logger(__name__)

class BackupManager:
    """
    Manage database backups dengan automatic daily backup dan retention policy.
    
    Fitur:
    - Automatic daily backup (saat app start)
    - Save dengan format: backup_YYYYMMDD.db
    - Keep last 7 backups only
    - Auto-delete old backups
    - Full logging dan error handling
    
    Attributes:
        backup_folder (str): Path ke folder backup
        retention_days (int): Berapa hari backup disimpan
        max_backups (int): Maksimal backup yang disimpan
    """
    
    def __init__(self, backup_folder: str = "backup", max_backups: int = 7):
        """
        Inisialisasi BackupManager.
        
        Args:
            backup_folder (str): Path ke folder backup (default: "backup")
            max_backups (int): Maksimal backup yang disimpan (default: 7)
        """
        self.backup_folder = backup_folder
        self.max_backups = max_backups
        
        # Buat folder backup jika belum ada
        self._create_backup_folder()
        
        logger.info(f"BackupManager initialized: folder={backup_folder}, max_backups={max_backups}")
    
    def _create_backup_folder(self):
        """Create backup folder if it doesn't exist."""
        try:
            Path(self.backup_folder).mkdir(parents=True, exist_ok=True)
            logger.info(f"Backup folder ready: {self.backup_folder}")
        except Exception as e:
            logger.error(f"Failed to create backup folder: {e}", exc_info=True)
            raise
    
    def backup_database(self, db_path: str) -> bool:
        """
        Create backup dari database file.
        
        Backup hanya dibuat jika belum ada backup untuk hari ini.
        Automatically cleanup old backups jika sudah lebih dari max_backups.
        
        Args:
            db_path (str): Path ke database file yang akan di-backup
            
        Returns:
            bool: True jika backup sukses, False jika tidak perlu backup
                  (sudah ada backup untuk hari ini)
        """
        try:
            # Check if database file exists
            if not os.path.exists(db_path):
                logger.warning(f"Database file not found: {db_path}")
                return False
            
            # Generate backup filename dengan format: backup_YYYYMMDD.db
            today = datetime.now().strftime("%Y%m%d")
            backup_filename = f"backup_{today}.db"
            backup_path = os.path.join(self.backup_folder, backup_filename)
            
            # Check if backup sudah ada untuk hari ini
            if os.path.exists(backup_path):
                logger.info(f"Backup already exists for today: {backup_filename}")
                return False
            
            # Copy database ke backup folder
            shutil.copy2(db_path, backup_path)
            logger.info(f"Database backup created: {backup_filename}")
            
            # Cleanup old backups (keep only max_backups)
            self._cleanup_old_backups()
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to backup database: {e}", exc_info=True)
            return False
    
    def _cleanup_old_backups(self):
        """Remove old backup files, keeping only latest max_backups files."""
        try:
            # Get all backup files
            backup_files = sorted([
                f for f in os.listdir(self.backup_folder)
                if f.startswith("backup_") and f.endswith(".db")
            ])
            
            # If more than max_backups, delete oldest
            if len(backup_files) > self.max_backups:
                files_to_delete = len(backup_files) - self.max_backups
                
                for i in range(files_to_delete):
                    old_backup = os.path.join(self.backup_folder, backup_files[i])
                    try:
                        os.remove(old_backup)
                        logger.info(f"Old backup deleted: {backup_files[i]}")
                    except Exception as e:
                        logger.warning(f"Failed to delete old backup {backup_files[i]}: {e}")
        
        except Exception as e:
            logger.error(f"Backup cleanup failed: {e}", exc_info=True)
    
    def get_backup_list(self) -> list:
        """
        Get list of all backup files dengan informasi size dan tanggal.
        
        Returns:
            list: List of dicts {filename, path, size, created_date}
        """
        try:
            backups = []
            for filename in sorted(os.listdir(self.backup_folder), reverse=True):
                if filename.startswith("backup_") and filename.endswith(".db"):
                    filepath = os.path.join(self.backup_folder, filename)
                    size = os.path.getsize(filepath)
                    mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    
                    # Extract date from filename (backup_YYYYMMDD.db)
                    date_str = filename.replace("backup_", "").replace(".db", "")
                    try:
                        date_obj = datetime.strptime(date_str, "%Y%m%d")
                    except:
                        date_obj = mtime
                    
                    backups.append({
                        'filename': filename,
                        'path': filepath,
                        'size': size,
                        'size_mb': round(size / (1024 * 1024), 2),
                        'created_date': date_obj,
                        'modified_time': mtime
                    })
            
            return backups
        except Exception as e:
            logger.error(f"Failed to get backup list: {e}", exc_info=True)
            return []
    
    def restore_backup(self, backup_filename: str, db_path: str) -> bool:
        """
        Restore database dari backup file.
        
        SAFETY: Membuat backup dari current database sebelum restore,
        untuk safety jika terjadi kesalahan.
        
        Args:
            backup_filename (str): Nama backup file (contoh: backup_20260403.db)
            db_path (str): Path ke database file yang akan di-restore
            
        Returns:
            bool: True jika restore sukses
        """
        try:
            backup_path = os.path.join(self.backup_folder, backup_filename)
            
            # Check if backup file exists
            if not os.path.exists(backup_path):
                logger.error(f"Backup file not found: {backup_filename}")
                return False
            
            # Create safety backup dari current database
            if os.path.exists(db_path):
                safety_backup_path = os.path.join(
                    self.backup_folder,
                    f"safety_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                )
                shutil.copy2(db_path, safety_backup_path)
                logger.info(f"Safety backup created before restore: {os.path.basename(safety_backup_path)}")
            
            # Restore dari backup
            shutil.copy2(backup_path, db_path)
            logger.info(f"Database restored from backup: {backup_filename}")
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}", exc_info=True)
            return False
    
    def get_backup_statistics(self) -> dict:
        """
        Get backup statistics (total size, count, latest backup, dll).
        
        Returns:
            dict: Statistics tentang backups
        """
        try:
            backups = self.get_backup_list()
            
            if not backups:
                return {
                    'total_backups': 0,
                    'total_size_mb': 0,
                    'latest_backup': None,
                    'oldest_backup': None
                }
            
            total_size = sum(b['size'] for b in backups)
            
            return {
                'total_backups': len(backups),
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'latest_backup': backups[0]['filename'] if backups else None,
                'latest_backup_date': backups[0]['created_date'].strftime("%Y-%m-%d") if backups else None,
                'oldest_backup': backups[-1]['filename'] if backups else None,
                'oldest_backup_date': backups[-1]['created_date'].strftime("%Y-%m-%d") if backups else None,
                'max_retention': self.max_backups
            }
        except Exception as e:
            logger.error(f"Failed to get backup statistics: {e}", exc_info=True)
            return {}


# Convenience function untuk usage di bagian lain aplikasi
def create_backup_manager(backup_folder: str = "backup", max_backups: int = 7) -> BackupManager:
    """Create dan return BackupManager instance."""
    return BackupManager(backup_folder, max_backups)
