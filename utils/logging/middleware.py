"""
FastAPI middleware for centralized logging, correlation tracking, and request/response logging.

This module provides middleware that:
- Automatically generates/propagates correlation IDs
- Logs all requests and responses with timing
- Handles errors with structured logging
- Integrates with the centralized logging system
"""

import time
import uuid
import json
from typing import Dict, Any, Optional, Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging

from .context import LogContext, correlation_id_ctx, generate_correlation_id, get_contextual_logger


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Enhanced logging middleware that provides:
    - Automatic correlation ID generation/propagation
    - Request/response logging with timing
    - Error logging with stack traces
    - Context propagation across the request lifecycle
    """
    
    def __init__(
        self, 
        app: ASGIApp, 
        service_name: str,
        logger: Optional[logging.Logger] = None,
        log_request_body: bool = False,
        log_response_body: bool = False,
        exclude_paths: Optional[list] = None
    ):
        super().__init__(app)
        self.service_name = service_name
        self.logger = logger or get_contextual_logger(f"{service_name}.middleware")
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/favicon.ico"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with comprehensive logging."""
        
        # Skip logging for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        start_time = time.time()
        
        # Get or generate correlation ID
        correlation_id = (
            request.headers.get("x-correlation-id") or 
            request.headers.get("correlation-id") or
            generate_correlation_id()
        )
        
        # Extract user ID from headers or auth context (if available)
        user_id = request.headers.get("x-user-id") or request.headers.get("user-id")
        
        # Create request context
        request_context = {
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_host": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "content_type": request.headers.get("content-type")
        }
        
        # Add request body if configured (be careful with sensitive data)
        # NOTE: Reading request body in middleware can cause issues with FastAPI's Pydantic validation
        # We'll capture the body after the request is processed instead
        if self.log_request_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                # Store the request for later body capture (if needed)
                request_context["capture_body"] = True
            except Exception:
                # If we can't setup body capture, don't fail the request
                pass
        
        # Set correlation ID in request state for use by route handlers
        request.state.correlation_id = correlation_id
        request.state.user_id = user_id
        
        # Use context manager to ensure correlation ID is available in all logs
        with LogContext(
            correlation_id=correlation_id,
            user_id=user_id,
            request_context=request_context
        ):
            # Log request start
            log_data = {
                "event_type": "request_start",
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "correlation_id": correlation_id,
                "user_id": user_id,
                "client_host": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
                "service_name": self.service_name
            }
            
            # Add request body to logs if captured
            if "body" in request_context:
                log_data["request_body"] = request_context["body"]
            
            self.logger.info(
                f"🔥 {request.method} {request.url.path} started",
                extra=log_data
            )
            
            try:
                # Process the request
                response = await call_next(request)
                
                # Calculate request duration
                duration = time.time() - start_time
                
                # Log successful response
                response_data = {
                    "event_type": "request_success",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_seconds": duration,
                    "correlation_id": correlation_id,
                    "user_id": user_id,
                    "service_name": self.service_name
                }
                
                # Add response body if configured and status is not successful
                if self.log_response_body and hasattr(response, 'body'):
                    try:
                        # This is tricky with streaming responses, so be careful
                        if hasattr(response, 'body') and len(str(response.body)) < 10000:
                            response_data["response_body"] = str(response.body)[:1000]
                    except Exception:
                        # If we can't read response body, don't fail
                        pass
                
                # Choose log level based on status code
                if response.status_code < 400:
                    self.logger.info(
                        f"✅ {request.method} {request.url.path} completed ({response.status_code}) in {duration:.3f}s",
                        extra=response_data
                    )
                elif response.status_code < 500:
                    self.logger.warning(
                        f"⚠️ {request.method} {request.url.path} client error ({response.status_code}) in {duration:.3f}s",
                        extra=response_data
                    )
                else:
                    self.logger.error(
                        f"❌ {request.method} {request.url.path} server error ({response.status_code}) in {duration:.3f}s",
                        extra=response_data
                    )
                
                # Add correlation ID to response headers
                response.headers["x-correlation-id"] = correlation_id
                
                return response
                
            except Exception as e:
                # Calculate request duration for error case
                duration = time.time() - start_time
                
                # Log request failure
                self.logger.error(
                    f"💥 {request.method} {request.url.path} failed after {duration:.3f}s: {str(e)}",
                    extra={
                        "event_type": "request_error",
                        "method": request.method,
                        "path": request.url.path,
                        "duration_seconds": duration,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "correlation_id": correlation_id,
                        "user_id": user_id,
                        "service_name": self.service_name
                    },
                    exc_info=True
                )
                
                # Re-raise the exception to let FastAPI handle it
                raise


class ServiceDiscoveryLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware specifically for logging service discovery and inter-service communication.
    
    This tracks when services call each other and helps build a complete picture
    of request flow across the microservices architecture.
    """
    
    def __init__(
        self, 
        app: ASGIApp, 
        service_name: str,
        logger: Optional[logging.Logger] = None
    ):
        super().__init__(app)
        self.service_name = service_name
        self.logger = logger or get_contextual_logger(f"{service_name}.service_discovery")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log service discovery and inter-service communication patterns."""
        
        # Check if this is an inter-service call
        calling_service = request.headers.get("x-calling-service")
        if calling_service:
            correlation_id = request.headers.get("x-correlation-id", "unknown")
            
            self.logger.info(
                f"🔗 Service call: {calling_service} → {self.service_name}",
                extra={
                    "event_type": "inter_service_call",
                    "calling_service": calling_service,
                    "target_service": self.service_name,
                    "endpoint": request.url.path,
                    "correlation_id": correlation_id
                }
            )
        
        # Process request normally
        response = await call_next(request)
        
        # Add our service name to response headers for downstream services
        response.headers["x-responding-service"] = self.service_name
        
        return response


def add_logging_middleware(
    app, 
    service_name: str, 
    logger: Optional[logging.Logger] = None,
    enable_service_discovery: bool = True,
    **kwargs
):
    """
    Convenience function to add all logging middleware to a FastAPI app.
    
    Args:
        app: FastAPI application instance
        service_name: Name of the service
        logger: Optional logger instance
        enable_service_discovery: Whether to enable service discovery logging
        **kwargs: Additional arguments for LoggingMiddleware
    """
    
    # Add main logging middleware
    app.add_middleware(LoggingMiddleware, service_name=service_name, logger=logger, **kwargs)
    
    # Add service discovery middleware if requested
    if enable_service_discovery:
        app.add_middleware(ServiceDiscoveryLoggingMiddleware, service_name=service_name, logger=logger)


class HTTPClientLoggingMixin:
    """
    Mixin class for HTTP clients to add automatic logging of outbound service calls.
    
    Usage:
        class MyServiceClient(HTTPClientLoggingMixin):
            def __init__(self):
                self.service_name = "my-service"
                super().__init__()
    """
    
    def __init__(self):
        if not hasattr(self, 'service_name'):
            raise ValueError("HTTPClientLoggingMixin requires 'service_name' to be set")
        
        self.logger = get_contextual_logger(f"{self.service_name}.http_client")
    
    def log_outbound_request(
        self, 
        method: str, 
        url: str, 
        target_service: Optional[str] = None,
        **kwargs
    ):
        """
        Log an outbound HTTP request.
        
        Args:
            method: HTTP method
            url: Target URL
            target_service: Name of target service (if known)
            **kwargs: Additional context
        """
        correlation_id = correlation_id_ctx.get() or generate_correlation_id()
        
        self.logger.info(
            f"📤 {method} {url} outbound call",
            extra={
                "event_type": "outbound_request",
                "method": method,
                "url": url,
                "target_service": target_service,
                "calling_service": self.service_name,
                "correlation_id": correlation_id,
                **kwargs
            }
        )
        
        return correlation_id
    
    def log_outbound_response(
        self, 
        correlation_id: str,
        method: str, 
        url: str, 
        status_code: int,
        duration: float,
        target_service: Optional[str] = None,
        **kwargs
    ):
        """Log an outbound HTTP response."""
        
        log_level = logging.INFO if status_code < 400 else logging.ERROR
        emoji = "✅" if status_code < 400 else "❌"
        
        self.logger.log(
            log_level,
            f"{emoji} {method} {url} response ({status_code}) in {duration:.3f}s",
            extra={
                "event_type": "outbound_response",
                "method": method,
                "url": url,
                "status_code": status_code,
                "duration_seconds": duration,
                "target_service": target_service,
                "calling_service": self.service_name,
                "correlation_id": correlation_id,
                **kwargs
            }
        )