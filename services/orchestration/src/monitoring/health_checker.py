"""
Health Checker - Monitor service health across the microservices architecture.

This module provides comprehensive health monitoring including:
- Service availability checking
- Response time monitoring  
- Health trend analysis
- Dependency checking
"""

import logging
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class HealthChecker:
    """
    Monitor health of all microservices in the fantasy football architecture.
    
    Provides comprehensive health checking including liveness, readiness, and deep checks.
    """
    
    def __init__(self, service_urls: Dict[str, str]):
        """
        Initialize health checker.
        
        Args:
            service_urls: Dictionary mapping service names to URLs
        """
        self.service_urls = service_urls
        self.health_history = {}
        self.last_check_time = None
        
        # Health check endpoints by depth
        self.health_endpoints = {
            "live": "/health/live",
            "ready": "/health/ready",
            "deep": "/health/deep",
            "metrics": "/health/metrics"
        }
        
        logger.info("🏥 Health Checker initialized")
    
    async def initialize(self):
        """Initialize health checker with initial checks."""
        try:
            logger.info("🔍 Performing initial health checks...")
            
            # Initialize health history for each service
            for service_name in self.service_urls.keys():
                self.health_history[service_name] = []
            
            # Perform initial health check
            await self.check_all_services()
            
            logger.info("✅ Health checker initialized")
        
        except Exception as e:
            logger.error(f"Failed to initialize health checker: {e}")
    
    async def check_all_services(self, check_type: str = "live") -> Dict[str, Any]:
        """
        Check health of all services.
        
        Args:
            check_type: Type of health check (live, ready, deep, metrics)
            
        Returns:
            Dictionary containing health status for all services
        """
        try:
            logger.info(f"🔍 Checking {check_type} health for all services...")
            
            health_results = {}
            
            # Check each service concurrently
            tasks = []
            for service_name, service_url in self.service_urls.items():
                task = self._check_service_health(service_name, service_url, check_type)
                tasks.append(task)
            
            # Wait for all checks to complete
            service_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for service_name, result in zip(self.service_urls.keys(), service_results):
                if isinstance(result, Exception):
                    health_results[service_name] = {
                        "healthy": False,
                        "error": str(result),
                        "check_type": check_type,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    health_results[service_name] = result
            
            # Update health history
            self._update_health_history(health_results)
            self.last_check_time = datetime.now()
            
            # Log summary
            healthy_count = sum(1 for result in health_results.values() if result.get("healthy", False))
            total_count = len(health_results)
            logger.info(f"📊 Health check complete: {healthy_count}/{total_count} services healthy")
            
            return health_results
        
        except Exception as e:
            logger.error(f"Failed to check all services: {e}")
            return {"error": str(e)}
    
    async def _check_service_health(self, service_name: str, service_url: str, 
                                  check_type: str) -> Dict[str, Any]:
        """Check health of a specific service."""
        try:
            endpoint = self.health_endpoints.get(check_type, "/health/live")
            url = f"{service_url}{endpoint}"
            
            start_time = datetime.now()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as response:
                    response_time = (datetime.now() - start_time).total_seconds() * 1000  # ms
                    
                    if response.status == 200:
                        try:
                            response_data = await response.json()
                        except:
                            response_data = {}
                        
                        return {
                            "healthy": True,
                            "status_code": response.status,
                            "response_time_ms": round(response_time, 2),
                            "check_type": check_type,
                            "service_url": service_url,
                            "endpoint": endpoint,
                            "response_data": response_data,
                            "timestamp": datetime.now().isoformat()
                        }
                    else:
                        return {
                            "healthy": False,
                            "status_code": response.status,
                            "response_time_ms": round(response_time, 2),
                            "error": f"HTTP {response.status}",
                            "check_type": check_type,
                            "service_url": service_url,
                            "endpoint": endpoint,
                            "timestamp": datetime.now().isoformat()
                        }
        
        except asyncio.TimeoutError:
            return {
                "healthy": False,
                "error": "Timeout",
                "check_type": check_type,
                "service_url": service_url,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "check_type": check_type,
                "service_url": service_url,
                "timestamp": datetime.now().isoformat()
            }
    
    async def comprehensive_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check across all endpoints."""
        try:
            logger.info("🔬 Performing comprehensive health check...")
            
            comprehensive_results = {
                "overall_status": "unknown",
                "check_timestamp": datetime.now().isoformat(),
                "services": {},
                "summary": {}
            }
            
            # Check each type of health endpoint
            for check_type in ["live", "ready", "deep"]:
                logger.info(f"  Checking {check_type} endpoints...")
                
                check_results = await self.check_all_services(check_type)
                
                for service_name, result in check_results.items():
                    if service_name not in comprehensive_results["services"]:
                        comprehensive_results["services"][service_name] = {}
                    
                    comprehensive_results["services"][service_name][check_type] = result
            
            # Calculate summary statistics
            total_services = len(comprehensive_results["services"])
            healthy_services = 0
            
            for service_name, service_checks in comprehensive_results["services"].items():
                # Service is healthy if all checks pass
                all_healthy = all(
                    check_result.get("healthy", False) 
                    for check_result in service_checks.values()
                )
                
                if all_healthy:
                    healthy_services += 1
            
            # Determine overall status
            if healthy_services == total_services:
                comprehensive_results["overall_status"] = "healthy"
            elif healthy_services == 0:
                comprehensive_results["overall_status"] = "unhealthy"
            else:
                comprehensive_results["overall_status"] = "degraded"
            
            comprehensive_results["summary"] = {
                "total_services": total_services,
                "healthy_services": healthy_services,
                "unhealthy_services": total_services - healthy_services,
                "health_percentage": round((healthy_services / total_services) * 100, 1) if total_services > 0 else 0
            }
            
            logger.info(f"📊 Comprehensive health check complete: {comprehensive_results['overall_status']} ({comprehensive_results['summary']['health_percentage']}% healthy)")
            
            return comprehensive_results
        
        except Exception as e:
            logger.error(f"Comprehensive health check failed: {e}")
            return {
                "overall_status": "error",
                "error": str(e),
                "check_timestamp": datetime.now().isoformat()
            }
    
    async def check_service_dependencies(self, service_name: str) -> Dict[str, Any]:
        """Check dependencies for a specific service."""
        try:
            logger.info(f"🔗 Checking dependencies for {service_name}...")
            
            # Service dependency map
            dependencies = {
                "data-ingestion": ["configuration"],
                "feature-engineering": ["configuration", "data-ingestion"],
                "ml-models": ["configuration", "feature-engineering"],
                "ranking": ["configuration", "ml-models"],
                "orchestration": ["configuration", "data-ingestion", "feature-engineering", "ml-models", "ranking"]
            }
            
            service_dependencies = dependencies.get(service_name, [])
            
            if not service_dependencies:
                return {
                    "service": service_name,
                    "dependencies": [],
                    "all_dependencies_healthy": True,
                    "message": "No dependencies"
                }
            
            dependency_results = {}
            all_healthy = True
            
            # Check each dependency
            for dep_service in service_dependencies:
                if dep_service in self.service_urls:
                    dep_result = await self._check_service_health(dep_service, self.service_urls[dep_service], "ready")
                    dependency_results[dep_service] = dep_result
                    
                    if not dep_result.get("healthy", False):
                        all_healthy = False
                else:
                    dependency_results[dep_service] = {
                        "healthy": False,
                        "error": "Service URL not configured"
                    }
                    all_healthy = False
            
            return {
                "service": service_name,
                "dependencies": service_dependencies,
                "dependency_results": dependency_results,
                "all_dependencies_healthy": all_healthy,
                "check_timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Failed to check dependencies for {service_name}: {e}")
            return {
                "service": service_name,
                "error": str(e),
                "all_dependencies_healthy": False
            }
    
    def _update_health_history(self, health_results: Dict[str, Any]):
        """Update health history for trend analysis."""
        try:
            current_time = datetime.now()
            
            for service_name, result in health_results.items():
                if service_name not in self.health_history:
                    self.health_history[service_name] = []
                
                # Add current result to history
                history_entry = {
                    "timestamp": current_time.isoformat(),
                    "healthy": result.get("healthy", False),
                    "response_time_ms": result.get("response_time_ms"),
                    "status_code": result.get("status_code"),
                    "error": result.get("error")
                }
                
                self.health_history[service_name].append(history_entry)
                
                # Keep only last 100 entries per service
                if len(self.health_history[service_name]) > 100:
                    self.health_history[service_name] = self.health_history[service_name][-100:]
        
        except Exception as e:
            logger.error(f"Failed to update health history: {e}")
    
    async def get_health_trends(self, service_name: Optional[str] = None, 
                              hours: int = 24) -> Dict[str, Any]:
        """Get health trends over time."""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            trends = {}
            
            services_to_check = [service_name] if service_name else self.health_history.keys()
            
            for svc_name in services_to_check:
                if svc_name not in self.health_history:
                    continue
                
                # Filter history by time window
                recent_history = [
                    entry for entry in self.health_history[svc_name]
                    if datetime.fromisoformat(entry["timestamp"]) >= cutoff_time
                ]
                
                if not recent_history:
                    continue
                
                # Calculate trend metrics
                total_checks = len(recent_history)
                healthy_checks = sum(1 for entry in recent_history if entry["healthy"])
                
                response_times = [entry["response_time_ms"] for entry in recent_history 
                                if entry["response_time_ms"] is not None]
                
                trends[svc_name] = {
                    "total_checks": total_checks,
                    "healthy_checks": healthy_checks,
                    "uptime_percentage": round((healthy_checks / total_checks) * 100, 2),
                    "avg_response_time_ms": round(sum(response_times) / len(response_times), 2) if response_times else None,
                    "max_response_time_ms": max(response_times) if response_times else None,
                    "min_response_time_ms": min(response_times) if response_times else None,
                    "time_window_hours": hours
                }
            
            return {
                "trends": trends,
                "generated_at": datetime.now().isoformat(),
                "time_window_hours": hours
            }
        
        except Exception as e:
            logger.error(f"Failed to get health trends: {e}")
            return {"error": str(e)}
    
    async def get_current_status(self) -> Dict[str, Any]:
        """Get current health status summary."""
        try:
            return {
                "health_checker_status": "active",
                "monitored_services": list(self.service_urls.keys()),
                "last_check_time": self.last_check_time.isoformat() if self.last_check_time else None,
                "health_history_entries": {service: len(history) for service, history in self.health_history.items()},
                "available_endpoints": list(self.health_endpoints.keys())
            }
        
        except Exception as e:
            logger.error(f"Failed to get current status: {e}")
            return {"error": str(e)}