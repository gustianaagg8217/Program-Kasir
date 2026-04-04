# ============================================================================
# USER_REPOSITORY.PY - User Data Access Layer
# ============================================================================
# Fungsi: Handle semua DB operations untuk User entity
# ============================================================================

from typing import List, Optional
from datetime import datetime

from ..core import User, DatabaseError
from .base_repository import CacheableRepository


class UserRepository(CacheableRepository):
    """
    Repository untuk User CRUD operations.
    
    Methods:
        create(username, password_hash, role, ...): Create user
        get_by_id(user_id): Get user by ID
        get_by_username(username): Get user by username (with cache)
        list_all(): List all users
        update(user_id, ...): Update user
        delete(user_id): Delete user (soft delete)
        authenticate(username, password_hash): Verify credentials
    """
    
    def create(self, username: str, password_hash: str, role: str, 
               nama_lengkap: str = "", is_active: bool = True) -> User:
        """
        Create new user.
        
        Args:
            username (str): Username (unique)
            password_hash (str): Hashed password
            role (str): User role (admin, cashier)
            nama_lengkap (str): Full name
            is_active (bool): Active status
            
        Returns:
            User: Created user object
            
        Raises:
            DatabaseError: If creation fails (e.g., duplicate username)
        """
        with self.get_db() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO users (username, password_hash, role, nama_lengkap, is_active, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (username, password_hash, role, nama_lengkap, is_active, datetime.now()))
                
                user_id = cursor.lastrowid
                
                # Invalidate cache
                self._invalidate_cache("users")
                
                return User(
                    id=user_id,
                    username=username,
                    password_hash=password_hash,
                    role=role,
                    nama_lengkap=nama_lengkap,
                    is_active=is_active,
                    created_at=datetime.now()
                )
            
            except Exception as e:
                if "UNIQUE constraint failed" in str(e):
                    raise DatabaseError(f"Username '{username}' sudah digunakan", "create")
                raise DatabaseError(f"Gagal create user: {str(e)}", "create")
    
    def read(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return self.get_by_id(user_id)
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id (int): User ID
            
        Returns:
            User: User object or None
        """
        with self.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, password_hash, role, nama_lengkap, is_active, created_at
                FROM users WHERE id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            return self._map_row_to_user(row) if row else None
    
    def get_by_username(self, username: str) -> Optional[User]:
        """
        Get user by username (with cache).
        
        Args:
            username (str): Username
            
        Returns:
            User: User object or None
        """
        # Check cache
        cache_key = f"user_{username.lower()}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached
        
        with self.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, password_hash, role, nama_lengkap, is_active, created_at
                FROM users WHERE LOWER(username) = LOWER(?)
            """, (username,))
            
            row = cursor.fetchone()
            user = self._map_row_to_user(row) if row else None
            
            if user:
                self._set_cache(cache_key, user)
            
            return user
    
    def list_all(self) -> List[User]:
        """
        Get all users (with cache).
        
        Returns:
            List[User]: List of all users
        """
        cache_key = "users_all"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached
        
        with self.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, password_hash, role, nama_lengkap, is_active, created_at
                FROM users WHERE is_active = 1 ORDER BY username ASC
            """)
            
            rows = cursor.fetchall()
            users = [self._map_row_to_user(row) for row in rows]
            
            self._set_cache(cache_key, users)
            return users
    
    def update(self, user_id: int, **kwargs) -> bool:
        """
        Update user.
        
        Args:
            user_id (int): User ID
            **kwargs: Fields to update (nama_lengkap, is_active, role)
            
        Returns:
            bool: True if updated
        """
        allowed_fields = {'nama_lengkap', 'is_active', 'role'}
        fields_to_update = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not fields_to_update:
            return False
        
        set_clause = ', '.join([f"{k} = ?" for k in fields_to_update.keys()])
        values = list(fields_to_update.values()) + [user_id]
        
        with self.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
            
            self._invalidate_cache("users")
            return cursor.rowcount > 0
    
    def delete(self, user_id: int) -> bool:
        """
        Soft delete user (deactivate).
        
        Args:
            user_id (int): User ID
            
        Returns:
            bool: True if deleted
        """
        return self.update(user_id, is_active=False)
    
    def update_password(self, user_id: int, new_password_hash: str) -> bool:
        """
        Update user password.
        
        Args:
            user_id (int): User ID
            new_password_hash (str): New hashed password
            
        Returns:
            bool: True if updated
        """
        with self.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET password_hash = ? WHERE id = ?
            """, (new_password_hash, user_id))
            
            self._invalidate_cache("users")
            return cursor.rowcount > 0
    
    def authenticate(self, username: str, password_hash: str) -> Optional[User]:
        """
        Authenticate user by username and password hash.
        
        Args:
            username (str): Username
            password_hash (str): Password hash to verify
            
        Returns:
            User: User object if credentials match and user is active, None otherwise
        """
        user = self.get_by_username(username)
        
        if user is None:
            return None
        
        # Verify password hash
        if user.password_hash == password_hash and user.is_active:
            return user
        
        return None
    
    def get_active_users(self) -> List[User]:
        """Get all active users."""
        with self.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, password_hash, role, nama_lengkap, is_active, created_at
                FROM users WHERE is_active = 1 ORDER BY username ASC
            """)
            
            rows = cursor.fetchall()
            return [self._map_row_to_user(row) for row in rows]
    
    def get_users_by_role(self, role: str) -> List[User]:
        """Get users by role."""
        with self.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, password_hash, role, nama_lengkap, is_active, created_at
                FROM users WHERE role = ? AND is_active = 1 ORDER BY username ASC
            """, (role,))
            
            rows = cursor.fetchall()
            return [self._map_row_to_user(row) for row in rows]
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    @staticmethod
    def _map_row_to_user(row) -> User:
        """Convert database row to User object."""
        if row is None:
            return None
        
        return User(
            id=row['id'],
            username=row['username'],
            password_hash=row['password_hash'],
            role=row['role'],
            nama_lengkap=row['nama_lengkap'],
            is_active=row['is_active'],
            created_at=row['created_at']
        )
