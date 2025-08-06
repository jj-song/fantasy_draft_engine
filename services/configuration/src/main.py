"""
Configuration Service - Centralized configuration management for Fantasy Football microservices.
"""
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse

from .api.base_api import BaseService, create_standard_response, create_error_response
from .managers.config_manager import ConfigManager, get_config
from .health.config_health_checker import ConfigHealthChecker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConfigurationService(BaseService):
    def __init__(self):
        super().__init__(
            service_name="Configuration Service",
            version="1.0.0",
            description="Centralized configuration management for Fantasy Football microservices"
        )
        
        self.config_manager: Optional[ConfigManager] = None
        self.health_checker = ConfigHealthChecker("Configuration Service", "1.0.0")
        
        # Override health endpoints with config-specific health checker
        self.app.health_checker = self.health_checker
        
        self._setup_routes()
    
    async def startup(self):
        """Initialize configuration manager on startup"""
        try:
            self.config_manager = get_config()
            self.health_checker.set_config_manager(self.config_manager)
            logger.info("Configuration Service started successfully")
        except Exception as e:
            logger.error(f"Failed to start Configuration Service: {e}")
            raise
    
    async def shutdown(self):
        """Cleanup on shutdown"""
        logger.info("Configuration Service shutting down")
    
    def _setup_routes(self):
        """Set up API routes for configuration service"""
        
        @self.app.get("/api/v1/config/{domain}")
        async def get_domain_config(domain: str):
            """Get complete configuration for a specific domain"""
            try:
                if not self.config_manager:
                    raise HTTPException(status_code=503, detail="Configuration manager not initialized")
                
                config_obj = self.config_manager.get_config(domain)
                config_dict = config_obj.to_dict()
                
                return create_standard_response(
                    data=config_dict,
                    metadata={"domain": domain, "service": "configuration"}
                )
                
            except ValueError as e:
                raise HTTPException(status_code=404, detail=f"Domain not found: {domain}")
            except Exception as e:
                logger.error(f"Error getting domain config {domain}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/config/{domain}/{key:path}")
        async def get_config_value(domain: str, key: str, default: Optional[str] = None):
            """Get specific configuration value"""
            try:
                if not self.config_manager:
                    raise HTTPException(status_code=503, detail="Configuration manager not initialized")
                
                full_key = f"{domain}.{key}"
                value = self.config_manager.get(full_key, default)
                
                if value is None and default is None:
                    raise HTTPException(status_code=404, detail=f"Configuration key not found: {full_key}")
                
                return create_standard_response(
                    data={"key": full_key, "value": value},
                    metadata={"domain": domain, "service": "configuration"}
                )
                
            except Exception as e:
                logger.error(f"Error getting config value {domain}.{key}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.put("/api/v1/config/{domain}/{key:path}")
        async def set_config_value(domain: str, key: str, request_body: Dict[str, Any]):
            """Set configuration value"""
            try:
                if not self.config_manager:
                    raise HTTPException(status_code=503, detail="Configuration manager not initialized")
                
                if "value" not in request_body:
                    raise HTTPException(status_code=400, detail="Request body must contain 'value' field")
                
                full_key = f"{domain}.{key}"
                value = request_body["value"]
                
                self.config_manager.set(full_key, value)
                
                return create_standard_response(
                    data={"key": full_key, "value": value, "updated": True},
                    message="Configuration updated successfully",
                    metadata={"domain": domain, "service": "configuration"}
                )
                
            except Exception as e:
                logger.error(f"Error setting config value {domain}.{key}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/config/summary")
        async def get_config_summary():
            """Get summary of all configurations"""
            try:
                if not self.config_manager:
                    raise HTTPException(status_code=503, detail="Configuration manager not initialized")
                
                summary = {
                    "environment": self.config_manager.get_environment(),
                    "data": self.config_manager.get_data_summary(),
                    "league": self.config_manager.get_league_summary(),
                    "model": self.config_manager.get_model_summary(),
                    "positions": {
                        "all": self.config_manager.get_all_positions(),
                        "core": self.config_manager.get_core_positions()
                    }
                }
                
                return create_standard_response(
                    data=summary,
                    metadata={"service": "configuration"}
                )
                
            except Exception as e:
                logger.error(f"Error getting config summary: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/config/reload")
        async def reload_config():
            """Reload configuration from files and environment"""
            try:
                if not self.config_manager:
                    raise HTTPException(status_code=503, detail="Configuration manager not initialized")
                
                self.config_manager.reload_configs()
                
                return create_standard_response(
                    data={"reloaded": True},
                    message="Configuration reloaded successfully",
                    metadata={"service": "configuration"}
                )
                
            except Exception as e:
                logger.error(f"Error reloading config: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/positions")
        async def get_positions():
            """Get supported positions"""
            try:
                if not self.config_manager:
                    raise HTTPException(status_code=503, detail="Configuration manager not initialized")
                
                return create_standard_response(
                    data={
                        "all_positions": self.config_manager.get_all_positions(),
                        "core_positions": self.config_manager.get_core_positions()
                    },
                    metadata={"service": "configuration"}
                )
                
            except Exception as e:
                logger.error(f"Error getting positions: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/scoring/system")
        async def get_scoring_system():
            """Get current scoring system configuration"""
            try:
                if not self.config_manager:
                    raise HTTPException(status_code=503, detail="Configuration manager not initialized")
                
                scoring_config = self.config_manager.get_config('scoring')
                
                return create_standard_response(
                    data={
                        "scoring_system": scoring_config.get_scoring_system(),
                        "ppr_value": scoring_config.fantasy_points.get('receptions', 0),
                        "system_name": scoring_config.default_scoring_system
                    },
                    metadata={"service": "configuration"}
                )
                
            except Exception as e:
                logger.error(f"Error getting scoring system: {e}")
                raise HTTPException(status_code=500, detail=str(e))

# Create service instance
service = ConfigurationService()
app = service.app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)