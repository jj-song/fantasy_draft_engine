"""
Base API template for all microservices with centralized logging.
"""
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time
import uuid
import os
from typing import Dict, Any, Optional
import traceback

from ..health.health_checks import HealthChecker

# Import centralized logging
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent / "utils"))
from utils.logging.config import get_service_logger
from utils.logging.middleware import add_logging_middleware
from utils.logging.context import get_contextual_logger

# Remove old logging configuration - now handled by centralized system

class BaseService:
    def __init__(
        self, 
        service_name: str,
        version: str = "1.0.0",
        description: str = "Fantasy Football Microservice"
    ):
        self.service_name = service_name
        self.version = version
        self.description = description
        
        # Initialize centralized logging
        self.logger = get_service_logger(service_name, version)
        self.contextual_logger = get_contextual_logger(f"{service_name}.base")
        
        self.health_checker = HealthChecker(service_name, version)
        
        # Create FastAPI app with enhanced lifespan management
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup logging
            start_time = time.time()
            self.logger.info(
                f"🚀 {service_name} v{version} starting up...",
                extra={
                    "event_type": "service_startup_begin",
                    "service_name": service_name,
                    "version": version,
                    "environment": os.getenv("ENVIRONMENT", "development"),
                    "process_id": os.getpid()
                }
            )
            
            try:
                await self.startup()
                startup_duration = time.time() - start_time
                self.logger.info(
                    f"✅ {service_name} v{version} started successfully in {startup_duration:.2f}s",
                    extra={
                        "event_type": "service_startup_complete",
                        "service_name": service_name,
                        "version": version,
                        "startup_duration_seconds": startup_duration
                    }
                )
            except Exception as e:
                startup_duration = time.time() - start_time
                self.logger.error(
                    f"❌ {service_name} v{version} failed to start: {str(e)}",
                    extra={
                        "event_type": "service_startup_failed",
                        "service_name": service_name,
                        "version": version,
                        "startup_duration_seconds": startup_duration,
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    },
                    exc_info=True
                )
                raise
            
            yield
            
            # Shutdown logging
            self.logger.info(
                f"🛑 {service_name} v{version} shutting down...",
                extra={
                    "event_type": "service_shutdown_begin",
                    "service_name": service_name,
                    "version": version
                }
            )
            
            try:
                await self.shutdown()
                self.logger.info(
                    f"✅ {service_name} v{version} shutdown complete",
                    extra={
                        "event_type": "service_shutdown_complete",
                        "service_name": service_name,
                        "version": version
                    }
                )
            except Exception as e:
                self.logger.error(
                    f"❌ {service_name} v{version} shutdown error: {str(e)}",
                    extra={
                        "event_type": "service_shutdown_error",
                        "service_name": service_name,
                        "version": version,
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    },
                    exc_info=True
                )
        
        self.app = FastAPI(
            title=service_name,
            version=version,
            description=description,
            lifespan=lifespan
        )
        
        self._setup_middleware()
        self._setup_health_endpoints()
        self._setup_error_handlers()
        
        # Log service initialization
        self.logger.info(
            f"🏗️ {service_name} v{version} initialized",
            extra={
                "event_type": "service_initialization",
                "service_name": service_name,
                "version": version
            }
        )
    
    def _setup_middleware(self):
        """Set up enhanced middleware with centralized logging"""
        
        # CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Add centralized logging middleware (replaces old request logging)
        add_logging_middleware(
            self.app,
            service_name=self.service_name,
            logger=self.logger,
            enable_service_discovery=True,
            log_request_body=True,   # Enable request payload logging
            log_response_body=True   # Enable response payload logging
        )
    
    def _setup_health_endpoints(self):
        """Set up health check endpoints with enhanced logging"""
        
        @self.app.get("/health/live")
        async def liveness_check():
            try:
                result = await self.health_checker.liveness_check()
                self.contextual_logger.debug("Liveness check completed", extra={"status": result.status})
                return result
            except Exception as e:
                self.contextual_logger.error(f"Liveness check failed: {str(e)}", exc_info=True)
                raise HTTPException(status_code=503, detail="Service not live")
        
        @self.app.get("/health/ready")
        async def readiness_check():
            try:
                result = await self.health_checker.readiness_check()
                status = result.status if isinstance(result, dict) else getattr(result, "status", "unknown")
                
                self.contextual_logger.debug("Readiness check completed", extra={"status": status})
                
                if status != "ready":
                    raise HTTPException(status_code=503, detail=result)
                return result
            except HTTPException:
                raise
            except Exception as e:
                self.contextual_logger.error(f"Readiness check failed: {str(e)}", exc_info=True)
                raise HTTPException(status_code=503, detail="Service not ready")
        
        @self.app.get("/health/deep")
        async def deep_health_check():
            try:
                result = await self.health_checker.deep_health_check()
                status = result.status if isinstance(result, dict) else getattr(result, "status", "unknown")
                
                self.contextual_logger.debug("Deep health check completed", extra={"status": status})
                
                if status == "unhealthy":
                    raise HTTPException(status_code=503, detail=result)
                return result
            except HTTPException:
                raise
            except Exception as e:
                self.contextual_logger.error(f"Deep health check failed: {str(e)}", exc_info=True)
                raise HTTPException(status_code=503, detail="Service unhealthy")
        
        @self.app.get("/health/metrics")
        async def metrics():
            try:
                result = await self.health_checker.metrics()
                return result
            except Exception as e:
                self.contextual_logger.error(f"Metrics collection failed: {str(e)}", exc_info=True)
                return {"status": "error", "message": "Failed to collect metrics"}
        
        @self.app.get("/api/v1/info")
        async def service_info():
            """Enhanced service info with logging metadata"""
            return {
                "service_name": self.service_name,
                "version": self.version,
                "description": self.description,
                "logging": {
                    "structured_logging_enabled": True,
                    "correlation_tracking": True,
                    "centralized_logging": True
                },
                "endpoints": [
                    "/health/live",
                    "/health/ready", 
                    "/health/deep",
                    "/health/metrics",
                    "/api/v1/info"
                ]
            }
    
    def _setup_error_handlers(self):
        """Set up enhanced error handling with centralized logging"""
        
        @self.app.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, exc: HTTPException):
            correlation_id = getattr(request.state, 'correlation_id', 'unknown')
            
            # Enhanced HTTP exception logging
            self.contextual_logger.warning(
                f"HTTP Exception {exc.status_code}: {exc.detail}",
                extra={
                    "event_type": "http_exception",
                    "status_code": exc.status_code,
                    "detail": str(exc.detail),
                    "path": request.url.path,
                    "method": request.method,
                    "correlation_id": correlation_id
                }
            )
            
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "status": "error",
                    "error_code": exc.status_code,
                    "message": exc.detail,
                    "correlation_id": correlation_id,
                    "service": self.service_name,
                    "timestamp": time.time()
                },
                headers={"X-Correlation-ID": correlation_id}
            )
        
        @self.app.exception_handler(Exception)
        async def general_exception_handler(request: Request, exc: Exception):
            correlation_id = getattr(request.state, 'correlation_id', 'unknown')
            
            # Enhanced general exception logging with full context
            self.contextual_logger.error(
                f"Unhandled exception: {str(exc)}",
                extra={
                    "event_type": "unhandled_exception",
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                    "path": request.url.path,
                    "method": request.method,
                    "correlation_id": correlation_id
                },
                exc_info=True
            )
            
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "error_code": 500,
                    "message": "Internal server error",
                    "correlation_id": correlation_id,
                    "service": self.service_name,
                    "timestamp": time.time()
                },
                headers={"X-Correlation-ID": correlation_id}
            )
    
    async def startup(self):
        """Override this method for service-specific startup logic"""
        self.logger.info(f"{self.service_name} startup completed")
    
    async def shutdown(self):
        """Override this method for service-specific shutdown logic"""
        self.logger.info(f"{self.service_name} shutdown completed")
    
    def get_logger(self):
        """Get the service logger for use in service implementations"""
        return self.logger
    
    def get_contextual_logger(self):
        """Get the contextual logger for use in service implementations"""
        return self.contextual_logger

def create_standard_response(
    status: str = "success",
    data: Any = None,
    message: Optional[str] = None,
    metadata: Optional[Dict] = None
) -> Dict[str, Any]:
    """Create standardized API response format"""
    response = {
        "status": status,
        "timestamp": time.time()
    }
    
    if data is not None:
        response["data"] = data
    
    if message:
        response["message"] = message
    
    if metadata:
        response["metadata"] = metadata
    
    return response

def create_error_response(
    message: str,
    code: int = 400,
    details: Optional[Dict] = None
) -> Dict[str, Any]:
    """Create standardized error response format"""
    response = {
        "status": "error",
        "error": {
            "code": code,
            "message": message
        },
        "timestamp": time.time()
    }
    
    if details:
        response["error"]["details"] = details
    
    return response