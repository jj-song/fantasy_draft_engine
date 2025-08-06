"""
Ranking Service - Generate and validate fantasy football rankings.
"""
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime
from fastapi import BackgroundTasks, HTTPException
from pydantic import BaseModel
import os
import sys
from pathlib import Path
import requests

# Add the services directory to the Python path
services_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(services_root))
sys.path.append(str(services_root / "legacy"))

from .api.base_api import BaseService, create_standard_response
from .calculation.vor_calculator import VORCalculator
from .outputs.cheatsheet_generator import CheatsheetGenerator
from .scoring.scoring_engine import ScoringEngine
from .validation.ranking_validator import RankingValidator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RankingCalculationRequest(BaseModel):
    positions: Optional[List[str]] = None  # If None, calculate for all positions
    season: Optional[int] = None  # If None, use current prediction season
    force_recalculate: bool = False
    include_validation: bool = True
    
class RankingGenerationRequest(BaseModel):
    positions: Optional[List[str]] = None
    season: Optional[int] = None
    tier_assignments: bool = True
    include_overrides: bool = True
    sort_by: str = "vor"  # "vor", "projected_points", "adp"
    
class ExportRequest(BaseModel):
    format: str = "csv"  # "csv", "pdf", "json", "cheatsheet"
    positions: Optional[List[str]] = None
    top_n: Optional[int] = None  # Export only top N players
    include_tiers: bool = True

class RankingService(BaseService):
    def __init__(self):
        super().__init__(
            service_name="Ranking Service",
            version="1.0.0",
            description="Generate and validate fantasy football rankings"
        )
        
        # Initialize components
        self.vor_calculator = VORCalculator()
        self.cheatsheet_generator = CheatsheetGenerator()
        self.scoring_engine = ScoringEngine()
        self.ranking_validator = RankingValidator()
        
        # Service state
        self.ranking_status = {"status": "idle", "message": ""}
        self.cached_rankings = {}
        
        self._setup_routes()
    
    async def startup(self):
        """Service startup initialization"""
        logger.info("🏆 Ranking Service starting up...")
        
        # Initialize VOR calculator with default baselines
        try:
            await self.vor_calculator.initialize_baselines()
            logger.info("✅ VOR baselines initialized")
        except Exception as e:
            logger.warning(f"⚠️ Could not initialize VOR baselines: {e}")
        
        logger.info("✅ Ranking Service started successfully")
    
    def _setup_routes(self):
        
        # Basic status endpoint
        @self.app.get("/api/v1/rankings/status")
        async def get_status():
            """Get overall service status"""
            vor_status = await self.vor_calculator.get_status()
            
            return create_standard_response(
                data={
                    "status": "ready", 
                    "service": "ranking",
                    "vor_baselines_loaded": vor_status["baselines_loaded"],
                    "ranking_status": self.ranking_status,
                    "cached_rankings": len(self.cached_rankings)
                },
                metadata={"service": "ranking"}
            )
        
        # VOR calculation endpoints
        @self.app.post("/api/v1/rankings/calculate")
        async def calculate_vor(request: RankingCalculationRequest, background_tasks: BackgroundTasks):
            """Calculate VOR for all positions"""
            try:
                if self.ranking_status["status"] == "calculating":
                    return create_standard_response(
                        data={"message": "VOR calculation already in progress", "status": self.ranking_status},
                        metadata={"service": "ranking", "endpoint": "calculate"}
                    )
                
                # Start VOR calculation in background
                background_tasks.add_task(
                    self._run_vor_calculation,
                    request.positions or ["QB", "RB", "WR", "TE"],
                    request.season,
                    request.force_recalculate,
                    request.include_validation
                )
                
                self.ranking_status = {"status": "calculating", "message": "VOR calculation started"}
                
                return create_standard_response(
                    data={
                        "message": "VOR calculation started in background",
                        "positions": request.positions or ["QB", "RB", "WR", "TE"],
                        "calculation_id": datetime.now().strftime("%Y%m%d_%H%M%S")
                    },
                    metadata={"service": "ranking", "endpoint": "calculate"}
                )
            
            except Exception as e:
                logger.error(f"Failed to start VOR calculation: {e}")
                raise HTTPException(status_code=500, detail=f"Calculation error: {str(e)}")
        
        @self.app.get("/api/v1/rankings/vor-status")
        async def get_vor_status():
            """Get VOR calculation status"""
            vor_status = await self.vor_calculator.get_detailed_status()
            return create_standard_response(
                data=vor_status,
                metadata={"service": "ranking", "endpoint": "vor-status"}
            )
        
        # Ranking generation endpoints
        @self.app.post("/api/v1/rankings/generate")
        async def generate_rankings(request: RankingGenerationRequest, background_tasks: BackgroundTasks):
            """Generate complete draft rankings"""
            try:
                # Start ranking generation in background
                background_tasks.add_task(
                    self._run_ranking_generation,
                    request.positions or ["QB", "RB", "WR", "TE"],
                    request.season,
                    request.tier_assignments,
                    request.include_overrides,
                    request.sort_by
                )
                
                return create_standard_response(
                    data={
                        "message": "Ranking generation started in background",
                        "positions": request.positions or ["QB", "RB", "WR", "TE"],
                        "generation_id": datetime.now().strftime("%Y%m%d_%H%M%S")
                    },
                    metadata={"service": "ranking", "endpoint": "generate"}
                )
            
            except Exception as e:
                logger.error(f"Failed to start ranking generation: {e}")
                raise HTTPException(status_code=500, detail=f"Generation error: {str(e)}")
        
        @self.app.get("/api/v1/rankings/list")
        async def list_rankings():
            """List available rankings"""
            try:
                rankings_info = await self._get_available_rankings()
                return create_standard_response(
                    data=rankings_info,
                    metadata={"service": "ranking", "endpoint": "list"}
                )
            except Exception as e:
                logger.error(f"Failed to list rankings: {e}")
                raise HTTPException(status_code=500, detail=f"List error: {str(e)}")
        
        # Export endpoints
        @self.app.post("/api/v1/rankings/export")
        async def export_rankings(request: ExportRequest):
            """Export rankings in specified format"""
            try:
                export_result = await self.cheatsheet_generator.export_rankings(
                    format=request.format,
                    positions=request.positions,
                    top_n=request.top_n,
                    include_tiers=request.include_tiers
                )
                
                return create_standard_response(
                    data=export_result,
                    metadata={"service": "ranking", "endpoint": "export"}
                )
            
            except Exception as e:
                logger.error(f"Failed to export rankings: {e}")
                raise HTTPException(status_code=500, detail=f"Export error: {str(e)}")
        
        # Validation endpoints
        @self.app.post("/api/v1/rankings/validate")
        async def validate_rankings():
            """Validate ranking consistency and quality"""
            try:
                validation_result = await self.ranking_validator.validate_all_rankings()
                return create_standard_response(
                    data=validation_result,
                    metadata={"service": "ranking", "endpoint": "validate"}
                )
            
            except Exception as e:
                logger.error(f"Failed to validate rankings: {e}")
                raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")
    
    async def _run_vor_calculation(self, positions: List[str], season: Optional[int], 
                                 force_recalculate: bool, include_validation: bool):
        """Run VOR calculation in background"""
        try:
            self.ranking_status = {"status": "calculating", "message": "Loading prediction data..."}
            
            # Calculate VOR for each position
            vor_results = {}
            for position in positions:
                self.ranking_status["message"] = f"Calculating VOR for {position}..."
                
                position_vor = await self.vor_calculator.calculate_position_vor(
                    position=position,
                    season=season,
                    force_recalculate=force_recalculate
                )
                
                vor_results[position] = position_vor
            
            # Validate results if requested
            if include_validation:
                self.ranking_status["message"] = "Validating VOR calculations..."
                validation_result = await self.ranking_validator.validate_vor_calculations(vor_results)
                vor_results["validation"] = validation_result
            
            # Cache results
            cache_key = f"vor_{datetime.now().strftime('%Y%m%d')}"
            self.cached_rankings[cache_key] = {
                "type": "vor",
                "results": vor_results,
                "positions": positions,
                "calculated_at": datetime.now().isoformat()
            }
            
            self.ranking_status = {
                "status": "completed",
                "message": f"VOR calculation completed for {positions}",
                "positions": positions,
                "completed_at": datetime.now().isoformat()
            }
            
            logger.info(f"✅ VOR calculation completed for positions: {positions}")
        
        except Exception as e:
            error_msg = f"VOR calculation failed: {str(e)}"
            self.ranking_status = {
                "status": "failed",
                "message": error_msg,
                "error": str(e),
                "failed_at": datetime.now().isoformat()
            }
            logger.error(f"❌ {error_msg}")
    
    async def _run_ranking_generation(self, positions: List[str], season: Optional[int],
                                    tier_assignments: bool, include_overrides: bool, sort_by: str):
        """Run ranking generation in background"""
        try:
            self.ranking_status = {"status": "generating", "message": "Generating rankings..."}
            
            # Generate rankings using scoring engine
            rankings = await self.scoring_engine.generate_overall_rankings(
                positions=positions,
                season=season,
                tier_assignments=tier_assignments,
                include_overrides=include_overrides,
                sort_by=sort_by
            )
            
            # Cache results
            cache_key = f"rankings_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.cached_rankings[cache_key] = {
                "type": "rankings",
                "results": rankings,
                "positions": positions,
                "sort_by": sort_by,
                "generated_at": datetime.now().isoformat()
            }
            
            self.ranking_status = {
                "status": "completed",
                "message": f"Rankings generated for {positions}",
                "positions": positions,
                "total_players": len(rankings) if isinstance(rankings, list) else rankings.get("total_players", 0),
                "completed_at": datetime.now().isoformat()
            }
            
            logger.info(f"✅ Ranking generation completed for positions: {positions}")
        
        except Exception as e:
            error_msg = f"Ranking generation failed: {str(e)}"
            self.ranking_status = {
                "status": "failed",
                "message": error_msg,
                "error": str(e),
                "failed_at": datetime.now().isoformat()
            }
            logger.error(f"❌ {error_msg}")
    
    async def _get_available_rankings(self) -> Dict[str, Any]:
        """Get information about available rankings"""
        available_rankings = {
            "cached_rankings": {},
            "file_rankings": {},
            "summary": {
                "total_cached": len(self.cached_rankings),
                "last_updated": None
            }
        }
        
        # Process cached rankings
        for cache_key, ranking_data in self.cached_rankings.items():
            available_rankings["cached_rankings"][cache_key] = {
                "type": ranking_data["type"],
                "positions": ranking_data["positions"],
                "timestamp": ranking_data.get("calculated_at") or ranking_data.get("generated_at")
            }
        
        # Check for file-based rankings
        rankings_dir = services_root / "data" / "draft_lists"
        if rankings_dir.exists():
            ranking_files = list(rankings_dir.glob("*.csv")) + list(rankings_dir.glob("*.txt"))
            for file_path in ranking_files:
                file_key = file_path.stem
                available_rankings["file_rankings"][file_key] = {
                    "file_path": str(file_path),
                    "file_size": file_path.stat().st_size,
                    "last_modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                }
        
        # Update summary
        all_timestamps = []
        for ranking_data in self.cached_rankings.values():
            timestamp = ranking_data.get("calculated_at") or ranking_data.get("generated_at")
            if timestamp:
                all_timestamps.append(timestamp)
        
        if all_timestamps:
            available_rankings["summary"]["last_updated"] = max(all_timestamps)
        
        return available_rankings

service = RankingService()
app = service.app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
