"""
Configuration Service - Centralized configuration management for Fantasy Football microservices.
"""
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from .api.base_api import BaseService, create_standard_response, create_error_response
from .managers.config_manager import ConfigManager, get_config
from .health.config_health_checker import ConfigHealthChecker

# Import validation framework with robust path resolution
VALIDATION_AVAILABLE = False
config_validator = None

try:
    # Try multiple path resolution approaches for Docker compatibility
    import os
    
    # Method 1: Try relative to current file
    project_root = Path(__file__).parent.parent.parent.parent
    utils_path = project_root / "utils"
    
    if utils_path.exists():
        sys.path.insert(0, str(project_root))
        from utils.debug_analysis.debug_integration import config_validator
        VALIDATION_AVAILABLE = True
        logger.info(f"Configuration validation framework loaded successfully from {project_root}")
    else:
        # Method 2: Try from working directory 
        cwd_project_root = Path.cwd()
        if cwd_project_root.name != "fantasy_draft_engine":
            # Look for fantasy_draft_engine in parent directories
            current = cwd_project_root
            for _ in range(5):  # Max 5 levels up
                if current.name == "fantasy_draft_engine":
                    cwd_project_root = current
                    break
                current = current.parent
        
        cwd_utils_path = cwd_project_root / "utils"
        if cwd_utils_path.exists():
            sys.path.insert(0, str(cwd_project_root))
            from utils.debug_analysis.debug_integration import config_validator
            VALIDATION_AVAILABLE = True
            logger.info(f"Configuration validation framework loaded from working directory: {cwd_project_root}")
        else:
            # Method 3: Try environment variable if set
            env_project_root = os.environ.get('FANTASY_DRAFT_ENGINE_ROOT')
            if env_project_root:
                env_utils_path = Path(env_project_root) / "utils"
                if env_utils_path.exists():
                    sys.path.insert(0, env_project_root)
                    from utils.debug_analysis.debug_integration import config_validator
                    VALIDATION_AVAILABLE = True
                    logger.info(f"Configuration validation framework loaded from environment: {env_project_root}")
                    
except Exception as e:
    VALIDATION_AVAILABLE = False
    logger.warning(f"Validation framework not available after trying multiple paths: {e}")

if not VALIDATION_AVAILABLE:
    logger.info("Validation framework unavailable - service will run without enhanced validation logging")

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
            # Step 1: Initialize configuration manager
            self.config_manager = get_config()
            logger.info("Configuration manager initialized")
            
            # Validate configuration manager initialization
            if VALIDATION_AVAILABLE:
                config_validator.validate_config_manager_initialization(
                    self.config_manager, 
                    environment=self.config_manager.get_environment()
                )
            
            # Step 2: Validate domain access
            domain_configs = {}
            for domain in ["data", "league", "model", "position", "scoring"]:
                try:
                    domain_configs[domain] = self.config_manager.get_config(domain)
                    logger.info(f"Successfully accessed {domain} configuration")
                except Exception as e:
                    logger.error(f"Failed to access {domain} configuration: {e}")
                    domain_configs[domain] = None
            
            if VALIDATION_AVAILABLE:
                config_validator.validate_domain_access(domain_configs)
            
            # Step 3: Set up health checker
            self.health_checker.set_config_manager(self.config_manager)
            logger.info("Health checker configured with configuration manager")
            
            # Step 4: Validate health checks
            if VALIDATION_AVAILABLE:
                health_data = await self.health_checker._service_specific_health_checks()
                config_validator.validate_health_checks(health_data)
            
            logger.info("Configuration Service started successfully with validation")
            
        except Exception as e:
            logger.error(f"Failed to start Configuration Service: {e}")
            
            # Log validation checkpoint even on failure
            if VALIDATION_AVAILABLE:
                config_validator.checkpoint("startup_failure", {"error": str(e), "service": "configuration"})
            
            raise
    
    async def shutdown(self):
        """Cleanup on shutdown"""
        logger.info("Configuration Service shutting down")
    
    def _setup_routes(self):
        """Set up API routes for configuration service"""
        
        # Register summary endpoint with a completely different path to avoid conflicts
        @self.app.get("/api/v1/configuration/summary")
        async def get_config_summary():
            """Get summary of all configurations"""
            try:
                if not self.config_manager:
                    raise HTTPException(status_code=503, detail="Configuration manager not initialized")
                
                logger.info("Generating configuration summary")
                
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
                
                # Validate the summary data
                if VALIDATION_AVAILABLE:
                    config_validator.checkpoint("config_summary_generation", summary,
                                              expected_type=dict,
                                              expected_keys=['environment', 'data', 'league', 'model', 'positions'])
                
                response = create_standard_response(
                    data=summary,
                    metadata={"service": "configuration"}
                )
                
                logger.info("Configuration summary generated successfully")
                return response
                
            except Exception as e:
                logger.error(f"Error getting config summary: {e}")
                
                # Log validation checkpoint for failure
                if VALIDATION_AVAILABLE:
                    config_validator.checkpoint("config_summary_error", {"error": str(e)})
                
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
        
        @self.app.get("/api/v1/config/{domain}")
        async def get_domain_config(domain: str):
            """Get complete configuration for a specific domain"""
            try:
                if not self.config_manager:
                    raise HTTPException(status_code=503, detail="Configuration manager not initialized")
                
                # Prevent conflicts with reserved endpoints
                reserved_domains = ["summary", "reload", "validate"]
                if domain in reserved_domains:
                    raise HTTPException(status_code=404, detail=f"Reserved endpoint name: {domain}")
                
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
        
        @self.app.get("/api/v1/positions")
        async def get_positions():
            """Get supported positions"""
            try:
                if not self.config_manager:
                    raise HTTPException(status_code=503, detail="Configuration manager not initialized")
                
                logger.info("Retrieving positions configuration")
                
                positions_data = {
                    "all_positions": self.config_manager.get_all_positions(),
                    "core_positions": self.config_manager.get_core_positions()
                }
                
                # Validate positions data
                if VALIDATION_AVAILABLE:
                    config_validator.validate_positions_config(positions_data)
                
                response = create_standard_response(
                    data=positions_data,
                    metadata={"service": "configuration"}
                )
                
                logger.info(f"Positions retrieved: all={len(positions_data['all_positions'])}, core={len(positions_data['core_positions'])}")
                return response
                
            except Exception as e:
                logger.error(f"Error getting positions: {e}")
                
                if VALIDATION_AVAILABLE:
                    config_validator.checkpoint("positions_error", {"error": str(e)})
                
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/scoring/system")
        async def get_scoring_system():
            """Get current scoring system configuration"""
            try:
                if not self.config_manager:
                    raise HTTPException(status_code=503, detail="Configuration manager not initialized")
                
                logger.info("Retrieving scoring system configuration")
                
                scoring_config = self.config_manager.get_config('scoring')
                
                scoring_data = {
                    "scoring_system": scoring_config.get_scoring_system(),
                    "ppr_value": scoring_config.fantasy_points.get('receptions', 0),
                    "system_name": scoring_config.default_scoring_system
                }
                
                # Validate scoring system data
                if VALIDATION_AVAILABLE:
                    config_validator.validate_scoring_system(scoring_data)
                
                response = create_standard_response(
                    data=scoring_data,
                    metadata={"service": "configuration"}
                )
                
                logger.info(f"Scoring system retrieved: {scoring_data['system_name']} (PPR: {scoring_data['ppr_value']})")
                return response
                
            except Exception as e:
                logger.error(f"Error getting scoring system: {e}")
                
                if VALIDATION_AVAILABLE:
                    config_validator.checkpoint("scoring_system_error", {"error": str(e)})
                
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/configuration/validate")
        async def validate_configuration_service():
            """Comprehensive validation endpoint for configuration service"""
            try:
                logger.info("Starting comprehensive configuration service validation")
                
                validation_results = {
                    "timestamp": "2025-08-06T19:20:00Z",
                    "service": "configuration",
                    "validation_steps": [],
                    "success_count": 0,
                    "failure_count": 0
                }
                
                # Test 1: Configuration Manager Initialization
                try:
                    if self.config_manager and hasattr(self.config_manager, 'get_environment'):
                        env = self.config_manager.get_environment()
                        validation_results["validation_steps"].append({
                            "step": "config_manager_initialization",
                            "status": "PASS",
                            "details": {"environment": env}
                        })
                        validation_results["success_count"] += 1
                    else:
                        validation_results["validation_steps"].append({
                            "step": "config_manager_initialization", 
                            "status": "FAIL",
                            "details": {"error": "Configuration manager not properly initialized"}
                        })
                        validation_results["failure_count"] += 1
                except Exception as e:
                    validation_results["validation_steps"].append({
                        "step": "config_manager_initialization",
                        "status": "ERROR", 
                        "details": {"error": str(e)}
                    })
                    validation_results["failure_count"] += 1
                
                # Test 2: Positions Configuration
                try:
                    positions_response = await get_positions()
                    if positions_response and 'data' in positions_response:
                        all_positions = positions_response['data'].get('all_positions', [])
                        core_positions = positions_response['data'].get('core_positions', [])
                        validation_results["validation_steps"].append({
                            "step": "positions_configuration",
                            "status": "PASS",
                            "details": {
                                "all_positions_count": len(all_positions),
                                "core_positions_count": len(core_positions),
                                "expected_core": ["QB", "RB", "WR", "TE"],
                                "actual_core": core_positions
                            }
                        })
                        validation_results["success_count"] += 1
                    else:
                        validation_results["validation_steps"].append({
                            "step": "positions_configuration",
                            "status": "FAIL",
                            "details": {"error": "Invalid positions response format"}
                        })
                        validation_results["failure_count"] += 1
                except Exception as e:
                    validation_results["validation_steps"].append({
                        "step": "positions_configuration",
                        "status": "ERROR",
                        "details": {"error": str(e)}
                    })
                    validation_results["failure_count"] += 1
                
                # Test 3: Scoring System Configuration
                try:
                    scoring_response = await get_scoring_system()
                    if scoring_response and 'data' in scoring_response:
                        ppr_value = scoring_response['data'].get('ppr_value')
                        system_name = scoring_response['data'].get('system_name')
                        scoring_system = scoring_response['data'].get('scoring_system', {})
                        
                        # Validate key scoring values
                        expected_values = {
                            'passing_yards': 0.04,
                            'passing_tds': 4,
                            'rushing_tds': 6,
                            'receiving_tds': 6,
                            'receptions': 0.5
                        }
                        
                        matches_expected = all(
                            scoring_system.get(key) == value 
                            for key, value in expected_values.items()
                        )
                        
                        validation_results["validation_steps"].append({
                            "step": "scoring_system_configuration",
                            "status": "PASS" if matches_expected and ppr_value == 0.5 else "FAIL",
                            "details": {
                                "ppr_value": ppr_value,
                                "system_name": system_name,
                                "claude_md_compliance": matches_expected and ppr_value == 0.5,
                                "scoring_keys": list(scoring_system.keys())
                            }
                        })
                        if matches_expected and ppr_value == 0.5:
                            validation_results["success_count"] += 1
                        else:
                            validation_results["failure_count"] += 1
                    else:
                        validation_results["validation_steps"].append({
                            "step": "scoring_system_configuration",
                            "status": "FAIL",
                            "details": {"error": "Invalid scoring response format"}
                        })
                        validation_results["failure_count"] += 1
                except Exception as e:
                    validation_results["validation_steps"].append({
                        "step": "scoring_system_configuration",
                        "status": "ERROR",
                        "details": {"error": str(e)}
                    })
                    validation_results["failure_count"] += 1
                
                # Test 4: Domain Access
                domain_test_results = {}
                for domain in ["data", "league", "model", "position", "scoring"]:
                    try:
                        config_obj = self.config_manager.get_config(domain)
                        config_dict = config_obj.to_dict() if config_obj else {}
                        domain_test_results[domain] = {
                            "accessible": True,
                            "keys_count": len(config_dict)
                        }
                    except Exception as e:
                        domain_test_results[domain] = {
                            "accessible": False,
                            "error": str(e)
                        }
                
                accessible_domains = sum(1 for result in domain_test_results.values() if result.get("accessible", False))
                validation_results["validation_steps"].append({
                    "step": "domain_access",
                    "status": "PASS" if accessible_domains == 5 else "FAIL",
                    "details": {
                        "accessible_domains": accessible_domains,
                        "total_domains": 5,
                        "domain_results": domain_test_results
                    }
                })
                if accessible_domains == 5:
                    validation_results["success_count"] += 1
                else:
                    validation_results["failure_count"] += 1
                
                # Calculate overall results
                total_tests = validation_results["success_count"] + validation_results["failure_count"]
                success_rate = validation_results["success_count"] / total_tests if total_tests > 0 else 0
                
                validation_results.update({
                    "total_tests": total_tests,
                    "success_rate": success_rate,
                    "overall_status": "PASS" if success_rate >= 0.8 else "FAIL"
                })
                
                logger.info(f"Configuration service validation completed: {validation_results['success_count']}/{total_tests} tests passed")
                
                return create_standard_response(
                    data=validation_results,
                    message=f"Configuration service validation completed: {validation_results['success_count']}/{total_tests} tests passed",
                    metadata={"service": "configuration"}
                )
                
            except Exception as e:
                logger.error(f"Error during configuration service validation: {e}")
                raise HTTPException(status_code=500, detail=str(e))

# Create service instance
service = ConfigurationService()
app = service.app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)