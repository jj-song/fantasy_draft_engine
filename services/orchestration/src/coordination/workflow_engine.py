"""
Workflow Engine - Core workflow coordination and execution.

This module provides workflow management including:
- Workflow registration and execution
- State management
- Error handling and recovery  
- Workflow templates
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import uuid

logger = logging.getLogger(__name__)

class WorkflowEngine:
    """
    Core workflow coordination and execution engine.
    
    Manages workflow lifecycles, state transitions, and execution coordination.
    """
    
    def __init__(self, service_urls: Dict[str, str]):
        """
        Initialize workflow engine.
        
        Args:
            service_urls: Dictionary mapping service names to URLs
        """
        self.service_urls = service_urls
        self.active_workflows = {}
        self.workflow_templates = {}
        
        # Register built-in workflow templates
        self._register_builtin_templates()
        
        logger.info("⚙️ Workflow Engine initialized")
    
    def _register_builtin_templates(self):
        """Register built-in workflow templates."""
        
        self.workflow_templates["full-pipeline"] = {
            "name": "Full Pipeline Workflow",
            "description": "Complete data-to-rankings pipeline",
            "steps": [
                "health_check",
                "configuration_load", 
                "data_ingestion",
                "feature_engineering",
                "model_predictions",
                "vor_calculation",
                "ranking_generation",
                "export_rankings"
            ],
            "estimated_duration_minutes": 30,
            "required_services": ["configuration", "data-ingestion", "feature-engineering", "ml-models", "ranking"]
        }
        
        self.workflow_templates["model-training"] = {
            "name": "Model Training Workflow",
            "description": "Train ML models for all positions",
            "steps": [
                "health_check",
                "configuration_load",
                "load_training_data",
                "train_models",
                "validate_models"
            ],
            "estimated_duration_minutes": 60,
            "required_services": ["configuration", "feature-engineering", "ml-models"]
        }
        
        self.workflow_templates["ranking-generation"] = {
            "name": "Ranking Generation Workflow", 
            "description": "Generate draft rankings from existing predictions",
            "steps": [
                "health_check",
                "vor_calculation", 
                "ranking_generation",
                "export_rankings"
            ],
            "estimated_duration_minutes": 10,
            "required_services": ["configuration", "ml-models", "ranking"]
        }
    
    async def execute_workflow(self, workflow_type: str, parameters: Dict[str, Any]) -> str:
        """
        Execute a workflow.
        
        Args:
            workflow_type: Type of workflow to execute
            parameters: Workflow parameters
            
        Returns:
            Workflow ID for tracking
        """
        try:
            workflow_id = str(uuid.uuid4())
            logger.info(f"🚀 Starting workflow execution: {workflow_type} (ID: {workflow_id})")
            
            # Validate workflow type
            if workflow_type not in self.workflow_templates:
                raise ValueError(f"Unknown workflow type: {workflow_type}")
            
            template = self.workflow_templates[workflow_type]
            
            # Initialize workflow state
            workflow_state = {
                "workflow_id": workflow_id,
                "workflow_type": workflow_type,
                "template": template,
                "parameters": parameters,
                "status": "initialized",
                "current_step": None,
                "step_results": {},
                "started_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            }
            
            self.active_workflows[workflow_id] = workflow_state
            
            # Execute workflow asynchronously
            asyncio.create_task(self._run_workflow(workflow_id))
            
            return workflow_id
        
        except Exception as e:
            logger.error(f"Failed to execute workflow {workflow_type}: {e}")
            raise
    
    async def _run_workflow(self, workflow_id: str):
        """Run workflow steps in sequence."""
        try:
            workflow_state = self.active_workflows[workflow_id]
            template = workflow_state["template"]
            
            workflow_state["status"] = "running"
            workflow_state["last_updated"] = datetime.now().isoformat()
            
            logger.info(f"🔄 Running workflow: {workflow_id}")
            
            # Execute each step
            for step in template["steps"]:
                workflow_state["current_step"] = step
                workflow_state["last_updated"] = datetime.now().isoformat()
                
                logger.info(f"  Executing step: {step}")
                
                # Simulate step execution (in real implementation, this would call actual services)
                step_result = await self._execute_step(step, workflow_state)
                
                workflow_state["step_results"][step] = step_result
                
                if not step_result.get("success", False):
                    workflow_state["status"] = "failed"
                    workflow_state["failed_step"] = step
                    workflow_state["error"] = step_result.get("error")
                    break
            
            # Update final status
            if workflow_state["status"] != "failed":
                workflow_state["status"] = "completed"
            
            workflow_state["completed_at"] = datetime.now().isoformat()
            workflow_state["last_updated"] = datetime.now().isoformat()
            
            logger.info(f"✅ Workflow completed: {workflow_id} (Status: {workflow_state['status']})")
        
        except Exception as e:
            logger.error(f"Workflow execution failed: {workflow_id} - {e}")
            
            if workflow_id in self.active_workflows:
                self.active_workflows[workflow_id]["status"] = "failed"
                self.active_workflows[workflow_id]["error"] = str(e)
                self.active_workflows[workflow_id]["completed_at"] = datetime.now().isoformat()
    
    async def _execute_step(self, step: str, workflow_state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a workflow step."""
        try:
            # Simulate step execution
            await asyncio.sleep(1)  # Simulate processing time
            
            # For now, all steps succeed (in real implementation, this would call services)
            return {
                "success": True,
                "step": step,
                "message": f"Step {step} completed successfully",
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            return {
                "success": False,
                "step": step,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get status of a workflow."""
        if workflow_id in self.active_workflows:
            return self.active_workflows[workflow_id]
        else:
            return {"error": "Workflow not found"}
    
    async def list_workflow_templates(self) -> Dict[str, Any]:
        """List available workflow templates."""
        return {
            "templates": self.workflow_templates,
            "total_templates": len(self.workflow_templates)
        }
    
    async def get_active_workflows(self) -> Dict[str, Any]:
        """Get all active workflows."""
        return {
            "active_workflows": self.active_workflows,
            "total_active": len(self.active_workflows)
        }