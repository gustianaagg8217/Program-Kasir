# ============================================================================
# USER_REPOSITORY.PY - Database Access Layer untuk Users
# ============================================================================
# Fungsi: CRUD operations untuk user data
# Responsibilitas: Direct database access ONLY, no business logic
# ============================================================================

from typing import List, Optional, Dict, Any
from database import DatabaseManager
from logger_config import get_logger
from app.utils.error_handler import DatabaseError

logger = get_logger(__name__)


class User:
    """Data model untuk User."""
    def __init__(self, id: int, username: str, password_hash: str, role: str, email: str = "", active: bool = True):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.role = role  # 'admin' atau 'cashier'
        self.email = email
        self.active = active
    
    def __repr__(self):
        return f"User(id={self.id}, username={self.username}, role={self.role})"


class UserRepository:
    """Repository untuk user data access."""
    
    def __init__(self, db: DatabaseManager):
        """
        Init dengan DatabaseManager instance.
        
        Args:
            db: DatabaseManager instance
        """
        self.db = db
    
    def create(self, username: str, password_hash: str, role: str = "cashier", email: str = "") -> User:
        """
        Create user baru di database.
        
        Args:
            username: Username unique
            password_hash: Hashed password (dari PasswordManager)
            role: User role ('admin' atau 'cashier')
            email: Email user
            
        Returns:
            User object yang baru dibuat
            
        Raises:
            DatabaseError: Jika insert gagal
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (username, password_hash, role, email, active)
                    VALUES (?, ?, ?, ?, 1)
                """, (username, password_hash, role, email))
                conn.commit()
                
                user_id = cursor.lastrowid
                logger.info(f"User created: ID={user_id}, username={username}, role={role}")
                
                return User(user_id, username, password_hash, role, email, True)
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise DatabaseError(str(e), "Gagal membuat user")
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user berdasarkan ID."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, username, password_hash, role, email, active
                    FROM users WHERE id = ?
                """, (user_id,))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                return self._map_to_user(row)
        except Exception as e:
            logger.error(f"Error getting user by id: {e}")
            return None
    
    def get_by_username(self, username: str) -> Optional[User]:
        """Get user berdasarkan username."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, username, password_hash, role, email, active
                    FROM users WHERE username = ?
                """, (username,))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                return self._map_to_user(row)
        except Exception as e:
            logger.error(f"Error getting user by username: {e}")
            return None
    
    def list_all(self) -> List[User]:
        """Get semua users."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, username, password_hash, role, email, active
                    FROM users ORDER BY username
                """)
                rows = cursor.fetchall()
                return [self._map_to_user(row) for row in rows]
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            return []
    
    def update(self, user_id: int, **kwargs) -> bool:
        """
        Update user berdasarkan ID.
        
        Args:
            user_id: User ID
            **kwargs: Field yang mau di-update (password_hash, email, role, active)
            
        Returns:
            True jika berhasil
        """
        try:
            allowed_fields = {'password_hash', 'email', 'role', 'active'}
            fields_to_update = {k: v for k, v in kwargs.items() if k in allowed_fields}
            
            if not fields_to_update:
                return False
            
            set_clause = ", ".join([f"{k} = ?" for k in fields_to_update.keys()])
            values = list(fields_to_update.values()) + [user_id]
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
                conn.commit()
                
                logger.info(f"User updated: ID={user_id}, fields={list(fields_to_update.keys())}")
                return True
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return False
    
    def delete(self, user_id: int) -> bool:
        """Delete user berdasarkan ID (soft delete - set active=0)."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                # Soft delete - jangan hard delete, set active=0
                cursor.execute("UPDATE users SET active = 0 WHERE id = ?", (user_id,))
                conn.commit()
                
                logger.info(f"User deactivated: ID={user_id}")
                return True
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return False
    
    def exists(self, username: str) -> bool:
        """Check apakah username sudah ada."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM users WHERE username = ? LIMIT 1", (username,))
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking user existence: {e}")
            return False
    
    def get_active_users(self) -> List[User]:
        """Get semua active users."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, username, password_hash, role, email, active
                    FROM users WHERE active = 1 ORDER BY username
                """)
                rows = cursor.fetchall()
                return [self._map_to_user(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting active users: {e}")
            return []
    
    @staticmethod
    def _map_to_user(row: tuple) -> User:
        """Map database row ke User object."""
        return User(
            id=row[0],
            username=row[1],
            password_hash=row[2],
            role=row[3],
            email=row[4],
            active=bool(row[5])
        )
