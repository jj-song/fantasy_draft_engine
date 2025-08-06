"""
Standardized health check framework for all microservices.
"""
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import HTTPException
from pydantic import BaseModel
import asyncio
import psutil
import logging

logger = logging.getLogger(__name__)

class HealthStatus(BaseModel):
    status: str
    timestamp: datetime
    service_name: str
    version: str
    details: Optional[Dict[str, Any]] = None

class HealthChecker:
    def __init__(self, service_name: str, version: str = "1.0.0"):
        self.service_name = service_name
        self.version = version
        
    async def liveness_check(self) -> HealthStatus:
        """Basic liveness check - is the service running?"""
        return HealthStatus(
            status="healthy",
            timestamp=datetime.utcnow(),
            service_name=self.service_name,
            version=self.version
        )
    
    async def readiness_check(self) -> HealthStatus:
        """Readiness check - can the service accept traffic?"""
        details = {}
        status = "ready"
        
        try:
            # Check basic system resources
            memory_usage = psutil.virtual_memory().percent
            cpu_usage = psutil.cpu_percent(interval=1)
            disk_usage = psutil.disk_usage('/').percent
            
            details.update({
                "memory_usage_percent": memory_usage,
                "cpu_usage_percent": cpu_usage,
                "disk_usage_percent": disk_usage
            })
            
            # Basic resource checks
            if memory_usage > 90 or cpu_usage > 95 or disk_usage > 95:
                status = "not_ready"
                
        except Exception as e:
            logger.error(f"Error in readiness check: {e}")
            status = "not_ready"
            details["error"] = str(e)
            
        return HealthStatus(
            status=status,
            timestamp=datetime.utcnow(),
            service_name=self.service_name,
            version=self.version,
            details=details
        )
    
    async def deep_health_check(self) -> HealthStatus:
        """Deep health check - comprehensive service validation"""
        details = {}
        status = "healthy"
        
        try:
            # System metrics
            memory_info = psutil.virtual_memory()
            details.update({
                "memory": {
                    "total_gb": round(memory_info.total / (1024**3), 2),
                    "available_gb": round(memory_info.available / (1024**3), 2),
                    "used_percent": memory_info.percent
                },
                "cpu_count": psutil.cpu_count(),
                "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
            })
            
            # Service-specific checks (to be overridden)
            service_checks = await self._service_specific_health_checks()
            details.update(service_checks)
            
            # Determine overall status
            if any(check.get("status") == "unhealthy" for check in service_checks.values() if isinstance(check, dict)):
                status = "unhealthy"
                
        except Exception as e:
            logger.error(f"Error in deep health check: {e}")
            status = "unhealthy"
            details["error"] = str(e)
            
        return HealthStatus(
            status=status,
            timestamp=datetime.utcnow(),
            service_name=self.service_name,
            version=self.version,
            details=details
        )
    
    async def metrics(self) -> Dict[str, Any]:
        """Service metrics for monitoring"""
        try:
            base_metrics = {
                "timestamp": datetime.utcnow().isoformat(),
                "service_name": self.service_name,
                "version": self.version,
                "uptime_seconds": self._get_uptime_seconds(),
                "memory_usage_bytes": psutil.virtual_memory().used,
                "cpu_usage_percent": psutil.cpu_percent(),
            }
            
            # Service-specific metrics (to be overridden)
            service_metrics = await self._service_specific_metrics()
            base_metrics.update(service_metrics)
            
            return base_metrics
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return {"error": str(e)}
    
    async def _service_specific_health_checks(self) -> Dict[str, Any]:
        """Override this method in service implementations"""
        return {"service_specific": {"status": "healthy", "message": "No specific checks defined"}}
    
    async def _service_specific_metrics(self) -> Dict[str, Any]:
        """Override this method in service implementations"""
        return {}
    
    def _get_uptime_seconds(self) -> float:
        """Get service uptime in seconds"""
        try:
            return psutil.boot_time()
        except:
            return 0.0

# Error handling decorators
def handle_health_check_errors(func):
    """Decorator to handle health check errors gracefully"""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Health check error in {func.__name__}: {e}")
            return HealthStatus(
                status="error",
                timestamp=datetime.utcnow(),
                service_name="unknown",
                version="unknown",
                details={"error": str(e)}
            )
    return wrapper