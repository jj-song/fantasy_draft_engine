"""
VOR Calculator - Calculate Value Over Replacement for fantasy players.

This module provides VOR calculation functionality including:
- Position-specific replacement level calculation
- Player value assessment
- VOR ranking generation
- Baseline management
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import sys
import requests

# Add paths for accessing legacy modules
services_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.append(str(services_root))
sys.path.append(str(services_root / "legacy"))

logger = logging.getLogger(__name__)

class VORCalculator:
    """
    Calculate Value Over Replacement (VOR) for fantasy football players.
    
    VOR is the key metric for determining draft value by comparing each player's
    projected points to the replacement level at their position.
    """
    
    def __init__(self, config_service_url: str = None,
                 ml_models_service_url: str = None):
        """
        Initialize VOR calculator.
        
        Args:
            config_service_url: Configuration service URL
            ml_models_service_url: ML Models service URL
        """
        import os
        self.config_service_url = config_service_url or os.getenv('CONFIG_SERVICE_URL', 'http://localhost:8001')
        self.ml_models_service_url = ml_models_service_url or os.getenv('ML_MODELS_URL', 'http://localhost:8004')
        
        # VOR baselines (replacement level by position)
        self.vor_baselines = {
            "QB": 15,   # QB15 - streaming QBs viable
            "RB": 36,   # RB36 - ~3 per team in 12-team league  
            "WR": 36,   # WR36 - similar depth to RB
            "TE": 15    # TE15 - significant dropoff after top tier
        }
        
        # Position roster requirements (for 12-team league)
        self.roster_requirements = {
            "QB": {"starters": 1, "total": 2},
            "RB": {"starters": 2, "total": 4}, 
            "WR": {"starters": 2, "total": 4},
            "TE": {"starters": 1, "total": 2}
        }
        
        # Cached data
        self.cached_predictions = {}
        self.cached_vor_results = {}
        
        logger.info("📊 VOR Calculator initialized")
    
    async def initialize_baselines(self) -> bool:
        """
        Initialize VOR baselines from configuration.
        
        Returns:
            True if initialization successful
        """
        try:
            logger.info("🎯 Initializing VOR baselines...")
            
            # Get configuration from config service
            config = await self._get_configuration()
            
            # Update baselines if provided in config
            if "vor_baselines" in config:
                self.vor_baselines.update(config["vor_baselines"])
                logger.info("✅ VOR baselines updated from configuration")
            
            # Update roster requirements if provided
            if "roster_requirements" in config:
                self.roster_requirements.update(config["roster_requirements"])
                logger.info("✅ Roster requirements updated from configuration")
            
            # Log current baselines
            logger.info("📊 Current VOR baselines:")
            for position, baseline in self.vor_baselines.items():
                logger.info(f"   {position}: {baseline} (replacement level)")
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to initialize VOR baselines: {e}")
            logger.info("Using default VOR baselines")
            return False
    
    async def calculate_position_vor(self, position: str, season: Optional[int] = None,
                                   force_recalculate: bool = False) -> Dict[str, Any]:
        """
        Calculate VOR for all players at a specific position.
        
        Args:
            position: Player position (QB, RB, WR, TE)
            season: Season for predictions (defaults to current prediction season)
            force_recalculate: Whether to force recalculation even if cached
            
        Returns:
            Dictionary containing VOR calculations for the position
        """
        try:
            position = position.upper()
            logger.info(f"📊 Calculating VOR for {position} position...")
            
            # Check cache first
            cache_key = f"{position}_{season or 'current'}"
            if not force_recalculate and cache_key in self.cached_vor_results:
                logger.info(f"✅ Using cached VOR results for {position}")
                return self.cached_vor_results[cache_key]
            
            # Get predictions for all players at this position
            predictions = await self._get_position_predictions(position, season)
            
            if not predictions or len(predictions) == 0:
                error_msg = f"❌ CRITICAL: No predictions available for {position}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            # Sort players by projected points (descending)
            sorted_players = sorted(predictions, key=lambda x: x.get("prediction", 0), reverse=True)
            
            # Get replacement level
            replacement_baseline = self.vor_baselines.get(position, 24)  # Default to 24 if position not found
            
            # Calculate replacement level points
            if len(sorted_players) >= replacement_baseline:
                replacement_points = sorted_players[replacement_baseline - 1]["prediction"]
            else:
                # If we don't have enough players, use the lowest available
                replacement_points = sorted_players[-1]["prediction"] if sorted_players else 0
                logger.warning(f"Only {len(sorted_players)} players available for {position}, using lowest as replacement")
            
            # Calculate VOR for each player
            vor_results = []
            for i, player in enumerate(sorted_players):
                predicted_points = player.get("prediction", 0)
                vor_value = predicted_points - replacement_points
                
                player_vor = {
                    "player_id": player.get("player_id"),
                    "player_name": player.get("player_name", "Unknown"),
                    "team": player.get("team", "Unknown"),
                    "position": position,
                    "predicted_points": predicted_points,
                    "vor_value": vor_value,
                    "position_rank": i + 1,
                    "is_replacement_level": i == (replacement_baseline - 1),
                    "tier": self._calculate_tier(vor_value, position)
                }
                
                vor_results.append(player_vor)
            
            # Calculate summary statistics
            vor_values = [p["vor_value"] for p in vor_results]
            summary_stats = {
                "total_players": len(vor_results),
                "replacement_baseline": replacement_baseline,
                "replacement_points": replacement_points,
                "max_vor": max(vor_values) if vor_values else 0,
                "min_vor": min(vor_values) if vor_values else 0,
                "avg_vor": np.mean(vor_values) if vor_values else 0,
                "std_vor": np.std(vor_values) if vor_values else 0
            }
            
            result = {
                "position": position,
                "players": vor_results,
                "summary": summary_stats,
                "vor_calculated": True,
                "calculated_at": datetime.now().isoformat()
            }
            
            # Cache results
            self.cached_vor_results[cache_key] = result
            
            logger.info(f"✅ VOR calculated for {position}: {len(vor_results)} players, replacement level: {replacement_points:.2f}")
            return result
        
        except Exception as e:
            logger.error(f"VOR calculation failed for {position}: {e}")
            return {
                "position": position,
                "players": [],
                "vor_calculated": False,
                "error": str(e)
            }
    
    async def _get_position_predictions(self, position: str, season: Optional[int]) -> List[Dict[str, Any]]:
        """Get predictions for all players at a position by calling ML Models Service."""
        try:
            # Check if we have cached predictions
            cache_key = f"predictions_{position}_{season or 'current'}"
            if cache_key in self.cached_predictions:
                return self.cached_predictions[cache_key]
            
            logger.info(f"🔄 Getting predictions from ML Models service for {position}...")
            
            # Load 2024 player data for inference
            player_data = await self._load_current_player_data(position, season)
            
            if not player_data:
                error_msg = f"❌ CRITICAL: No current player data found for {position}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            # Call ML Models Service for batch predictions
            predictions = await self._call_ml_models_service(position, player_data)
            logger.info(f"✅ Got predictions from ML Models Service for {position}")
            
            if predictions:
                self.cached_predictions[cache_key] = predictions
                logger.info(f"✅ Loaded {len(predictions)} predictions for {position}")
                return predictions
            else:
                error_msg = f"❌ CRITICAL: No predictions generated for {position}"
                logger.error(error_msg)
                return []
        
        except Exception as e:
            # Only catch exceptions from player data loading, not from prediction generation
            if "current player data" in str(e):
                error_msg = f"❌ CRITICAL: Failed to get position predictions for {position}: {str(e)}"
                logger.error(error_msg)
                logger.error(f"Full error details: {e}", exc_info=True)
                raise
            else:
                # For other exceptions, return empty list
                logger.error(f"Unexpected error in prediction generation: {e}")
                return []
    
    async def _load_current_player_data(self, position: str, season: Optional[int]) -> List[Dict[str, Any]]:
        """Generate 2025 projection features for current players."""
        try:
            logger.info(f"🎯 Generating 2025 projection features for {position} players...")
            
            # Generate 2025 projections using feature engineering pipeline
            projection_data = await self._generate_2025_projections(position, season)
            
            if not projection_data or len(projection_data) == 0:
                error_msg = f"❌ CRITICAL: Failed to generate 2025 projections for {position}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"✅ Generated {len(projection_data)} 2025 projections for {position}")
            return projection_data
        
        except Exception as e:
            error_msg = f"❌ CRITICAL: Failed to load current player data for {position}: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Full error details: {e}", exc_info=True)
            raise

    async def _generate_2025_projections(self, position: str, season: Optional[int]) -> List[Dict[str, Any]]:
        """Load existing feature files for 2024 data (used for 2025 projections)."""
        try:
            logger.info(f"🔧 Loading existing 2024 features for {position} for projection purposes...")
            
            # Use existing feature files instead of importing feature engineering modules
            # This follows proper microservices architecture
            feature_file_path = Path("/data/processed/position_specific") / f"{position.lower()}_features_2024.parquet"
            
            # Check if the feature file exists
            if not feature_file_path.exists():
                raise Exception(f"Feature file not found: {feature_file_path}")
            
            logger.info(f"   Loading features from: {feature_file_path}")
            
            # Load the parquet file with 2024 features
            import pandas as pd
            projection_features_df = pd.read_parquet(feature_file_path)
            
            if projection_features_df.empty:
                raise Exception(f"Feature file is empty: {feature_file_path}")
            
            logger.info(f"   Loaded {len(projection_features_df)} player records with {len(projection_features_df.columns)} features")
            
            # The data is already position-specific from the filename, so no filtering needed
            position_data = projection_features_df
            
            logger.info(f"   Found {len(position_data)} {position} players in projection features")
            
            # Convert to the format expected by ML Models Service
            # Skip local feature extraction and let the ML service handle it
            player_data = []
            for _, row in position_data.iterrows():
                # Clean the features to ensure JSON compatibility
                features_dict = {}
                for col, value in row.items():
                    if pd.isna(value):
                        features_dict[col] = 0.0  # Replace NaN with 0
                    elif value == float('inf') or value == float('-inf'):
                        features_dict[col] = 0.0  # Replace infinity with 0
                    else:
                        try:
                            features_dict[col] = float(value)  # Ensure it's a valid float
                        except (ValueError, TypeError):
                            features_dict[col] = 0.0  # Default fallback
                
                player_record = {
                    "player_data": {
                        "player_id": row.get('player_id', f"player_{len(player_data)}"),
                        "player_name": row.get('player_name', f"{position}_Player_{len(player_data)}"),
                        "team": row.get('team', 'UNK'),
                        "position": position
                    },
                    "features": features_dict  # Send cleaned feature data to ML service
                }
                player_data.append(player_record)
            
            logger.info(f"✅ Generated 2025 projection data for {len(player_data)} {position} players")
            return player_data
            
        except Exception as e:
            logger.error(f"❌ Failed to load 2024 features for {position}: {e}")
            raise

    async def _call_ml_models_service(self, position: str, player_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Call ML Models Service for individual predictions (no batch endpoint available)."""
        try:
            import requests
            
            logger.info(f"🔄 Making {len(player_data)} individual prediction calls to ML Models Service for {position}...")
            predictions = []
            
            for player_record in player_data:
                # Call individual prediction endpoint for each player
                individual_request = {
                    "position": position,
                    "features": player_record["features"],
                    "player_data": player_record["player_data"]
                }
                
                response = requests.post(
                    f"{self.ml_models_service_url}/api/v1/models/predict",
                    json=individual_request,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("status") == "success":
                        # Extract prediction from individual response
                        prediction_data = result.get("data", {})
                        player_info = prediction_data.get("player_info", {})
                        
                        prediction = {
                            "player_id": player_info.get("player_id") or player_record["player_data"]["player_id"],
                            "player_name": player_info.get("player_name") or player_record["player_data"]["player_name"],
                            "team": player_info.get("team") or player_record["player_data"]["team"],
                            "position": position,
                            "prediction": prediction_data.get("predicted_fantasy_points", 0.0)
                        }
                        predictions.append(prediction)
                    else:
                        logger.warning(f"Individual prediction failed for player: {result}")
                        # Add a fallback prediction with 0 points
                        predictions.append({
                            "player_id": player_record["player_data"]["player_id"],
                            "player_name": player_record["player_data"]["player_name"],
                            "team": player_record["player_data"]["team"],
                            "position": position,
                            "prediction": 0.0
                        })
                else:
                    logger.warning(f"HTTP {response.status_code} for player {player_record['player_data']['player_name']}")
                    # Add a fallback prediction
                    predictions.append({
                        "player_id": player_record["player_data"]["player_id"],
                        "player_name": player_record["player_data"]["player_name"],
                        "team": player_record["player_data"]["team"],
                        "position": position,
                        "prediction": 0.0
                    })
            
            logger.info(f"✅ Got {len(predictions)} predictions from ML Models Service for {position}")
            return predictions
        
        except Exception as e:
            error_msg = f"❌ CRITICAL: Failed to get predictions from ML Models Service: {str(e)}"
            logger.error(error_msg)
            raise

    def _estimate_predictions_from_features(self, player_data: List[Dict[str, Any]], position: str) -> List[Dict[str, Any]]:
        """Estimate 2025 projections from player features when ML service is not available."""
        logger.warning(f"⚠️ ML Models Service unavailable, using projection estimates for {position}")
        predictions = []
        
        for data in player_data:
            player_info = data["player_data"]
            features = data["features"]
            
            # Use lagged features with regression adjustments for realistic 2025 projections
            estimated_points = 0.0
            
            # Look for previous season stats (L1 = lag 1 = previous year)
            prev_fantasy_points = features.get("fantasy_points_ppr_L1", features.get("fantasy_points_L1", 0))
            prev_games = features.get("games_L1", features.get("games", 16))
            
            # If we have previous season data, use it as base with regression to mean
            if prev_fantasy_points > 0 and prev_games > 0:
                # Calculate per-game average from previous season
                prev_fppg = prev_fantasy_points / max(prev_games, 1)
                
                # Apply position-specific regression factors for realistic projections
                regression_factors = {"QB": 0.85, "RB": 0.80, "WR": 0.82, "TE": 0.85}
                regression_factor = regression_factors.get(position, 0.80)
                
                # Get position baseline (typical starter performance)
                position_baselines = {"QB": 18.0, "RB": 12.0, "WR": 11.0, "TE": 9.0}
                baseline = position_baselines.get(position, 10.0)
                
                # Regress toward position baseline for realistic projections
                estimated_points = (prev_fppg * regression_factor) + (baseline * (1 - regression_factor))
                
                logger.debug(f"   {player_info.get('player_name', 'Unknown')}: {prev_fppg:.1f} → {estimated_points:.1f} FPPG")
            else:
                # No previous season data, use position baseline
                position_baselines = {"QB": 16.0, "RB": 10.0, "WR": 9.0, "TE": 7.0}
                estimated_points = position_baselines.get(position, 8.0)
            
            # Ensure reasonable bounds for projections (convert to per-game)
            estimated_points = max(3.0, min(estimated_points, 28.0))  # Realistic FPPG range
            
            prediction = {
                "player_id": player_info.get("player_id"),
                "player_name": player_info.get("player_name", "Unknown"),
                "team": player_info.get("team", "Unknown"),
                "position": position,
                "prediction": float(estimated_points)
            }
            predictions.append(prediction)
        
        logger.info(f"✅ Generated {len(predictions)} estimated predictions for {position}")
        return predictions

# _extract_ml_features function removed - now using ML service API directly

# Obsolete functions removed - now using direct ML service API calls
    
    def _generate_mock_predictions(self, position: str) -> List[Dict[str, Any]]:
        """Generate mock prediction data for testing."""
        # Position-specific point ranges
        point_ranges = {
            "QB": (8, 35),
            "RB": (3, 25), 
            "WR": (2, 22),
            "TE": (1, 18)
        }
        
        min_points, max_points = point_ranges.get(position, (5, 20))
        num_players = 60  # Generate 60 players per position
        
        predictions = []
        for i in range(num_players):
            # Create decreasing point values with some randomness
            base_points = max_points - (i * (max_points - min_points) / num_players)
            random_factor = np.random.normal(0, 1)  # Add some noise
            predicted_points = max(min_points, base_points + random_factor)
            
            prediction = {
                "player_id": f"{position.lower()}_mock_{i+1}",
                "player_name": f"{position} Player {i+1}",
                "team": f"TEAM{(i % 32) + 1}",  # 32 NFL teams
                "position": position,
                "prediction": round(predicted_points, 2)
            }
            predictions.append(prediction)
        
        logger.info(f"✅ Generated {len(predictions)} mock predictions for {position}")
        return predictions
    
    def _calculate_tier(self, vor_value: float, position: str) -> int:
        """Calculate tier based on VOR value and position."""
        # Position-specific tier thresholds
        tier_thresholds = {
            "QB": [15, 10, 5, 0, -5],      # Tier 1: >15, Tier 2: 10-15, etc.
            "RB": [12, 8, 4, 0, -4],       # RBs more valuable, higher thresholds
            "WR": [10, 6, 3, 0, -3],       # WRs have more depth
            "TE": [8, 5, 2, 0, -2]         # TEs have big drop-off
        }
        
        thresholds = tier_thresholds.get(position, [10, 6, 3, 0, -3])
        
        for tier, threshold in enumerate(thresholds, 1):
            if vor_value >= threshold:
                return tier
        
        return len(thresholds) + 1  # Lowest tier
    
    async def _get_configuration(self) -> Dict[str, Any]:
        """Get configuration from configuration service."""
        try:
            response = requests.get(f"{self.config_service_url}/api/v1/config/summary", timeout=10)
            if response.status_code == 200:
                config_data = response.json()
                return config_data.get("data", {})
            else:
                logger.warning(f"Could not get configuration: {response.status_code}")
                return {}
        except Exception as e:
            logger.warning(f"Configuration service unavailable: {e}")
            return {}
    
    async def get_status(self) -> Dict[str, Any]:
        """Get VOR calculator status."""
        return {
            "baselines_loaded": len(self.vor_baselines) > 0,
            "cached_predictions": len(self.cached_predictions),
            "cached_vor_results": len(self.cached_vor_results),
            "supported_positions": list(self.vor_baselines.keys())
        }
    
    async def get_detailed_status(self) -> Dict[str, Any]:
        """Get detailed VOR calculator status."""
        return {
            "vor_baselines": self.vor_baselines,
            "roster_requirements": self.roster_requirements,
            "cached_predictions": {
                position: len(data) for position, data in self.cached_predictions.items()
            },
            "cached_vor_results": {
                position: len(data.get("players", [])) for position, data in self.cached_vor_results.items()
            },
            "status": "ready",
            "last_updated": datetime.now().isoformat()
        }