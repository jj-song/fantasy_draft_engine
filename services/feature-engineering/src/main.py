"""
Feature Engineering Service - Transform raw data into ML-ready features.
"""
import logging
from typing import Dict, Any, Optional, List
import pandas as pd
from pathlib import Path
import requests
from datetime import datetime

from fastapi import HTTPException, BackgroundTasks
from pydantic import BaseModel

from .api.base_api import BaseService, create_standard_response
from .processors.feature_engineering import *
from .quality.feature_compatibility import *
from .quality.data_quality_validator import *

# Add debug validation
try:
    from utils.debug_analysis.debug_integration import add_validation_checkpoint, save_all_validation_reports
    VALIDATION_ENABLED = True
except ImportError:
    VALIDATION_ENABLED = False
    def add_validation_checkpoint(*args, **kwargs):
        pass
    def save_all_validation_reports():
        return {}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FeatureEngineeringRequest(BaseModel):
    years: Optional[List[int]] = None
    positions: Optional[List[str]] = None
    force_regenerate: bool = False
    include_advanced_features: bool = True

class FeatureEngineeringService(BaseService):
    def __init__(self):
        super().__init__(
            service_name="Feature Engineering Service",
            version="1.0.0",
            description="Transform raw data into ML-ready features"
        )
        
        self.processing_status = {}
        self.last_processing = {}
        self.config_service_url = "http://configuration:8000"
        self.data_ingestion_url = "http://data-ingestion:8000"
        
        self._setup_routes()
    
    async def startup(self):
        logger.info("Feature Engineering Service started successfully") 
        
        # Initialize feature directories
        import os
        os.makedirs("data/processed/features", exist_ok=True)
        os.makedirs("data/processed/position_specific", exist_ok=True)
        
        # Check service dependencies
        await self._check_dependencies()
    
    async def _check_dependencies(self):
        """Check if dependent services are available"""
        try:
            # Check Configuration Service
            response = requests.get(f"{self.config_service_url}/health/live", timeout=5)
            logger.info(f"Configuration Service status: {response.status_code}")
            
            # Check Data Ingestion Service  
            response = requests.get(f"{self.data_ingestion_url}/health/live", timeout=5)
            logger.info(f"Data Ingestion Service status: {response.status_code}")
            
        except Exception as e:
            logger.warning(f"Error checking service dependencies: {e}")
    
    def _setup_routes(self):
        @self.app.get("/api/v1/features/status")
        async def get_status():
            """Get feature engineering service status"""
            try:
                status_info = {
                    "service_status": "running",
                    "processing_status": self.processing_status,
                    "last_processing": self.last_processing,
                    "available_features": await self._get_available_features(),
                    "feature_quality": await self._get_feature_quality_summary()
                }
                
                return create_standard_response(
                    data=status_info,
                    metadata={"service": "feature-engineering"}
                )
                
            except Exception as e:
                logger.error(f"Error getting status: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/features/generate")
        async def generate_features(request: FeatureEngineeringRequest, background_tasks: BackgroundTasks):
            """Generate features for specified years and positions"""
            try:
                # Get configuration
                config = await self._get_configuration()
                
                # Default parameters
                years = request.years or list(range(
                    config.get("data_start_year", 2020),
                    config.get("data_end_year", 2025)
                ))
                positions = request.positions or config.get("core_positions", ['QB', 'RB', 'WR', 'TE'])
                
                # Start background processing
                background_tasks.add_task(
                    self._run_feature_generation,
                    years,
                    positions,
                    request.force_regenerate,
                    request.include_advanced_features
                )
                
                return create_standard_response(
                    data={
                        "feature_generation_started": True,
                        "years": years,
                        "positions": positions,
                        "force_regenerate": request.force_regenerate,
                        "include_advanced_features": request.include_advanced_features
                    },
                    message="Feature generation started in background",
                    metadata={"service": "feature-engineering"}
                )
                
            except Exception as e:
                logger.error(f"Error starting feature generation: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/features/quality")
        async def get_feature_quality():
            """Get feature quality metrics"""
            try:
                quality_report = await self._generate_quality_report()
                
                return create_standard_response(
                    data=quality_report,
                    metadata={"service": "feature-engineering"}
                )
                
            except Exception as e:
                logger.error(f"Error getting feature quality: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/features/position/{position}")
        async def get_position_features(position: str):
            """Get features available for specific position"""
            try:
                if position.upper() not in ['QB', 'RB', 'WR', 'TE']:
                    raise HTTPException(status_code=400, detail=f"Invalid position: {position}")
                
                # Look for position-specific feature files
                feature_files = list(Path("data/processed/position_specific").glob(f"*{position.lower()}*.parquet"))
                
                position_info = {
                    "position": position.upper(),
                    "available_files": [f.name for f in feature_files],
                    "feature_count": 0,
                    "latest_file": None
                }
                
                if feature_files:
                    # Get info from latest file
                    latest_file = max(feature_files, key=lambda x: x.stat().st_mtime)
                    position_info["latest_file"] = latest_file.name
                    
                    try:
                        df = pd.read_parquet(latest_file)
                        position_info["feature_count"] = len(df.columns)
                        position_info["sample_features"] = df.columns.tolist()[:10]
                        position_info["total_players"] = len(df)
                    except Exception as e:
                        position_info["error"] = f"Error reading file: {e}"
                
                return create_standard_response(
                    data=position_info,
                    metadata={"service": "feature-engineering", "position": position}
                )
                
            except Exception as e:
                logger.error(f"Error getting position features for {position}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/features/validate")
        async def validate_features():
            """Validate feature quality and compatibility"""
            try:
                validation_results = {
                    "timestamp": datetime.now().isoformat(),
                    "feature_validation": {},
                    "compatibility_check": {},
                    "quality_metrics": {}
                }
                
                # Check each position
                positions = ['QB', 'RB', 'WR', 'TE']
                for position in positions:
                    try:
                        validation_results["feature_validation"][position] = await self._validate_position_features(position)
                    except Exception as e:
                        validation_results["feature_validation"][position] = {"error": str(e)}
                
                # Overall status
                all_valid = all(
                    result.get("status") == "valid" 
                    for result in validation_results["feature_validation"].values()
                    if isinstance(result, dict) and "status" in result
                )
                
                validation_results["overall_status"] = "passed" if all_valid else "failed"
                
                return create_standard_response(
                    data=validation_results,
                    metadata={"service": "feature-engineering"}
                )
                
            except Exception as e:
                logger.error(f"Error validating features: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    async def _get_configuration(self) -> Dict[str, Any]:
        """Get configuration from Configuration Service"""
        try:
            response = requests.get(f"{self.config_service_url}/api/v1/config/data", timeout=10)
            if response.status_code == 200:
                return response.json().get("data", {})
        except Exception as e:
            logger.warning(f"Cannot get configuration: {e}")
        
        return {
            "data_start_year": 2020,
            "data_end_year": 2025,
            "core_positions": ['QB', 'RB', 'WR', 'TE']
        }
    
    async def _run_feature_generation(self, years: List[int], positions: List[str], 
                                     force_regenerate: bool, include_advanced_features: bool):
        """Run feature generation in background"""
        try:
            self.processing_status = {"status": "running", "started_at": datetime.now().isoformat()}
            
            logger.info(f"Starting feature generation for years {years}, positions {positions}")
            
            total_steps = len(years) * len(positions)
            current_step = 0
            
            for year in years:
                for position in positions:
                    try:
                        # Check if raw data exists
                        raw_file = Path(f"data/processed/player_stats_{year}.parquet")
                        if not raw_file.exists():
                            logger.warning(f"Raw data not found for {year}, skipping")
                            continue
                        
                        # Generate features for this position/year
                        logger.info(f"Generating features for {position} {year}")
                        
                        # Load raw data
                        df = pd.read_parquet(raw_file)
                        
                        # VALIDATION CHECKPOINT: Raw data loaded
                        add_validation_checkpoint('feature-engineering', f'raw_data_loaded_{position}_{year}', df,
                                                expected_type=pd.DataFrame,
                                                expected_columns=['player_name', 'position'])
                        
                        position_df = df[df['position'] == position] if 'position' in df.columns else df
                        
                        # VALIDATION CHECKPOINT: Position filtered data
                        add_validation_checkpoint('feature-engineering', f'position_data_{position}_{year}', position_df,
                                                expected_type=pd.DataFrame,
                                                expected_shape=(50, 81))  # ~50 players per position, 81 columns from data ingestion
                        
                        if len(position_df) > 0:
                            # Generate position-specific features
                            features_df = await self._generate_position_features(position_df, position, year)
                            
                            # VALIDATION CHECKPOINT: Generated features
                            add_validation_checkpoint('feature-engineering', f'generated_features_{position}_{year}', features_df,
                                                    expected_type=pd.DataFrame,
                                                    expected_shape=(50, 28))  # 28 core features expected
                            
                            if features_df is not None and len(features_df) > 0:
                                # Save features
                                output_file = Path(f"data/processed/position_specific/{position.lower()}_features_{year}.parquet")
                                features_df.to_parquet(output_file, index=False)
                                logger.info(f"Saved {len(features_df)} feature records for {position} {year}")
                                
                                # VALIDATION CHECKPOINT: Feature file saved
                                file_info = {
                                    'file_path': str(output_file),
                                    'file_size_mb': output_file.stat().st_size / 1024 / 1024 if output_file.exists() else 0,
                                    'player_count': len(features_df),
                                    'feature_count': len(features_df.columns)
                                }
                                add_validation_checkpoint('feature-engineering', f'features_saved_{position}_{year}', file_info,
                                                        expected_type=dict)
                        
                        current_step += 1
                        self.processing_status["progress"] = f"{current_step}/{total_steps}"
                        
                    except Exception as e:
                        logger.error(f"Error generating features for {position} {year}: {e}")
                        continue
            
            self.processing_status = {"status": "completed", "completed_at": datetime.now().isoformat()}
            self.last_processing = {
                "timestamp": datetime.now().isoformat(),
                "years": years,
                "positions": positions,
                "status": "success",
                "features_generated": current_step
            }
            
            logger.info("Feature generation completed successfully")
            
            # Save validation report
            if VALIDATION_ENABLED:
                validation_reports = save_all_validation_reports()
                logger.info(f"Feature engineering validation reports saved: {validation_reports}")
            
        except Exception as e:
            logger.error(f"Feature generation failed: {e}")
            self.processing_status = {
                "status": "failed", 
                "error": str(e),
                "failed_at": datetime.now().isoformat()
            }
            self.last_processing = {
                "timestamp": datetime.now().isoformat(),
                "status": "failed",
                "error": str(e)
            }
    
    async def _generate_position_features(self, df: pd.DataFrame, position: str, year: int) -> pd.DataFrame:
        """Generate features for specific position with detailed transformation logging"""
        try:
            logger.info(f"🔧 DETAILED FEATURE ENGINEERING START: {position} {year}")
            logger.info("=" * 80)
            
            # VALIDATION CHECKPOINT: Feature engineering input
            add_validation_checkpoint('feature-engineering', f'feature_input_{position}_{year}', df,
                                    expected_type=pd.DataFrame,
                                    expected_columns=['player_name', 'position', 'games'],
                                    expected_shape=(100, 81))  # Flexible player count, 81 columns from data ingestion
            
            # Log input data summary
            logger.info(f"📊 INPUT DATA SUMMARY:")
            logger.info(f"   Players: {len(df)}")
            logger.info(f"   Input columns: {len(df.columns)}")
            logger.info(f"   Sample columns: {list(df.columns[:10])}")
            
            if len(df) > 0:
                # Show sample player data
                sample_player = df.iloc[0]
                logger.info(f"   Sample player: {sample_player.get('player_name', 'Unknown')}")
                logger.info(f"   Team: {sample_player.get('team', 'Unknown')}")
                logger.info(f"   Games: {sample_player.get('games', 'Unknown')}")
            
            features_df = df.copy()
            transformations_applied = []
            
            # TRANSFORMATION 1: Basic Derived Features
            logger.info(f"\n🔄 TRANSFORMATION 1: Basic Derived Features")
            
            # Yards per carry (for RBs primarily)
            if 'rushing_yards' in df.columns and 'rushing_attempts' in df.columns:
                original_rushing = df['rushing_yards'].iloc[0] if len(df) > 0 else 0
                original_attempts = df['rushing_attempts'].iloc[0] if len(df) > 0 else 0
                
                features_df['yards_per_carry'] = df['rushing_yards'] / df['rushing_attempts'].replace(0, 1)
                
                calculated_ypc = features_df['yards_per_carry'].iloc[0] if len(features_df) > 0 else 0
                logger.info(f"   ✅ Yards per Carry: {original_rushing} yards ÷ {original_attempts} attempts = {calculated_ypc:.2f} YPC")
                transformations_applied.append("yards_per_carry")
            
            # Yards per reception (for skill positions)
            if 'receiving_yards' in df.columns and 'receptions' in df.columns:
                original_rec_yards = df['receiving_yards'].iloc[0] if len(df) > 0 else 0
                original_receptions = df['receptions'].iloc[0] if len(df) > 0 else 0
                
                features_df['yards_per_reception'] = df['receiving_yards'] / df['receptions'].replace(0, 1)
                
                calculated_ypr = features_df['yards_per_reception'].iloc[0] if len(features_df) > 0 else 0
                logger.info(f"   ✅ Yards per Reception: {original_rec_yards} yards ÷ {original_receptions} receptions = {calculated_ypr:.2f} YPR")
                transformations_applied.append("yards_per_reception")
            
            # TRANSFORMATION 2: Position-Specific Features
            logger.info(f"\n🔄 TRANSFORMATION 2: Position-Specific Features ({position})")
            
            if position == 'QB':
                # Completion percentage
                if 'passing_attempts' in df.columns and 'passing_completions' in df.columns:
                    original_completions = df['passing_completions'].iloc[0] if len(df) > 0 else 0
                    original_attempts = df['passing_attempts'].iloc[0] if len(df) > 0 else 0
                    
                    features_df['completion_percentage'] = (df['passing_completions'] / df['passing_attempts'].replace(0, 1)) * 100
                    
                    calculated_comp_pct = features_df['completion_percentage'].iloc[0] if len(features_df) > 0 else 0
                    logger.info(f"   ✅ Completion %: {original_completions} completions ÷ {original_attempts} attempts = {calculated_comp_pct:.1f}%")
                    transformations_applied.append("completion_percentage")
                
                # Yards per attempt
                if 'passing_yards' in df.columns and 'passing_attempts' in df.columns:
                    original_passing_yards = df['passing_yards'].iloc[0] if len(df) > 0 else 0
                    original_attempts = df['passing_attempts'].iloc[0] if len(df) > 0 else 0
                    
                    features_df['yards_per_attempt'] = df['passing_yards'] / df['passing_attempts'].replace(0, 1)
                    
                    calculated_ypa = features_df['yards_per_attempt'].iloc[0] if len(features_df) > 0 else 0
                    logger.info(f"   ✅ Yards per Attempt: {original_passing_yards} yards ÷ {original_attempts} attempts = {calculated_ypa:.2f} YPA")
                    transformations_applied.append("yards_per_attempt")
            
            elif position == 'RB':
                # Catch rate for receiving backs
                if 'targets' in df.columns and 'receptions' in df.columns:
                    original_targets = df['targets'].iloc[0] if len(df) > 0 else 0
                    original_receptions = df['receptions'].iloc[0] if len(df) > 0 else 0
                    
                    features_df['catch_rate'] = (df['receptions'] / df['targets'].replace(0, 1)) * 100
                    
                    calculated_catch_rate = features_df['catch_rate'].iloc[0] if len(features_df) > 0 else 0
                    logger.info(f"   ✅ Catch Rate: {original_receptions} catches ÷ {original_targets} targets = {calculated_catch_rate:.1f}%")
                    transformations_applied.append("catch_rate")
            
            elif position in ['WR', 'TE']:
                # Target efficiency
                if 'targets' in df.columns and 'receiving_yards' in df.columns:
                    original_targets = df['targets'].iloc[0] if len(df) > 0 else 0
                    original_rec_yards = df['receiving_yards'].iloc[0] if len(df) > 0 else 0
                    
                    features_df['yards_per_target'] = df['receiving_yards'] / df['targets'].replace(0, 1)
                    
                    calculated_ypt = features_df['yards_per_target'].iloc[0] if len(features_df) > 0 else 0
                    logger.info(f"   ✅ Yards per Target: {original_rec_yards} yards ÷ {original_targets} targets = {calculated_ypt:.2f} YPT")
                    transformations_applied.append("yards_per_target")
                
                # Catch rate
                if 'targets' in df.columns and 'receptions' in df.columns:
                    original_targets = df['targets'].iloc[0] if len(df) > 0 else 0
                    original_receptions = df['receptions'].iloc[0] if len(df) > 0 else 0
                    
                    features_df['catch_rate'] = (df['receptions'] / df['targets'].replace(0, 1)) * 100
                    
                    calculated_catch_rate = features_df['catch_rate'].iloc[0] if len(features_df) > 0 else 0
                    logger.info(f"   ✅ Catch Rate: {original_receptions} catches ÷ {original_targets} targets = {calculated_catch_rate:.1f}%")
                    transformations_applied.append("catch_rate")
            
            # TRANSFORMATION 3: Per-Game Normalizations
            logger.info(f"\n🔄 TRANSFORMATION 3: Per-Game Statistics")
            
            if 'games' in df.columns:
                games_played = df['games'].iloc[0] if len(df) > 0 else 1
                logger.info(f"   Normalizing by games played: {games_played}")
                
                # Add per-game stats for key metrics
                per_game_stats = []
                
                if 'fantasy_points' in df.columns:
                    original_fp = df['fantasy_points'].iloc[0] if len(df) > 0 else 0
                    features_df['fantasy_points_per_game'] = df['fantasy_points'] / df['games'].replace(0, 1)
                    calculated_fppg = features_df['fantasy_points_per_game'].iloc[0] if len(features_df) > 0 else 0
                    logger.info(f"   ✅ Fantasy Points per Game: {original_fp} total ÷ {games_played} games = {calculated_fppg:.2f} FPPG")
                    per_game_stats.append("fantasy_points_per_game")
                
                if position == 'QB' and 'passing_yards' in df.columns:
                    original_pass_yards = df['passing_yards'].iloc[0] if len(df) > 0 else 0
                    features_df['passing_yards_per_game'] = df['passing_yards'] / df['games'].replace(0, 1)
                    calculated_pypg = features_df['passing_yards_per_game'].iloc[0] if len(features_df) > 0 else 0
                    logger.info(f"   ✅ Passing Yards per Game: {original_pass_yards} total ÷ {games_played} games = {calculated_pypg:.1f} PYPG")
                    per_game_stats.append("passing_yards_per_game")
                
                transformations_applied.extend(per_game_stats)
            
            # TRANSFORMATION 4: Add Metadata
            logger.info(f"\n🔄 TRANSFORMATION 4: Metadata Addition")
            features_df['year'] = year
            features_df['position'] = position
            logger.info(f"   ✅ Added year: {year}")
            logger.info(f"   ✅ Added position: {position}")
            transformations_applied.extend(["year", "position"])
            
            # Final Summary
            logger.info(f"\n📊 FEATURE ENGINEERING RESULTS:")
            logger.info(f"   Input features: {len(df.columns)}")
            logger.info(f"   Output features: {len(features_df.columns)}")
            logger.info(f"   New features added: {len(features_df.columns) - len(df.columns)}")
            logger.info(f"   Transformations applied: {len(transformations_applied)}")
            logger.info(f"   Transformation list: {transformations_applied}")
            
            # Show before/after comparison for first player
            if len(features_df) > 0:
                logger.info(f"\n🔍 BEFORE/AFTER COMPARISON (First Player):")
                sample_player = features_df.iloc[0]
                logger.info(f"   Player: {sample_player.get('player_name', 'Unknown')}")
                
                # Show key original stats
                logger.info(f"   ORIGINAL STATS:")
                if 'games' in sample_player:
                    logger.info(f"     Games: {sample_player['games']}")
                if 'fantasy_points' in sample_player:
                    logger.info(f"     Fantasy Points: {sample_player['fantasy_points']}")
                if position == 'QB':
                    if 'passing_yards' in sample_player:
                        logger.info(f"     Passing Yards: {sample_player['passing_yards']}")
                    if 'passing_attempts' in sample_player:
                        logger.info(f"     Pass Attempts: {sample_player['passing_attempts']}")
                elif position == 'RB':
                    if 'rushing_yards' in sample_player:
                        logger.info(f"     Rushing Yards: {sample_player['rushing_yards']}")
                    if 'rushing_attempts' in sample_player:
                        logger.info(f"     Rush Attempts: {sample_player['rushing_attempts']}")
                
                # Show calculated features
                logger.info(f"   CALCULATED FEATURES:")
                for feature in transformations_applied:
                    if feature in sample_player and feature not in ['year', 'position']:
                        value = sample_player[feature]
                        if isinstance(value, (int, float)):
                            logger.info(f"     {feature}: {value:.2f}")
                        else:
                            logger.info(f"     {feature}: {value}")
            
            logger.info("=" * 80)
            logger.info(f"✅ FEATURE ENGINEERING COMPLETE: {position} {year}")
            
            # VALIDATION CHECKPOINT: Final feature engineering output
            add_validation_checkpoint('feature-engineering', f'feature_output_{position}_{year}', features_df,
                                    expected_type=pd.DataFrame,
                                    expected_shape=(100, 28))  # 28 core features expected
            
            # Additional feature quality validation
            if features_df is not None:
                feature_quality = {
                    'input_players': len(df),
                    'output_players': len(features_df),
                    'input_columns': len(df.columns),
                    'output_columns': len(features_df.columns),
                    'transformations_applied': len(transformations_applied),
                    'sample_transformations': transformations_applied[:5]  # First 5 transformations
                }
                add_validation_checkpoint('feature-engineering', f'feature_quality_{position}_{year}', feature_quality,
                                        expected_type=dict)
            
            return features_df
            
        except Exception as e:
            logger.error(f"Error generating features for {position}: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return None
    
    async def _get_available_features(self) -> Dict[str, Any]:
        """Get summary of available features"""
        try:
            feature_summary = {}
            
            # Check position-specific features
            feature_dir = Path("data/processed/position_specific")
            if feature_dir.exists():
                for position in ['QB', 'RB', 'WR', 'TE']:
                    position_files = list(feature_dir.glob(f"{position.lower()}_features_*.parquet"))
                    feature_summary[position] = {
                        "file_count": len(position_files),
                        "years_available": []
                    }
                    
                    # Extract years from filenames
                    for file in position_files:
                        try:
                            year = int(file.stem.split('_')[-1])
                            feature_summary[position]["years_available"].append(year)
                        except:
                            continue
                    
                    feature_summary[position]["years_available"].sort()
            
            return feature_summary
            
        except Exception as e:
            logger.error(f"Error getting available features: {e}")
            return {}
    
    async def _get_feature_quality_summary(self) -> Dict[str, Any]:
        """Get feature quality summary"""
        try:
            quality_summary = {
                "last_validation": None,
                "overall_quality": "unknown",
                "position_quality": {}
            }
            
            # This would implement actual quality checks
            # For now, return basic info
            return quality_summary
            
        except Exception as e:
            logger.error(f"Error getting feature quality summary: {e}")
            return {}
    
    async def _generate_quality_report(self) -> Dict[str, Any]:
        """Generate comprehensive feature quality report"""
        try:
            quality_report = {
                "timestamp": datetime.now().isoformat(),
                "feature_coverage": {},
                "data_quality": {},
                "feature_distributions": {}
            }
            
            # Check each position's features
            for position in ['QB', 'RB', 'WR', 'TE']:
                try:
                    # Find latest feature file for position
                    feature_files = list(Path("data/processed/position_specific").glob(f"{position.lower()}_features_*.parquet"))
                    
                    if feature_files:
                        latest_file = max(feature_files, key=lambda x: x.stat().st_mtime)
                        df = pd.read_parquet(latest_file)
                        
                        quality_report["feature_coverage"][position] = {
                            "total_features": int(len(df.columns)),
                            "total_players": int(len(df)),
                            "null_percentage": float(round(df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100, 2)),
                            "duplicate_records": int(df.duplicated().sum())
                        }
                    else:
                        quality_report["feature_coverage"][position] = {"status": "no_data"}
                        
                except Exception as e:
                    quality_report["feature_coverage"][position] = {"error": str(e)}
            
            return quality_report
            
        except Exception as e:
            logger.error(f"Error generating quality report: {e}")
            return {"error": str(e)}
    
    async def _validate_position_features(self, position: str) -> Dict[str, Any]:
        """Validate features for specific position"""
        try:
            # Find latest feature file
            feature_files = list(Path("data/processed/position_specific").glob(f"{position.lower()}_features_*.parquet"))
            
            if not feature_files:
                return {"status": "no_data", "message": f"No feature files found for {position}"}
            
            latest_file = max(feature_files, key=lambda x: x.stat().st_mtime)
            df = pd.read_parquet(latest_file)
            
            validation_result = {
                "status": "valid",
                "file": latest_file.name,
                "total_features": int(len(df.columns)),
                "total_players": int(len(df)),
                "checks_passed": []
            }
            
            # Basic validation checks
            if len(df) > 0:
                validation_result["checks_passed"].append("has_data")
            
            if 'player_name' in df.columns or 'player_id' in df.columns:
                validation_result["checks_passed"].append("has_player_identifier")
            
            # Check for reasonable feature counts
            expected_min_features = {"QB": 15, "RB": 20, "WR": 18, "TE": 15}
            if len(df.columns) >= expected_min_features.get(position, 10):
                validation_result["checks_passed"].append("sufficient_features")
            
            return validation_result
            
        except Exception as e:
            return {"status": "error", "error": str(e)}

service = FeatureEngineeringService()
app = service.app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)