"""
Centralized Logging Configuration for Fantasy Draft Engine
==========================================================

This module provides a unified logging configuration for all services in the fantasy
draft engine. It implements structured logging with service identification, correlation
tracking, and proper output formatting for both development and production environments.

Key Features:
- Service-aware logging with automatic service identification
- Correlation ID tracking across service calls
- Structured logging with consistent formatting
- Log level management by service
- File and console output with rotation
- Performance monitoring and error tracking
"""

import logging
import logging.handlers
import os
import sys
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any
import traceback
import functools
import time

# Global configuration
LOG_BASE_DIR = Path("/Users/jihoonsong/Documents/projects/fantasy_draft_engine/logs")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(service_name)s:%(correlation_id)s] - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Ensure logs directory exists
LOG_BASE_DIR.mkdir(exist_ok=True)

# Service registry for tracking
SERVICE_REGISTRY = {}

class ServiceContextFilter(logging.Filter):
    """Filter to add service context to log records."""
    
    def __init__(self, service_name: str, service_version: str = "1.0.0"):
        super().__init__()
        self.service_name = service_name
        self.service_version = service_version
        self.correlation_id = str(uuid.uuid4())[:8]  # Short correlation ID
    
    def filter(self, record):
        record.service_name = self.service_name
        record.service_version = self.service_version
        record.correlation_id = getattr(record, 'correlation_id', self.correlation_id)
        return True

class StructuredFormatter(logging.Formatter):
    """Formatter that outputs structured JSON logs for machine processing."""
    
    def format(self, record):
        log_obj = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'service': getattr(record, 'service_name', 'unknown'),
            'service_version': getattr(record, 'service_version', '1.0.0'),
            'correlation_id': getattr(record, 'correlation_id', 'none'),
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception information if present
        if record.exc_info:
            log_obj['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields if present
        extra_fields = getattr(record, 'extra_fields', {})
        if extra_fields:
            log_obj['extra'] = extra_fields
        
        return json.dumps(log_obj, default=str)

class PerformanceFilter(logging.Filter):
    """Filter to add performance metrics to log records."""
    
    def filter(self, record):
        # Add process/thread info for performance tracking
        record.process_id = os.getpid()
        record.thread_name = getattr(record, 'thread_name', 'MainThread')
        return True

def setup_service_logging(
    service_name: str,
    service_version: str = "1.0.0",
    log_level: str = "INFO",
    enable_console: bool = True,
    enable_file: bool = True,
    enable_structured: bool = True,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    extra_handlers: Optional[list] = None
) -> logging.Logger:
    """
    Set up centralized logging for a service.
    
    Args:
        service_name: Name of the service (e.g., 'data-ingestion', 'feature-engineering')
        service_version: Version of the service
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_console: Whether to log to console
        enable_file: Whether to log to file
        enable_structured: Whether to use structured JSON logging
        max_file_size: Maximum size of log files before rotation
        backup_count: Number of backup files to keep
        extra_handlers: Additional custom handlers
        
    Returns:
        Configured logger instance
    """
    
    # Create logger for the service
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear any existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create service context filter
    service_filter = ServiceContextFilter(service_name, service_version)
    performance_filter = PerformanceFilter()
    
    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        
        if enable_structured:
            console_handler.setFormatter(StructuredFormatter())
        else:
            console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
        
        console_handler.addFilter(service_filter)
        console_handler.addFilter(performance_filter)
        logger.addHandler(console_handler)
    
    # File handler with rotation
    if enable_file:
        service_log_dir = LOG_BASE_DIR / service_name
        service_log_dir.mkdir(exist_ok=True)
        
        # Main service log file
        log_file = service_log_dir / f"{service_name}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_file_size,
            backupCount=backup_count
        )
        file_handler.setLevel(getattr(logging, log_level.upper()))
        
        if enable_structured:
            file_handler.setFormatter(StructuredFormatter())
        else:
            file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
        
        file_handler.addFilter(service_filter)
        file_handler.addFilter(performance_filter)
        logger.addHandler(file_handler)
        
        # Error-only log file for quick issue identification
        error_log_file = service_log_dir / f"{service_name}-errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=max_file_size,
            backupCount=backup_count
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(StructuredFormatter() if enable_structured else 
                                  logging.Formatter(LOG_FORMAT, DATE_FORMAT))
        error_handler.addFilter(service_filter)
        error_handler.addFilter(performance_filter)
        logger.addHandler(error_handler)
    
    # Add any extra handlers
    if extra_handlers:
        for handler in extra_handlers:
            handler.addFilter(service_filter)
            handler.addFilter(performance_filter)
            logger.addHandler(handler)
    
    # Register the service
    SERVICE_REGISTRY[service_name] = {
        'logger': logger,
        'service_version': service_version,
        'created_at': datetime.now(),
        'filter': service_filter
    }
    
    logger.info(f"Logging initialized for service '{service_name}' v{service_version}")
    logger.info(f"Log level: {log_level}, Console: {enable_console}, File: {enable_file}")
    logger.info(f"Log directory: {service_log_dir if enable_file else 'N/A'}")
    
    return logger

def get_service_logger(service_name: str) -> Optional[logging.Logger]:
    """Get the logger for a specific service."""
    if service_name in SERVICE_REGISTRY:
        return SERVICE_REGISTRY[service_name]['logger']
    return None

def set_correlation_id(service_name: str, correlation_id: str):
    """Set correlation ID for service requests."""
    if service_name in SERVICE_REGISTRY:
        SERVICE_REGISTRY[service_name]['filter'].correlation_id = correlation_id

def log_service_start(service_name: str, **kwargs):
    """Log service startup with configuration details."""
    logger = get_service_logger(service_name)
    if logger:
        logger.info("=" * 60)
        logger.info(f"🚀 SERVICE STARTUP: {service_name}")
        logger.info("=" * 60)
        
        for key, value in kwargs.items():
            logger.info(f"   {key}: {value}")
        
        logger.info("=" * 60)

def log_service_shutdown(service_name: str):
    """Log service shutdown."""
    logger = get_service_logger(service_name)
    if logger:
        logger.info("=" * 60)
        logger.info(f"🛑 SERVICE SHUTDOWN: {service_name}")
        logger.info("=" * 60)

def log_operation_start(logger: logging.Logger, operation: str, **context):
    """Log the start of an operation with context."""
    logger.info("▶️ " + "=" * 50)
    logger.info(f"OPERATION START: {operation}")
    
    for key, value in context.items():
        logger.info(f"   {key}: {value}")
    
    logger.info("=" * 50)
    return time.time()  # Return start time for duration calculation

def log_operation_complete(logger: logging.Logger, operation: str, start_time: float, **results):
    """Log the completion of an operation with results."""
    duration = time.time() - start_time
    
    logger.info("✅ " + "=" * 50)
    logger.info(f"OPERATION COMPLETE: {operation}")
    logger.info(f"   Duration: {duration:.3f} seconds")
    
    for key, value in results.items():
        logger.info(f"   {key}: {value}")
    
    logger.info("=" * 50)

def log_operation_error(logger: logging.Logger, operation: str, start_time: float, error: Exception, **context):
    """Log operation failure with error details."""
    duration = time.time() - start_time
    
    logger.error("❌ " + "=" * 50)
    logger.error(f"OPERATION FAILED: {operation}")
    logger.error(f"   Duration: {duration:.3f} seconds")
    logger.error(f"   Error Type: {type(error).__name__}")
    logger.error(f"   Error Message: {str(error)}")
    
    for key, value in context.items():
        logger.error(f"   {key}: {value}")
    
    logger.error("=" * 50)
    logger.error(f"Full traceback:\n{traceback.format_exc()}")

def log_with_context(logger: logging.Logger, level: int, message: str, **context):
    """Log message with structured context."""
    # Add context as extra fields
    extra = {'extra_fields': context}
    logger.log(level, message, extra=extra)

def operation_logger(operation_name: str):
    """Decorator for logging operation start/completion/errors."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get logger from the first argument if it's a class instance
            logger = None
            if args and hasattr(args[0], 'logger'):
                logger = args[0].logger
            else:
                logger = logging.getLogger(__name__)
            
            # Build context from function arguments
            context = {'function': func.__name__, 'args_count': len(args), 'kwargs': list(kwargs.keys())}
            
            start_time = log_operation_start(logger, operation_name, **context)
            
            try:
                result = func(*args, **kwargs)
                
                # Log results if they're simple types
                results = {}
                if isinstance(result, (int, float, str, bool)):
                    results['result'] = result
                elif hasattr(result, '__len__'):
                    results['result_count'] = len(result)
                
                log_operation_complete(logger, operation_name, start_time, **results)
                return result
                
            except Exception as e:
                log_operation_error(logger, operation_name, start_time, e, **context)
                raise
        
        return wrapper
    return decorator

def setup_microservice_logging():
    """Set up logging for all microservices with standard configuration."""
    services = [
        'data-ingestion',
        'feature-engineering', 
        'ml-models',
        'ranking',
        'orchestration',
        'configuration'
    ]
    
    loggers = {}
    
    for service in services:
        logger = setup_service_logging(
            service_name=service,
            log_level="INFO",
            enable_console=True,
            enable_file=True,
            enable_structured=True
        )
        loggers[service] = logger
    
    return loggers

# Health check endpoint data collection
def collect_logging_health():
    """Collect health information about the logging system."""
    health_info = {
        'logging_system': 'healthy',
        'services_registered': len(SERVICE_REGISTRY),
        'log_directory': str(LOG_BASE_DIR),
        'disk_usage': {},
        'service_status': {}
    }
    
    # Check disk usage for log directory
    if LOG_BASE_DIR.exists():
        try:
            import shutil
            total, used, free = shutil.disk_usage(LOG_BASE_DIR)
            health_info['disk_usage'] = {
                'total_gb': round(total / (1024**3), 2),
                'used_gb': round(used / (1024**3), 2),
                'free_gb': round(free / (1024**3), 2),
                'used_percentage': round((used / total) * 100, 1)
            }
        except Exception as e:
            health_info['disk_usage'] = {'error': str(e)}
    
    # Check each registered service
    for service_name, service_info in SERVICE_REGISTRY.items():
        service_log_dir = LOG_BASE_DIR / service_name
        log_file = service_log_dir / f"{service_name}.log"
        
        status = {
            'registered_at': service_info['created_at'].isoformat(),
            'log_file_exists': log_file.exists(),
            'log_file_size_mb': 0,
            'handler_count': len(service_info['logger'].handlers)
        }
        
        if log_file.exists():
            status['log_file_size_mb'] = round(log_file.stat().st_size / (1024**2), 2)
        
        health_info['service_status'][service_name] = status
    
    return health_info

# Module-level setup for easy import
def get_logger(service_name: str, **kwargs) -> logging.Logger:
    """Convenience function to get or create a service logger."""
    existing_logger = get_service_logger(service_name)
    if existing_logger:
        return existing_logger
    
    return setup_service_logging(service_name, **kwargs)

# Example usage patterns
if __name__ == "__main__":
    # Example: Set up logging for a service
    logger = setup_service_logging(
        service_name="example-service",
        log_level="DEBUG",
        enable_structured=True
    )
    
    # Example: Log service startup
    log_service_start("example-service", 
                     port=8000, 
                     database_url="postgresql://localhost",
                     debug_mode=True)
    
    # Example: Log operations
    start = log_operation_start(logger, "Data Processing", 
                               input_files=100, 
                               processing_mode="batch")
    
    # Simulate some work
    import time
    time.sleep(0.1)
    
    log_operation_complete(logger, "Data Processing", start,
                          records_processed=1500,
                          files_created=25,
                          success_rate=98.5)
    
    # Example: Structured logging
    log_with_context(logger, logging.INFO, "User action completed",
                    user_id="12345",
                    action="file_upload", 
                    file_size=2048,
                    duration_ms=150)
    
    # Example: Decorator usage
    @operation_logger("Database Query")
    def example_function(query_type, limit):
        return f"Found {limit} results for {query_type}"
    
    result = example_function("user_search", 50)
    
    # Log service shutdown
    log_service_shutdown("example-service")
    
    # Show health information
    health = collect_logging_health()
    print(json.dumps(health, indent=2))