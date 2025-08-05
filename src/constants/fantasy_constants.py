"""
Fantasy Football Constants

This module contains all constants, magic numbers, and default values used throughout
the Fantasy Draft Engine. Centralizing these values makes the code more maintainable
and easier to configure.

Design Philosophy:
- All magic numbers should be defined here with clear explanations
- Values should be organized by functional area
- Use dataclasses for complex constant groups
- Provide methods for common operations (like tier classification)
"""

from dataclasses import dataclass
from typing import Dict, List
import pandas as pd


@dataclass(frozen=True)
class VORTiers:
    """Value Over Replacement tier thresholds and classification logic.
    
    These thresholds are based on fantasy football research showing that:
    - Elite players (18+ VOR) are league-winners, must draft early
    - Premium players (14-18 VOR) are strong starters worth reaching for
    - Solid players (10-14 VOR) are reliable starters, good value picks
    - Depth players (6-10 VOR) are viable starters or strong bench options
    - Below 6 VOR are replacement level or worse
    """
    ELITE: float = 18.0      # Must-draft players, significant drop-off after this group
    PREMIUM: float = 14.0    # Excellent picks, strong weekly floors and ceilings
    SOLID: float = 10.0      # Decent starters, good for middle rounds
    DEPTH: float = 6.0       # Replacement level starts here
    
    # Tier names for display
    TIER_NAMES = {
        'ELITE': 'Elite Tier (League Winners)',
        'PREMIUM': 'Premium Tier (Strong Starters)', 
        'SOLID': 'Solid Tier (Reliable Contributors)',
        'DEPTH': 'Depth Tier (Viable Options)',
        'BENCH': 'Bench Tier (Replacement Level)'
    }
    
    def get_tier(self, vor_value: float) -> str:
        """Get tier name for a VOR value."""
        if vor_value >= self.ELITE:
            return "ELITE"
        elif vor_value >= self.PREMIUM:
            return "PREMIUM"
        elif vor_value >= self.SOLID:
            return "SOLID"
        elif vor_value >= self.DEPTH:
            return "DEPTH"
        else:
            return "BENCH"
    
    def get_tier_description(self, vor_value: float) -> str:
        """Get descriptive tier name for a VOR value."""
        tier = self.get_tier(vor_value)
        return self.TIER_NAMES.get(tier, 'Unknown Tier')
    
    def get_all_thresholds(self) -> Dict[str, float]:
        """Get all tier thresholds as a dictionary."""
        return {
            'ELITE': self.ELITE,
            'PREMIUM': self.PREMIUM,
            'SOLID': self.SOLID,
            'DEPTH': self.DEPTH
        }


@dataclass(frozen=True)
class FantasyDefaults:
    """Default values used throughout the fantasy football system.
    
    These represent reasonable fallback values when data is missing or
    calculations need baseline assumptions.
    """
    # Player defaults
    DEFAULT_AGE: int = 25                    # Average NFL player age
    DEFAULT_GAMES_IN_SEASON: int = 17        # Current NFL regular season length
    PREDICTION_YEAR: int = 2025              # Year we're predicting for
    
    # Age-related constants
    MIN_REASONABLE_AGE: int = 20             # Youngest realistic NFL player
    MAX_REASONABLE_AGE: int = 45             # Oldest realistic NFL player
    
    # Prediction bounds (seasonal fantasy points)
    MIN_PREDICTION_VALUE: float = 0.0        # No negative fantasy points
    MAX_PREDICTION_VALUE: float = 500.0      # Cap unrealistic predictions
    
    # Data quality thresholds
    MAX_NULL_PERCENTAGE: float = 0.1         # 10% max null values allowed
    MIN_GAMES_FOR_PROJECTION: int = 4        # Need at least 4 games of data
    
    @property
    def POSITION_BASELINES(self) -> Dict[str, float]:
        """Baseline seasonal fantasy points by position.
        
        These represent average/replacement level fantasy points for a full season.
        Used as fallback values when predictions fail.
        """
        return {
            'QB': 255.0,   # ~15 fantasy points per game average
            'RB': 170.0,   # ~10 fantasy points per game average  
            'WR': 136.0,   # ~8 fantasy points per game average
            'TE': 102.0,   # ~6 fantasy points per game average
            'K': 136.0,    # ~8 fantasy points per game average
            'DST': 136.0   # ~8 fantasy points per game average
        }
    
    def get_baseline_for_position(self, position: str) -> float:
        """Get baseline seasonal fantasy points for a position."""
        return self.POSITION_BASELINES.get(position.upper(), 85.0)


@dataclass(frozen=True)
class VORConfiguration:
    """Value Over Replacement calculation configuration.
    
    These settings control how VOR is calculated for each position, based on:
    - League size (12 teams assumed)
    - Starting lineup requirements
    - Typical draft patterns
    - Position scarcity analysis
    """
    
    @property
    def REPLACEMENT_LEVELS(self) -> Dict[str, int]:
        """Replacement level rank for each position (where VOR = 0).
        
        Based on 12-team league with typical roster construction:
        - QB: 12-15 range (can stream QBs effectively)
        - RB: 24-30 range (2.5 RBs per team on average)
        - WR: 24-30 range (2.5 WRs per team on average) 
        - TE: 12-15 range (big drop-off after top tier)
        - K/DST: 12 (one per team, streamable)
        """
        return {
            'QB': 13,   # QB13 - streaming QBs is viable strategy
            'RB': 30,   # RB30 - about 2.5 per team (injury-prone position)
            'WR': 30,   # WR30 - similar depth to RB but less injury risk
            'TE': 13,   # TE13 - significant drop after top tier TEs
            'K': 12,    # K12 - completely streamable position
            'DST': 12   # DST12 - completely streamable position
        }
    
    @property
    def SCARCITY_MULTIPLIERS(self) -> Dict[str, float]:
        """Position scarcity multipliers for VOR calculation.
        
        These multipliers account for:
        - How quickly position value drops off
        - Injury risk and replaceability
        - Draft strategy importance
        """
        return {
            'QB': 1.0,   # Baseline - lots of QB depth, late-round viable
            'RB': 1.5,   # High multiplier - injury-prone, big drop-offs
            'WR': 1.2,   # Medium multiplier - some depth but targets concentrated  
            'TE': 1.4,   # High multiplier - big gap between elite and replacement
            'K': 0.8,    # Low multiplier - completely replaceable position
            'DST': 0.9   # Low multiplier - mostly streamable with some consistency
        }
    
    def get_replacement_level(self, position: str) -> int:
        """Get replacement level rank for a position."""
        return self.REPLACEMENT_LEVELS.get(position.upper(), 15)
    
    def get_scarcity_multiplier(self, position: str) -> float:
        """Get scarcity multiplier for a position."""
        return self.SCARCITY_MULTIPLIERS.get(position.upper(), 1.0)


@dataclass(frozen=True)
class ScoringSystem:
    """Fantasy football scoring system configuration.
    
    Currently configured for 0.5 PPR (Half Point Per Reception) scoring,
    which is the most balanced and commonly used format.
    """
    # Passing scoring (per event)
    PASSING_YARDS_PER_POINT: float = 25.0    # 1 point per 25 yards
    PASSING_TD_POINTS: float = 4.0           # 4 points per passing TD
    INTERCEPTION_POINTS: float = -2.0        # -2 points per interception
    
    # Rushing scoring (per event)
    RUSHING_YARDS_PER_POINT: float = 10.0    # 1 point per 10 yards
    RUSHING_TD_POINTS: float = 6.0           # 6 points per rushing TD
    
    # Receiving scoring (per event)
    RECEPTION_POINTS: float = 0.5            # 0.5 points per reception (Half PPR)
    RECEIVING_YARDS_PER_POINT: float = 10.0  # 1 point per 10 yards
    RECEIVING_TD_POINTS: float = 6.0         # 6 points per receiving TD
    
    # Miscellaneous scoring
    FUMBLE_LOST_POINTS: float = -2.0         # -2 points per fumble lost
    TWO_POINT_CONVERSION_POINTS: float = 2.0 # 2 points per 2-point conversion
    
    # Position-specific scoring
    KICKER_PAT_POINTS: float = 1.0           # 1 point per extra point
    KICKER_FG_POINTS: Dict[int, float] = None # Field goal points by distance
    
    def __post_init__(self):
        # Field goal scoring by distance (yards)
        object.__setattr__(self, 'KICKER_FG_POINTS', {
            range(0, 40): 3.0,    # Under 40 yards: 3 points
            range(40, 50): 4.0,   # 40-49 yards: 4 points  
            range(50, 60): 5.0,   # 50-59 yards: 5 points
            range(60, 70): 6.0    # 60+ yards: 6 points
        })
    
    def calculate_passing_points(self, yards: float, tds: float, ints: float) -> float:
        """Calculate fantasy points for passing stats."""
        return (yards / self.PASSING_YARDS_PER_POINT + 
                tds * self.PASSING_TD_POINTS + 
                ints * self.INTERCEPTION_POINTS)
    
    def calculate_rushing_points(self, yards: float, tds: float) -> float:
        """Calculate fantasy points for rushing stats."""
        return (yards / self.RUSHING_YARDS_PER_POINT + 
                tds * self.RUSHING_TD_POINTS)
    
    def calculate_receiving_points(self, receptions: float, yards: float, tds: float) -> float:
        """Calculate fantasy points for receiving stats."""
        return (receptions * self.RECEPTION_POINTS + 
                yards / self.RECEIVING_YARDS_PER_POINT + 
                tds * self.RECEIVING_TD_POINTS)


@dataclass(frozen=True)
class ModelConfiguration:
    """Configuration constants for machine learning models."""
    
    # Feature engineering
    MIN_FEATURE_IMPORTANCE: float = 0.001    # Minimum importance to keep feature
    MAX_FEATURES_PER_MODEL: int = 100        # Cap features to prevent overfitting
    
    # Model validation
    MIN_R2_THRESHOLD: float = 0.4            # Minimum acceptable R² score
    MAX_RMSE_THRESHOLD: float = 5.0          # Maximum acceptable RMSE
    CROSS_VALIDATION_FOLDS: int = 5          # Number of CV folds
    
    # Prediction bounds
    MIN_PREDICTION_CONFIDENCE: float = 0.1   # Minimum confidence interval width
    MAX_PREDICTION_CONFIDENCE: float = 0.9   # Maximum confidence interval width
    
    # Ensemble weights (if not using dynamic weighting)
    DEFAULT_RF_WEIGHT: float = 0.4           # Random Forest weight in ensemble
    DEFAULT_LGB_WEIGHT: float = 0.6          # LightGBM weight in ensemble


@dataclass(frozen=True)
class ValidationThresholds:
    """Thresholds for data validation and quality checks."""
    
    # Prediction validation by position (seasonal fantasy points)
    POSITION_RANGES = {
        'QB': (150.0, 450.0),    # QBs typically score 150-450 points
        'RB': (50.0, 350.0),     # RBs typically score 50-350 points  
        'WR': (50.0, 350.0),     # WRs typically score 50-350 points
        'TE': (30.0, 250.0),     # TEs typically score 30-250 points
        'K': (80.0, 180.0),      # Kickers typically score 80-180 points
        'DST': (80.0, 200.0)     # Defenses typically score 80-200 points
    }
    
    # Feature validation
    MIN_FEATURE_CORRELATION: float = 0.05    # Min correlation with target to keep
    MAX_FEATURE_CORRELATION: float = 0.95    # Max correlation to avoid redundancy
    MAX_MISSING_DATA_RATIO: float = 0.3      # Max 30% missing data per feature
    
    def get_position_range(self, position: str) -> tuple:
        """Get valid prediction range for a position."""
        return self.POSITION_RANGES.get(position.upper(), (0.0, 500.0))
    
    def is_prediction_valid(self, prediction: float, position: str) -> bool:
        """Check if a prediction is within valid range for position."""
        min_val, max_val = self.get_position_range(position)
        return min_val <= prediction <= max_val


# Create singleton instances for easy importing
VOR_TIERS = VORTiers()
FANTASY_DEFAULTS = FantasyDefaults()
VOR_CONFIG = VORConfiguration()
SCORING_SYSTEM = ScoringSystem()
MODEL_CONFIG = ModelConfiguration()
VALIDATION_THRESHOLDS = ValidationThresholds()


# Convenience lists for validation
VALID_POSITIONS = ['QB', 'RB', 'WR', 'TE', 'K', 'DST']
CORE_POSITIONS = ['QB', 'RB', 'WR', 'TE']  # Exclude K/DST for some operations
SKILL_POSITIONS = ['RB', 'WR', 'TE']       # Exclude QB for some analyses


def get_all_constants() -> Dict[str, any]:
    """Get all constants as a dictionary for debugging/inspection."""
    return {
        'VOR_TIERS': VOR_TIERS,
        'FANTASY_DEFAULTS': FANTASY_DEFAULTS,
        'VOR_CONFIG': VOR_CONFIG,
        'SCORING_SYSTEM': SCORING_SYSTEM,
        'MODEL_CONFIG': MODEL_CONFIG,
        'VALIDATION_THRESHOLDS': VALIDATION_THRESHOLDS,
        'VALID_POSITIONS': VALID_POSITIONS,
        'CORE_POSITIONS': CORE_POSITIONS,
        'SKILL_POSITIONS': SKILL_POSITIONS
    }


if __name__ == "__main__":
    # Demo usage and validation
    print("Fantasy Football Constants Configuration")
    print("=" * 50)
    
    # Test VOR tier classification
    test_vor_values = [25.0, 16.0, 12.0, 8.0, 3.0]
    print("\nVOR Tier Classification:")
    for vor in test_vor_values:
        tier = VOR_TIERS.get_tier(vor)
        description = VOR_TIERS.get_tier_description(vor)
        print(f"  VOR {vor:4.1f} → {tier:7} ({description})")
    
    # Test position baselines
    print(f"\nPosition Baseline Fantasy Points:")
    for pos in VALID_POSITIONS:
        baseline = FANTASY_DEFAULTS.get_baseline_for_position(pos)
        print(f"  {pos:3}: {baseline:5.1f} points")
    
    # Test VOR configuration
    print(f"\nVOR Configuration:")
    for pos in CORE_POSITIONS:
        replacement = VOR_CONFIG.get_replacement_level(pos)
        multiplier = VOR_CONFIG.get_scarcity_multiplier(pos)
        print(f"  {pos:3}: Replacement={replacement:2d}, Multiplier={multiplier:.1f}x")
    
    # Test prediction validation
    print(f"\nPrediction Validation Ranges:")
    for pos in VALID_POSITIONS:
        min_val, max_val = VALIDATION_THRESHOLDS.get_position_range(pos)
        print(f"  {pos:3}: {min_val:5.1f} - {max_val:5.1f} points")