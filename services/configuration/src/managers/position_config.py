"""
Position-specific configuration for the Fantasy Draft Engine.

This module contains all configuration related to position-specific settings,
thresholds, and adjustments for fantasy football analysis.
"""

from typing import Dict, Any, List, Union
from .base_config import BaseConfig


class PositionConfig(BaseConfig):
    """
    Configuration for position-specific settings and thresholds.
    
    This class manages position-specific feature thresholds, statistical
    expectations, and position-specific adjustments for analysis.
    """
    
    def _initialize(self) -> None:
        """Initialize position configuration values."""
        
        # Basic position information
        self.positions = ['QB', 'RB', 'WR', 'TE', 'K', 'DST']
        self.core_positions = ['QB', 'RB', 'WR', 'TE']  # Positions with full feature engineering
        self.skill_positions = ['QB', 'RB', 'WR', 'TE']  # Offensive skill positions
        
        # Position priorities for draft analysis
        self.position_priorities = {
            'RB': 1,   # Highest priority due to scarcity
            'TE': 2,   # High priority for elite tier
            'WR': 3,   # Moderate priority 
            'QB': 4,   # Lower priority due to depth
            'K': 5,    # Low priority
            'DST': 6   # Lowest priority
        }
        
        # Statistical thresholds for meaningful production by position
        self.meaningful_production_thresholds = {
            'QB': {
                'min_attempts': 100,        # Minimum pass attempts for relevance
                'min_games': 6,             # Minimum games for sample size
                'min_passing_yards': 1000,  # Minimum passing yards
                'starter_attempts': 250     # Attempts threshold for likely starter
            },
            'RB': {
                'min_carries': 50,          # Minimum carries for relevance
                'min_games': 4,             # Minimum games for sample size
                'min_rushing_yards': 200,   # Minimum rushing yards
                'min_touches': 75,          # Minimum total touches (carries + targets)
                'starter_touches': 150      # Touches threshold for likely starter
            },
            'WR': {
                'min_targets': 20,          # Minimum targets for relevance
                'min_games': 4,             # Minimum games for sample size
                'min_receiving_yards': 150, # Minimum receiving yards
                'starter_targets': 60       # Targets threshold for likely starter
            },
            'TE': {
                'min_targets': 15,          # Minimum targets for relevance
                'min_games': 4,             # Minimum games for sample size
                'min_receiving_yards': 100, # Minimum receiving yards
                'starter_targets': 40       # Targets threshold for likely starter
            }
        }
        
        # Position-specific feature importance categories
        self.feature_importance_categories = {
            'QB': {
                'primary': ['passing_attempts', 'passing_yards', 'passing_tds', 'interceptions'],
                'secondary': ['rushing_yards', 'rushing_tds', 'sacks', 'completion_percentage'],
                'advanced': ['air_yards', 'yards_after_catch', 'passer_rating', 'qb_rating']
            },
            'RB': {
                'primary': ['rushing_attempts', 'rushing_yards', 'rushing_tds', 'targets'],
                'secondary': ['receptions', 'receiving_yards', 'receiving_tds', 'fumbles'],
                'advanced': ['yards_per_carry', 'target_share', 'touch_share', 'red_zone_carries']
            },
            'WR': {
                'primary': ['targets', 'receptions', 'receiving_yards', 'receiving_tds'],
                'secondary': ['rushing_attempts', 'rushing_yards', 'fumbles'],
                'advanced': ['target_share', 'air_yards', 'yards_after_catch', 'catch_rate', 'adot']
            },
            'TE': {
                'primary': ['targets', 'receptions', 'receiving_yards', 'receiving_tds'],
                'secondary': ['blocking_snaps', 'fumbles'],
                'advanced': ['target_share', 'air_yards', 'yards_after_catch', 'catch_rate', 'red_zone_targets']
            }
        }
        
        # Expected statistical ranges by position (for outlier detection)
        self.statistical_ranges = {
            'QB': {
                'passing_attempts': (100, 700),
                'passing_yards': (1000, 5500),
                'passing_tds': (5, 55),
                'interceptions': (0, 25),
                'rushing_attempts': (0, 150),
                'rushing_yards': (0, 1200),
                'rushing_tds': (0, 15)
            },
            'RB': {
                'rushing_attempts': (20, 400),
                'rushing_yards': (50, 2000),
                'rushing_tds': (0, 25),
                'targets': (0, 150),
                'receptions': (0, 120),
                'receiving_yards': (0, 1000),
                'receiving_tds': (0, 15)
            },
            'WR': {
                'targets': (10, 180),
                'receptions': (5, 140),
                'receiving_yards': (50, 2000),
                'receiving_tds': (0, 20),
                'rushing_attempts': (0, 50),
                'rushing_yards': (0, 500),
                'rushing_tds': (0, 10)
            },
            'TE': {
                'targets': (5, 150),
                'receptions': (5, 120),
                'receiving_yards': (50, 1500),
                'receiving_tds': (0, 15),
                'blocking_snaps': (0, 800)
            }
        }
        
        # Position-specific draft strategy tiers
        self.draft_tiers = {
            'QB': {
                'elite': {'count': 3, 'description': 'Elite QBs with rushing upside'},
                'starter': {'count': 12, 'description': 'Reliable weekly starters'},
                'backup': {'count': 8, 'description': 'Streaming options with upside'},
                'deep': {'count': 10, 'description': 'Deep sleepers and handcuffs'}
            },
            'RB': {
                'elite': {'count': 8, 'description': 'Workhorse RBs with heavy usage'},
                'rb2': {'count': 12, 'description': 'Solid RB2 options'},
                'flex': {'count': 15, 'description': 'FLEX-worthy options'},
                'handcuff': {'count': 20, 'description': 'Handcuffs and committee backs'}
            },
            'WR': {
                'wr1': {'count': 12, 'description': 'True WR1s with high target share'},
                'wr2': {'count': 18, 'description': 'Reliable WR2 options'},
                'wr3': {'count': 24, 'description': 'WR3s and FLEX options'},
                'deep': {'count': 30, 'description': 'Deep sleepers and upside plays'}
            },
            'TE': {
                'elite': {'count': 3, 'description': 'Game-changing elite TEs'},
                'mid_tier': {'count': 6, 'description': 'Reliable mid-tier options'},
                'streaming': {'count': 15, 'description': 'Streaming and matchup plays'},
                'deep': {'count': 20, 'description': 'Deep sleepers and rookies'}
            }
        }
        
        # Position-specific opportunity metrics definitions
        self.opportunity_metrics = {
            'QB': [
                'snap_share', 'pass_rate', 'red_zone_attempts', 'goal_line_attempts'
            ],
            'RB': [
                'snap_share', 'carry_share', 'target_share', 'touch_share', 
                'red_zone_carries', 'goal_line_carries', 'high_value_touches'
            ],
            'WR': [
                'snap_share', 'target_share', 'air_yards_share', 'red_zone_targets',
                'end_zone_targets', 'route_participation'
            ],
            'TE': [
                'snap_share', 'target_share', 'air_yards_share', 'red_zone_targets',
                'route_participation', 'blocking_rate'
            ]
        }
        
        # Position-specific efficiency metrics
        self.efficiency_metrics = {
            'QB': [
                'yards_per_attempt', 'completion_percentage', 'touchdown_percentage',
                'interception_percentage', 'passer_rating', 'yards_per_rush'
            ],
            'RB': [
                'yards_per_carry', 'yards_per_target', 'catch_rate',
                'yards_after_contact', 'breakaway_run_rate', 'goal_line_conversion_rate'
            ],
            'WR': [
                'yards_per_target', 'yards_per_reception', 'catch_rate',
                'yards_after_catch_per_reception', 'contested_catch_rate', 'drop_rate'
            ],
            'TE': [
                'yards_per_target', 'yards_per_reception', 'catch_rate',
                'yards_after_catch_per_reception', 'red_zone_catch_rate'
            ]
        }
        
        # Age curves and career stage definitions
        self.age_curves = {
            'QB': {
                'rookie': (22, 23),
                'developing': (24, 26),
                'prime': (27, 32),
                'veteran': (33, 37),
                'decline': (38, 45)
            },
            'RB': {
                'rookie': (21, 22),
                'developing': (23, 24),
                'prime': (25, 28),
                'veteran': (29, 31),
                'decline': (32, 35)
            },
            'WR': {
                'rookie': (21, 22),
                'developing': (23, 25),
                'prime': (26, 29),
                'veteran': (30, 33),
                'decline': (34, 37)
            },
            'TE': {
                'rookie': (21, 22),
                'developing': (23, 25),
                'prime': (26, 30),
                'veteran': (31, 34),
                'decline': (35, 38)
            }
        }
        
        # Position-specific injury risk factors
        self.injury_risk_factors = {
            'QB': {'base_risk': 0.15, 'rushing_qb_multiplier': 1.3},
            'RB': {'base_risk': 0.35, 'workhorse_multiplier': 1.2},
            'WR': {'base_risk': 0.20, 'deep_threat_multiplier': 1.1},
            'TE': {'base_risk': 0.25, 'blocking_multiplier': 1.15}
        }
        
        # Environment-specific overrides
        if self.environment == 'test':
            self._apply_test_overrides()
    
    def _apply_test_overrides(self) -> None:
        """Apply test-specific configuration overrides."""
        # Lower thresholds for test data
        for pos in self.meaningful_production_thresholds:
            for threshold in self.meaningful_production_thresholds[pos]:
                if 'min_' in threshold:
                    self.meaningful_production_thresholds[pos][threshold] *= 0.5
    
    def _validate(self) -> None:
        """Validate position configuration values."""
        
        # Validate required fields
        required_fields = [
            'positions', 'core_positions', 'meaningful_production_thresholds',
            'feature_importance_categories', 'statistical_ranges'
        ]
        self.validate_required_fields(required_fields)
        
        # Validate types
        type_mapping = {
            'positions': list,
            'core_positions': list,
            'skill_positions': list,
            'position_priorities': dict,
            'meaningful_production_thresholds': dict,
            'feature_importance_categories': dict,
            'statistical_ranges': dict,
            'draft_tiers': dict
        }
        self.validate_types(type_mapping)
        
        # Validate position consistency
        self._validate_position_consistency()
        
        # Validate threshold values
        self._validate_thresholds()
    
    def _validate_position_consistency(self) -> None:
        """Validate that positions are consistently defined across all configs."""
        # Check that core positions are subset of all positions
        for pos in self.core_positions:
            if pos not in self.positions:
                raise ValueError(f"Core position {pos} not in positions list")
        
        # Check that all core positions have required configurations
        for pos in self.core_positions:
            if pos not in self.meaningful_production_thresholds:
                raise ValueError(f"Missing production thresholds for {pos}")
            if pos not in self.feature_importance_categories:
                raise ValueError(f"Missing feature importance categories for {pos}")
            if pos not in self.statistical_ranges:
                raise ValueError(f"Missing statistical ranges for {pos}")
    
    def _validate_thresholds(self) -> None:
        """Validate threshold values are reasonable."""
        for pos, thresholds in self.meaningful_production_thresholds.items():
            for threshold, value in thresholds.items():
                if not isinstance(value, (int, float)) or value < 0:
                    raise ValueError(f"Invalid threshold {threshold} for {pos}: {value}")
        
        # Validate statistical ranges
        for pos, ranges in self.statistical_ranges.items():
            for stat, (min_val, max_val) in ranges.items():
                if min_val >= max_val:
                    raise ValueError(f"Invalid range for {pos} {stat}: {min_val} >= {max_val}")
    
    def get_meaningful_production_threshold(self, position: str, threshold_type: str) -> Union[int, float]:
        """
        Get meaningful production threshold for a position.
        
        Args:
            position: Player position
            threshold_type: Type of threshold (e.g., 'min_attempts', 'min_games')
            
        Returns:
            Threshold value
        """
        position = position.upper()
        
        if position not in self.meaningful_production_thresholds:
            raise ValueError(f"No production thresholds defined for {position}")
        
        thresholds = self.meaningful_production_thresholds[position]
        
        if threshold_type not in thresholds:
            raise ValueError(f"Unknown threshold type {threshold_type} for {position}")
        
        return thresholds[threshold_type]
    
    def is_meaningful_production(self, position: str, player_stats: Dict[str, Any]) -> bool:
        """
        Check if a player has meaningful production for their position.
        
        Args:
            position: Player position
            player_stats: Dictionary of player statistics
            
        Returns:
            True if player has meaningful production
        """
        position = position.upper()
        
        if position not in self.meaningful_production_thresholds:
            return True  # Assume meaningful if no thresholds defined
        
        thresholds = self.meaningful_production_thresholds[position]
        
        # Check each minimum threshold
        for threshold_type, min_value in thresholds.items():
            if threshold_type.startswith('min_'):
                stat_name = threshold_type.replace('min_', '')
                
                # Convert stat name variations
                stat_mapping = {
                    'attempts': 'passing_attempts',
                    'carries': 'rushing_attempts',
                    'touches': 'total_touches'  # Would need to be calculated
                }
                
                actual_stat = stat_mapping.get(stat_name, stat_name)
                
                if actual_stat in player_stats:
                    if player_stats[actual_stat] < min_value:
                        return False
        
        return True
    
    def get_feature_importance_categories(self, position: str) -> Dict[str, List[str]]:
        """
        Get feature importance categories for a position.
        
        Args:
            position: Player position
            
        Returns:
            Dictionary mapping categories to feature lists
        """
        position = position.upper()
        
        if position not in self.feature_importance_categories:
            return {'primary': [], 'secondary': [], 'advanced': []}
        
        return self.feature_importance_categories[position].copy()
    
    def get_statistical_range(self, position: str, stat: str) -> tuple:
        """
        Get expected statistical range for a position and stat.
        
        Args:
            position: Player position
            stat: Statistical category
            
        Returns:
            Tuple of (min_value, max_value)
        """
        position = position.upper()
        
        if position not in self.statistical_ranges:
            return (0, float('inf'))
        
        ranges = self.statistical_ranges[position]
        
        if stat not in ranges:
            return (0, float('inf'))
        
        return ranges[stat]
    
    def is_statistical_outlier(self, position: str, stat: str, value: float) -> bool:
        """
        Check if a statistical value is an outlier for a position.
        
        Args:
            position: Player position
            stat: Statistical category
            value: Statistical value to check
            
        Returns:
            True if value is outside expected range
        """
        min_val, max_val = self.get_statistical_range(position, stat)
        return value < min_val or value > max_val
    
    def get_draft_tier_info(self, position: str, tier: str) -> Dict[str, Any]:
        """
        Get draft tier information for a position.
        
        Args:
            position: Player position
            tier: Tier name (e.g., 'elite', 'starter')
            
        Returns:
            Dictionary with tier information
        """
        position = position.upper()
        
        if position not in self.draft_tiers:
            return {'count': 0, 'description': 'Unknown tier'}
        
        tiers = self.draft_tiers[position]
        
        if tier not in tiers:
            return {'count': 0, 'description': 'Unknown tier'}
        
        return tiers[tier].copy()
    
    def get_opportunity_metrics(self, position: str) -> List[str]:
        """
        Get list of opportunity metrics for a position.
        
        Args:
            position: Player position
            
        Returns:
            List of opportunity metric names
        """
        position = position.upper()
        return self.opportunity_metrics.get(position, []).copy()
    
    def get_efficiency_metrics(self, position: str) -> List[str]:
        """
        Get list of efficiency metrics for a position.
        
        Args:
            position: Player position
            
        Returns:
            List of efficiency metric names
        """
        position = position.upper()
        return self.efficiency_metrics.get(position, []).copy()
    
    def get_age_stage(self, position: str, age: int) -> str:
        """
        Get career stage based on position and age.
        
        Args:
            position: Player position
            age: Player age
            
        Returns:
            Career stage string
        """
        position = position.upper()
        
        if position not in self.age_curves:
            return 'unknown'
        
        age_ranges = self.age_curves[position]
        
        for stage, (min_age, max_age) in age_ranges.items():
            if min_age <= age <= max_age:
                return stage
        
        return 'unknown'
    
    def get_injury_risk_multiplier(self, position: str, player_type: str = 'default') -> float:
        """
        Get injury risk multiplier for a position and player type.
        
        Args:
            position: Player position
            player_type: Player type (e.g., 'rushing_qb', 'workhorse')
            
        Returns:
            Injury risk multiplier
        """
        position = position.upper()
        
        if position not in self.injury_risk_factors:
            return 1.0
        
        risk_factors = self.injury_risk_factors[position]
        base_risk = risk_factors.get('base_risk', 0.2)
        
        # Apply type-specific multipliers
        type_key = f"{player_type}_multiplier"
        multiplier = risk_factors.get(type_key, 1.0)
        
        return base_risk * multiplier
    
    def get_position_priority(self, position: str) -> int:
        """
        Get draft priority for a position (lower number = higher priority).
        
        Args:
            position: Player position
            
        Returns:
            Priority ranking (1 = highest priority)
        """
        position = position.upper()
        return self.position_priorities.get(position, 999)
    
    def is_core_position(self, position: str) -> bool:
        """Check if position is a core position with full feature engineering."""
        return position.upper() in [pos.upper() for pos in self.core_positions]
    
    def is_skill_position(self, position: str) -> bool:
        """Check if position is an offensive skill position."""
        return position.upper() in [pos.upper() for pos in self.skill_positions]
    
    def get_all_positions(self) -> List[str]:
        """Get list of all supported positions."""
        return self.positions.copy()
    
    def get_supported_positions(self) -> List[str]:
        """Get list of positions with full configuration support."""
        return self.core_positions.copy()