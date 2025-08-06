"""
Scoring Engine - Generate overall fantasy football rankings.

This module provides ranking generation functionality including:
- Overall ranking compilation  
- Tier assignment
- Manual overrides integration
- Multiple sorting strategies
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)

class ScoringEngine:
    """
    Generate comprehensive fantasy football rankings and apply scoring logic.
    
    Combines VOR calculations, tier assignments, and manual overrides to create
    final draft rankings.
    """
    
    def __init__(self):
        """Initialize scoring engine."""
        services_root = Path(__file__).parent.parent.parent.parent.parent
        self.overrides_file = services_root / "overrides.yaml"
        self.manual_overrides = {}
        
        # Tier break thresholds by position
        self.tier_thresholds = {
            "QB": [15, 10, 5, 0, -5],
            "RB": [12, 8, 4, 0, -4], 
            "WR": [10, 6, 3, 0, -3],
            "TE": [8, 5, 2, 0, -2]
        }
        
        # Position scarcity adjustments
        self.scarcity_multipliers = {
            "QB": 0.8,  # QBs less scarce (can stream)
            "RB": 1.2,  # RBs more scarce
            "WR": 1.0,  # WRs baseline
            "TE": 1.1   # TEs somewhat scarce after top tier
        }
        
        logger.info("🎯 Scoring Engine initialized")
    
    async def generate_overall_rankings(self, positions: List[str], season: Optional[int] = None,
                                      tier_assignments: bool = True, include_overrides: bool = True,
                                      sort_by: str = "vor") -> Dict[str, Any]:
        """
        Generate complete overall rankings.
        
        Args:
            positions: Positions to include in rankings
            season: Season for rankings (defaults to current)
            tier_assignments: Whether to assign tiers
            include_overrides: Whether to apply manual overrides
            sort_by: Sorting strategy ("vor", "projected_points", "adp")
            
        Returns:
            Dictionary containing complete rankings
        """
        try:
            logger.info(f"🏆 Generating overall rankings for {positions}...")
            
            # Load manual overrides if requested
            if include_overrides:
                await self._load_manual_overrides()
            
            # Get player data for all positions
            all_players = []
            for position in positions:
                position_players = await self._get_position_players(position, season)
                all_players.extend(position_players)
            
            if not all_players:
                logger.error("No player data available for ranking generation")
                raise Exception("No player data available")
            
            # Apply manual overrides
            if include_overrides and self.manual_overrides:
                all_players = self._apply_manual_overrides(all_players)
            
            # Calculate adjusted scores based on scarcity
            all_players = self._apply_scarcity_adjustments(all_players)
            
            # Sort players by chosen metric
            all_players = self._sort_players(all_players, sort_by)
            
            # Assign overall ranks
            for i, player in enumerate(all_players):
                player["overall_rank"] = i + 1
            
            # Assign tiers if requested
            if tier_assignments:
                all_players = await self._assign_cross_position_tiers(all_players)
            
            # Generate summary statistics
            summary = self._generate_ranking_summary(all_players, positions)
            
            result = {
                "success": True,
                "rankings": all_players,
                "summary": summary,
                "metadata": {
                    "positions": positions,
                    "season": season,
                    "sort_by": sort_by,
                    "tier_assignments": tier_assignments,
                    "include_overrides": include_overrides,
                    "generated_at": datetime.now().isoformat()
                }
            }
            
            logger.info(f"✅ Overall rankings generated: {len(all_players)} players")
            return result
        
        except Exception as e:
            logger.error(f"Failed to generate overall rankings: {e}")
            raise
    
    async def _get_position_players(self, position: str, season: Optional[int]) -> List[Dict[str, Any]]:
        """Get player data for a specific position."""
        try:
            logger.info(f"📊 Loading player data for {position}...")
            
            # Import VOR calculator and get real player data
            from ..calculation.vor_calculator import VORCalculator
            
            # Use Docker service URLs for inter-service communication
            vor_calculator = VORCalculator(
                config_service_url="http://configuration:8000",
                ml_models_service_url="http://ml-models:8000"
            )
            
            # Get VOR calculations for this position (real player data)
            vor_results = await vor_calculator.calculate_position_vor(position, season)
            
            if not vor_results.get("vor_calculated", False) or not vor_results.get("players"):
                logger.warning(f"No VOR data available for {position}, falling back to sample data")
                players = await self._generate_position_sample_data(position)
            else:
                # Use real player data from VOR calculations
                players = vor_results["players"]
                
                # Add missing fields that the ranking system expects
                for player in players:
                    player.setdefault("age", 25)  # Default age
                    player.setdefault("bye_week", 7)  # Default bye week
                    player.setdefault("adp", -1)  # Will be calculated later
                    player.setdefault("tier", None)  # Will be assigned later
                    player.setdefault("adjusted_score", None)  # Will be calculated later
            
            logger.info(f"✅ Loaded {len(players)} players for {position}")
            return players
        
        except Exception as e:
            logger.error(f"Failed to get players for {position}: {e}")
            logger.warning("Falling back to sample data due to error")
            # Fallback to sample data if real data fails
            return await self._generate_position_sample_data(position)
    
    async def _generate_position_sample_data(self, position: str) -> List[Dict[str, Any]]:
        """Generate sample player data for a position."""
        # Position-specific configurations
        position_configs = {
            "QB": {"count": 24, "points_range": (8, 35), "replacement_level": 12},
            "RB": {"count": 60, "points_range": (3, 25), "replacement_level": 8},
            "WR": {"count": 72, "points_range": (2, 22), "replacement_level": 6},
            "TE": {"count": 20, "points_range": (1, 18), "replacement_level": 4}
        }
        
        config = position_configs.get(position, {"count": 30, "points_range": (5, 20), "replacement_level": 8})
        
        players = []
        min_pts, max_pts = config["points_range"]
        replacement_level = config["replacement_level"]
        
        for i in range(config["count"]):
            # Create realistic point distribution
            base_points = max_pts - (i * (max_pts - min_pts) / config["count"])
            noise = np.random.normal(0, 1.0)  # Add some randomness
            predicted_points = max(min_pts, base_points + noise)
            
            # Calculate VOR
            vor_value = predicted_points - replacement_level
            
            # Generate player info
            player = {
                "player_id": f"{position.lower()}_{i+1:03d}",
                "player_name": f"{position} Player {i+1}",
                "team": f"TEAM{(i % 32) + 1}",
                "position": position,
                "predicted_points": round(predicted_points, 1),
                "vor_value": round(vor_value, 1),
                "position_rank": i + 1,
                "age": 20 + (i % 15),  # Ages 20-34
                "bye_week": (i % 14) + 4,  # Weeks 4-17
                "adp": None,  # Will be calculated
                "tier": None,  # Will be assigned
                "adjusted_score": None  # Will be calculated
            }
            
            players.append(player)
        
        return players
    
    async def _load_manual_overrides(self) -> bool:
        """Load manual overrides from YAML file."""
        try:
            if not self.overrides_file.exists():
                logger.info("No manual overrides file found")
                return False
            
            with open(self.overrides_file, 'r') as f:
                overrides_data = yaml.safe_load(f)
            
            self.manual_overrides = overrides_data.get("player_overrides", {})
            
            if self.manual_overrides:
                logger.info(f"✅ Loaded {len(self.manual_overrides)} manual overrides")
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to load manual overrides: {e}")
            return False
    
    def _apply_manual_overrides(self, players: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply manual overrides to player data."""
        try:
            overrides_applied = 0
            
            for player in players:
                player_key = player.get("player_name", "").lower().replace(" ", "_")
                
                if player_key in self.manual_overrides:
                    override_data = self.manual_overrides[player_key]
                    
                    # Apply point adjustments
                    if "points_adjustment" in override_data:
                        adjustment = override_data["points_adjustment"]
                        player["predicted_points"] += adjustment
                        player["vor_value"] += adjustment  # VOR adjusts with points
                        logger.info(f"Applied {adjustment:+.1f} point adjustment to {player['player_name']}")
                    
                    # Apply rank adjustments
                    if "rank_adjustment" in override_data:
                        player["manual_rank_adjustment"] = override_data["rank_adjustment"]
                    
                    # Apply notes
                    if "notes" in override_data:
                        player["override_notes"] = override_data["notes"]
                    
                    overrides_applied += 1
            
            if overrides_applied > 0:
                logger.info(f"✅ Applied {overrides_applied} manual overrides")
            
            return players
        
        except Exception as e:
            logger.error(f"Failed to apply manual overrides: {e}")
            return players
    
    def _apply_scarcity_adjustments(self, players: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply position scarcity adjustments to player values."""
        try:
            for player in players:
                position = player["position"]
                multiplier = self.scarcity_multipliers.get(position, 1.0)
                
                # Calculate adjusted score (VOR * scarcity multiplier)
                base_score = player["vor_value"]
                adjusted_score = base_score * multiplier
                
                player["adjusted_score"] = round(adjusted_score, 2)
                player["scarcity_multiplier"] = multiplier
            
            logger.info("✅ Applied position scarcity adjustments")
            return players
        
        except Exception as e:
            logger.error(f"Failed to apply scarcity adjustments: {e}")
            raise
    
    def _sort_players(self, players: List[Dict[str, Any]], sort_by: str) -> List[Dict[str, Any]]:
        """Sort players by specified metric."""
        try:
            sort_key_map = {
                "vor": "vor_value",
                "adjusted_vor": "adjusted_score", 
                "projected_points": "predicted_points",
                "adp": "adp"
            }
            
            sort_key = sort_key_map.get(sort_by, "vor_value")
            
            # Handle ADP sorting (ascending, with None values last)
            if sort_by == "adp":
                # First, assign mock ADP values for sorting
                for i, player in enumerate(players):
                    if player.get("adp") is None:
                        player["adp"] = i + 1  # Use current order as mock ADP
                
                players.sort(key=lambda x: x.get("adp", 999))
            else:
                # All other metrics sort descending (higher is better)
                players.sort(key=lambda x: x.get(sort_key, 0), reverse=True)
            
            logger.info(f"✅ Players sorted by {sort_by}")
            return players
        
        except Exception as e:
            logger.error(f"Failed to sort players: {e}")
            raise
    
    async def _assign_cross_position_tiers(self, players: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Assign tiers across all positions based on overall value."""
        try:
            # Sort by adjusted score for tier assignment
            sorted_players = sorted(players, key=lambda x: x.get("adjusted_score", 0), reverse=True)
            
            # Calculate tier breaks based on value gaps
            adjusted_scores = [p["adjusted_score"] for p in sorted_players]
            tier_breaks = self._find_tier_breaks(adjusted_scores)
            
            # Assign tiers
            current_tier = 1
            tier_break_index = 0
            
            for i, player in enumerate(sorted_players):
                # Check if we've hit a tier break
                if tier_break_index < len(tier_breaks) and i >= tier_breaks[tier_break_index]:
                    current_tier += 1
                    tier_break_index += 1
                
                player["overall_tier"] = current_tier
            
            # Also assign position-specific tiers
            for position in ["QB", "RB", "WR", "TE"]:
                position_players = [p for p in players if p["position"] == position]
                if position_players:
                    self._assign_position_tiers(position_players, position)
            
            logger.info(f"✅ Assigned tiers across {current_tier} overall tiers")
            return players
        
        except Exception as e:
            logger.error(f"Failed to assign tiers: {e}")
            raise
    
    def _find_tier_breaks(self, values: List[float]) -> List[int]:
        """Find natural tier breaks in value list."""
        if len(values) <= 1:
            return []
        
        # Calculate gaps between consecutive values
        gaps = [values[i] - values[i+1] for i in range(len(values)-1)]
        
        # Find significant gaps (above mean + std)
        mean_gap = np.mean(gaps)
        std_gap = np.std(gaps)
        threshold = mean_gap + (1.5 * std_gap)  # 1.5 std above mean
        
        tier_breaks = []
        for i, gap in enumerate(gaps):
            if gap > threshold:
                tier_breaks.append(i + 1)  # Break after position i
        
        # Limit to reasonable number of tiers (max 8)
        return tier_breaks[:7]  # Max 8 tiers
    
    def _assign_position_tiers(self, players: List[Dict[str, Any]], position: str):
        """Assign position-specific tiers."""
        # Sort by VOR for position tiers
        players.sort(key=lambda x: x["vor_value"], reverse=True)
        
        thresholds = self.tier_thresholds.get(position, [10, 6, 3, 0, -3])
        
        for player in players:
            vor_value = player["vor_value"]
            tier = len(thresholds) + 1  # Default to lowest tier
            
            for t, threshold in enumerate(thresholds, 1):
                if vor_value >= threshold:
                    tier = t
                    break
            
            player[f"{position.lower()}_tier"] = tier
    
    def _generate_ranking_summary(self, players: List[Dict[str, Any]], positions: List[str]) -> Dict[str, Any]:
        """Generate summary statistics for rankings."""
        try:
            summary = {
                "total_players": len(players),
                "positions": positions,
                "by_position": {},
                "by_tier": {},
                "top_players": players[:10] if len(players) >= 10 else players,
                "value_ranges": {}
            }
            
            # Position breakdown
            for position in positions:
                position_players = [p for p in players if p["position"] == position]
                if position_players:
                    summary["by_position"][position] = {
                        "count": len(position_players),
                        "avg_points": np.mean([p["predicted_points"] for p in position_players]),
                        "avg_vor": np.mean([p["vor_value"] for p in position_players])
                    }
            
            # Tier breakdown (if tiers assigned)
            if players and "overall_tier" in players[0]:
                tier_counts = {}
                for player in players:
                    tier = player.get("overall_tier", 1)
                    tier_counts[tier] = tier_counts.get(tier, 0) + 1
                
                summary["by_tier"] = tier_counts
            
            # Value ranges
            all_points = [p["predicted_points"] for p in players]
            all_vor = [p["vor_value"] for p in players]
            
            summary["value_ranges"] = {
                "points": {"min": min(all_points), "max": max(all_points), "avg": np.mean(all_points)},
                "vor": {"min": min(all_vor), "max": max(all_vor), "avg": np.mean(all_vor)}
            }
            
            return summary
        
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            raise
    
    async def get_scoring_config(self) -> Dict[str, Any]:
        """Get current scoring engine configuration."""
        return {
            "tier_thresholds": self.tier_thresholds,
            "scarcity_multipliers": self.scarcity_multipliers,
            "manual_overrides_loaded": len(self.manual_overrides),
            "overrides_file": str(self.overrides_file),
            "supported_sort_methods": ["vor", "adjusted_vor", "projected_points", "adp"]
        }