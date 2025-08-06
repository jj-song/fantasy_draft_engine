"""
Data Ingestion Service - External data acquisition and standardization.
"""
import logging
from typing import Dict, Any, Optional, List
import asyncio
from datetime import datetime
import pandas as pd
from pathlib import Path
import requests
import numpy as np
import json
import uuid
import os

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .api.base_api import BaseService, create_standard_response, create_error_response
from .acquisition.nfl_data_fetcher import fetch_player_season_stats
from .cleaning.data_cleaning import *
from .storage.data_storage import *
from .config import get_data_paths

# Custom JSON Response class to handle pandas/numpy serialization
class SafeJSONResponse(JSONResponse):
    """Custom JSON response that safely handles pandas and numpy data types"""
    
    def render(self, content: Any) -> bytes:
        """Override render method to handle numpy/pandas serialization issues"""
        def safe_serializer(obj):
            """Custom serializer for numpy/pandas types"""
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                if np.isnan(obj) or np.isinf(obj):
                    return None
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif pd.isna(obj):
                return None
            elif hasattr(obj, 'item'):  # numpy scalar types
                try:
                    val = obj.item()
                    if isinstance(val, float) and (np.isnan(val) or np.isinf(val)):
                        return None
                    return val
                except (ValueError, OverflowError):
                    return None
            return obj
        
        return json.dumps(
            content, 
            default=safe_serializer, 
            ensure_ascii=False, 
            allow_nan=False,
            separators=(',', ':')
        ).encode('utf-8')

# Configure logging with environment-based level
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/data-ingestion.log', mode='a') if os.path.exists('logs') else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)

class DataIngestionRequest(BaseModel):
    years: Optional[List[int]] = None
    positions: Optional[List[str]] = None
    force_refresh: bool = False
    include_weather: bool = True
    include_rosters: bool = True

class DataIngestionService(BaseService):
    def __init__(self):
        super().__init__(
            service_name="Data Ingestion Service",
            version="1.0.0",
            description="External data acquisition and standardization for Fantasy Football"
        )
        
        self.ingestion_status = {}
        self.last_ingestion = {}
        self.config_service_url = os.environ.get("CONFIG_SERVICE_URL", "http://configuration:8000")
        
        # Override the default response class for the entire app
        self.app.default_response_class = SafeJSONResponse
        
        self._setup_routes()
    
    def _setup_error_handlers(self):
        """Override parent's error handlers to use SafeJSONResponse"""
        from fastapi import Request
        import traceback
        import time
        
        @self.app.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, exc: HTTPException):
            correlation_id = getattr(request.state, 'correlation_id', str(uuid.uuid4()))
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
            return SafeJSONResponse(
                status_code=exc.status_code,
                content=error_response
            )
        
        @self.app.exception_handler(Exception)
        async def general_exception_handler(request: Request, exc: Exception):
            correlation_id = getattr(request.state, 'correlation_id', str(uuid.uuid4()))
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
            return SafeJSONResponse(
                status_code=500,
                content=error_response
            )
    
    async def startup(self):
        """Initialize data ingestion service"""
        logger.info("Data Ingestion Service started successfully")
        
        # Initialize data directories using dynamic paths
        import os
        paths = get_data_paths()
        os.makedirs(paths["raw"], exist_ok=True)
        os.makedirs(paths["processed"], exist_ok=True)
        
        # Try to connect to Configuration Service (if configured)
        if self.config_service_url and not self.config_service_url.startswith("http://configuration"):
            try:
                response = requests.get(f"{self.config_service_url}/health/live", timeout=5)
                if response.status_code == 200:
                    logger.info("Successfully connected to Configuration Service")
                else:
                    logger.warning("Configuration Service not healthy, using default settings")
            except Exception as e:
                logger.warning(f"Cannot connect to Configuration Service: {e}")
        else:
            logger.info("Configuration Service not configured, using default settings")
    
    async def shutdown(self):
        """Cleanup on shutdown"""
        logger.info("Data Ingestion Service shutting down")
    
    def _setup_routes(self):
        """Set up API routes for data ingestion service"""
        
        @self.app.get("/api/v1/data/status")
        async def get_data_status():
            """Get status of data ingestion"""
            try:
                # Check what data files exist
                import os
                from pathlib import Path
                
                paths = get_data_paths()
                data_status = {}
                raw_data_dir = Path(paths["raw"])
                processed_data_dir = Path(paths["processed"])
                
                if raw_data_dir.exists():
                    raw_files = list(raw_data_dir.glob("*.parquet"))
                    data_status["raw_files"] = [f.name for f in raw_files]
                    data_status["raw_count"] = len(raw_files)
                    
                    # Check file ages
                    file_ages = {}
                    for file in raw_files:
                        mtime = os.path.getmtime(file)
                        age_hours = (datetime.now().timestamp() - mtime) / 3600
                        file_ages[file.name] = {
                            "age_hours": round(age_hours, 2),
                            "size_mb": round(file.stat().st_size / (1024*1024), 2)
                        }
                    data_status["file_details"] = file_ages
                else:
                    data_status["raw_files"] = []
                    data_status["raw_count"] = 0
                
                if processed_data_dir.exists():
                    processed_files = list(processed_data_dir.glob("*.parquet"))
                    data_status["processed_files"] = [f.name for f in processed_files]
                    data_status["processed_count"] = len(processed_files)
                else:
                    data_status["processed_files"] = []
                    data_status["processed_count"] = 0
                
                data_status["last_ingestion"] = self.last_ingestion
                data_status["current_status"] = self.ingestion_status
                
                return create_standard_response(
                    data=data_status,
                    metadata={"service": "data-ingestion"}
                )
                
            except Exception as e:
                logger.error(f"Error getting data status: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/data/ingest")
        async def ingest_data(request: DataIngestionRequest, background_tasks: BackgroundTasks):
            """Trigger data ingestion"""
            try:
                # Get configuration from Configuration Service
                config = await self._get_configuration()
                
                # Default parameters from config or fallback
                years = request.years or list(range(
                    config.get("data_start_year", 2010), 
                    config.get("data_end_year", 2025)
                ))
                positions = request.positions or config.get("positions", ['QB', 'RB', 'WR', 'TE', 'K'])
                
                # Start background ingestion
                background_tasks.add_task(
                    self._run_data_ingestion,
                    years,
                    positions,
                    request.force_refresh,
                    request.include_weather,
                    request.include_rosters
                )
                
                return create_standard_response(
                    data={
                        "ingestion_started": True,
                        "years": years,
                        "positions": positions,
                        "force_refresh": request.force_refresh,
                        "include_weather": request.include_weather,
                        "include_rosters": request.include_rosters
                    },
                    message="Data ingestion started in background",
                    metadata={"service": "data-ingestion"}
                )
                
            except Exception as e:
                logger.error(f"Error starting data ingestion: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/data/health")
        async def check_data_health():
            """Check health of ingested data"""
            try:
                health_report = {
                    "data_freshness": {},
                    "data_quality": {},
                    "data_completeness": {},
                    "external_apis": {}
                }
                
                # Check data freshness
                import os
                from pathlib import Path
                
                paths = get_data_paths()
                raw_data_dir = Path(paths["raw"])
                if raw_data_dir.exists():
                    for file in raw_data_dir.glob("*.parquet"):
                        mtime = os.path.getmtime(file)
                        age_hours = (datetime.now().timestamp() - mtime) / 3600
                        health_report["data_freshness"][file.name] = {
                            "age_hours": round(age_hours, 2),
                            "status": "fresh" if age_hours < 24 else "stale"
                        }
                
                # Check external API connectivity
                try:
                    # Check NFL data availability
                    import nfl_data_py as nfl
                    health_report["external_apis"]["nfl_data_py"] = {
                        "status": "available",
                        "test_data": "accessible"
                    }
                except Exception as e:
                    health_report["external_apis"]["nfl_data_py"] = {
                        "status": "error",
                        "error": str(e)
                    }
                
                # Check Configuration Service connectivity
                try:
                    response = requests.get(f"{self.config_service_url}/health/live", timeout=5)
                    health_report["external_apis"]["configuration_service"] = {
                        "status": "available" if response.status_code == 200 else "degraded",
                        "response_code": response.status_code
                    }
                except Exception as e:
                    health_report["external_apis"]["configuration_service"] = {
                        "status": "unavailable",
                        "error": str(e)
                    }
                
                # Overall status
                overall_status = "healthy"
                if any(api.get("status") in ["error", "unavailable"] for api in health_report["external_apis"].values()):
                    overall_status = "degraded"
                
                health_report["overall_status"] = overall_status
                
                return create_standard_response(
                    data=health_report,
                    metadata={"service": "data-ingestion"}
                )
                
            except Exception as e:
                logger.error(f"Error checking data health: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/data/test")
        async def test_endpoint():
            """Simple test endpoint"""
            return {"status": "success", "message": "Test endpoint working"}
        
        @self.app.get("/api/v1/data/years/{year}", response_model=None)
        async def get_year_data(year: int):
            """Get data for specific year"""
            try:
                from pathlib import Path
                import pandas as pd
                from fastapi import Response
                
                # Look for year-specific data file using dynamic paths
                paths = get_data_paths()
                data_file = Path(f"{paths['processed']}/player_stats_{year}.parquet")
                
                if not data_file.exists():
                    # Return SafeJSONResponse directly for 404
                    return SafeJSONResponse(
                        status_code=404,
                        content={"detail": f"Data for year {year} not found"}
                    )
                
                # Read parquet file 
                df = pd.read_parquet(data_file)
                
                # Build response data with explicit type conversions
                positions = [str(p) for p in df['position'].unique()] if 'position' in df.columns else []
                
                # Get sample players with safe conversion
                sample_players = []
                if len(df) > 0:
                    for idx in range(min(3, len(df))):
                        row = df.iloc[idx]
                        player = {}
                        for col in ['player_name', 'position', 'games']:
                            if col in df.columns:
                                val = row[col]
                                # Convert numpy types to Python types
                                if hasattr(val, 'item'):
                                    val = val.item()
                                elif pd.isna(val):
                                    val = None
                                player[col] = val
                        sample_players.append(player)
                
                data_info = {
                    "year": int(year),
                    "total_players": int(len(df)),
                    "positions": positions,
                    "columns": [str(c) for c in df.columns[:20]],
                    "total_columns": int(len(df.columns)),
                    "data_shape": [int(df.shape[0]), int(df.shape[1])],
                    "sample_players": sample_players
                }
                
                response_data = {
                    "status": "success",
                    "data": data_info,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Return SafeJSONResponse directly to bypass FastAPI's encoder
                return SafeJSONResponse(content=response_data)
                
            except Exception as e:
                logger.error(f"Error in get_year_data: {e}", exc_info=True)
                return SafeJSONResponse(
                    status_code=500,
                    content={"detail": "Internal server error", "error": str(e)}
                )
        
        @self.app.post("/api/v1/data/validate", response_model=None)
        async def validate_data():
            """Run data quality validation checks"""
            try:
                validation_results = {
                    "timestamp": datetime.now().isoformat(),
                    "checks": {}
                }
                
                # Check for required data files using dynamic paths
                paths = get_data_paths()
                required_files = ["player_stats_2023.parquet", "player_stats_2024.parquet"]
                for file in required_files:
                    file_path = Path(f"{paths['processed']}/{file}")
                    validation_results["checks"][file] = {
                        "exists": bool(file_path.exists()),
                        "size_bytes": int(file_path.stat().st_size) if file_path.exists() else 0
                    }
                
                # Basic data quality checks with proper pandas handling
                try:
                    latest_file = Path(f"{paths['processed']}/player_stats_2024.parquet")
                    if latest_file.exists():
                        df = pd.read_parquet(latest_file)
                        
                        # Calculate statistics with explicit type conversion
                        total_records = int(len(df))
                        total_cells = int(len(df) * len(df.columns))
                        null_count = int(df.isnull().sum().sum())
                        null_percentage = float(null_count / total_cells * 100) if total_cells > 0 else 0.0
                        duplicate_count = int(df.duplicated().sum())
                        
                        # Position distribution with safe conversion
                        position_dist = {}
                        if 'position' in df.columns:
                            pos_counts = df['position'].value_counts()
                            for pos, count in pos_counts.items():
                                position_dist[str(pos)] = int(count)
                        
                        validation_results["checks"]["data_quality"] = {
                            "total_records": total_records,
                            "null_percentage": round(null_percentage, 2),
                            "duplicate_records": duplicate_count,
                            "position_distribution": position_dist
                        }
                except Exception as e:
                    validation_results["checks"]["data_quality"] = {"error": str(e)}
                
                # Overall status check
                overall_status = "passed"
                for file_check in validation_results["checks"].values():
                    if isinstance(file_check, dict) and not file_check.get("exists", True):
                        overall_status = "failed"
                        break
                
                validation_results["overall_status"] = overall_status
                
                response_data = {
                    "status": "success",
                    "data": validation_results,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Return SafeJSONResponse directly
                return SafeJSONResponse(content=response_data)
                
            except Exception as e:
                logger.error(f"Error validating data: {e}", exc_info=True)
                return SafeJSONResponse(
                    status_code=500,
                    content={"detail": "Internal server error", "error": str(e)}
                )
    
    async def _get_configuration(self) -> Dict[str, Any]:
        """Get configuration from Configuration Service"""
        try:
            response = requests.get(f"{self.config_service_url}/api/v1/config/data", timeout=10)
            if response.status_code == 200:
                return response.json().get("data", {})
        except Exception as e:
            logger.warning(f"Cannot get configuration: {e}")
        
        # Return default configuration
        return {
            "data_start_year": 2010,
            "data_end_year": 2025,
            "positions": ['QB', 'RB', 'WR', 'TE', 'K']
        }
    
    async def _run_data_ingestion(self, years: List[int], positions: List[str], 
                                 force_refresh: bool, include_weather: bool, include_rosters: bool):
        """Run data ingestion in background"""
        try:
            self.ingestion_status = {"status": "running", "started_at": datetime.now().isoformat()}
            
            logger.info(f"Starting data ingestion for years {years}, positions {positions}")
            
            total_steps = len(years) * (1 + (1 if include_weather else 0) + (1 if include_rosters else 0))
            current_step = 0
            
            for year in years:
                try:
                    # Fetch player stats
                    logger.info(f"Fetching player stats for {year}")
                    df = fetch_player_season_stats(year, positions)
                    
                    if df is not None and len(df) > 0:
                        # Save raw data using dynamic paths
                        paths = get_data_paths()
                        raw_file = Path(f"{paths['raw']}/player_stats_{year}.parquet")
                        df.to_parquet(raw_file, index=False)
                        logger.info(f"Saved {len(df)} records for {year}")
                        
                        # Basic cleaning and processing
                        processed_df = self._clean_data(df)
                        processed_file = Path(f"{paths['processed']}/player_stats_{year}.parquet")
                        processed_df.to_parquet(processed_file, index=False)
                        
                    current_step += 1
                    self.ingestion_status["progress"] = f"{current_step}/{total_steps}"
                    
                except Exception as e:
                    logger.error(f"Error ingesting data for year {year}: {e}")
                    continue
            
            self.ingestion_status = {"status": "completed", "completed_at": datetime.now().isoformat()}
            self.last_ingestion = {
                "timestamp": datetime.now().isoformat(),
                "years": years,
                "positions": positions,
                "status": "success",
                "records_processed": current_step
            }
            
            logger.info("Data ingestion completed successfully")
            
        except Exception as e:
            logger.error(f"Data ingestion failed: {e}")
            self.ingestion_status = {
                "status": "failed", 
                "error": str(e),
                "failed_at": datetime.now().isoformat()
            }
            self.last_ingestion = {
                "timestamp": datetime.now().isoformat(),
                "status": "failed",
                "error": str(e)
            }
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Basic data cleaning"""
        # Remove duplicates
        df = df.drop_duplicates()
        
        # Handle missing values for key columns
        if 'player_name' in df.columns:
            df = df.dropna(subset=['player_name'])
        
        # Ensure position column exists
        if 'position' not in df.columns and 'pos' in df.columns:
            df['position'] = df['pos']
        
        return df

# Create service instance
service = DataIngestionService()
app = service.app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)