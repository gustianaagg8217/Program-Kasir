# ============================================================================
# ACTIVITY_REPOSITORY.PY - Activity Logging Data Access Layer
# ============================================================================
# Fungsi: Handle activity log storage and retrieval for audit trails
# ============================================================================

from typing import List, Optional
from datetime import datetime, timedelta

from ..core import ActivityLog
from .base_repository import BaseRepository
from logger_config import get_logger

logger = get_logger(__name__)


class ActivityRepository(BaseRepository):
    """Repository untuk activity logging (audit trail)."""
    
    def create(self, **kwargs) -> ActivityLog:
        """Create activity log entry."""
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO activity_logs (
                        user_id, username, action, resource_type, resource_id,
                        details, status, timestamp, ip_address, user_agent
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    kwargs.get('user_id'),
                    kwargs.get('username', ''),
                    kwargs.get('action', ''),
                    kwargs.get('resource_type', ''),
                    kwargs.get('resource_id', ''),
                    kwargs.get('details', ''),
                    kwargs.get('status', 'success'),
                    kwargs.get('timestamp', datetime.now()),
                    kwargs.get('ip_address', ''),
                    kwargs.get('user_agent', '')
                ))
                
                log_id = cursor.lastrowid
                logger.debug(f"Activity logged: ID {log_id}")
                
                return self.get_by_id(log_id)
                
        except Exception as e:
            logger.error(f"Error creating activity log: {e}", exc_info=e)
            raise
    
    def get_by_id(self, log_id: int) -> Optional[ActivityLog]:
        """Get activity log by ID."""
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM activity_logs WHERE id = ?
                """, (log_id,))
                
                row = cursor.fetchone()
                if row:
                    return self._row_to_activity(row)
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting activity log {log_id}: {e}", exc_info=e)
            raise
    
    def get_by_user(self, user_id: int, limit: int = 100, days: int = 7) -> List[ActivityLog]:
        """Get activity logs for specific user."""
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()
                
                start_date = datetime.now() - timedelta(days=days)
                
                cursor.execute("""
                    SELECT * FROM activity_logs
                    WHERE user_id = ? AND timestamp >= ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (user_id, start_date, limit))
                
                activities = []
                for row in cursor.fetchall():
                    activities.append(self._row_to_activity(row))
                
                return activities
                
        except Exception as e:
            logger.error(f"Error getting activities for user {user_id}: {e}", exc_info=e)
            raise
    
    def get_all(self, limit: int = 1000, offset: int = 0, action: str = None, status: str = None) -> List[ActivityLog]:
        """Get all activity logs with optional filters."""
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM activity_logs WHERE 1=1"
                params = []
                
                if action:
                    query += " AND action = ?"
                    params.append(action)
                
                if status:
                    query += " AND status = ?"
                    params.append(status)
                
                query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])
                
                cursor.execute(query, params)
                
                activities = []
                for row in cursor.fetchall():
                    activities.append(self._row_to_activity(row))
                
                return activities
                
        except Exception as e:
            logger.error(f"Error getting activity logs: {e}", exc_info=e)
            raise
    
    def get_by_resource(self, resource_type: str, resource_id: str) -> List[ActivityLog]:
        """Get all activities for a resource."""
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM activity_logs
                    WHERE resource_type = ? AND resource_id = ?
                    ORDER BY timestamp DESC
                """, (resource_type, resource_id))
                
                activities = []
                for row in cursor.fetchall():
                    activities.append(self._row_to_activity(row))
                
                return activities
                
        except Exception as e:
            logger.error(f"Error getting activities for resource: {e}", exc_info=e)
            raise
    
    def delete(self, log_id: int) -> bool:
        """Delete activity log (archive recommended instead)."""
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()
                
                cursor.execute("DELETE FROM activity_logs WHERE id = ?", (log_id,))
                
                logger.warning(f"Activity log {log_id} deleted")
                return True
                
        except Exception as e:
            logger.error(f"Error deleting activity log {log_id}: {e}", exc_info=e)
            raise
    
    @staticmethod
    def _row_to_activity(row) -> ActivityLog:
        """Convert database row to ActivityLog object."""
        return ActivityLog(
            id=row['id'] if 'id' in row.keys() else None,
            user_id=row['user_id'] if 'user_id' in row.keys() else None,
            username=row['username'] if 'username' in row.keys() else '',
            action=row['action'] if 'action' in row.keys() else '',
            resource_type=row['resource_type'] if 'resource_type' in row.keys() else '',
            resource_id=row['resource_id'] if 'resource_id' in row.keys() else '',
            details=row['details'] if 'details' in row.keys() else '',
            status=row['status'] if 'status' in row.keys() else 'success',
            timestamp=row['timestamp'] if 'timestamp' in row.keys() else datetime.now(),
            ip_address=row['ip_address'] if 'ip_address' in row.keys() else '',
            user_agent=row['user_agent'] if 'user_agent' in row.keys() else ''
        )
