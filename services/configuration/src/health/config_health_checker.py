"""
Configuration-specific health checks.
"""
from typing import Dict, Any, Optional
import logging
from .health_checks import HealthChecker

logger = logging.getLogger(__name__)

class ConfigHealthChecker(HealthChecker):
    """Extended health checker for Configuration Service"""
    
    def __init__(self, service_name: str, version: str = "1.0.0"):
        super().__init__(service_name, version)
        self.config_manager = None
    
    def set_config_manager(self, config_manager):
        """Set the configuration manager for health checks"""
        self.config_manager = config_manager
    
    async def _service_specific_health_checks(self) -> Dict[str, Any]:
        """Configuration service specific health checks"""
        checks = {}
        
        try:
            # Check if config manager is initialized
            if self.config_manager is None:
                checks["config_manager"] = {
                    "status": "unhealthy",
                    "message": "Configuration manager not initialized"
                }
                return checks
            
            checks["config_manager"] = {
                "status": "healthy",
                "environment": self.config_manager.get_environment(),
                "message": "Configuration manager initialized"
            }
            
            # Check configuration domains
            domains = ["data", "league", "model", "position", "scoring"]
            domain_checks = {}
            
            for domain in domains:
                try:
                    config_obj = self.config_manager.get_config(domain)
                    # Test basic functionality
                    config_dict = config_obj.to_dict()
                    domain_checks[domain] = {
                        "status": "healthy",
                        "keys_count": len(config_dict),
                        "message": f"{domain.title()} config accessible"
                    }
                except Exception as e:
                    domain_checks[domain] = {
                        "status": "unhealthy",
                        "error": str(e),
                        "message": f"{domain.title()} config error"
                    }
            
            checks["config_domains"] = domain_checks
            
            # Check critical configuration values
            critical_checks = {}
            
            try:
                # Check positions
                all_positions = self.config_manager.get_all_positions()
                core_positions = self.config_manager.get_core_positions()
                
                critical_checks["positions"] = {
                    "status": "healthy" if all_positions and core_positions else "unhealthy",
                    "all_positions_count": len(all_positions),
                    "core_positions_count": len(core_positions),
                    "all_positions": all_positions,
                    "core_positions": core_positions
                }
                
                # Check league settings
                league_summary = self.config_manager.get_league_summary()
                critical_checks["league"] = {
                    "status": "healthy" if league_summary else "unhealthy",
                    "summary": league_summary
                }
                
                # Check data configuration
                data_summary = self.config_manager.get_data_summary()
                critical_checks["data"] = {
                    "status": "healthy" if data_summary else "unhealthy",
                    "summary": data_summary
                }
                
            except Exception as e:
                critical_checks["error"] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "message": "Error checking critical configurations"
                }
            
            checks["critical_configs"] = critical_checks
            
            # Overall status
            all_healthy = all(
                check.get("status") == "healthy" 
                for check in checks.values() 
                if isinstance(check, dict) and "status" in check
            )
            
            if not all_healthy:
                # Check domain statuses
                domain_healthy = all(
                    domain_check.get("status") == "healthy"
                    for domain_check in domain_checks.values()
                )
                
                critical_healthy = all(
                    crit_check.get("status") == "healthy"
                    for crit_check in critical_checks.values()
                    if isinstance(crit_check, dict) and "status" in crit_check
                )
                
                if not domain_healthy or not critical_healthy:
                    checks["overall_status"] = {"status": "unhealthy"}
            
        except Exception as e:
            logger.error(f"Error in configuration health checks: {e}")
            checks["health_check_error"] = {
                "status": "unhealthy",
                "error": str(e),
                "message": "Failed to perform health checks"
            }
        
        return checks
    
    async def _service_specific_metrics(self) -> Dict[str, Any]:
        """Configuration service specific metrics"""
        metrics = {}
        
        try:
            if self.config_manager is None:
                metrics["config_manager_initialized"] = False
                return metrics
            
            metrics["config_manager_initialized"] = True
            metrics["environment"] = self.config_manager.get_environment()
            
            # Count configurations by domain
            domains = ["data", "league", "model", "position", "scoring"]
            domain_metrics = {}
            
            for domain in domains:
                try:
                    config_obj = self.config_manager.get_config(domain)
                    config_dict = config_obj.to_dict()
                    domain_metrics[f"{domain}_keys_count"] = len(config_dict)
                    domain_metrics[f"{domain}_status"] = "healthy"
                except Exception as e:
                    domain_metrics[f"{domain}_keys_count"] = 0
                    domain_metrics[f"{domain}_status"] = "error"
                    domain_metrics[f"{domain}_error"] = str(e)
            
            metrics.update(domain_metrics)
            
            # Configuration summary metrics
            try:
                metrics["total_positions"] = len(self.config_manager.get_all_positions())
                metrics["core_positions"] = len(self.config_manager.get_core_positions())
                
                league_summary = self.config_manager.get_league_summary()
                metrics["league_size"] = league_summary.get("league_size", 0)
                metrics["ppr_scoring"] = league_summary.get("ppr_scoring", 0)
                
                data_summary = self.config_manager.get_data_summary()
                if "data_years" in data_summary:
                    metrics["data_years_range"] = data_summary["data_years"]
                if "training_years" in data_summary:
                    metrics["training_years_range"] = data_summary["training_years"]
                
            except Exception as e:
                logger.warning(f"Error collecting configuration metrics: {e}")
                metrics["metrics_collection_error"] = str(e)
        
        except Exception as e:
            logger.error(f"Error in configuration metrics collection: {e}")
            metrics["metrics_error"] = str(e)
        
        return metrics