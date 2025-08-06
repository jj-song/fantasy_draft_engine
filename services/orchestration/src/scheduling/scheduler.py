"""
Scheduler - Handle scheduled workflow execution.

This module provides scheduling functionality including:
- Cron-style scheduling
- Recurring workflow execution  
- Schedule management
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid

logger = logging.getLogger(__name__)

class Scheduler:
    """
    Handle scheduled workflow execution.
    
    Provides cron-style scheduling for automated workflow runs.
    """
    
    def __init__(self, workflow_engine):
        """
        Initialize scheduler.
        
        Args:
            workflow_engine: WorkflowEngine instance
        """
        self.workflow_engine = workflow_engine
        self.scheduled_tasks = {}
        self.scheduler_running = False
        
        logger.info("📅 Scheduler initialized")
    
    async def add_schedule(self, schedule_id: str, workflow_type: str, 
                          cron_expression: str, parameters: Dict[str, Any]) -> bool:
        """
        Add a scheduled workflow.
        
        Args:
            schedule_id: Unique identifier for schedule
            workflow_type: Type of workflow to schedule
            cron_expression: Cron-style schedule expression
            parameters: Parameters for workflow execution
            
        Returns:
            True if schedule was added successfully
        """
        try:
            schedule = {
                "schedule_id": schedule_id,
                "workflow_type": workflow_type,
                "cron_expression": cron_expression,
                "parameters": parameters,
                "created_at": datetime.now().isoformat(),
                "last_run": None,
                "next_run": self._calculate_next_run(cron_expression),
                "enabled": True
            }
            
            self.scheduled_tasks[schedule_id] = schedule
            
            logger.info(f"📅 Schedule added: {schedule_id} -> {workflow_type} at {cron_expression}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to add schedule {schedule_id}: {e}")
            return False
    
    async def remove_schedule(self, schedule_id: str) -> bool:
        """Remove a scheduled workflow."""
        try:
            if schedule_id in self.scheduled_tasks:
                del self.scheduled_tasks[schedule_id]
                logger.info(f"📅 Schedule removed: {schedule_id}")
                return True
            else:
                logger.warning(f"Schedule not found: {schedule_id}")
                return False
        
        except Exception as e:
            logger.error(f"Failed to remove schedule {schedule_id}: {e}")
            return False
    
    async def start_scheduler(self) -> bool:
        """Start the scheduler."""
        try:
            if self.scheduler_running:
                logger.warning("Scheduler is already running")
                return True
            
            self.scheduler_running = True
            logger.info("📅 Scheduler started")
            
            # Start the scheduler loop
            asyncio.create_task(self._scheduler_loop())
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            return False
    
    async def stop_scheduler(self):
        """Stop the scheduler."""
        self.scheduler_running = False
        logger.info("🛑 Scheduler stop requested")
    
    async def _scheduler_loop(self):
        """Main scheduler loop."""
        logger.info("📅 Scheduler loop started")
        
        while self.scheduler_running:
            try:
                current_time = datetime.now()
                
                for schedule_id, schedule in self.scheduled_tasks.items():
                    if not schedule["enabled"]:
                        continue
                    
                    next_run = datetime.fromisoformat(schedule["next_run"])
                    
                    if current_time >= next_run:
                        logger.info(f"📅 Executing scheduled workflow: {schedule_id}")
                        
                        # Execute the workflow
                        try:
                            workflow_id = await self.workflow_engine.execute_workflow(
                                schedule["workflow_type"],
                                schedule["parameters"]
                            )
                            
                            # Update schedule
                            schedule["last_run"] = current_time.isoformat()
                            schedule["next_run"] = self._calculate_next_run(schedule["cron_expression"])
                            schedule["last_workflow_id"] = workflow_id
                            
                            logger.info(f"📅 Scheduled workflow started: {workflow_id}")
                        
                        except Exception as e:
                            logger.error(f"Failed to execute scheduled workflow {schedule_id}: {e}")
                
                # Sleep for a minute before checking again
                await asyncio.sleep(60)
            
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)
        
        logger.info("📅 Scheduler loop stopped")
    
    def _calculate_next_run(self, cron_expression: str) -> str:
        """Calculate next run time from cron expression."""
        # Simple implementation - for a real system, use a proper cron library
        # For now, just schedule for next hour
        next_run = datetime.now() + timedelta(hours=1)
        return next_run.isoformat()
    
    async def get_schedules(self) -> Dict[str, Any]:
        """Get all scheduled tasks."""
        return {
            "schedules": self.scheduled_tasks,
            "total_schedules": len(self.scheduled_tasks),
            "scheduler_running": self.scheduler_running
        }
    
    async def get_schedule(self, schedule_id: str) -> Dict[str, Any]:
        """Get a specific schedule."""
        if schedule_id in self.scheduled_tasks:
            return self.scheduled_tasks[schedule_id]
        else:
            return {"error": "Schedule not found"}
    
    async def enable_schedule(self, schedule_id: str) -> bool:
        """Enable a schedule."""
        if schedule_id in self.scheduled_tasks:
            self.scheduled_tasks[schedule_id]["enabled"] = True
            logger.info(f"📅 Schedule enabled: {schedule_id}")
            return True
        return False
    
    async def disable_schedule(self, schedule_id: str) -> bool:
        """Disable a schedule."""
        if schedule_id in self.scheduled_tasks:
            self.scheduled_tasks[schedule_id]["enabled"] = False
            logger.info(f"📅 Schedule disabled: {schedule_id}")
            return True
        return False
    
    async def get_scheduled_count(self) -> int:
        """Get the count of scheduled workflows."""
        return len(self.scheduled_tasks)
    
    async def schedule_workflow(self, workflow_type: str, schedule: str, 
                              parameters: Dict[str, Any], enabled: bool = True) -> str:
        """
        Schedule a workflow with given parameters.
        
        Args:
            workflow_type: Type of workflow to schedule
            schedule: Cron-style schedule expression
            parameters: Parameters for workflow execution
            enabled: Whether the schedule is enabled
            
        Returns:
            Schedule ID for the created schedule
        """
        try:
            schedule_id = f"{workflow_type}_{uuid.uuid4().hex[:8]}"
            
            success = await self.add_schedule(
                schedule_id=schedule_id,
                workflow_type=workflow_type,
                cron_expression=schedule,
                parameters=parameters
            )
            
            if success and not enabled:
                await self.disable_schedule(schedule_id)
            
            return schedule_id
        
        except Exception as e:
            logger.error(f"Failed to schedule workflow: {e}")
            raise e
    
    async def get_all_scheduled(self) -> Dict[str, Any]:
        """Get all scheduled workflows."""
        try:
            schedules = await self.get_schedules()
            return {
                "schedules": list(schedules["schedules"].values()),
                "total": schedules["total_schedules"],
                "scheduler_status": "running" if schedules["scheduler_running"] else "stopped"
            }
        
        except Exception as e:
            logger.error(f"Failed to get all scheduled workflows: {e}")
            return {
                "schedules": [],
                "total": 0,
                "scheduler_status": "error",
                "error": str(e)
            }