from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from storage.repositories import SystemLogRepository
from storage.models import SystemLog as SystemLogModel


class LogService:
    """Service for system log operations"""
    
    def __init__(self, db: Session):
        self.repository = SystemLogRepository(db)
    
    def log_info(self, module: str, message: str, details: Optional[str] = None, account_id: Optional[str] = None) -> None:
        """Log an info message"""
        self.repository.log_info(module, message, details, account_id)
    
    def log_warning(self, module: str, message: str, details: Optional[str] = None, account_id: Optional[str] = None) -> None:
        """Log a warning message"""
        self.repository.log_warning(module, message, details, account_id)
    
    def log_error(self, module: str, message: str, details: Optional[str] = None, account_id: Optional[str] = None) -> None:
        """Log an error message"""
        self.repository.log_error(module, message, details, account_id)
    
    def log_debug(self, module: str, message: str, details: Optional[str] = None, account_id: Optional[str] = None) -> None:
        """Log a debug message"""
        self._log('DEBUG', module, message, details, account_id)
    
    def log_custom(self, level: str, module: str, message: str, details: Optional[str] = None, account_id: Optional[str] = None) -> None:
        """Log a custom level message"""
        valid_levels = ['INFO', 'WARNING', 'ERROR', 'DEBUG']
        if level not in valid_levels:
            raise ValueError(f"Invalid log level: {level}. Must be one of {valid_levels}")
        self._log(level, module, message, details, account_id)
    
    def _log(self, level: str, module: str, message: str, details: Optional[str] = None, account_id: Optional[str] = None) -> None:
        """Internal log method"""
        log = SystemLogModel(
            level=level,
            module=module,
            message=message,
            details=details,
            account_id=account_id
        )
        self.repository.db.add(log)
        self.repository.db.commit()
    
    def get_logs(self, 
                 level: Optional[str] = None,
                 module: Optional[str] = None,
                 limit: int = 100,
                 offset: int = 0) -> List[SystemLogModel]:
        """Get logs with optional filtering"""
        query = self.repository.db.query(SystemLogModel)
        
        if level:
            query = query.filter(SystemLogModel.level == level)
        
        if module:
            query = query.filter(SystemLogModel.module == module)
        
        return query.order_by(SystemLogModel.timestamp.desc()).offset(offset).limit(limit).all()
    
    def get_logs_by_time_range(self, 
                              start_time: str, 
                              end_time: str,
                              level: Optional[str] = None,
                              module: Optional[str] = None) -> List[SystemLogModel]:
        """Get logs within a specific time range"""
        query = self.repository.db.query(SystemLogModel).filter(
            SystemLogModel.timestamp >= start_time,
            SystemLogModel.timestamp <= end_time
        )
        
        if level:
            query = query.filter(SystemLogModel.level == level)
        
        if module:
            query = query.filter(SystemLogModel.module == module)
        
        return query.order_by(SystemLogModel.timestamp.desc()).all()
    
    def get_error_logs(self, limit: int = 50) -> List[SystemLogModel]:
        """Get recent error logs"""
        return self.get_logs(level='ERROR', limit=limit)
    
    def get_warning_logs(self, limit: int = 50) -> List[SystemLogModel]:
        """Get recent warning logs"""
        return self.get_logs(level='WARNING', limit=limit)
    
    def get_log_by_id(self, log_id: int) -> Optional[SystemLogModel]:
        """Get a specific log by ID"""
        return self.repository.db.query(SystemLogModel).filter(SystemLogModel.id == log_id).first()
    
    def get_log_summary(self) -> Dict[str, Any]:
        """Get log statistics summary"""
        total_logs = self.repository.db.query(SystemLogModel).count()
        
        # Count by level
        level_counts = {}
        levels = ['INFO', 'WARNING', 'ERROR', 'DEBUG']
        for level in levels:
            count = self.repository.db.query(SystemLogModel).filter(SystemLogModel.level == level).count()
            level_counts[level] = count
        
        # Get recent activity
        recent_logs = self.get_logs(limit=10)
        
        return {
            'total_logs': total_logs,
            'level_counts': level_counts,
            'recent_activity': [
                {
                    'id': log.id,
                    'timestamp': log.timestamp.isoformat() if log.timestamp else None,
                    'level': log.level,
                    'module': log.module,
                    'message': log.message
                }
                for log in recent_logs
            ]
        }
    
    def clear_old_logs(self, days: int = 30) -> int:
        """Clear logs older than specified number of days"""
        from sqlalchemy import text
        
        if days <= 0:
            raise ValueError("Days must be a positive integer")
        
        # Delete logs older than specified days
        result = self.repository.db.execute(
            text("DELETE FROM system_logs WHERE timestamp < datetime('now', '-' || :days || ' days')"),
            {'days': days}
        )
        self.repository.db.commit()
        
        return result.rowcount
