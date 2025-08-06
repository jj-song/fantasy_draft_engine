"""
Enhanced Data Ingestion Service - External data acquisition and standardization.

ENHANCED FEATURES:
- Centralized logging with correlation IDs and structured output
- Unified data storage configuration
- Comprehensive operation tracking
- Enhanced error handling and recovery
- Performance monitoring
- Service health reporting
"""

import sys
sys.path.append('/Users/jihoonsong/Documents/projects/fantasy_draft_engine')

# Import centralized logging and data configuration
from logging_config import (
    setup_service_logging, 
    log_service_start, 
    log_service_shutdown,
    log_operation_start, 
    log_operation_complete, 
    log_operation_error,
    operation_logger,
    log_with_context
)
from data_config import get_data_config, get_path, get_file_path

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
import traceback

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .api.base_api import BaseService, create_standard_response, create_error_response
from .acquisition.nfl_data_fetcher import fetch_player_season_stats
from .cleaning.data_cleaning import *
from .storage.data_storage import *
from .config import get_data_paths

# Initialize centralized logging
logger = setup_service_logging(
    service_name="data-ingestion",
    service_version="2.0.0",
    log_level=os.environ.get("LOG_LEVEL", "INFO"),
    enable_console=True,
    enable_file=True,
    enable_structured=True
)

# Initialize centralized data configuration
data_config = get_data_config()

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

class DataIngestionRequest(BaseModel):
    years: Optional[List[int]] = None
    positions: Optional[List[str]] = None
    force_refresh: bool = False
    include_weather: bool = True
    include_rosters: bool = True

class DataIngestionService(BaseService):
    def __init__(self):
        super().__init__(
            service_name="Data Ingestion Service Enhanced",
            version="2.0.0",
            description="External data acquisition and standardization with enhanced logging and data management"
        )
        
        # Set up service-specific logger
        self.logger = logger
        
        # Service state
        self.ingestion_status = {}
        self.last_ingestion = {}
        self.config_service_url = os.environ.get("CONFIG_SERVICE_URL", "http://configuration:8000")
        
        # Override the default response class for the entire app
        self.app.default_response_class = SafeJSONResponse
        
        # Log service initialization
        log_with_context(
            self.logger, 
            self.logger.info.im_func.__code__.co_filename,  # Convert method to function code
            "Service initialization started",
            service_name="data-ingestion",
            version="2.0.0",
            config_url=self.config_service_url
        )
        
        self._setup_routes()
        
        # Override parent error handlers
        self._setup_error_handlers()
    
    def _setup_error_handlers(self):
        """Override parent's error handlers to use enhanced logging"""
        from fastapi import Request
        import time
        
        @self.app.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, exc: HTTPException):
            correlation_id = getattr(request.state, 'correlation_id', str(uuid.uuid4()))
            
            self.logger.error(
                f"HTTP Exception occurred: {exc.status_code} - {exc.detail}",
                extra={'extra_fields': {
                    'correlation_id': correlation_id,
                    'endpoint': str(request.url),
                    'method': request.method,
                    'status_code': exc.status_code,
                    'error_type': 'HTTPException'
                }}
            )
            
            error_response = {
                "status": "error",
                "error": {
                    "code": exc.status_code,
                    "message": exc.detail,
                    "correlation_id": correlation_id
                },
                "timestamp": time.time(),
                "service": "data-ingestion"
            }
            
            return SafeJSONResponse(
                status_code=exc.status_code,
                content=error_response
            )
        
        @self.app.exception_handler(Exception)
        async def general_exception_handler(request: Request, exc: Exception):
            correlation_id = getattr(request.state, 'correlation_id', str(uuid.uuid4()))
            
            self.logger.error(
                f"Unhandled exception occurred: {type(exc).__name__}: {str(exc)}",
                exc_info=True,
                extra={'extra_fields': {
                    'correlation_id': correlation_id,
                    'endpoint': str(request.url),
                    'method': request.method,
                    'error_type': type(exc).__name__,
                    'traceback': traceback.format_exc()
                }}
            )
            
            error_response = {
                "status": "error",
                "error": {
                    "code": 500,
                    "message": "Internal server error",
                    "correlation_id": correlation_id
                },
                "timestamp": time.time(),
                "service": "data-ingestion"
            }
            
            return SafeJSONResponse(
                status_code=500,
                content=error_response
            )
    
    async def startup(self):
        """Enhanced startup with detailed logging"""
        start_time = log_operation_start(
            self.logger, 
            "Service Startup",
            service="data-ingestion",
            version="2.0.0",
            environment=os.environ.get("ENVIRONMENT", "development")
        )
        
        try:
            # Log startup configuration
            log_service_start(
                "data-ingestion",
                port=8000,
                config_service_url=self.config_service_url,
                data_base_path=str(data_config.base_path),
                log_level=os.environ.get("LOG_LEVEL", "INFO"),
                structured_logging=True
            )
            
            # Ensure data directories exist using centralized config
            raw_path = data_config.ensure_path_exists("raw")
            processed_path = data_config.ensure_path_exists("processed")
            
            self.logger.info(f"Data directories initialized: raw={raw_path}, processed={processed_path}")
            
            # Try to connect to Configuration Service
            if self.config_service_url and not self.config_service_url.startswith("http://configuration"):
                try:
                    response = requests.get(f"{self.config_service_url}/health/live", timeout=5)
                    if response.status_code == 200:
                        self.logger.info("Successfully connected to Configuration Service")
                    else:
                        self.logger.warning(f"Configuration Service not healthy: {response.status_code}")
                except Exception as e:
                    self.logger.warning(f"Cannot connect to Configuration Service: {e}")
            else:
                self.logger.info("Using default configuration (Configuration Service not configured)")
            
            log_operation_complete(
                self.logger,
                "Service Startup",
                start_time,
                status="success",
                raw_path=str(raw_path),
                processed_path=str(processed_path)
            )
            
        except Exception as e:
            log_operation_error(
                self.logger,
                "Service Startup", 
                start_time,
                e,
                service="data-ingestion"
            )
            raise
    
    async def shutdown(self):
        """Enhanced shutdown with logging"""
        self.logger.info("Data Ingestion Service shutdown initiated")
        log_service_shutdown("data-ingestion")
    
    def _setup_routes(self):
        """Set up API routes with enhanced logging and error handling"""
        
        @self.app.get("/api/v1/data/status")
        @operation_logger("Get Data Status")
        async def get_data_status():
            """Get status of data ingestion with enhanced logging"""
            try:
                # Use centralized data paths
                raw_files = data_config.list_files("raw", "*.parquet")
                processed_files = data_config.list_files("processed", "*.parquet")
                
                data_status = {
                    "raw_files": [f.name for f in raw_files],
                    "raw_count": len(raw_files),
                    "processed_files": [f.name for f in processed_files],
                    "processed_count": len(processed_files),
                    "last_ingestion": self.last_ingestion,
                    "current_status": self.ingestion_status,
                    "data_paths": {
                        "raw": str(data_config.get_path("raw")),
                        "processed": str(data_config.get_path("processed"))
                    }
                }
                
                # Add file details
                file_details = {}
                for file in raw_files[:10]:  # Limit to prevent large responses
                    file_stat = file.stat()
                    age_hours = (datetime.now().timestamp() - file_stat.st_mtime) / 3600
                    file_details[file.name] = {
                        "age_hours": round(age_hours, 2),
                        "size_mb": round(file_stat.st_size / (1024*1024), 2)
                    }
                
                data_status["file_details"] = file_details
                
                log_with_context(
                    self.logger,
                    30,  # INFO level
                    "Data status requested",
                    raw_files_count=len(raw_files),
                    processed_files_count=len(processed_files),
                    total_files_size_mb=sum(f.stat().st_size for f in raw_files + processed_files) / (1024*1024)
                )
                
                return create_standard_response(
                    data=data_status,
                    metadata={"service": "data-ingestion", "version": "2.0.0"}
                )
                
            except Exception as e:
                self.logger.error(f"Error getting data status: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/data/ingest")
        async def ingest_data(request: DataIngestionRequest, background_tasks: BackgroundTasks):
            """Trigger data ingestion with enhanced logging"""
            correlation_id = str(uuid.uuid4())[:8]
            
            start_time = log_operation_start(
                self.logger,
                "Data Ingestion Request",
                correlation_id=correlation_id,
                years=request.years,
                positions=request.positions,
                force_refresh=request.force_refresh,
                include_weather=request.include_weather,
                include_rosters=request.include_rosters
            )
            
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
                    request.include_rosters,
                    correlation_id
                )
                
                response_data = {
                    "ingestion_started": True,
                    "years": years,
                    "positions": positions,
                    "force_refresh": request.force_refresh,
                    "include_weather": request.include_weather,
                    "include_rosters": request.include_rosters,
                    "correlation_id": correlation_id,
                    "estimated_duration_minutes": len(years) * 2  # Rough estimate
                }
                
                log_operation_complete(
                    self.logger,
                    "Data Ingestion Request",
                    start_time,
                    correlation_id=correlation_id,
                    years_count=len(years),
                    positions_count=len(positions)
                )
                
                return create_standard_response(
                    data=response_data,
                    message="Data ingestion started in background",
                    metadata={"service": "data-ingestion", "correlation_id": correlation_id}
                )
                
            except Exception as e:
                log_operation_error(
                    self.logger,
                    "Data Ingestion Request",
                    start_time,
                    e,
                    correlation_id=correlation_id
                )
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/data/health")
        @operation_logger("Data Health Check")
        async def check_data_health():
            """Enhanced health check with comprehensive reporting"""
            try:
                health_report = {
                    "service": "data-ingestion",
                    "version": "2.0.0",
                    "timestamp": datetime.now().isoformat(),
                    "data_freshness": {},
                    "data_quality": {},
                    "data_completeness": {},
                    "external_apis": {},
                    "storage_info": {}
                }
                
                # Check data freshness using centralized paths
                raw_files = data_config.list_files("raw", "*.parquet")
                for file in raw_files:
                    mtime = file.stat().st_mtime
                    age_hours = (datetime.now().timestamp() - mtime) / 3600
                    health_report["data_freshness"][file.name] = {
                        "age_hours": round(age_hours, 2),
                        "status": "fresh" if age_hours < 24 else "stale" if age_hours < 168 else "old"
                    }
                
                # Check external API connectivity
                try:
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
                
                # Add storage information
                health_report["storage_info"] = data_config.get_storage_info()
                
                # Overall status
                fresh_files = sum(1 for f in health_report["data_freshness"].values() if f["status"] == "fresh")
                total_files = len(health_report["data_freshness"])
                
                if fresh_files >= total_files * 0.8:  # 80% fresh files
                    overall_status = "healthy"
                elif fresh_files >= total_files * 0.5:  # 50% fresh files
                    overall_status = "degraded"
                else:
                    overall_status = "unhealthy"
                
                health_report["overall_status"] = overall_status
                health_report["health_score"] = round((fresh_files / max(total_files, 1)) * 100, 1)
                
                return create_standard_response(
                    data=health_report,
                    metadata={"service": "data-ingestion", "health_check": True}
                )
                
            except Exception as e:
                self.logger.error(f"Error checking data health: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/data/years/{year}")
        @operation_logger("Get Year Data")
        async def get_year_data(year: int):
            """Get data for specific year with enhanced error handling"""
            try:
                # Use centralized data paths
                data_file = data_config.get_file_path("processed", f"player_stats_{year}.parquet")
                
                if not data_file.exists():
                    self.logger.warning(f"Data file not found for year {year}: {data_file}")
                    return SafeJSONResponse(
                        status_code=404,
                        content={
                            "detail": f"Data for year {year} not found",
                            "expected_path": str(data_file),
                            "service": "data-ingestion"
                        }
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
                        for col in ['player_name', 'position', 'games', 'fantasy_points']:
                            if col in df.columns:
                                val = row[col]
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
                    "sample_players": sample_players,
                    "file_path": str(data_file),
                    "file_size_mb": round(data_file.stat().st_size / (1024*1024), 2)
                }
                
                response_data = {
                    "status": "success",
                    "data": data_info,
                    "timestamp": datetime.now().isoformat(),
                    "service": "data-ingestion"
                }
                
                log_with_context(
                    self.logger,
                    30,  # INFO level
                    f"Year {year} data retrieved successfully",
                    year=year,
                    total_players=len(df),
                    file_size_mb=data_info["file_size_mb"]
                )
                
                return SafeJSONResponse(content=response_data)
                
            except Exception as e:
                self.logger.error(f"Error retrieving data for year {year}: {e}", exc_info=True)
                return SafeJSONResponse(
                    status_code=500,
                    content={
                        "detail": "Internal server error", 
                        "error": str(e),
                        "service": "data-ingestion"
                    }
                )
        
        @self.app.post("/api/v1/data/validate")
        @operation_logger("Data Validation")
        async def validate_data():
            """Enhanced data validation with detailed reporting"""
            try:
                validation_results = {
                    "timestamp": datetime.now().isoformat(),
                    "service": "data-ingestion",
                    "version": "2.0.0",
                    "checks": {},
                    "summary": {}
                }
                
                # Check for required data files using centralized paths
                required_files = ["player_stats_2023.parquet", "player_stats_2024.parquet"]
                files_status = {}
                
                for file in required_files:
                    file_path = data_config.get_file_path("processed", file)
                    files_status[file] = {
                        "exists": file_path.exists(),
                        "path": str(file_path),
                        "size_bytes": int(file_path.stat().st_size) if file_path.exists() else 0,
                        "size_mb": round(file_path.stat().st_size / (1024*1024), 2) if file_path.exists() else 0
                    }
                
                validation_results["checks"]["required_files"] = files_status
                
                # Basic data quality checks
                try:
                    latest_file_path = data_config.get_file_path("processed", "player_stats_2024.parquet")
                    if latest_file_path.exists():
                        df = pd.read_parquet(latest_file_path)
                        
                        # Calculate statistics with explicit type conversion
                        total_records = int(len(df))
                        total_cells = int(len(df) * len(df.columns))
                        null_count = int(df.isnull().sum().sum())
                        null_percentage = float(null_count / total_cells * 100) if total_cells > 0 else 0.0
                        duplicate_count = int(df.duplicated().sum())
                        
                        # Position distribution
                        position_dist = {}
                        if 'position' in df.columns:
                            pos_counts = df['position'].value_counts()
                            for pos, count in pos_counts.items():
                                position_dist[str(pos)] = int(count)
                        
                        validation_results["checks"]["data_quality"] = {
                            "total_records": total_records,
                            "total_columns": len(df.columns),
                            "null_percentage": round(null_percentage, 2),
                            "duplicate_records": duplicate_count,
                            "position_distribution": position_dist,
                            "memory_usage_mb": round(df.memory_usage(deep=True).sum() / (1024*1024), 2)
                        }
                except Exception as e:
                    validation_results["checks"]["data_quality"] = {"error": str(e)}
                
                # Overall validation status
                files_exist = all(f["exists"] for f in files_status.values())
                data_quality_good = validation_results["checks"].get("data_quality", {}).get("null_percentage", 100) < 20
                
                overall_status = "passed" if files_exist and data_quality_good else "failed"
                
                validation_results["summary"] = {
                    "overall_status": overall_status,
                    "files_checked": len(required_files),
                    "files_passed": sum(1 for f in files_status.values() if f["exists"]),
                    "total_size_mb": sum(f["size_mb"] for f in files_status.values()),
                    "validation_score": round(
                        (sum(1 for f in files_status.values() if f["exists"]) / len(required_files)) * 100, 1
                    )
                }
                
                response_data = {
                    "status": "success",
                    "data": validation_results,
                    "timestamp": datetime.now().isoformat()
                }
                
                return SafeJSONResponse(content=response_data)
                
            except Exception as e:
                self.logger.error(f"Error validating data: {e}", exc_info=True)
                return SafeJSONResponse(
                    status_code=500,
                    content={"detail": "Internal server error", "error": str(e)}
                )
    
    async def _get_configuration(self) -> Dict[str, Any]:
        """Get configuration from Configuration Service with enhanced logging"""
        try:
            self.logger.debug(f"Fetching configuration from: {self.config_service_url}")
            response = requests.get(f"{self.config_service_url}/api/v1/config/data", timeout=10)
            if response.status_code == 200:
                config = response.json().get("data", {})
                self.logger.info("Successfully retrieved configuration from Configuration Service")
                return config
            else:
                self.logger.warning(f"Configuration service returned status {response.status_code}")
        except Exception as e:
            self.logger.warning(f"Cannot get configuration from service: {e}")
        
        # Return default configuration
        default_config = {
            "data_start_year": 2010,
            "data_end_year": 2025,
            "positions": ['QB', 'RB', 'WR', 'TE', 'K']
        }
        
        self.logger.info("Using default configuration")
        return default_config
    
    async def _run_data_ingestion(self, years: List[int], positions: List[str], 
                                 force_refresh: bool, include_weather: bool, 
                                 include_rosters: bool, correlation_id: str):
        """Enhanced data ingestion with comprehensive logging and error handling"""
        
        operation_start = log_operation_start(
            self.logger, 
            "Background Data Ingestion",
            correlation_id=correlation_id,
            years=years,
            positions=positions,
            force_refresh=force_refresh,
            include_weather=include_weather,
            include_rosters=include_rosters
        )
        
        try:
            self.ingestion_status = {
                "status": "running", 
                "started_at": datetime.now().isoformat(),
                "correlation_id": correlation_id
            }
            
            self.logger.info(f"Starting data ingestion for {len(years)} years, {len(positions)} positions")
            
            total_steps = len(years) * (1 + (1 if include_weather else 0) + (1 if include_rosters else 0))
            current_step = 0
            records_processed = 0
            files_created = 0
            
            for year in years:
                year_start_time = log_operation_start(
                    self.logger,
                    f"Process Year {year}",
                    correlation_id=correlation_id,
                    year=year,
                    positions=positions
                )
                
                try:
                    # Fetch player stats
                    self.logger.info(f"Fetching player stats for {year}")
                    df = fetch_player_season_stats(year, positions)
                    
                    if df is not None and len(df) > 0:
                        # Save raw data using centralized paths
                        raw_file = data_config.get_file_path("raw", f"player_stats_{year}.parquet")
                        df.to_parquet(raw_file, index=False)
                        
                        self.logger.info(f"Saved {len(df)} raw records for {year} to {raw_file}")
                        
                        # Basic cleaning and processing
                        processed_df = self._clean_data(df)
                        processed_file = data_config.get_file_path("processed", f"player_stats_{year}.parquet")
                        processed_df.to_parquet(processed_file, index=False)
                        
                        records_processed += len(processed_df)
                        files_created += 2  # raw + processed
                        
                        log_operation_complete(
                            self.logger,
                            f"Process Year {year}",
                            year_start_time,
                            correlation_id=correlation_id,
                            records_processed=len(processed_df),
                            raw_file=str(raw_file),
                            processed_file=str(processed_file)
                        )
                        
                    else:
                        self.logger.warning(f"No data retrieved for year {year}")
                        
                    current_step += 1
                    progress_pct = round((current_step / total_steps) * 100, 1)
                    self.ingestion_status["progress"] = f"{current_step}/{total_steps} ({progress_pct}%)"
                    
                except Exception as e:
                    log_operation_error(
                        self.logger,
                        f"Process Year {year}",
                        year_start_time,
                        e,
                        correlation_id=correlation_id,
                        year=year
                    )
                    continue
            
            # Successful completion
            self.ingestion_status = {
                "status": "completed", 
                "completed_at": datetime.now().isoformat(),
                "correlation_id": correlation_id
            }
            
            self.last_ingestion = {
                "timestamp": datetime.now().isoformat(),
                "years": years,
                "positions": positions,
                "status": "success",
                "records_processed": records_processed,
                "files_created": files_created,
                "correlation_id": correlation_id
            }
            
            log_operation_complete(
                self.logger,
                "Background Data Ingestion",
                operation_start,
                correlation_id=correlation_id,
                total_years=len(years),
                records_processed=records_processed,
                files_created=files_created,
                success_rate=round((current_step / total_steps) * 100, 1)
            )
            
        except Exception as e:
            # Failed completion
            log_operation_error(
                self.logger,
                "Background Data Ingestion",
                operation_start,
                e,
                correlation_id=correlation_id,
                years=years,
                positions=positions
            )
            
            self.ingestion_status = {
                "status": "failed", 
                "error": str(e),
                "failed_at": datetime.now().isoformat(),
                "correlation_id": correlation_id
            }
            
            self.last_ingestion = {
                "timestamp": datetime.now().isoformat(),
                "status": "failed",
                "error": str(e),
                "correlation_id": correlation_id
            }
    
    @operation_logger("Data Cleaning")
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enhanced data cleaning with logging"""
        original_count = len(df)
        
        # Remove duplicates
        df = df.drop_duplicates()
        duplicate_removed = original_count - len(df)
        
        # Handle missing values for key columns
        if 'player_name' in df.columns:
            before_count = len(df)
            df = df.dropna(subset=['player_name'])
            missing_names_removed = before_count - len(df)
        else:
            missing_names_removed = 0
        
        # Ensure position column exists
        if 'position' not in df.columns and 'pos' in df.columns:
            df['position'] = df['pos']
            self.logger.info("Mapped 'pos' column to 'position'")
        
        final_count = len(df)
        
        log_with_context(
            self.logger,
            30,  # INFO level
            "Data cleaning completed",
            original_records=original_count,
            final_records=final_count,
            duplicates_removed=duplicate_removed,
            missing_names_removed=missing_names_removed,
            retention_rate=round((final_count / max(original_count, 1)) * 100, 1)
        )
        
        return df

# Create service instance
service = DataIngestionService()
app = service.app

if __name__ == "__main__":
    import uvicorn
    
    # Log startup information
    logger.info("Starting Data Ingestion Service Enhanced")
    logger.info(f"Data base path: {data_config.base_path}")
    logger.info(f"Logging configuration: Structured logging enabled")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)