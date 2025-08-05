"""
Feature Mapper for Fantasy Football Models

This module provides centralized feature mapping logic to eliminate the 200+ lines
of duplicate code found throughout the codebase. It handles the conversion between
different column naming conventions and provides consistent feature preparation
for all models.

Key Responsibilities:
- Map between new feature engineering names and legacy model expectations
- Handle special conversions (birth_date → age, etc.)
- Provide consistent feature defaults for missing data
- Validate feature availability and compatibility
"""

from typing import Dict, List, Optional, Set, Tuple, Any
import pandas as pd
import numpy as np
import logging
from datetime import datetime

# Import our constants for default values
from src.constants.fantasy_constants import FANTASY_DEFAULTS, VALID_POSITIONS

logger = logging.getLogger(__name__)


class FeatureMappingError(Exception):
    """Raised when feature mapping fails or produces invalid results."""
    pass


class FeatureMapper:
    """Centralized feature mapping logic for model compatibility.
    
    This class eliminates duplicate feature mapping code found in:
    - predict_fantasy_points_baseline() 
    - predict_fantasy_points()
    - Various model prediction functions
    
    It provides a single source of truth for how features should be mapped
    between data pipeline outputs and model inputs.
    """
    
    # Core feature mappings: new_name → source_column_name
    COMMON_MAPPINGS = {
        # Basic player info
        'age': 'birth_date',           # Special conversion needed
        'games_played': 'games',       # Direct mapping
        'games': 'games',              # Passthrough
        
        # Passing stats (QB primary)
        'passing_attempts': 'passing_attempts',
        'passing_completions': 'completions',
        'passing_yards': 'passing_yards', 
        'passing_tds': 'passing_tds',
        'interceptions': 'interceptions',
        
        # Rushing stats (RB primary, QB secondary)
        'rushing_attempts': 'carries',     # Key mapping for RBs
        'rushing_yards': 'rushing_yards',
        'rushing_tds': 'rushing_tds',
        
        # Receiving stats (WR/TE primary, RB secondary)
        'targets': 'targets',
        'receptions': 'receptions', 
        'receiving_yards': 'receiving_yards',
        'receiving_tds': 'receiving_tds',
        
        # Advanced metrics (if available)
        'yards_per_carry': 'ypc',
        'yards_per_target': 'ypt',
        'yards_per_reception': 'ypr',
        'target_share': 'target_share',
        'air_yards': 'air_yards',
        'red_zone_targets': 'rz_targets',
        'touchdown_rate': 'td_rate'
    }
    
    # Position-specific mappings for special cases
    POSITION_SPECIFIC_MAPPINGS = {
        'QB': {
            'rushing_attempts': 'carries',  # QB rushing
            'qb_rating': 'passer_rating',
            'completion_percentage': 'completion_pct'
        },
        'RB': {
            'carries': 'carries',           # Primary stat for RBs
            'rushing_attempts': 'carries',  # Alternative name
            'receptions': 'receptions',     # Receiving work
            'receiving_targets': 'targets'  # PPR relevance
        },
        'WR': {
            'targets': 'targets',           # Primary opportunity metric
            'air_yards': 'air_yards',       # Target quality
            'separation': 'avg_separation'  # Route running
        },
        'TE': {
            'targets': 'targets',           # Primary opportunity metric 
            'red_zone_targets': 'rz_targets', # TD upside
            'slot_rate': 'slot_pct'         # Usage pattern
        }
    }
    
    # Alternative column names to try if primary mapping fails
    ALTERNATIVE_NAMES = {
        'carries': ['rushing_attempts', 'rush_att', 'att'],
        'targets': ['receiving_targets', 'tgt', 'rec_tgt'],
        'receptions': ['rec', 'catches', 'receiving_receptions'],
        'games': ['games_played', 'g', 'gp'],
        'passing_yards': ['pass_yards', 'py', 'pass_yds'],
        'rushing_yards': ['rush_yards', 'ry', 'rush_yds'],
        'receiving_yards': ['rec_yards', 'rec_yds', 'receiving_yds']
    }
    
    def __init__(self, target_year: int = None):
        """Initialize the feature mapper.
        
        Args:
            target_year: Year for age calculations (defaults to FANTASY_DEFAULTS.PREDICTION_YEAR)
        """
        self.target_year = target_year or FANTASY_DEFAULTS.PREDICTION_YEAR
        self._mapping_cache: Dict[str, Dict[str, str]] = {}
        
    def map_features(self, 
                    df: pd.DataFrame, 
                    expected_features: List[str],
                    position: Optional[str] = None) -> pd.DataFrame:
        """Map dataframe columns to expected model features.
        
        Args:
            df: Input dataframe with raw features
            expected_features: List of feature names the model expects
            position: Player position for position-specific mappings
            
        Returns:
            DataFrame with columns mapped to expected feature names
            
        Raises:
            FeatureMappingError: If critical features cannot be mapped
        """
        if df.empty:
            raise FeatureMappingError("Cannot map features for empty dataframe")
            
        if not expected_features:
            logger.warning("No expected features provided, returning empty DataFrame")
            return pd.DataFrame(index=df.index)
        
        logger.info(f"Mapping {len(df.columns)} input columns to {len(expected_features)} expected features")
        if position:
            logger.info(f"Using position-specific mappings for {position}")
            
        # Initialize result dataframe
        result = pd.DataFrame(index=df.index)
        mapping_stats = {'direct_match': 0, 'mapped': 0, 'default': 0, 'missing': 0}
        
        for feature in expected_features:
            try:
                # Try to map this feature
                mapped_value = self._map_single_feature(df, feature, position)
                result[feature] = mapped_value
                
                # Track mapping statistics
                if feature in df.columns:
                    mapping_stats['direct_match'] += 1
                elif self._has_mapping_for_feature(feature, position):
                    mapping_stats['mapped'] += 1
                else:
                    mapping_stats['default'] += 1
                    
            except Exception as e:
                logger.warning(f"Failed to map feature '{feature}': {e}")
                result[feature] = self._get_default_value(feature, position)
                mapping_stats['missing'] += 1
        
        # Log mapping results
        self._log_mapping_results(mapping_stats, len(expected_features))
        
        # Validate result
        self._validate_mapped_features(result, expected_features)
        
        return result
    
    def _map_single_feature(self, 
                           df: pd.DataFrame, 
                           feature: str, 
                           position: Optional[str] = None) -> pd.Series:
        """Map a single feature from the dataframe.
        
        Args:
            df: Input dataframe
            feature: Feature name to map
            position: Player position for position-specific logic
            
        Returns:
            Series with mapped feature values
        """
        # 1. Direct column match (fastest path)
        if feature in df.columns:
            return df[feature].fillna(self._get_default_value(feature, position))
        
        # 2. Special handling for age conversion
        if feature == 'age':
            return self._calculate_age(df, position)
        
        # 3. Position-specific mappings
        if position and position in self.POSITION_SPECIFIC_MAPPINGS:
            pos_mappings = self.POSITION_SPECIFIC_MAPPINGS[position]
            if feature in pos_mappings:
                source_col = pos_mappings[feature]
                if source_col in df.columns:
                    return df[source_col].fillna(self._get_default_value(feature, position))
        
        # 4. Common mappings
        if feature in self.COMMON_MAPPINGS:
            source_col = self.COMMON_MAPPINGS[feature]
            if source_col in df.columns:
                return df[source_col].fillna(self._get_default_value(feature, position))
        
        # 5. Try alternative names
        if feature in self.ALTERNATIVE_NAMES:
            for alt_name in self.ALTERNATIVE_NAMES[feature]:
                if alt_name in df.columns:
                    logger.info(f"Mapped '{feature}' using alternative name '{alt_name}'")
                    return df[alt_name].fillna(self._get_default_value(feature, position))
        
        # 6. Try common variations (plurals, underscores, etc.)
        variations = self._generate_name_variations(feature)
        for variation in variations:
            if variation in df.columns:
                logger.info(f"Mapped '{feature}' using variation '{variation}'")
                return df[variation].fillna(self._get_default_value(feature, position))
        
        # 7. Default value (feature not found)
        logger.warning(f"Feature '{feature}' not found in dataframe, using default value")
        default_val = self._get_default_value(feature, position)
        return pd.Series([default_val] * len(df), index=df.index)
    
    def _calculate_age(self, df: pd.DataFrame, position: Optional[str] = None) -> pd.Series:
        """Calculate age from birth_date column.
        
        Args:
            df: Input dataframe
            position: Player position (for position-specific defaults)
            
        Returns:
            Series with calculated ages
        """
        # Try different birth date column names
        birth_cols = ['birth_date', 'birthdate', 'dob', 'date_of_birth']
        birth_col = None
        
        for col in birth_cols:
            if col in df.columns:
                birth_col = col
                break
        
        if birth_col is None:
            logger.warning("No birth date column found, using default age")
            return pd.Series([FANTASY_DEFAULTS.DEFAULT_AGE] * len(df), index=df.index)
        
        try:
            # Convert to datetime and calculate age
            birth_dates = pd.to_datetime(df[birth_col], errors='coerce')
            ages = self.target_year - birth_dates.dt.year
            
            # Validate age ranges
            ages = ages.clip(
                lower=FANTASY_DEFAULTS.MIN_REASONABLE_AGE,
                upper=FANTASY_DEFAULTS.MAX_REASONABLE_AGE
            )
            
            # Fill missing ages with default
            ages = ages.fillna(FANTASY_DEFAULTS.DEFAULT_AGE)
            
            logger.info(f"Calculated ages from '{birth_col}': range {ages.min():.0f}-{ages.max():.0f}")
            return ages
            
        except Exception as e:
            logger.error(f"Failed to calculate age from '{birth_col}': {e}")
            return pd.Series([FANTASY_DEFAULTS.DEFAULT_AGE] * len(df), index=df.index)
    
    def _get_default_value(self, feature: str, position: Optional[str] = None) -> float:
        """Get default value for a feature when data is missing.
        
        Args:
            feature: Feature name
            position: Player position for position-specific defaults
            
        Returns:
            Default value for the feature
        """
        # Position and context-aware defaults
        if feature == 'age':
            return float(FANTASY_DEFAULTS.DEFAULT_AGE)
        elif feature in ['games', 'games_played']:
            return float(FANTASY_DEFAULTS.DEFAULT_GAMES_IN_SEASON)
        elif 'rate' in feature.lower() or 'percentage' in feature.lower():
            return 0.0  # Rates/percentages default to 0
        elif any(stat in feature.lower() for stat in ['yards', 'attempts', 'targets', 'carries']):
            return 0.0  # Counting stats default to 0
        else:
            return 0.0  # Safe default for most features
    
    def _generate_name_variations(self, feature: str) -> List[str]:
        """Generate common variations of a feature name.
        
        Args:
            feature: Original feature name
            
        Returns:
            List of possible variations
        """
        variations = []
        
        # Add/remove 's' for plurals
        if feature.endswith('s'):
            variations.append(feature[:-1])
        else:
            variations.append(feature + 's')
        
        # Add/remove underscores
        if '_' in feature:
            variations.append(feature.replace('_', ''))
        else:
            # Insert underscores in common places
            for pos in ['passing', 'rushing', 'receiving']:
                if feature.startswith(pos):
                    variations.append(f"{pos}_{feature[len(pos):]}")
        
        # Add common abbreviations
        abbreviations = {
            'attempts': 'att',
            'yards': 'yds', 
            'touchdowns': 'tds',
            'receptions': 'rec',
            'targets': 'tgt'
        }
        
        for full, abbr in abbreviations.items():
            if full in feature:
                variations.append(feature.replace(full, abbr))
            elif abbr in feature:
                variations.append(feature.replace(abbr, full))
        
        return variations
    
    def _has_mapping_for_feature(self, feature: str, position: Optional[str] = None) -> bool:
        """Check if we have a mapping available for this feature."""
        # Check position-specific mappings
        if position and position in self.POSITION_SPECIFIC_MAPPINGS:
            if feature in self.POSITION_SPECIFIC_MAPPINGS[position]:
                return True
        
        # Check common mappings
        if feature in self.COMMON_MAPPINGS:
            return True
        
        # Check alternative names
        if feature in self.ALTERNATIVE_NAMES:
            return True
        
        return False
    
    def _validate_mapped_features(self, result: pd.DataFrame, expected_features: List[str]) -> None:
        """Validate that feature mapping was successful.
        
        Args:
            result: Mapped feature dataframe
            expected_features: List of expected features
            
        Raises:
            FeatureMappingError: If validation fails
        """
        # Check that all expected features are present
        missing_features = set(expected_features) - set(result.columns)
        if missing_features:
            raise FeatureMappingError(f"Missing expected features after mapping: {missing_features}")
        
        # Check for excessive null values
        null_counts = result.isnull().sum()
        high_null_features = null_counts[null_counts > len(result) * 0.5]  # More than 50% null
        
        if not high_null_features.empty:
            logger.warning(f"Features with high null rates after mapping: {high_null_features.to_dict()}")
        
        # Check data types
        non_numeric = result.select_dtypes(exclude=[np.number]).columns
        if len(non_numeric) > 0:
            logger.warning(f"Non-numeric features detected: {list(non_numeric)}")
    
    def _log_mapping_results(self, stats: Dict[str, int], total_features: int) -> None:
        """Log the results of feature mapping."""
        logger.info(f"Feature mapping completed:")
        logger.info(f"  Direct matches: {stats['direct_match']}/{total_features}")
        logger.info(f"  Mapped features: {stats['mapped']}/{total_features}")
        logger.info(f"  Default values: {stats['default']}/{total_features}")
        logger.info(f"  Missing features: {stats['missing']}/{total_features}")
        
        success_rate = (stats['direct_match'] + stats['mapped']) / total_features
        logger.info(f"  Success rate: {success_rate:.1%}")
    
    def get_mapping_info(self, 
                        df: pd.DataFrame, 
                        expected_features: List[str],
                        position: Optional[str] = None) -> Dict[str, Any]:
        """Get detailed information about how features would be mapped.
        
        Args:
            df: Input dataframe
            expected_features: Expected feature names
            position: Player position
            
        Returns:
            Dictionary with mapping information
        """
        mapping_info = {
            'available_columns': list(df.columns),
            'expected_features': expected_features,
            'mappings': {},
            'missing': [],
            'statistics': {}
        }
        
        for feature in expected_features:
            if feature in df.columns:
                mapping_info['mappings'][feature] = {'source': feature, 'type': 'direct'}
            elif feature == 'age' and any(col in df.columns for col in ['birth_date', 'birthdate']):
                mapping_info['mappings'][feature] = {'source': 'birth_date', 'type': 'calculated'}
            elif self._has_mapping_for_feature(feature, position):
                # Find the actual source column
                source = self._find_source_column(feature, position, df.columns)
                if source:
                    mapping_info['mappings'][feature] = {'source': source, 'type': 'mapped'}
                else:
                    mapping_info['missing'].append(feature)
            else:
                mapping_info['missing'].append(feature)
        
        # Calculate statistics
        total = len(expected_features)
        mapped = len(mapping_info['mappings'])
        missing = len(mapping_info['missing'])
        
        mapping_info['statistics'] = {
            'total_features': total,
            'successfully_mapped': mapped,
            'missing_features': missing,
            'success_rate': mapped / total if total > 0 else 0.0
        }
        
        return mapping_info
    
    def _find_source_column(self, feature: str, position: Optional[str], available_columns: List[str]) -> Optional[str]:
        """Find the source column for a feature given available columns."""
        # Check position-specific mappings
        if position and position in self.POSITION_SPECIFIC_MAPPINGS:
            pos_mappings = self.POSITION_SPECIFIC_MAPPINGS[position]
            if feature in pos_mappings and pos_mappings[feature] in available_columns:
                return pos_mappings[feature]
        
        # Check common mappings
        if feature in self.COMMON_MAPPINGS and self.COMMON_MAPPINGS[feature] in available_columns:
            return self.COMMON_MAPPINGS[feature]
        
        # Check alternatives
        if feature in self.ALTERNATIVE_NAMES:
            for alt in self.ALTERNATIVE_NAMES[feature]:
                if alt in available_columns:
                    return alt
        
        return None


# Convenience function for quick feature mapping
def map_features_for_model(df: pd.DataFrame, 
                          model: Any, 
                          position: Optional[str] = None) -> pd.DataFrame:
    """Convenience function to map features for a specific model.
    
    Args:
        df: Input dataframe
        model: Model object (should have feature_names_in_ attribute)
        position: Player position
        
    Returns:
        DataFrame with features mapped for the model
    """
    # Extract expected features from model
    if hasattr(model, 'feature_names_in_'):
        expected_features = list(model.feature_names_in_)
    elif hasattr(model, 'feature_name_'):  # Some models use different attribute names
        expected_features = list(model.feature_name_)
    else:
        raise FeatureMappingError("Model does not expose expected feature names")
    
    # Map features
    mapper = FeatureMapper()
    return mapper.map_features(df, expected_features, position)


if __name__ == "__main__":
    # Demo and testing
    print("FeatureMapper Demo")
    print("=" * 50)
    
    # Create sample data
    sample_data = pd.DataFrame({
        'player_name': ['Josh Allen', 'Christian McCaffrey', 'Cooper Kupp'],
        'position': ['QB', 'RB', 'WR'],
        'birth_date': ['1996-05-21', '1996-06-07', '1993-06-15'],
        'games': [16, 14, 17],
        'carries': [0, 287, 5],
        'passing_yards': [4283, 0, 0],
        'targets': [0, 85, 145],
        'receptions': [0, 70, 128]
    })
    
    # Test feature mapping
    expected_features = ['age', 'games_played', 'rushing_attempts', 'passing_yards', 'targets']
    
    mapper = FeatureMapper()
    mapped_features = mapper.map_features(sample_data, expected_features, 'RB')
    
    print("Sample mapping result:")
    print(mapped_features)
    
    # Test mapping info
    info = mapper.get_mapping_info(sample_data, expected_features, 'RB')
    print(f"\nMapping Statistics:")
    print(f"Success Rate: {info['statistics']['success_rate']:.1%}")
    print(f"Mapped: {info['statistics']['successfully_mapped']}")
    print(f"Missing: {info['statistics']['missing_features']}")