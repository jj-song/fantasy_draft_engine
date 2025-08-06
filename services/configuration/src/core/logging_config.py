"""
Centralized logging configuration for the Fantasy Draft Engine.

This module provides consistent logging setup and utilities across all
components of the fantasy football system.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import json


class FantasyFootballFormatter(logging.Formatter):
    """
    Custom formatter for fantasy football logging with structured output.
    
    This formatter adds consistent formatting and optional JSON structure
    for better log analysis and monitoring.
    """
    
    def __init__(self, use_json: bool = False, include_context: bool = True):
        """
        Initialize the formatter.
        
        Args:
            use_json: Whether to output logs in JSON format
            include_context: Whether to include contextual information
        """
        self.use_json = use_json
        self.include_context = include_context
        
        if use_json:
            super().__init__()
        else:
            format_str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            if include_context:
                format_str = '%(asctime)s - %(name)s - %(levelname)s - [%(module)s:%(funcName)s:%(lineno)d] - %(message)s'
            super().__init__(format_str)
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record."""
        if self.use_json:
            log_data = {
                'timestamp': datetime.fromtimestamp(record.created).isoformat(),
                'level': record.levelname,
                'logger': record.name,
                'message': record.getMessage(),
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno
            }
            
            # Add any extra fields from the record
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                              'filename', 'module', 'lineno', 'funcName', 'created', 
                              'msecs', 'relativeCreated', 'thread', 'threadName', 
                              'processName', 'process', 'getMessage']:
                    log_data[key] = value
            
            return json.dumps(log_data)
        else:
            return super().format(record)


def setup_logger(name: str,
                level: str = 'INFO',
                log_file: Optional[str] = None,
                console_output: bool = True,
                use_json: bool = False,
                max_file_size: int = 10 * 1024 * 1024,  # 10MB
                backup_count: int = 5) -> logging.Logger:
    """
    Setup a logger with consistent configuration.
    
    Args:
        name: Logger name
        level: Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        log_file: Optional file path for file logging
        console_output: Whether to output to console
        use_json: Whether to use JSON formatting
        max_file_size: Maximum size of log file before rotation (bytes)
        backup_count: Number of backup files to keep
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Clear any existing handlers to avoid duplication
    logger.handlers.clear()
    
    # Set level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)
    
    # Create formatter
    formatter = FantasyFootballFormatter(use_json=use_json)
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler with rotation
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_file_size,
            backupCount=backup_count
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str, **kwargs) -> logging.Logger:
    """
    Get or create a logger with default fantasy football configuration.
    
    Args:
        name: Logger name
        **kwargs: Additional arguments passed to setup_logger
        
    Returns:
        Logger instance
    """
    # Check if logger already exists and is configured
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        # Logger doesn't exist or isn't configured, set it up
        default_kwargs = {
            'level': 'INFO',
            'console_output': True,
            'use_json': False
        }
        default_kwargs.update(kwargs)
        
        logger = setup_logger(name, **default_kwargs)
    
    return logger


def configure_root_logger(log_level: str = 'INFO',
                         log_file: Optional[str] = None) -> None:
    """
    Configure the root logger for the entire fantasy football system.
    
    Args:
        log_level: Root logging level
        log_file: Optional file path for centralized logging
    """
    root_logger = logging.getLogger('fantasy_football')
    
    if not root_logger.handlers:
        setup_logger(
            'fantasy_football',
            level=log_level,
            log_file=log_file,
            console_output=True
        )
    
    # Also configure some third-party loggers to reduce noise
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('matplotlib').setLevel(logging.WARNING)


class LogContext:
    """
    Context manager for adding structured context to logs within a block.
    
    This allows adding contextual information (like player position, operation type)
    to all log messages within a specific code block.
    """
    
    def __init__(self, logger: logging.Logger, **context):
        """
        Initialize the log context.
        
        Args:
            logger: Logger to add context to
            **context: Context information to add to log messages
        """
        self.logger = logger
        self.context = context
        self.old_filter = None
    
    def __enter__(self):
        """Enter the context and add the filter."""
        if self.context:
            # Create a filter that adds context to log records
            def context_filter(record):
                for key, value in self.context.items():
                    setattr(record, key, value)
                return True
            
            self.old_filter = context_filter
            self.logger.addFilter(context_filter)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context and remove the filter."""
        if self.old_filter:
            self.logger.removeFilter(self.old_filter)


def log_execution_time(logger: logging.Logger, operation: str):
    """
    Decorator to log execution time of functions.
    
    Args:
        logger: Logger to use for timing messages
        operation: Description of the operation being timed
        
    Returns:
        Decorator function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            try:
                result = func(*args, **kwargs)
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                logger.info(f"{operation} completed in {duration:.2f} seconds")
                return result
            except Exception as e:
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                logger.error(f"{operation} failed after {duration:.2f} seconds: {e}")
                raise
        return wrapper
    return decorator


def create_operation_logger(base_logger: logging.Logger, 
                          operation: str,
                          **context) -> logging.LoggerAdapter:
    """
    Create a logger adapter that adds operation context to all messages.
    
    Args:
        base_logger: Base logger to adapt
        operation: Operation name to include in logs
        **context: Additional context information
        
    Returns:
        Logger adapter with operation context
    """
    context_dict = {'operation': operation}
    context_dict.update(context)
    
    return logging.LoggerAdapter(base_logger, context_dict)


# Default configuration for the fantasy football system
DEFAULT_LOG_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
        'detailed': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - [%(module)s:%(funcName)s:%(lineno)d] - %(message)s'
        }
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'stream': 'ext://sys.stdout'
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console']
    }
}