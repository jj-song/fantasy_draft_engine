"""
Full Pipeline Workflow - Orchestrate the complete data-to-rankings pipeline.

This workflow coordinates all services to run the complete fantasy football
pipeline from data ingestion through final ranking generation.
"""

import logging
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class FullPipelineWorkflow:
    """
    Orchestrate the complete fantasy football pipeline workflow.
    
    Coordinates data ingestion, feature engineering, model training/prediction,
    and ranking generation across all microservices.
    """
    
    def __init__(self, service_urls: Dict[str, str]):
        """
        Initialize full pipeline workflow.
        
        Args:
            service_urls: Dictionary mapping service names to URLs
        """
        self.service_urls = service_urls
        self.workflow_steps = [
            "health_check",
            "configuration_load",
            "data_ingestion", 
            "feature_engineering",
            "model_predictions",
            "vor_calculation",
            "ranking_generation",
            "export_rankings"
        ]
        
        # Step timeouts (in seconds)
        self.step_timeouts = {
            "health_check": 30,
            "configuration_load": 30,
            "data_ingestion": 1800,  # 30 minutes
            "feature_engineering": 1200,  # 20 minutes
            "model_predictions": 600,   # 10 minutes
            "vor_calculation": 300,     # 5 minutes
            "ranking_generation": 300,  # 5 minutes
            "export_rankings": 180      # 3 minutes
        }
        
        logger.info("🚀 Full Pipeline Workflow initialized")
    
    async def execute(self, workflow_id: str, parameters: Dict[str, Any], 
                     status_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Execute the complete pipeline workflow.
        
        Args:
            workflow_id: Unique workflow identifier
            parameters: Workflow parameters
            status_callback: Optional callback for status updates
            
        Returns:
            Dictionary containing workflow results
        """
        try:
            logger.info(f"🏁 Starting full pipeline workflow: {workflow_id}")
            
            workflow_results = {
                "workflow_id": workflow_id,
                "started_at": datetime.now().isoformat(),
                "parameters": parameters,
                "step_results": {},
                "success": False
            }
            
            # Execute each step in sequence
            for step in self.workflow_steps:
                try:
                    logger.info(f"🔄 Executing step: {step}")
                    
                    if status_callback:
                        status_callback(step, "running")
                    
                    step_result = await self._execute_step(step, parameters, workflow_results)
                    workflow_results["step_results"][step] = step_result
                    
                    if not step_result.get("success", False):
                        logger.error(f"❌ Step {step} failed: {step_result.get('error')}")
                        
                        if status_callback:
                            status_callback(step, "failed")
                        
                        workflow_results["failed_step"] = step
                        workflow_results["error"] = step_result.get("error")
                        break
                    
                    logger.info(f"✅ Step {step} completed successfully")
                    
                    if status_callback:
                        status_callback(step, "completed")
                
                except Exception as e:
                    logger.error(f"❌ Step {step} failed with exception: {e}")
                    
                    if status_callback:
                        status_callback(step, "failed")
                    
                    workflow_results["step_results"][step] = {"success": False, "error": str(e)}
                    workflow_results["failed_step"] = step
                    workflow_results["error"] = str(e)
                    break
            
            # Determine overall success
            workflow_results["success"] = len(workflow_results["step_results"]) == len(self.workflow_steps) and \
                                         all(result.get("success", False) for result in workflow_results["step_results"].values())
            
            workflow_results["completed_at"] = datetime.now().isoformat()
            
            if workflow_results["success"]:
                logger.info(f"🎉 Full pipeline workflow completed successfully: {workflow_id}")
            else:
                logger.error(f"❌ Full pipeline workflow failed: {workflow_id}")
            
            return workflow_results
        
        except Exception as e:
            logger.error(f"❌ Full pipeline workflow failed with exception: {e}")
            return {
                "workflow_id": workflow_id,
                "success": False,
                "error": str(e),
                "completed_at": datetime.now().isoformat()
            }
    
    async def _execute_step(self, step: str, parameters: Dict[str, Any], 
                          workflow_results: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific workflow step."""
        step_method = getattr(self, f"_step_{step}", None)
        
        if not step_method:
            return {"success": False, "error": f"Unknown step: {step}"}
        
        timeout = self.step_timeouts.get(step, 300)
        
        try:
            result = await asyncio.wait_for(
                step_method(parameters, workflow_results),
                timeout=timeout
            )
            return result
        
        except asyncio.TimeoutError:
            return {"success": False, "error": f"Step {step} timed out after {timeout} seconds"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _step_health_check(self, parameters: Dict[str, Any], 
                               workflow_results: Dict[str, Any]) -> Dict[str, Any]:
        """Check health of all required services."""
        try:
            logger.info("🔍 Checking service health...")
            
            health_results = {}
            all_healthy = True
            
            async with aiohttp.ClientSession() as session:
                for service_name, service_url in self.service_urls.items():
                    try:
                        async with session.get(f"{service_url}/health/live", timeout=10) as response:
                            if response.status == 200:
                                health_results[service_name] = {"status": "healthy", "url": service_url}
                            else:
                                health_results[service_name] = {"status": "unhealthy", "error": f"HTTP {response.status}"}
                                all_healthy = False
                    
                    except Exception as e:
                        health_results[service_name] = {"status": "unreachable", "error": str(e)}
                        all_healthy = False
            
            if all_healthy:
                logger.info("✅ All services are healthy")
                return {"success": True, "health_results": health_results}
            else:
                logger.warning("⚠️ Some services are unhealthy, but continuing...")
                return {"success": True, "health_results": health_results, "warning": "Some services unhealthy"}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _step_configuration_load(self, parameters: Dict[str, Any], 
                                     workflow_results: Dict[str, Any]) -> Dict[str, Any]:
        """Load configuration from configuration service."""
        try:
            logger.info("📋 Loading configuration...")
            
            # Skip configuration loading for now - use defaults
            logger.info("⚠️ Using default configuration (config service endpoint not available)")
            
            default_config = {
                "scoring_system": "half_ppr",
                "league_size": 12,
                "positions": ["QB", "RB", "WR", "TE"],
                "data_years": [2024]
            }
            
            return {
                "success": True,
                "configuration": default_config,
                "message": "Using default configuration",
                "warning": "Configuration service endpoint not available - using defaults"
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _step_data_ingestion(self, parameters: Dict[str, Any], 
                                 workflow_results: Dict[str, Any]) -> Dict[str, Any]:
        """Execute data ingestion step."""
        try:
            logger.info("📥 Starting data ingestion...")
            
            ingestion_request = {
                "years": parameters.get("years"),
                "positions": parameters.get("positions"),
                "force_refresh": parameters.get("force_refresh", False),
                "include_weather": True,
                "include_rosters": True
            }
            
            async with aiohttp.ClientSession() as session:
                # Start data ingestion
                ingestion_url = f"{self.service_urls['data-ingestion']}/api/v1/data/ingest"
                async with session.post(ingestion_url, json=ingestion_request, timeout=60) as response:
                    if response.status != 200:
                        return {
                            "success": False,
                            "error": f"Data ingestion failed to start: HTTP {response.status}"
                        }
                
                # Poll for completion
                status_url = f"{self.service_urls['data-ingestion']}/api/v1/data/status"
                max_wait = 1800  # 30 minutes
                wait_time = 0
                
                while wait_time < max_wait:
                    await asyncio.sleep(10)  # Wait 10 seconds between checks
                    wait_time += 10
                    
                    async with session.get(status_url, timeout=30) as response:
                        if response.status == 200:
                            status_data = await response.json()
                            current_status = status_data.get("data", {}).get("current_status", {})
                            
                            if current_status.get("status") == "completed":
                                return {
                                    "success": True,
                                    "message": "Data ingestion completed",
                                    "ingestion_result": current_status
                                }
                            elif current_status.get("status") == "failed":
                                return {
                                    "success": False,
                                    "error": f"Data ingestion failed: {current_status.get('error')}"
                                }
                
                return {"success": False, "error": "Data ingestion timed out"}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _step_feature_engineering(self, parameters: Dict[str, Any], 
                                      workflow_results: Dict[str, Any]) -> Dict[str, Any]:
        """Execute feature engineering step."""
        try:
            logger.info("🔧 Starting feature engineering...")
            
            features_request = {
                "years": parameters.get("years"),
                "positions": parameters.get("positions"),
                "force_regenerate": parameters.get("force_regenerate", False),
                "include_advanced_features": True
            }
            
            async with aiohttp.ClientSession() as session:
                features_url = f"{self.service_urls['feature-engineering']}/api/v1/features/generate"
                async with session.post(features_url, json=features_request, timeout=60) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        return {
                            "success": True,
                            "message": "Feature engineering completed",
                            "features_result": response_data
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Feature engineering failed: HTTP {response.status}"
                        }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _step_model_predictions(self, parameters: Dict[str, Any], 
                                    workflow_results: Dict[str, Any]) -> Dict[str, Any]:
        """Execute model predictions step."""
        try:
            logger.info("🤖 Starting model predictions...")
            
            # Check if models are ready
            async with aiohttp.ClientSession() as session:
                models_url = f"{self.service_urls['ml-models']}/api/v1/models/status"
                async with session.get(models_url, timeout=30) as response:
                    if response.status == 200:
                        return {
                            "success": True,
                            "message": "Models are ready for predictions",
                            "models_status": await response.json()
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Models service not ready: HTTP {response.status}"
                        }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _step_vor_calculation(self, parameters: Dict[str, Any], 
                                  workflow_results: Dict[str, Any]) -> Dict[str, Any]:
        """Execute VOR calculation step."""
        try:
            logger.info("📊 Starting VOR calculation...")
            
            vor_request = {
                "positions": parameters.get("positions", ["QB", "RB", "WR", "TE"]),
                "season": parameters.get("season"),
                "force_recalculate": parameters.get("force_recalculate", False),
                "include_validation": True
            }
            
            async with aiohttp.ClientSession() as session:
                vor_url = f"{self.service_urls['ranking']}/api/v1/rankings/calculate"
                async with session.post(vor_url, json=vor_request, timeout=60) as response:
                    if response.status == 200:
                        return {
                            "success": True,
                            "message": "VOR calculation started",
                            "vor_result": await response.json()
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"VOR calculation failed: HTTP {response.status}"
                        }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _step_ranking_generation(self, parameters: Dict[str, Any], 
                                     workflow_results: Dict[str, Any]) -> Dict[str, Any]:
        """Execute ranking generation step."""
        try:
            logger.info("🏆 Starting ranking generation...")
            
            ranking_request = {
                "positions": parameters.get("positions", ["QB", "RB", "WR", "TE"]),
                "season": parameters.get("season"),
                "tier_assignments": True,
                "include_overrides": True,
                "sort_by": "vor"
            }
            
            async with aiohttp.ClientSession() as session:
                ranking_url = f"{self.service_urls['ranking']}/api/v1/rankings/generate"
                async with session.post(ranking_url, json=ranking_request, timeout=60) as response:
                    if response.status == 200:
                        return {
                            "success": True,
                            "message": "Ranking generation started",
                            "ranking_result": await response.json()
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Ranking generation failed: HTTP {response.status}"
                        }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _step_export_rankings(self, parameters: Dict[str, Any], 
                                  workflow_results: Dict[str, Any]) -> Dict[str, Any]:
        """Execute ranking export step."""
        try:
            logger.info("📤 Starting ranking export...")
            
            export_request = {
                "format": parameters.get("export_format", "csv"),
                "positions": parameters.get("positions"),
                "top_n": parameters.get("top_n"),
                "include_tiers": True
            }
            
            async with aiohttp.ClientSession() as session:
                export_url = f"{self.service_urls['ranking']}/api/v1/rankings/export"
                async with session.post(export_url, json=export_request, timeout=60) as response:
                    if response.status == 200:
                        return {
                            "success": True,
                            "message": "Rankings exported successfully",
                            "export_result": await response.json()
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Ranking export failed: HTTP {response.status}"
                        }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_workflow_info(self) -> Dict[str, Any]:
        """Get information about the workflow."""
        return {
            "workflow_name": "Full Pipeline Workflow",
            "description": "Complete data-to-rankings pipeline",
            "steps": self.workflow_steps,
            "estimated_duration": "15-30 minutes",
            "step_timeouts": self.step_timeouts,
            "required_services": list(self.service_urls.keys())
        }