"""
Centralized logging configuration for all microservices.

This module provides structured logging configuration that is:
- Cloud-ready (JSON format for CloudWatch/similar)
- Consistent across all services  
- Environment-aware (dev vs production)
- Easily configurable
"""

import os
import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from enum import Enum
import json
from datetime import datetime


class LogLevel(Enum):
    """Standard log levels for the application."""
    DEBUG = "DEBUG"
    INFO = "INFO" 
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(Enum):
    """Available log output formats."""
    STRUCTURED = "structured"  # JSON format for cloud services
    SIMPLE = "simple"         # Human-readable for development


class FantasyLogFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured JSON logs for cloud compatibility.
    
    Each log entry includes:
    - Standard fields: timestamp, level, message, logger_name
    - Service context: service_name, version, correlation_id
    - Request context: method, endpoint, user_id (when available)
    - System context: hostname, process_id
    """
    
    def __init__(self, service_name: str, version: str = "1.0.0", format_type: LogFormat = LogFormat.STRUCTURED):
        super().__init__()
        self.service_name = service_name
        self.version = version
        self.format_type = format_type
        self.hostname = os.uname().nodename if hasattr(os, 'uname') else 'unknown'
        self.process_id = os.getpid()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON or simple text."""
        
        if self.format_type == LogFormat.STRUCTURED:
            return self._format_json(record)
        else:
            return self._format_simple(record)
    
    def _format_json(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        
        # Base log entry structure
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "logger_name": record.name,
            "service": {
                "name": self.service_name,
                "version": self.version,
                "hostname": self.hostname,
                "process_id": self.process_id
            }
        }
        
        # Add correlation ID if available (set by middleware)
        if hasattr(record, 'correlation_id'):
            log_entry["correlation_id"] = record.correlation_id
        
        # Add request context if available
        if hasattr(record, 'request_context'):
            log_entry["request"] = record.request_context
            
        # Add user context if available
        if hasattr(record, 'user_id'):
            log_entry["user_id"] = record.user_id
        
        # Add error details if this is an exception
        if record.exc_info:
            log_entry["error"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info)
            }
        
        # Add any custom fields passed via extra parameter
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 'msecs', 
                          'relativeCreated', 'thread', 'threadName', 'processName', 
                          'process', 'getMessage', 'exc_info', 'exc_text', 'stack_info',
                          'correlation_id', 'request_context', 'user_id']:
                # Add custom fields under a 'custom' namespace to avoid conflicts
                if 'custom' not in log_entry:
                    log_entry['custom'] = {}
                log_entry['custom'][key] = value
        
        return json.dumps(log_entry, default=str)
    
    def _format_simple(self, record: logging.LogRecord) -> str:
        """Format log record as human-readable text."""
        
        # Base format: timestamp - service - level - logger - message
        base_msg = f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} - {self.service_name} - {record.levelname} - {record.name} - {record.getMessage()}"
        
        # Add correlation ID if available
        if hasattr(record, 'correlation_id'):
            base_msg += f" [correlation_id: {record.correlation_id}]"
        
        # Add exception info if available
        if record.exc_info:
            base_msg += f"\\n{self.formatException(record.exc_info)}"
        
        return base_msg


class LoggingConfig:
    """
    Centralized logging configuration manager.
    
    Handles:
    - Environment-based configuration (dev vs production)
    - Log file rotation and management  
    - Multiple output formats (console, file, cloud)
    - Service-specific customization
    """
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.logs_dir = self.project_root / "logs"
        self.logs_dir.mkdir(exist_ok=True)
        
        # Environment detection
        self.environment = os.getenv("ENVIRONMENT", "development").lower()
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        self.log_format = LogFormat.STRUCTURED if self.environment == "production" else LogFormat.SIMPLE
        
        # Cloud logging configuration
        self.enable_cloud_logging = os.getenv("ENABLE_CLOUD_LOGGING", "false").lower() == "true"
        self.cloud_log_group = os.getenv("CLOUD_LOG_GROUP", "fantasy-draft-engine")
        
    def configure_service_logging(
        self, 
        service_name: str,
        version: str = "1.0.0",
        log_level: Optional[LogLevel] = None,
        enable_file_logging: bool = True,
        enable_console_logging: bool = True
    ) -> logging.Logger:
        """
        Configure logging for a specific service with standardized settings.
        
        Args:
            service_name: Name of the service (e.g., "data-ingestion")
            version: Service version
            log_level: Override default log level for this service
            enable_file_logging: Whether to write logs to files
            enable_console_logging: Whether to output logs to console
            
        Returns:
            Configured logger for the service
        """
        
        # Create logger for this service
        logger = logging.getLogger(service_name)
        logger.setLevel(getattr(logging, log_level.value if log_level else self.log_level))
        
        # Clear any existing handlers to avoid duplicates
        logger.handlers.clear()
        
        # Create formatter
        formatter = FantasyLogFormatter(service_name, version, self.log_format)
        
        # Console handler
        if enable_console_logging:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        # File handler with rotation
        if enable_file_logging:
            log_file = self.logs_dir / f"{service_name}.log"
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=50 * 1024 * 1024,  # 50MB per file
                backupCount=5  # Keep 5 backup files
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        # Error-specific file handler for easy error tracking
        error_log_file = self.logs_dir / f"{service_name}-errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB per file
            backupCount=3
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)
        
        # Cloud logging handler (if enabled)
        if self.enable_cloud_logging:
            cloud_handler = self._create_cloud_handler(service_name)
            if cloud_handler:
                cloud_handler.setFormatter(formatter)
                logger.addHandler(cloud_handler)
        
        return logger
    
    def _create_cloud_handler(self, service_name: str) -> Optional[logging.Handler]:
        """
        Create cloud logging handler using the dedicated cloud configuration module.
        """
        from .cloud_config import get_cloud_handler
        return get_cloud_handler(service_name)
    
    def get_log_directory(self) -> Path:
        """Get the centralized logs directory."""
        return self.logs_dir
    
    def get_service_log_file(self, service_name: str) -> Path:
        """Get the log file path for a specific service."""
        return self.logs_dir / f"{service_name}.log"
    
    def get_service_error_log_file(self, service_name: str) -> Path:
        """Get the error log file path for a specific service."""
        return self.logs_dir / f"{service_name}-errors.log"


# Global instance
_logging_config = LoggingConfig()


def get_service_logger(
    service_name: str,
    version: str = "1.0.0",
    log_level: Optional[LogLevel] = None
) -> logging.Logger:
    """
    Get a configured logger for a service.
    
    This is the main entry point that services should use.
    """
    return _logging_config.configure_service_logging(service_name, version, log_level)


def get_logging_config() -> LoggingConfig:
    """Get the global logging configuration instance."""
    return _logging_config