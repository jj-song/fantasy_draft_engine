"""
Logging context utilities for correlation tracking and request flow.

This module provides utilities to:
- Track requests across multiple services with correlation IDs
- Add contextual information to logs (user, request details, etc.)
- Manage application lifecycle logging (startup, shutdown, errors)
"""

import logging
import uuid
import contextvars
import asyncio
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from functools import wraps
import traceback
import time


# Context variables for correlation tracking
correlation_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar('correlation_id', default=None)
user_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar('user_id', default=None)
request_context_ctx: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar('request_context', default=None)


class LogContext:
    """
    Context manager for adding structured context to log entries.
    
    Usage:
        with LogContext(correlation_id="abc123", user_id="user456"):
            logger.info("Processing request")  # Will include correlation_id and user_id
    """
    
    def __init__(self, **context):
        self.context = context
        self.tokens = {}
    
    def __enter__(self):
        # Set context variables
        if 'correlation_id' in self.context:
            self.tokens['correlation_id'] = correlation_id_ctx.set(self.context['correlation_id'])
        if 'user_id' in self.context:
            self.tokens['user_id'] = user_id_ctx.set(self.context['user_id'])
        if 'request_context' in self.context:
            self.tokens['request_context'] = request_context_ctx.set(self.context['request_context'])
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Reset context variables
        for key, token in self.tokens.items():
            if key == 'correlation_id':
                correlation_id_ctx.reset(token)
            elif key == 'user_id':
                user_id_ctx.reset(token)
            elif key == 'request_context':
                request_context_ctx.reset(token)


class ContextualLoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that automatically adds context variables to log records.
    
    This ensures that correlation IDs, user IDs, and request context 
    are automatically included in all log entries.
    """
    
    def process(self, msg, kwargs):
        # Add context variables to the log record
        extra = kwargs.get('extra', {})
        
        # Add correlation ID if available
        correlation_id = correlation_id_ctx.get()
        if correlation_id:
            extra['correlation_id'] = correlation_id
        
        # Add user ID if available
        user_id = user_id_ctx.get()
        if user_id:
            extra['user_id'] = user_id
            
        # Add request context if available
        request_context = request_context_ctx.get()
        if request_context:
            extra['request_context'] = request_context
        
        kwargs['extra'] = extra
        return msg, kwargs


def get_contextual_logger(name: str) -> ContextualLoggerAdapter:
    """
    Get a logger that automatically includes context variables.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger adapter with automatic context inclusion
    """
    base_logger = logging.getLogger(name)
    return ContextualLoggerAdapter(base_logger, {})


def generate_correlation_id() -> str:
    """Generate a new correlation ID for request tracking."""
    return str(uuid.uuid4())


def log_application_lifecycle(logger: logging.Logger, service_name: str, version: str):
    """
    Decorator to add application lifecycle logging to service startup/shutdown.
    
    Usage:
        @log_application_lifecycle(logger, "data-ingestion", "1.0.0")
        def main():
            # Service logic here
            pass
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Log application startup
            logger.info(
                f"🚀 {service_name} v{version} starting up",
                extra={
                    "event_type": "application_startup",
                    "service_name": service_name,
                    "version": version,
                    "startup_time": datetime.utcnow().isoformat() + "Z"
                }
            )
            
            try:
                result = func(*args, **kwargs)
                
                # Log successful startup
                startup_duration = time.time() - start_time
                logger.info(
                    f"✅ {service_name} v{version} started successfully in {startup_duration:.2f}s",
                    extra={
                        "event_type": "application_ready",
                        "service_name": service_name,
                        "version": version,
                        "startup_duration_seconds": startup_duration
                    }
                )
                
                return result
                
            except Exception as e:
                # Log startup failure
                startup_duration = time.time() - start_time
                logger.error(
                    f"❌ {service_name} v{version} failed to start: {str(e)}",
                    extra={
                        "event_type": "application_startup_failed",
                        "service_name": service_name,
                        "version": version,
                        "startup_duration_seconds": startup_duration,
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    },
                    exc_info=True
                )
                raise
        
        # Add shutdown logging
        original_wrapper = wrapper
        
        @wraps(func)
        def enhanced_wrapper(*args, **kwargs):
            try:
                return original_wrapper(*args, **kwargs)
            finally:
                # This will be called on normal shutdown or exception
                logger.info(
                    f"🛑 {service_name} v{version} shutting down",
                    extra={
                        "event_type": "application_shutdown",
                        "service_name": service_name,
                        "version": version,
                        "shutdown_time": datetime.utcnow().isoformat() + "Z"
                    }
                )
        
        return enhanced_wrapper
    return decorator


def log_function_execution(logger: Optional[logging.Logger] = None):
    """
    Decorator to log function execution with timing and error handling.
    
    Usage:
        @log_function_execution(logger)
        def process_data():
            # Function logic here
            pass
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Use provided logger or get one for the function's module
            actual_logger = logger or get_contextual_logger(func.__module__)
            
            function_name = f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            
            # Log function start
            actual_logger.debug(
                f"📥 Starting {function_name}",
                extra={
                    "event_type": "function_start",
                    "function_name": function_name
                }
            )
            
            try:
                result = func(*args, **kwargs)
                
                # Log successful completion
                duration = time.time() - start_time
                actual_logger.debug(
                    f"✅ Completed {function_name} in {duration:.3f}s",
                    extra={
                        "event_type": "function_success",
                        "function_name": function_name,
                        "duration_seconds": duration
                    }
                )
                
                return result
                
            except Exception as e:
                # Log function failure
                duration = time.time() - start_time
                actual_logger.error(
                    f"❌ Failed {function_name} after {duration:.3f}s: {str(e)}",
                    extra={
                        "event_type": "function_error",
                        "function_name": function_name,
                        "duration_seconds": duration,
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    },
                    exc_info=True
                )
                raise
        
        return wrapper
    return decorator


async def log_async_function_execution(logger: Optional[logging.Logger] = None):
    """
    Async version of function execution logging decorator.
    
    Usage:
        @log_async_function_execution(logger)
        async def async_process_data():
            # Async function logic here
            pass
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Use provided logger or get one for the function's module
            actual_logger = logger or get_contextual_logger(func.__module__)
            
            function_name = f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            
            # Log function start
            actual_logger.debug(
                f"📥 Starting async {function_name}",
                extra={
                    "event_type": "async_function_start",
                    "function_name": function_name
                }
            )
            
            try:
                result = await func(*args, **kwargs)
                
                # Log successful completion
                duration = time.time() - start_time
                actual_logger.debug(
                    f"✅ Completed async {function_name} in {duration:.3f}s",
                    extra={
                        "event_type": "async_function_success",
                        "function_name": function_name,
                        "duration_seconds": duration
                    }
                )
                
                return result
                
            except Exception as e:
                # Log function failure
                duration = time.time() - start_time
                actual_logger.error(
                    f"❌ Failed async {function_name} after {duration:.3f}s: {str(e)}",
                    extra={
                        "event_type": "async_function_error",
                        "function_name": function_name,
                        "duration_seconds": duration,
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    },
                    exc_info=True
                )
                raise
        
        return wrapper
    return decorator


def log_service_call(service_name: str, endpoint: str, logger: Optional[logging.Logger] = None):
    """
    Decorator to log inter-service API calls with timing and error handling.
    
    Usage:
        @log_service_call("ml-models", "/api/v1/models/predict")
        def call_ml_service():
            # Service call logic here
            pass
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Use provided logger or get one for the function's module
            actual_logger = logger or get_contextual_logger(func.__module__)
            
            start_time = time.time()
            correlation_id = correlation_id_ctx.get() or generate_correlation_id()
            
            # Log service call start
            actual_logger.info(
                f"🔗 Calling {service_name}{endpoint}",
                extra={
                    "event_type": "service_call_start",
                    "target_service": service_name,
                    "endpoint": endpoint,
                    "correlation_id": correlation_id
                }
            )
            
            try:
                result = func(*args, **kwargs)
                
                # Log successful service call
                duration = time.time() - start_time
                actual_logger.info(
                    f"✅ {service_name}{endpoint} responded in {duration:.3f}s",
                    extra={
                        "event_type": "service_call_success",
                        "target_service": service_name,
                        "endpoint": endpoint,
                        "duration_seconds": duration,
                        "correlation_id": correlation_id
                    }
                )
                
                return result
                
            except Exception as e:
                # Log service call failure
                duration = time.time() - start_time
                actual_logger.error(
                    f"❌ {service_name}{endpoint} failed after {duration:.3f}s: {str(e)}",
                    extra={
                        "event_type": "service_call_error",
                        "target_service": service_name,
                        "endpoint": endpoint,
                        "duration_seconds": duration,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "correlation_id": correlation_id
                    },
                    exc_info=True
                )
                raise
        
        return wrapper
    return decorator