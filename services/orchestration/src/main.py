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
import sys
import os

# Try to import validation framework - make it optional for Docker environments
try:
    # Add utils to path for validation framework
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
    from utils.debug_analysis.debug_integration import add_validation_checkpoint
    VALIDATION_AVAILABLE = True
except ImportError:
    # Fallback for Docker environments without utils directory
    def add_validation_checkpoint(service_name, checkpoint_name, description, data):
        """Mock validation checkpoint for environments without utils directory"""
        logger.info(f"VALIDATION: {service_name} - {checkpoint_name}: {description}")
        logger.debug(f"VALIDATION DATA: {data}")
    VALIDATION_AVAILABLE = False

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
import uuid
import traceback
from .workflows.full_pipeline_workflow import FullPipelineWorkflow
from .monitoring.health_checker import HealthChecker
from .coordination.workflow_engine import WorkflowEngine
from .scheduling.scheduler import Scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_standard_response(
    status: str = "success",
    data = None,
    message = None,
    metadata = None
):
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

class WorkflowRequest(BaseModel):
    workflow_type: str  # "full-pipeline", "model-training", "ranking-generation"
    parameters: Optional[Dict[str, Any]] = {}
    schedule: Optional[str] = None  # Cron-like schedule string
    
class ScheduleRequest(BaseModel):
    workflow_type: str
    schedule: str  # Cron expression
    parameters: Optional[Dict[str, Any]] = {}
    enabled: bool = True

class OrchestrationService:
    def __init__(self):
        self.service_name = "Orchestration Service"
        self.version = "1.0.0"
        self.description = "Coordinate workflows and manage service interactions"
        
        # Create FastAPI app with lifespan management
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            logger.info(f"Starting {self.service_name} service v{self.version}")
            await self.startup()
            yield
            # Shutdown
            logger.info(f"Shutting down {self.service_name} service")
            await self.shutdown()
        
        self.app = FastAPI(
            title=self.service_name,
            version=self.version,
            description=self.description,
            lifespan=lifespan
        )
        
        self._setup_middleware()
        
        # Service URLs (use Docker container names for inter-service communication)
        # All services run on port 8000 inside their containers
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
        
        # Validation tracking
        self.validation_enabled = True
        self.service_validation_results = {}
        
        self._setup_health_endpoints()
        self._setup_routes()
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
        async def log_requests(request, call_next):
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
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "service_name": self.service_name,
                "version": self.version
            }
        
        @self.app.get("/health/ready")
        async def readiness_check():
            # Check if all services are accessible
            health_status = await self.health_checker.check_all_services()
            healthy_services = sum(1 for result in health_status.values() if result.get("healthy", False))
            total_services = len(health_status)
            
            if healthy_services >= (total_services * 0.7):  # 70% of services must be healthy
                status = "ready"
            else:
                status = "not_ready"
            
            return {
                "status": status,
                "timestamp": datetime.now().isoformat(), 
                "service_name": self.service_name,
                "version": self.version,
                "details": {
                    "healthy_services": healthy_services,
                    "total_services": total_services,
                    "health_percentage": round((healthy_services / total_services) * 100, 1) if total_services > 0 else 0
                }
            }
        
        @self.app.get("/health/deep")
        async def deep_health_check():
            comprehensive_results = await self.health_checker.comprehensive_health_check()
            return comprehensive_results
        
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
                    "/api/v1/info",
                    "/api/v1/orchestration/status",
                    "/api/v1/workflows/full-pipeline",
                    "/api/v1/workflows/health-check"
                ]
            }
    
    def _setup_error_handlers(self):
        """Set up standardized error handling"""
        
        @self.app.exception_handler(HTTPException)
        async def http_exception_handler(request, exc):
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
        async def general_exception_handler(request, exc):
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
    
    async def shutdown(self):
        """Service shutdown logic"""
        logger.info(f"{self.service_name} shutdown completed")
    
    async def startup(self):
        """Service startup initialization"""
        logger.info("🎭 Orchestration Service starting up...")
        
        # Validation checkpoint 1: Service startup
        if self.validation_enabled:
            add_validation_checkpoint(
                "orchestration", 
                "Service Startup", 
                "Orchestration service initializing",
                {
                    "service_name": self.service_name,
                    "version": self.version,
                    "service_urls_count": len(self.service_urls),
                    "service_urls": list(self.service_urls.keys())
                }
            )
        
        # Initialize health checker
        await self.health_checker.initialize()
        
        # Validation checkpoint 2: Health checker initialization
        if self.validation_enabled:
            add_validation_checkpoint(
                "orchestration",
                "Health Checker Initialized", 
                "Health monitoring system ready",
                {
                    "health_checker_ready": True,
                    "monitored_services": list(self.service_urls.keys())
                }
            )
        
        # Start background health monitoring
        asyncio.create_task(self._start_background_monitoring())
        
        logger.info("✅ Orchestration Service started successfully")
    
    def _setup_routes(self):
        
        # Basic status endpoint
        @self.app.get("/api/v1/orchestration/status")
        async def get_status():
            """Get overall orchestration status"""
            # Validation checkpoint 3: Status check initiated
            if self.validation_enabled:
                add_validation_checkpoint(
                    "orchestration",
                    "Status Check Request",
                    "Client requesting orchestration status",
                    {
                        "endpoint": "/api/v1/orchestration/status",
                        "active_workflows_count": len(self.active_workflows),
                        "workflow_history_count": len(self.workflow_history)
                    }
                )
            
            health_status = await self.health_checker.check_all_services()
            
            # Validation checkpoint 4: Health check completed
            if self.validation_enabled:
                healthy_services = sum(1 for result in health_status.values() if result.get("healthy", False))
                add_validation_checkpoint(
                    "orchestration",
                    "Health Check Completed",
                    "Service health assessment finished",
                    {
                        "total_services": len(health_status),
                        "healthy_services": healthy_services,
                        "health_percentage": round((healthy_services / len(health_status)) * 100, 1) if health_status else 0,
                        "unhealthy_services": [svc for svc, health in health_status.items() if not health.get("healthy", False)]
                    }
                )
            
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
                
                # Validation checkpoint 5: Full pipeline workflow requested
                if self.validation_enabled:
                    add_validation_checkpoint(
                        "orchestration",
                        "Full Pipeline Workflow Request",
                        "Client requested full pipeline execution",
                        {
                            "workflow_id": workflow_id,
                            "workflow_type": request.workflow_type,
                            "parameters": request.parameters,
                            "schedule": request.schedule,
                            "services_required": list(self.service_urls.keys())
                        }
                    )
                
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
                
                # Validation checkpoint 6: Workflow successfully initiated
                if self.validation_enabled:
                    add_validation_checkpoint(
                        "orchestration",
                        "Workflow Started Successfully",
                        "Full pipeline workflow initiated in background",
                        {
                            "workflow_id": workflow_id,
                            "status": "started",
                            "background_task_added": True,
                            "total_active_workflows": len(self.active_workflows)
                        }
                    )
                
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
                
                # Validation checkpoint: Workflow failed to start
                if self.validation_enabled:
                    add_validation_checkpoint(
                        "orchestration",
                        "Workflow Start Failed",
                        "Full pipeline workflow failed to start",
                        {
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "workflow_type": request.workflow_type if request else "unknown"
                        }
                    )
                
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
                # Validation checkpoint 11: Comprehensive health check initiated
                if self.validation_enabled:
                    add_validation_checkpoint(
                        "orchestration",
                        "Comprehensive Health Check Started",
                        "Initiating comprehensive health assessment of all services",
                        {
                            "services_to_check": list(self.service_urls.keys()),
                            "check_types": ["live", "ready", "deep"],
                            "endpoint": "/api/v1/workflows/health-check"
                        }
                    )
                
                health_results = await self.health_checker.comprehensive_health_check()
                
                # Validation checkpoint 12: Health check completed
                if self.validation_enabled:
                    overall_status = health_results.get("overall_status", "unknown")
                    summary = health_results.get("summary", {})
                    add_validation_checkpoint(
                        "orchestration",
                        "Comprehensive Health Check Completed",
                        "Health assessment of all services finished",
                        {
                            "overall_status": overall_status,
                            "total_services": summary.get("total_services", 0),
                            "healthy_services": summary.get("healthy_services", 0),
                            "health_percentage": summary.get("health_percentage", 0),
                            "services_checked": len(health_results.get("services", {}))  
                        }
                    )
                
                return create_standard_response(
                    data=health_results,
                    metadata={"service": "orchestration", "endpoint": "health-check"}
                )
            
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                
                # Validation checkpoint: Health check failed
                if self.validation_enabled:
                    add_validation_checkpoint(
                        "orchestration",
                        "Health Check Failed",
                        "Comprehensive health check failed with error",
                        {
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "services_attempted": list(self.service_urls.keys())
                        }
                    )
                
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
            
            # Validation checkpoint 7: Pipeline execution started
            if self.validation_enabled:
                add_validation_checkpoint(
                    "orchestration",
                    "Pipeline Execution Started",
                    "Background execution of full pipeline initiated",
                    {
                        "workflow_id": workflow_id,
                        "parameters": parameters,
                        "execution_status": "running",
                        "current_step": "initializing"
                    }
                )
            
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
                
                # Validation checkpoint 8: Pipeline completed successfully
                if self.validation_enabled:
                    add_validation_checkpoint(
                        "orchestration",
                        "Pipeline Execution Completed",
                        "Full pipeline workflow completed successfully",
                        {
                            "workflow_id": workflow_id,
                            "success": True,
                            "step_results_count": len(result.get("step_results", {})),
                            "completed_steps": list(result.get("step_results", {}).keys()),
                            "total_duration": result.get("completed_at") 
                        }
                    )
            else:
                self.active_workflows[workflow_id]["status"] = "failed"
                self.active_workflows[workflow_id]["error"] = result.get("error")
                logger.error(f"❌ Full pipeline workflow failed: {workflow_id}")
                
                # Validation checkpoint 9: Pipeline failed
                if self.validation_enabled:
                    add_validation_checkpoint(
                        "orchestration",
                        "Pipeline Execution Failed",
                        "Full pipeline workflow failed during execution",
                        {
                            "workflow_id": workflow_id,
                            "success": False,
                            "error": result.get("error"),
                            "failed_step": result.get("failed_step"),
                            "completed_steps": list(result.get("step_results", {}).keys())
                        }
                    )
            
            # Move to history and remove from active
            self.active_workflows[workflow_id]["completed_at"] = datetime.now().isoformat()
            self.workflow_history.append(self.active_workflows[workflow_id].copy())
            del self.active_workflows[workflow_id]
        
        except Exception as e:
            error_msg = f"Full pipeline workflow failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            
            # Validation checkpoint 10: Pipeline execution exception
            if self.validation_enabled:
                add_validation_checkpoint(
                    "orchestration",
                    "Pipeline Execution Exception",
                    "Full pipeline workflow failed with unhandled exception",
                    {
                        "workflow_id": workflow_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "current_step": self.active_workflows.get(workflow_id, {}).get("current_step", "unknown")
                    }
                )
            
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
        
        # Validation checkpoint 13: Background monitoring started
        if self.validation_enabled:
            add_validation_checkpoint(
                "orchestration",
                "Background Monitoring Started",
                "Background health monitoring task initiated",
                {
                    "monitoring_interval_seconds": 300,
                    "services_monitored": list(self.service_urls.keys()),
                    "monitoring_enabled": True
                }
            )
        
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
                    
                    # Validation checkpoint: Unhealthy services detected
                    if self.validation_enabled:
                        add_validation_checkpoint(
                            "orchestration",
                            "Unhealthy Services Detected",
                            "Background monitoring found unhealthy services",
                            {
                                "unhealthy_services": unhealthy_services,
                                "total_services": len(health_results),
                                "healthy_services": len(health_results) - len(unhealthy_services),
                                "monitoring_timestamp": datetime.now().isoformat()
                            }
                        )
                
            except Exception as e:
                logger.error(f"Background monitoring error: {e}")
                
                # Validation checkpoint: Background monitoring error
                if self.validation_enabled:
                    add_validation_checkpoint(
                        "orchestration",
                        "Background Monitoring Error",
                        "Background health monitoring encountered error",
                        {
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "retry_delay_seconds": 60
                        }
                    )
                
                await asyncio.sleep(60)  # Wait 1 minute before retrying

service = OrchestrationService()
app = service.app

if __name__ == "__main__":
    import uvicorn
    # Orchestration service runs on port 8000 inside Docker container (mapped to 8006 on host)
    uvicorn.run(app, host="0.0.0.0", port=8000)
