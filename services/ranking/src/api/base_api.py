"""
Base API template for all microservices with standardized patterns.
"""
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time
import uuid
from typing import Dict, Any, Optional
import traceback

from ..health.health_checks import HealthChecker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
        self.health_checker = HealthChecker(service_name, version)
        
        # Create FastAPI app with lifespan management
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            logger.info(f"Starting {service_name} service v{version}")
            await self.startup()
            yield
            # Shutdown
            logger.info(f"Shutting down {service_name} service")
            await self.shutdown()
        
        self.app = FastAPI(
            title=service_name,
            version=version,
            description=description,
            lifespan=lifespan
        )
        
        self._setup_middleware()
        self._setup_health_endpoints()
        self._setup_error_handlers()
    
    def _setup_middleware(self):
        """Set up standard middleware for all services"""
        
        # CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Request logging middleware
        @self.app.middleware("http")
        async def log_requests(request: Request, call_next):
            correlation_id = str(uuid.uuid4())
            start_time = time.time()
            
            # Add correlation ID to request state
            request.state.correlation_id = correlation_id
            
            # Log request
            logger.info(
                f"Request started: {request.method} {request.url.path} "
                f"[correlation_id: {correlation_id}]"
            )
            
            response = await call_next(request)
            
            # Log response
            duration = time.time() - start_time
            logger.info(
                f"Request completed: {request.method} {request.url.path} "
                f"Status: {response.status_code} Duration: {duration:.3f}s "
                f"[correlation_id: {correlation_id}]"
            )
            
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            
            return response
    
    def _setup_health_endpoints(self):
        """Set up standardized health check endpoints"""
        
        @self.app.get("/health/live")
        async def liveness_check():
            result = await self.health_checker.liveness_check()
            return result
        
        @self.app.get("/health/ready")
        async def readiness_check():
            result = await self.health_checker.readiness_check()
            if result.status != "ready":
                raise HTTPException(status_code=503, detail=result.dict())
            return result
        
        @self.app.get("/health/deep")
        async def deep_health_check():
            result = await self.health_checker.deep_health_check()
            if result.status == "unhealthy":
                raise HTTPException(status_code=503, detail=result.dict())
            return result
        
        @self.app.get("/health/metrics")
        async def metrics():
            result = await self.health_checker.metrics()
            return result
        
        @self.app.get("/api/v1/info")
        async def service_info():
            return {
                "service_name": self.service_name,
                "version": self.version,
                "description": self.description,
                "endpoints": [
                    "/health/live",
                    "/health/ready", 
                    "/health/deep",
                    "/health/metrics",
                    "/api/v1/info"
                ]
            }
    
    def _setup_error_handlers(self):
        """Set up standardized error handling"""
        
        @self.app.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, exc: HTTPException):
            correlation_id = getattr(request.state, 'correlation_id', 'unknown')
            
            error_response = {
                "status": "error",
                "error": {
                    "code": exc.status_code,
                    "message": exc.detail,
                    "correlation_id": correlation_id
                },
                "timestamp": time.time()
            }
            
            logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail} [correlation_id: {correlation_id}]")
            
            return JSONResponse(
                status_code=exc.status_code,
                content=error_response
            )
        
        @self.app.exception_handler(Exception)
        async def general_exception_handler(request: Request, exc: Exception):
            correlation_id = getattr(request.state, 'correlation_id', 'unknown')
            
            error_response = {
                "status": "error", 
                "error": {
                    "code": 500,
                    "message": "Internal server error",
                    "correlation_id": correlation_id
                },
                "timestamp": time.time()
            }
            
            logger.error(
                f"Unhandled exception: {type(exc).__name__}: {str(exc)} "
                f"[correlation_id: {correlation_id}]\n{traceback.format_exc()}"
            )
            
            return JSONResponse(
                status_code=500,
                content=error_response
            )
    
    async def startup(self):
        """Override this method for service-specific startup logic"""
        logger.info(f"{self.service_name} startup completed")
    
    async def shutdown(self):
        """Override this method for service-specific shutdown logic"""
        logger.info(f"{self.service_name} shutdown completed")

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