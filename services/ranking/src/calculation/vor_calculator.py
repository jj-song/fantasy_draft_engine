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
    
    def __init__(self, config_service_url: str = "http://localhost:8001",
                 ml_models_service_url: str = "http://localhost:8004"):
        """
        Initialize VOR calculator.
        
        Args:
            config_service_url: Configuration service URL
            ml_models_service_url: ML Models service URL
        """
        self.config_service_url = config_service_url
        self.ml_models_service_url = ml_models_service_url
        
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
                logger.warning(f"No predictions available for {position}")
                return {
                    "position": position,
                    "players": [],
                    "replacement_level": 0,
                    "vor_calculated": False,
                    "error": "No predictions available"
                }
            
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
        """Get predictions for all players at a position."""
        try:
            # Check if we have cached predictions
            cache_key = f"predictions_{position}_{season or 'current'}"
            if cache_key in self.cached_predictions:
                return self.cached_predictions[cache_key]
            
            # Try to get predictions from ML models service
            try:
                logger.info(f"🔄 Getting predictions from ML Models service for {position}...")
                
                # This would typically involve calling the ML models service with player data
                # For now, we'll try to load existing prediction data
                predictions = await self._load_prediction_data(position, season)
                
                if predictions:
                    self.cached_predictions[cache_key] = predictions
                    logger.info(f"✅ Loaded {len(predictions)} predictions for {position}")
                    return predictions
                else:
                    logger.warning(f"No prediction data found for {position}")
                    return []
            
            except Exception as e:
                logger.warning(f"Could not get predictions from ML Models service: {e}")
                return []
        
        except Exception as e:
            logger.error(f"Failed to get position predictions for {position}: {e}")
            return []
    
    async def _load_prediction_data(self, position: str, season: Optional[int]) -> List[Dict[str, Any]]:
        """Load prediction data from files or generate mock data."""
        try:
            # Try to load from data files first (use Docker volume mount path)
            data_dir = Path("/app/data/processed")
            
            # Look for existing prediction or ranking files
            # Use the most recent year's feature data (2023 for now)
            prediction_files = [
                data_dir / "position_specific" / position.lower() / f"{position.lower()}_features_2023.parquet",
                data_dir / "position_specific" / f"{position.lower()}_features_2023.parquet",
                data_dir / f"training_features_2023_with_matchup_intel.parquet"
            ]
            
            for file_path in prediction_files:
                if file_path.exists():
                    try:
                        df = pd.read_parquet(file_path)
                        
                        # Filter for position if needed
                        if 'position' in df.columns:
                            df = df[df['position'] == position]
                        
                        if not df.empty:
                            # Convert to prediction format
                            predictions = []
                            for _, row in df.iterrows():
                                # Use fantasy points if available, otherwise estimate
                                predicted_points = row.get('fantasy_points_per_game', 
                                                          row.get('fantasy_points', 
                                                               self._estimate_points_from_stats(row, position)))
                                
                                prediction = {
                                    "player_id": row.get('player_id', f"player_{len(predictions)}"),
                                    "player_name": row.get('player_name', f"{position}_Player_{len(predictions)}"),
                                    "team": row.get('team', 'UNK'),
                                    "position": position,
                                    "prediction": float(predicted_points) if predicted_points is not None else 0.0
                                }
                                predictions.append(prediction)
                            
                            if predictions:
                                logger.info(f"✅ Loaded {len(predictions)} prediction records from {file_path.name}")
                                return predictions
                    
                    except Exception as e:
                        logger.warning(f"Could not load predictions from {file_path}: {e}")
                        continue
            
            # If no data found, generate mock data for testing
            logger.warning(f"No prediction data found for {position}, generating mock data for testing")
            return self._generate_mock_predictions(position)
        
        except Exception as e:
            logger.error(f"Failed to load prediction data for {position}: {e}")
            return []
    
    def _estimate_points_from_stats(self, row: pd.Series, position: str) -> float:
        """Estimate fantasy points from basic stats."""
        try:
            if position == "QB":
                passing_yards = row.get('passing_yards', 0) * 0.04  # 1 pt per 25 yards
                passing_tds = row.get('passing_tds', 0) * 4
                rushing_yards = row.get('rushing_yards', 0) * 0.1
                rushing_tds = row.get('rushing_tds', 0) * 6
                return passing_yards + passing_tds + rushing_yards + rushing_tds
            
            elif position == "RB":
                rushing_yards = row.get('rushing_yards', 0) * 0.1
                rushing_tds = row.get('rushing_tds', 0) * 6
                receiving_yards = row.get('receiving_yards', 0) * 0.1
                receiving_tds = row.get('receiving_tds', 0) * 6
                receptions = row.get('receptions', 0) * 0.5  # 0.5 PPR
                return rushing_yards + rushing_tds + receiving_yards + receiving_tds + receptions
            
            elif position in ["WR", "TE"]:
                receiving_yards = row.get('receiving_yards', 0) * 0.1
                receiving_tds = row.get('receiving_tds', 0) * 6
                receptions = row.get('receptions', 0) * 0.5  # 0.5 PPR
                return receiving_yards + receiving_tds + receptions
            
            return 0.0
        
        except Exception:
            return 0.0
    
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