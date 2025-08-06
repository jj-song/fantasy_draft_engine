"""
Orchestration Service - Coordinate workflows and manage service interactions.
"""
import logging
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from fastapi import BackgroundTasks, HTTPException
from pydantic import BaseModel
import json

from .api.base_api import BaseService, create_standard_response
from .workflows.full_pipeline_workflow import FullPipelineWorkflow
from .monitoring.health_checker import HealthChecker
from .coordination.workflow_engine import WorkflowEngine
from .scheduling.scheduler import Scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WorkflowRequest(BaseModel):
    workflow_type: str  # "full-pipeline", "model-training", "ranking-generation"
    parameters: Optional[Dict[str, Any]] = {}
    schedule: Optional[str] = None  # Cron-like schedule string
    
class ScheduleRequest(BaseModel):
    workflow_type: str
    schedule: str  # Cron expression
    parameters: Optional[Dict[str, Any]] = {}
    enabled: bool = True

class OrchestrationService(BaseService):
    def __init__(self):
        super().__init__(
            service_name="Orchestration Service",
            version="1.0.0",
            description="Coordinate workflows and manage service interactions"
        )
        
        # Service URLs (use Docker container names for inter-service communication)
        self.service_urls = {
            "configuration": "http://configuration:8000",
            "data-ingestion": "http://data-ingestion:8000",
            "feature-engineering": "http://feature-engineering:8000",
            "ml-models": "http://ml-models:8000",
            "ranking": "http://ranking:8000"
        }
        
        # Initialize components
        self.health_checker = HealthChecker(self.service_urls)
        self.workflow_engine = WorkflowEngine(self.service_urls)
        self.scheduler = Scheduler(self.workflow_engine)
        self.full_pipeline = FullPipelineWorkflow(self.service_urls)
        
        # Orchestration state
        self.active_workflows = {}
        self.workflow_history = []
        
        self._setup_routes()
    
    async def startup(self):
        """Service startup initialization"""
        logger.info("🎭 Orchestration Service starting up...")
        
        # Initialize health checker
        await self.health_checker.initialize()
        
        # Start background health monitoring
        asyncio.create_task(self._start_background_monitoring())
        
        logger.info("✅ Orchestration Service started successfully")
    
    def _setup_routes(self):
        
        # Basic status endpoint
        @self.app.get("/api/v1/orchestration/status")
        async def get_status():
            """Get overall orchestration status"""
            health_status = await self.health_checker.check_all_services()
            
            return create_standard_response(
                data={
                    "status": "ready",
                    "service": "orchestration",
                    "services_health": health_status,
                    "active_workflows": len(self.active_workflows),
                    "scheduled_workflows": await self.scheduler.get_scheduled_count()
                },
                metadata={"service": "orchestration"}
            )
        
        # Workflow execution endpoints
        @self.app.post("/api/v1/workflows/full-pipeline")
        async def run_full_pipeline(request: WorkflowRequest, background_tasks: BackgroundTasks):
            """Run the complete data-to-rankings pipeline"""
            try:
                workflow_id = f"full_pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                # Start workflow in background
                background_tasks.add_task(
                    self._execute_full_pipeline,
                    workflow_id,
                    request.parameters
                )
                
                # Track active workflow
                self.active_workflows[workflow_id] = {
                    "type": "full-pipeline",
                    "status": "started",
                    "started_at": datetime.now().isoformat(),
                    "parameters": request.parameters
                }
                
                return create_standard_response(
                    data={
                        "message": "Full pipeline workflow started",
                        "workflow_id": workflow_id,
                        "estimated_duration": "15-30 minutes"
                    },
                    metadata={"service": "orchestration", "endpoint": "full-pipeline"}
                )
            
            except Exception as e:
                logger.error(f"Failed to start full pipeline: {e}")
                raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")
        
        @self.app.get("/api/v1/workflows/{workflow_id}/status")
        async def get_workflow_status(workflow_id: str):
            """Get status of a specific workflow"""
            try:
                if workflow_id in self.active_workflows:
                    workflow_info = self.active_workflows[workflow_id]
                    return create_standard_response(
                        data=workflow_info,
                        metadata={"service": "orchestration", "workflow_id": workflow_id}
                    )
                else:
                    # Check workflow history
                    historical_workflow = next(
                        (w for w in self.workflow_history if w["workflow_id"] == workflow_id),
                        None
                    )
                    
                    if historical_workflow:
                        return create_standard_response(
                            data=historical_workflow,
                            metadata={"service": "orchestration", "workflow_id": workflow_id}
                        )
                    else:
                        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
            
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to get workflow status: {e}")
                raise HTTPException(status_code=500, detail=f"Status error: {str(e)}")
        
        # Health monitoring endpoints
        @self.app.get("/api/v1/workflows/health-check")
        async def check_all_services_health():
            """Check health of all dependent services"""
            try:
                health_results = await self.health_checker.comprehensive_health_check()
                return create_standard_response(
                    data=health_results,
                    metadata={"service": "orchestration", "endpoint": "health-check"}
                )
            
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                raise HTTPException(status_code=500, detail=f"Health check error: {str(e)}")
        
        # Scheduling endpoints
        @self.app.post("/api/v1/workflows/schedule")
        async def schedule_workflow(request: ScheduleRequest):
            """Schedule a workflow to run automatically"""
            try:
                schedule_id = await self.scheduler.schedule_workflow(
                    workflow_type=request.workflow_type,
                    schedule=request.schedule,
                    parameters=request.parameters,
                    enabled=request.enabled
                )
                
                return create_standard_response(
                    data={
                        "message": f"Workflow scheduled successfully",
                        "schedule_id": schedule_id,
                        "workflow_type": request.workflow_type,
                        "schedule": request.schedule
                    },
                    metadata={"service": "orchestration", "endpoint": "schedule"}
                )
            
            except Exception as e:
                logger.error(f"Failed to schedule workflow: {e}")
                raise HTTPException(status_code=500, detail=f"Scheduling error: {str(e)}")
        
        @self.app.get("/api/v1/workflows/scheduled")
        async def get_scheduled_workflows():
            """Get all scheduled workflows"""
            try:
                scheduled_workflows = await self.scheduler.get_all_scheduled()
                return create_standard_response(
                    data=scheduled_workflows,
                    metadata={"service": "orchestration", "endpoint": "scheduled"}
                )
            
            except Exception as e:
                logger.error(f"Failed to get scheduled workflows: {e}")
                raise HTTPException(status_code=500, detail=f"Scheduled workflows error: {str(e)}")
        
        # Workflow history endpoints
        @self.app.get("/api/v1/workflows/history")
        async def get_workflow_history():
            """Get workflow execution history"""
            try:
                # Return recent workflow history (last 50 executions)
                recent_history = self.workflow_history[-50:] if len(self.workflow_history) > 50 else self.workflow_history
                
                return create_standard_response(
                    data={
                        "total_executions": len(self.workflow_history),
                        "recent_executions": recent_history,
                        "active_workflows": len(self.active_workflows)
                    },
                    metadata={"service": "orchestration", "endpoint": "history"}
                )
            
            except Exception as e:
                logger.error(f"Failed to get workflow history: {e}")
                raise HTTPException(status_code=500, detail=f"History error: {str(e)}")
    
    async def _execute_full_pipeline(self, workflow_id: str, parameters: Dict[str, Any]):
        """Execute the full pipeline workflow in background"""
        try:
            logger.info(f"🚀 Starting full pipeline workflow: {workflow_id}")
            
            # Update workflow status
            self.active_workflows[workflow_id]["status"] = "running"
            self.active_workflows[workflow_id]["current_step"] = "initializing"
            
            # Execute the full pipeline
            result = await self.full_pipeline.execute(
                workflow_id=workflow_id,
                parameters=parameters,
                status_callback=lambda step, status: self._update_workflow_status(workflow_id, step, status)
            )
            
            # Update final status
            if result["success"]:
                self.active_workflows[workflow_id]["status"] = "completed"
                self.active_workflows[workflow_id]["result"] = result
                logger.info(f"✅ Full pipeline workflow completed: {workflow_id}")
            else:
                self.active_workflows[workflow_id]["status"] = "failed"
                self.active_workflows[workflow_id]["error"] = result.get("error")
                logger.error(f"❌ Full pipeline workflow failed: {workflow_id}")
            
            # Move to history and remove from active
            self.active_workflows[workflow_id]["completed_at"] = datetime.now().isoformat()
            self.workflow_history.append(self.active_workflows[workflow_id].copy())
            del self.active_workflows[workflow_id]
        
        except Exception as e:
            error_msg = f"Full pipeline workflow failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            
            # Update error status
            if workflow_id in self.active_workflows:
                self.active_workflows[workflow_id]["status"] = "failed"
                self.active_workflows[workflow_id]["error"] = str(e)
                self.active_workflows[workflow_id]["completed_at"] = datetime.now().isoformat()
                
                # Move to history
                self.workflow_history.append(self.active_workflows[workflow_id].copy())
                del self.active_workflows[workflow_id]
    
    def _update_workflow_status(self, workflow_id: str, step: str, status: str):
        """Update workflow status during execution"""
        if workflow_id in self.active_workflows:
            self.active_workflows[workflow_id]["current_step"] = step
            self.active_workflows[workflow_id]["last_updated"] = datetime.now().isoformat()
            
            if status:
                self.active_workflows[workflow_id]["step_status"] = status
    
    async def _start_background_monitoring(self):
        """Start background health monitoring"""
        logger.info("🔍 Starting background health monitoring...")
        
        while True:
            try:
                # Run health check every 5 minutes
                await asyncio.sleep(300)  # 5 minutes
                
                health_results = await self.health_checker.check_all_services()
                
                # Log any unhealthy services
                unhealthy_services = [service for service, health in health_results.items() 
                                    if not health.get("healthy", False)]
                
                if unhealthy_services:
                    logger.warning(f"⚠️ Unhealthy services detected: {unhealthy_services}")
                
            except Exception as e:
                logger.error(f"Background monitoring error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

service = OrchestrationService()
app = service.app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
