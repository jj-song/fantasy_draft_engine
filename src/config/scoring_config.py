"""
Scoring system configuration for the Fantasy Draft Engine.

This module contains all configuration related to fantasy point calculations,
scoring systems, and baseline projections for different player types.
"""

from typing import Dict, Any, Union, List
from .base_config import BaseConfig


class ScoringConfig(BaseConfig):
    """
    Configuration for fantasy football scoring systems.
    
    This class manages point values for different statistical categories,
    baseline projections, and scoring system variations.
    """
    
    def _initialize(self) -> None:
        """Initialize scoring configuration values."""
        
        # Standard 0.5 PPR scoring system
        self.fantasy_points = {
            'passing_yards': 0.04,      # 1 point per 25 yards
            'passing_tds': 4,           # 4 points per passing TD
            'interceptions': -2,        # -2 points per interception
            'rushing_yards': 0.1,       # 1 point per 10 yards
            'rushing_tds': 6,           # 6 points per rushing TD
            'receptions': 0.5,          # Half-point PPR
            'receiving_yards': 0.1,     # 1 point per 10 yards
            'receiving_tds': 6,         # 6 points per receiving TD
            'fumbles_lost': -2,         # -2 points per fumble lost
            'two_point_conversions': 2, # 2 points per 2-point conversion
        }
        
        # Kicker scoring
        self.kicker_scoring = {
            'extra_points': 1,          # 1 point per XP
            'field_goals_0_19': 3,      # 3 points for FG 0-19 yards
            'field_goals_20_29': 3,     # 3 points for FG 20-29 yards
            'field_goals_30_39': 3,     # 3 points for FG 30-39 yards
            'field_goals_40_49': 4,     # 4 points for FG 40-49 yards
            'field_goals_50_plus': 5,   # 5 points for FG 50+ yards
            'field_goal_missed': 0,     # 0 points for missed FG (some leagues -1)
        }
        
        # Defense/Special Teams scoring
        self.dst_scoring = {
            'points_allowed_0': 10,     # 10 points for 0 points allowed
            'points_allowed_1_6': 7,    # 7 points for 1-6 points allowed
            'points_allowed_7_13': 4,   # 4 points for 7-13 points allowed
            'points_allowed_14_20': 1,  # 1 point for 14-20 points allowed
            'points_allowed_21_27': 0,  # 0 points for 21-27 points allowed
            'points_allowed_28_34': -1, # -1 point for 28-34 points allowed
            'points_allowed_35_plus': -4, # -4 points for 35+ points allowed
            'yards_allowed_under_100': 10, # Bonus for under 100 yards allowed
            'yards_allowed_100_199': 5,    # 5 points for 100-199 yards
            'yards_allowed_200_299': 2,    # 2 points for 200-299 yards
            'yards_allowed_300_399': 0,    # 0 points for 300-399 yards
            'yards_allowed_400_449': -1,   # -1 point for 400-449 yards
            'yards_allowed_450_499': -3,   # -3 points for 450-499 yards
            'yards_allowed_500_plus': -5,  # -5 points for 500+ yards
            'sacks': 1,                    # 1 point per sack
            'interceptions': 2,            # 2 points per interception
            'fumble_recoveries': 2,        # 2 points per fumble recovery
            'safeties': 2,                 # 2 points per safety
            'blocked_punts': 2,            # 2 points per blocked punt
            'blocked_field_goals': 2,      # 2 points per blocked FG
            'touchdowns': 6,               # 6 points per defensive/ST TD
        }
        
        # Alternative scoring systems
        self.scoring_variations = {
            'standard': {  # Standard (no PPR)
                **self.fantasy_points,
                'receptions': 0  # Override PPR to 0
            },
            'half_ppr': self.fantasy_points.copy(),  # Already 0.5 PPR
            'full_ppr': {  # Full PPR
                **self.fantasy_points,
                'receptions': 1.0  # Override to full PPR
            },
            'ppr_plus': {  # PPR with bonuses
                **self.fantasy_points,
                'receptions': 1.0,
                'passing_yards': 0.05,  # Slight passing bonus
                'long_td_bonus': 2      # Bonus for long TDs
            }
        }
        
        # Default scoring system to use
        self.default_scoring_system = 'half_ppr'
        
        # Mapping of scoring system names to column names in data
        self.fantasy_points_columns = {
            'standard': 'fantasy_points',      # Uses calculated points based on settings
            'half_ppr': 'fantasy_points',      # Uses calculated points
            'full_ppr': 'fantasy_points_ppr',  # Uses nfl_data_py PPR column
            'ppr': 'fantasy_points_ppr'        # Alias for full PPR
        }
        
        # Target variable name for model training
        self.target_variable = 'next_season_fppg'
        
        # Rookie baseline projections by draft round
        self.rookie_baseline_fppg = {
            'QB': {
                1: 15.0,  # 1st round
                2: 12.0,  # 2nd round
                3: 10.0,  # 3rd round
                4: 8.0,   # 4th round
                5: 7.0,   # 5th round
                6: 6.0,   # 6th round
                7: 5.0,   # 7th round
                'UDFA': 3.0,  # Undrafted free agent
            },
            'RB': {
                1: 12.0,  # 1st round
                2: 9.0,   # 2nd round
                3: 7.0,   # 3rd round
                4: 5.0,   # 4th round
                5: 4.0,   # 5th round
                6: 3.5,   # 6th round
                7: 3.0,   # 7th round
                'UDFA': 2.0,  # Undrafted free agent
            },
            'WR': {
                1: 11.0,  # 1st round
                2: 8.0,   # 2nd round
                3: 6.0,   # 3rd round
                4: 4.5,   # 4th round
                5: 3.5,   # 5th round
                6: 3.0,   # 6th round
                7: 2.5,   # 7th round
                'UDFA': 1.5,  # Undrafted free agent
            },
            'TE': {
                1: 9.0,   # 1st round
                2: 7.0,   # 2nd round
                3: 5.0,   # 3rd round
                4: 4.0,   # 4th round
                5: 3.0,   # 5th round
                6: 2.0,   # 6th round
                7: 1.5,   # 7th round
                'UDFA': 1.0,  # Undrafted free agent
            },
        }
        
        # Baseline FPPG for players with minimal recent NFL data
        self.minimal_data_baseline_fppg = {
            'QB': 5.0,
            'RB': 3.0,
            'WR': 2.5,
            'TE': 1.5,
            'K': 8.0,    # Kickers are more consistent
            'DST': 6.0,  # Defenses have moderate baseline
        }
        
        # Positional scoring adjustments for different league types
        self.league_type_adjustments = {
            'superflex': {
                'QB': 1.3,  # QBs more valuable in superflex
                'RB': 1.0,
                'WR': 1.0,
                'TE': 1.0
            },
            'dynasty': {
                'QB': 1.1,  # Slight QB premium for longevity
                'RB': 0.9,  # RBs depreciate faster
                'WR': 1.1,  # WRs have longer careers
                'TE': 1.05  # TEs develop slower but last longer
            },
            'best_ball': {
                'QB': 1.0,
                'RB': 1.1,  # RB depth more valuable
                'WR': 1.1,  # WR depth more valuable
                'TE': 0.95  # TE streaming less viable
            }
        }
        
        # Bonus scoring thresholds
        self.bonus_thresholds = {
            'passing_yards': {300: 3, 400: 6},    # Bonus points for passing yard milestones
            'rushing_yards': {100: 3, 200: 6},    # Bonus points for rushing yard milestones
            'receiving_yards': {100: 3, 200: 6},  # Bonus points for receiving yard milestones
            'long_td': {40: 2, 50: 4},            # Bonus for long TDs
        }
        
        # Environment-specific overrides
        if self.environment == 'test':
            self._apply_test_overrides()
    
    def _apply_test_overrides(self) -> None:
        """Apply test-specific configuration overrides."""
        # Simplified scoring for tests
        self.fantasy_points = {
            'passing_yards': 0.04,
            'passing_tds': 4,
            'rushing_yards': 0.1,
            'rushing_tds': 6,
            'receptions': 0.5,
            'receiving_yards': 0.1,
            'receiving_tds': 6
        }
    
    def _validate(self) -> None:
        """Validate scoring configuration values."""
        
        # Validate required fields
        required_fields = [
            'fantasy_points', 'default_scoring_system', 'target_variable'
        ]
        self.validate_required_fields(required_fields)
        
        # Validate types
        type_mapping = {
            'fantasy_points': dict,
            'kicker_scoring': dict,
            'dst_scoring': dict,
            'scoring_variations': dict,
            'rookie_baseline_fppg': dict,
            'minimal_data_baseline_fppg': dict,
            'default_scoring_system': str,
            'target_variable': str
        }
        self.validate_types(type_mapping)
        
        # Validate scoring values are reasonable
        self._validate_scoring_values()
        self._validate_baseline_projections()
    
    def _validate_scoring_values(self) -> None:
        """Validate that scoring values are reasonable."""
        # Basic sanity checks for scoring values
        if self.fantasy_points['passing_tds'] <= 0:
            raise ValueError("Passing TDs must have positive points")
        
        if self.fantasy_points['rushing_tds'] <= 0:
            raise ValueError("Rushing TDs must have positive points")
        
        if self.fantasy_points['receiving_tds'] <= 0:
            raise ValueError("Receiving TDs must have positive points")
        
        if self.fantasy_points['interceptions'] >= 0:
            raise ValueError("Interceptions should have negative points")
        
        if self.fantasy_points['fumbles_lost'] >= 0:
            raise ValueError("Fumbles lost should have negative points")
        
        # Check PPR value is reasonable
        ppr_value = self.fantasy_points.get('receptions', 0)
        if ppr_value < 0 or ppr_value > 2:
            raise ValueError(f"PPR value ({ppr_value}) should be between 0 and 2")
    
    def _validate_baseline_projections(self) -> None:
        """Validate baseline projection values."""
        positions = ['QB', 'RB', 'WR', 'TE']
        
        for pos in positions:
            if pos not in self.rookie_baseline_fppg:
                raise ValueError(f"Missing rookie baseline for {pos}")
            
            if pos not in self.minimal_data_baseline_fppg:
                raise ValueError(f"Missing minimal data baseline for {pos}")
            
            # Check that 1st round rookies have higher projections than UDFAs
            pos_rookies = self.rookie_baseline_fppg[pos]
            if pos_rookies.get(1, 0) <= pos_rookies.get('UDFA', 0):
                raise ValueError(f"1st round {pos} baseline should be higher than UDFA baseline")
    
    def get_scoring_system(self, system_name: str = None) -> Dict[str, float]:
        """
        Get scoring values for a specific system.
        
        Args:
            system_name: Name of scoring system (defaults to default_scoring_system)
            
        Returns:
            Dictionary of scoring values
        """
        if system_name is None:
            system_name = self.default_scoring_system
        
        if system_name in self.scoring_variations:
            return self.scoring_variations[system_name].copy()
        else:
            raise ValueError(f"Unknown scoring system: {system_name}")
    
    def calculate_fantasy_points(self, stats: Dict[str, Union[int, float]], 
                                scoring_system: str = None) -> float:
        """
        Calculate fantasy points based on player statistics.
        
        Args:
            stats: Dictionary of player statistics
            scoring_system: Scoring system to use (defaults to default)
            
        Returns:
            Total fantasy points
        """
        scoring = self.get_scoring_system(scoring_system)
        points = 0.0
        
        for stat, value in stats.items():
            if stat in scoring and value is not None:
                points += float(value) * scoring[stat]
        
        return round(points, 2)
    
    def get_rookie_baseline(self, position: str, draft_round: Union[int, str]) -> float:
        """
        Get baseline projection for a rookie player.
        
        Args:
            position: Player position
            draft_round: Draft round (1-7) or 'UDFA'
            
        Returns:
            Baseline fantasy points per game
        """
        position = position.upper()
        
        if position not in self.rookie_baseline_fppg:
            return self.minimal_data_baseline_fppg.get(position, 0.0)
        
        pos_baselines = self.rookie_baseline_fppg[position]
        
        if draft_round in pos_baselines:
            return pos_baselines[draft_round]
        elif isinstance(draft_round, int) and draft_round > 7:
            return pos_baselines.get('UDFA', 0.0)
        else:
            return self.minimal_data_baseline_fppg.get(position, 0.0)
    
    def get_minimal_data_baseline(self, position: str) -> float:
        """
        Get baseline projection for players with minimal data.
        
        Args:
            position: Player position
            
        Returns:
            Baseline fantasy points per game
        """
        return self.minimal_data_baseline_fppg.get(position.upper(), 0.0)
    
    def get_position_adjustment(self, position: str, league_type: str = 'standard') -> float:
        """
        Get positional adjustment multiplier for different league types.
        
        Args:
            position: Player position
            league_type: Type of league ('standard', 'superflex', 'dynasty', 'best_ball')
            
        Returns:
            Adjustment multiplier
        """
        if league_type in self.league_type_adjustments:
            return self.league_type_adjustments[league_type].get(position.upper(), 1.0)
        else:
            return 1.0
    
    def get_target_column(self, scoring_system: str = None) -> str:
        """
        Get the column name for the target variable based on scoring system.
        
        Args:
            scoring_system: Scoring system name
            
        Returns:
            Column name for fantasy points
        """
        if scoring_system is None:
            scoring_system = self.default_scoring_system
        
        return self.fantasy_points_columns.get(scoring_system, 'fantasy_points')
    
    def get_bonus_points(self, stat_type: str, value: float) -> float:
        """
        Calculate bonus points for statistical milestones.
        
        Args:
            stat_type: Type of statistic ('passing_yards', 'rushing_yards', etc.)
            value: Statistical value achieved
            
        Returns:
            Bonus points earned
        """
        if stat_type not in self.bonus_thresholds:
            return 0.0
        
        bonus_points = 0.0
        thresholds = self.bonus_thresholds[stat_type]
        
        for threshold, points in sorted(thresholds.items()):
            if value >= threshold:
                bonus_points = points
        
        return bonus_points
    
    def get_available_scoring_systems(self) -> List[str]:
        """Get list of available scoring systems."""
        return list(self.scoring_variations.keys())
    
    def is_ppr_league(self, scoring_system: str = None) -> bool:
        """
        Check if the league uses PPR scoring.
        
        Args:
            scoring_system: Scoring system to check
            
        Returns:
            True if PPR scoring is used
        """
        scoring = self.get_scoring_system(scoring_system)
        return scoring.get('receptions', 0) > 0