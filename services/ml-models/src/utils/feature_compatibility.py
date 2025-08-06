"""
Feature Compatibility Module

This module handles the mapping between current feature engineering output
and the expected feature names for baseline models. This fixes the 
"10 expected vs 5 provided" feature mismatch issue.

Key Functions:
- Map current feature names to model-expected names
- Validate feature availability
- Handle missing features with appropriate defaults
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Set, Optional, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class FeatureCompatibilityMapper:
    """
    Maps current feature engineering output to baseline model expectations.
    
    This class solves the feature mismatch where baseline models expect specific
    column names (like 'games_played', 'rushing_attempts') but current data 
    provides different names (like 'games', 'carries').
    """
    
    def __init__(self):
        """Initialize the feature compatibility mapper."""
        
        # Core feature mappings based on model inspection results
        self.feature_mappings = {
            # Universal mappings (all positions)
            'games_played': 'games',
            'age': 'age',  # Direct match, but may need conversion from birth_date
            
            # QB-specific mappings
            'passing_attempts': 'attempts', 
            'passing_completions': 'completions',
            'passing_yards': 'passing_yards',
            'passing_tds': 'passing_tds', 
            'interceptions': 'interceptions',
            
            # RB/WR/TE rushing mappings
            'rushing_attempts': 'carries',
            'rushing_yards': 'rushing_yards',
            'rushing_tds': 'rushing_tds',
            
            # Skill position receiving mappings
            'targets': 'targets',
            'receptions': 'receptions', 
            'receiving_yards': 'receiving_yards',
            'receiving_tds': 'receiving_tds',
            
            # DST mappings (for defense/special teams)
            'sacks': 'sacks',
            'fumbles_recovered': 'fumbles_recovered',
            'defensive_tds': 'defensive_tds', 
            'safety': 'safety',
            
            # K mappings (for kickers)
            'fg_made': 'fg_made',
            'fg_attempted': 'fg_attempted', 
            'extra_points_made': 'extra_points_made'
        }
        
        # Position-specific required features (from baseline model inspection)
        self.position_features = {
            'QB': ['age', 'games_played', 'passing_attempts', 'passing_completions', 
                   'passing_yards', 'passing_tds', 'interceptions', 'rushing_attempts', 
                   'rushing_yards', 'rushing_tds'],
            'RB': ['age', 'games_played', 'rushing_attempts', 'rushing_yards', 'rushing_tds',
                   'targets', 'receptions', 'receiving_yards', 'receiving_tds'],
            'WR': ['age', 'games_played', 'targets', 'receptions', 'receiving_yards', 
                   'receiving_tds', 'rushing_attempts', 'rushing_yards', 'rushing_tds'],
            'TE': ['age', 'games_played', 'targets', 'receptions', 'receiving_yards', 'receiving_tds'],
            'K': ['age', 'games_played', 'fg_made', 'fg_attempted', 'extra_points_made'],
            'DST': ['age', 'games_played', 'sacks', 'interceptions', 'fumbles_recovered', 
                    'defensive_tds', 'safety']
        }
        
        # Default values for missing features by position
        self.default_values = {
            'QB': {
                'age': 27,
                'games_played': 16,
                'passing_attempts': 0,
                'passing_completions': 0,
                'passing_yards': 0,
                'passing_tds': 0,
                'interceptions': 0,
                'rushing_attempts': 0,
                'rushing_yards': 0,
                'rushing_tds': 0
            },
            'RB': {
                'age': 25,
                'games_played': 16,
                'rushing_attempts': 0,
                'rushing_yards': 0,
                'rushing_tds': 0,
                'targets': 0,
                'receptions': 0,
                'receiving_yards': 0,
                'receiving_tds': 0
            },
            'WR': {
                'age': 26,
                'games_played': 16,
                'targets': 0,
                'receptions': 0,
                'receiving_yards': 0,
                'receiving_tds': 0,
                'rushing_attempts': 0,
                'rushing_yards': 0,
                'rushing_tds': 0
            },
            'TE': {
                'age': 27,
                'games_played': 16,
                'targets': 0,
                'receptions': 0,
                'receiving_yards': 0,
                'receiving_tds': 0
            },
            'K': {
                'age': 29,
                'games_played': 16,
                'fg_made': 0,
                'fg_attempted': 0,
                'extra_points_made': 0
            },
            'DST': {
                'age': 25,  # Team average age
                'games_played': 16,
                'sacks': 0,
                'interceptions': 0,
                'fumbles_recovered': 0,
                'defensive_tds': 0,
                'safety': 0
            }
        }
        
        logger.info("✅ FeatureCompatibilityMapper initialized with mappings for all positions")
    
    def map_features_for_position(self, df: pd.DataFrame, position: str) -> pd.DataFrame:
        """
        Map current features to model-expected features for a specific position.
        
        Args:
            df: DataFrame with current feature names
            position: Player position (QB, RB, WR, TE, K, DST)
            
        Returns:
            DataFrame with features mapped to model expectations
        """
        position = position.upper()
        logger.info(f"🔄 Mapping features for {position} position")
        logger.info(f"   Input shape: {df.shape}")
        
        if position not in self.position_features:
            raise ValueError(f"Unsupported position: {position}")
        
        # Get required features for this position
        required_features = self.position_features[position]
        logger.info(f"   Required features ({len(required_features)}): {required_features}")
        
        # Create output DataFrame with mapped features
        mapped_df = pd.DataFrame(index=df.index)
        
        for required_feature in required_features:
            if required_feature in self.feature_mappings:
                # Get the current column name that maps to this required feature
                current_col = self.feature_mappings[required_feature]
                
                if current_col in df.columns:
                    # Direct mapping
                    mapped_df[required_feature] = df[current_col]
                    logger.debug(f"   ✅ Mapped {required_feature} ← {current_col}")
                    
                elif required_feature == 'age' and 'birth_date' in df.columns:
                    # Special handling for age conversion from birth_date
                    mapped_df[required_feature] = self._convert_birth_date_to_age(df['birth_date'])
                    logger.debug(f"   ✅ Mapped {required_feature} ← birth_date (converted)")
                    
                else:
                    # Use default value
                    default_val = self.default_values[position][required_feature]
                    mapped_df[required_feature] = default_val
                    logger.warning(f"   ⚠️ Missing {current_col} for {required_feature}, using default: {default_val}")
            
            else:
                # Direct column name match attempt
                if required_feature in df.columns:
                    mapped_df[required_feature] = df[required_feature]
                    logger.debug(f"   ✅ Direct match {required_feature}")
                else:
                    # Use default value
                    default_val = self.default_values[position][required_feature]
                    mapped_df[required_feature] = default_val
                    logger.warning(f"   ⚠️ Missing {required_feature}, using default: {default_val}")
        
        # Ensure all values are numeric and handle NaN
        mapped_df = mapped_df.fillna(0).astype(float)
        
        logger.info(f"   ✅ Output shape: {mapped_df.shape}")
        logger.info(f"   Mapped features: {list(mapped_df.columns)}")
        
        return mapped_df
    
    def _convert_birth_date_to_age(self, birth_dates: pd.Series) -> pd.Series:
        """
        Convert birth_date to age as of current prediction season.
        
        Args:
            birth_dates: Series of birth dates
            
        Returns:
            Series of ages
        """
        try:
            # Convert to datetime if needed
            birth_dates = pd.to_datetime(birth_dates, errors='coerce')
            
            # Calculate age as of September 1st of current season (2025)
            current_year = 2025
            ages = current_year - birth_dates.dt.year
            
            # Adjust for players who haven't had birthday yet this year
            current_date = datetime(current_year, 9, 1)  # NFL season start
            for i, birth_date in enumerate(birth_dates):
                if pd.notna(birth_date):
                    if (current_date.month, current_date.day) < (birth_date.month, birth_date.day):
                        ages.iloc[i] -= 1
            
            # Fill missing ages with reasonable defaults
            ages = ages.fillna(25)
            
            logger.debug(f"   Age conversion: range {ages.min():.0f}-{ages.max():.0f} years")
            return ages
            
        except Exception as e:
            logger.error(f"Error converting birth_date to age: {e}")
            # Return default ages if conversion fails
            return pd.Series([25] * len(birth_dates), index=birth_dates.index)
    
    def validate_mapped_features(self, mapped_df: pd.DataFrame, position: str) -> Dict[str, Any]:
        """
        Validate that mapped features meet model requirements.
        
        Args:
            mapped_df: DataFrame with mapped features
            position: Player position
            
        Returns:
            Validation results dictionary
        """
        position = position.upper()
        required_features = self.position_features[position]
        
        # Check feature completeness
        missing_features = [f for f in required_features if f not in mapped_df.columns]
        extra_features = [f for f in mapped_df.columns if f not in required_features]
        
        # Check for null values
        null_counts = mapped_df.isnull().sum()
        features_with_nulls = null_counts[null_counts > 0].to_dict()
        
        # Check data types
        non_numeric = []
        for col in mapped_df.columns:
            if not pd.api.types.is_numeric_dtype(mapped_df[col]):
                non_numeric.append(col)
        
        validation_results = {
            'position': position,
            'expected_feature_count': len(required_features),
            'actual_feature_count': len(mapped_df.columns),
            'missing_features': missing_features,
            'extra_features': extra_features,
            'features_with_nulls': features_with_nulls,
            'non_numeric_features': non_numeric,
            'validation_passed': len(missing_features) == 0 and len(features_with_nulls) == 0 and len(non_numeric) == 0
        }
        
        if validation_results['validation_passed']:
            logger.info(f"✅ Feature validation passed for {position}")
        else:
            logger.error(f"❌ Feature validation failed for {position}")
            if missing_features:
                logger.error(f"   Missing features: {missing_features}")
            if features_with_nulls:
                logger.error(f"   Features with nulls: {features_with_nulls}")
            if non_numeric:
                logger.error(f"   Non-numeric features: {non_numeric}")
        
        return validation_results
    
    def get_compatibility_report(self, df: pd.DataFrame, position: str) -> Dict[str, Any]:
        """
        Generate a compatibility report between current data and model expectations.
        
        Args:
            df: Current feature DataFrame
            position: Player position
            
        Returns:
            Detailed compatibility report
        """
        position = position.upper()
        required_features = self.position_features[position]
        current_features = set(df.columns)
        
        # Calculate compatibility metrics
        available_mappings = 0
        missing_mappings = []
        
        for required_feature in required_features:
            if required_feature in self.feature_mappings:
                current_col = self.feature_mappings[required_feature]
                if current_col in current_features:
                    available_mappings += 1
                else:
                    missing_mappings.append(f"{required_feature} ← {current_col}")
            elif required_feature in current_features:
                available_mappings += 1
            else:
                missing_mappings.append(f"{required_feature} ← [no mapping]")
        
        compatibility_score = (available_mappings / len(required_features)) * 100
        
        report = {
            'position': position,
            'required_features': required_features,
            'required_count': len(required_features),
            'available_mappings': available_mappings,
            'missing_mappings': missing_mappings,
            'compatibility_score': compatibility_score,
            'can_generate_predictions': compatibility_score >= 70  # Threshold for usable predictions
        }
        
        return report


def create_compatibility_mapper() -> FeatureCompatibilityMapper:
    """Factory function to create a feature compatibility mapper."""
    return FeatureCompatibilityMapper()


# Convenience function for quick testing
def test_feature_mapping(df: pd.DataFrame, position: str) -> pd.DataFrame:
    """
    Test feature mapping for a position.
    
    Args:
        df: Input DataFrame with current features
        position: Position to test
        
    Returns:
        Mapped DataFrame
    """
    mapper = create_compatibility_mapper()
    return mapper.map_features_for_position(df, position)


if __name__ == "__main__":
    # Quick test if run directly
    print("🔧 Feature Compatibility Mapper")
    print("=" * 50)
    
    # Create sample data for testing
    sample_data = pd.DataFrame({
        'age': [25, 27, 24],
        'games': [16, 14, 12],
        'carries': [200, 150, 100],
        'rushing_yards': [1000, 800, 500],
        'rushing_tds': [8, 6, 3],
        'targets': [50, 40, 30],
        'receptions': [40, 35, 25],
        'receiving_yards': [400, 300, 200],
        'receiving_tds': [2, 3, 1]
    })
    
    mapper = create_compatibility_mapper()
    
    # Test RB mapping
    print("\n🏃 Testing RB Feature Mapping:")
    rb_mapped = mapper.map_features_for_position(sample_data, 'RB')
    print(f"Mapped shape: {rb_mapped.shape}")
    print(f"Mapped columns: {list(rb_mapped.columns)}")
    
    # Test validation
    validation = mapper.validate_mapped_features(rb_mapped, 'RB')
    print(f"Validation passed: {validation['validation_passed']}")
    
    print("\n✅ Feature mapping test complete!")