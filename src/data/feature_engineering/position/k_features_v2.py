"""
K Feature Engineering - Refactored Version

This module contains the KFeatureEngineer class that inherits from BaseFeatureEngineer
and implements K-specific feature engineering using centralized utilities.

This replaces the legacy k_features.py with a cleaner, more maintainable architecture.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union

from src.core.base_feature_engineer import BaseFeatureEngineer
from src.core.column_mapper import ColumnMapper
from src.core.feature_utils import FeatureCalculator


class KFeatureEngineer(BaseFeatureEngineer):
    """
    Feature engineer for kicker (K) position.
    
    Inherits from BaseFeatureEngineer to provide standardized feature engineering
    with K-specific calculations and efficiency metrics.
    """
    
    def __init__(self):
        """Initialize K feature engineer with position-specific settings."""
        super().__init__(position='K')
        self.column_mapper = ColumnMapper()
        self.feature_calculator = FeatureCalculator()
    
    def validate_data(self, df: pd.DataFrame) -> bool:
        """
        Validate that DataFrame contains required K data.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            bool: True if data is valid for K feature engineering
        """
        if df.empty:
            self.logger.warning("Empty DataFrame provided for K feature engineering")
            return False
            
        # Check for K position data
        if 'position' not in df.columns:
            self.logger.error("Missing 'position' column in DataFrame")
            return False
            
        k_players = df[df['position'] == 'K']
        if k_players.empty:
            self.logger.warning("No K players found in DataFrame")
            return False
            
        self.logger.info(f"Found {len(k_players)} K players for feature engineering")
        return True
    
    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Engineer K-specific features from player data.
        
        Args:
            df: DataFrame containing player data for this position
            
        Returns:
            DataFrame with engineered features added
        """
        self.logger.info(f"Engineering features for {len(df)} K records")
        
        if not self.validate_data(df):
            return df
        
        # Filter to K players only
        k_df = df[df['position'] == 'K'].copy()
        
        if k_df.empty:
            self.logger.warning("No K players to process")
            return df
        
        try:
            # Step 1: Calculate efficiency metrics
            k_df = self._calculate_efficiency_metrics(k_df)
            
            # Step 2: Calculate per-game metrics
            k_df = self._calculate_per_game_metrics(k_df)
            
            # Step 3: Calculate advanced K metrics
            k_df = self._calculate_advanced_metrics(k_df)
            
            # Step 4: Calculate reliability scores
            k_df = self._calculate_reliability_scores(k_df)
            
            # Replace K records in original dataframe, preserving new columns
            result_df = df.copy()
            k_mask = result_df['position'] == 'K'
            
            # Add new columns from k_df to result_df
            for col in k_df.columns:
                if col not in result_df.columns:
                    result_df[col] = np.nan
            
            # Now update the K rows with all the features
            result_df.loc[k_mask] = k_df
            
            self.logger.info(f"K feature engineering completed successfully")
            return result_df
            
        except Exception as e:
            self.logger.error(f"Error in K feature engineering: {str(e)}")
            return df
    
    def _get_column_name(self, df: pd.DataFrame, possible_names: List[str]) -> Optional[str]:
        """Find the first matching column name from a list of possibilities."""
        for name in possible_names:
            if name in df.columns:
                return name
        return None
    
    def _calculate_efficiency_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate K efficiency metrics like FG percentage."""
        result = df.copy()
        
        # Map column names
        fg_attempts = self._get_column_name(result, ['fg_attempts', 'field_goal_attempts', 'fga'])
        fg_made = self._get_column_name(result, ['fg_made', 'field_goals_made', 'fgm'])
        xp_attempts = self._get_column_name(result, ['xp_attempts', 'extra_point_attempts', 'xpa'])
        xp_made = self._get_column_name(result, ['xp_made', 'extra_points_made', 'xpm'])
        
        # Field goal percentage
        if fg_attempts and fg_made:
            result['fg_percentage'] = np.where(
                result[fg_attempts] > 0,
                (result[fg_made] / result[fg_attempts]) * 100,
                0
            )
        else:
            result['fg_percentage'] = 0
        
        # Extra point percentage
        if xp_attempts and xp_made:
            result['xp_percentage'] = np.where(
                result[xp_attempts] > 0,
                (result[xp_made] / result[xp_attempts]) * 100,
                0
            )
        else:
            result['xp_percentage'] = 0
        
        # Overall kicking percentage (combined FG + XP)
        if fg_attempts and fg_made and xp_attempts and xp_made:
            total_attempts = result[fg_attempts] + result[xp_attempts]
            total_made = result[fg_made] + result[xp_made]
            result['overall_kicking_percentage'] = np.where(
                total_attempts > 0,
                (total_made / total_attempts) * 100,
                0
            )
        else:
            result['overall_kicking_percentage'] = 0
        
        return result
    
    def _calculate_per_game_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate K per-game metrics."""
        result = df.copy()
        
        # Get games column
        games_col = self._get_column_name(result, ['games', 'games_played', 'g'])
        if not games_col:
            self.logger.warning("No games column found for per-game calculations")
            return result
        
        # Avoid division by zero
        games = result[games_col].replace(0, 1)
        
        # Map kicking stat columns
        fg_attempts = self._get_column_name(result, ['fg_attempts', 'field_goal_attempts', 'fga'])
        fg_made = self._get_column_name(result, ['fg_made', 'field_goals_made', 'fgm'])
        xp_attempts = self._get_column_name(result, ['xp_attempts', 'extra_point_attempts', 'xpa'])
        xp_made = self._get_column_name(result, ['xp_made', 'extra_points_made', 'xpm'])
        
        # Per-game stats
        if fg_attempts:
            result['fg_attempts_per_game'] = result[fg_attempts] / games
        if fg_made:
            result['fg_made_per_game'] = result[fg_made] / games
        if xp_attempts:
            result['xp_attempts_per_game'] = result[xp_attempts] / games
        if xp_made:
            result['xp_made_per_game'] = result[xp_made] / games
        
        # Fantasy points per game (standard scoring: 3 for FG, 1 for XP)
        if fg_made and xp_made:
            fantasy_points = result[fg_made] * 3 + result[xp_made]
            result['k_fantasy_points_per_game'] = fantasy_points / games
        
        return result
    
    def _calculate_advanced_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate advanced K metrics."""
        result = df.copy()
        
        # Map columns
        fg_attempts = self._get_column_name(result, ['fg_attempts', 'field_goal_attempts', 'fga'])
        fg_made = self._get_column_name(result, ['fg_made', 'field_goals_made', 'fgm'])
        
        if fg_attempts and fg_made:
            # High-pressure accuracy (attempts > 2 per game indicates high-volume)
            games_col = self._get_column_name(result, ['games', 'games_played', 'g'])
            if games_col:
                attempts_per_game = result[fg_attempts] / result[games_col].replace(0, 1)
                result['high_volume_kicker'] = (attempts_per_game >= 2.0).astype(int)
                
                # Volume-adjusted accuracy
                result['volume_adjusted_accuracy'] = result['fg_percentage'] * np.log1p(attempts_per_game)
        
        # Distance-based metrics (if available)
        distance_ranges = ['0_19', '20_29', '30_39', '40_49', '50_plus']
        for distance in distance_ranges:
            attempts_col = f'fg_attempts_{distance}'
            made_col = f'fg_made_{distance}'
            
            if attempts_col in result.columns and made_col in result.columns:
                result[f'fg_percentage_{distance}'] = np.where(
                    result[attempts_col] > 0,
                    (result[made_col] / result[attempts_col]) * 100,
                    0
                )
        
        # Long-range specialist indicator
        if 'fg_attempts_50_plus' in result.columns and 'fg_made_50_plus' in result.columns:
            result['long_range_specialist'] = (
                (result['fg_attempts_50_plus'] >= 3) & 
                (result['fg_percentage_50_plus'] >= 60)
            ).astype(int)
        
        return result
    
    def _calculate_reliability_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate K reliability and consistency scores."""
        result = df.copy()
        
        # Clutch performance (combination of accuracy and volume)
        if 'fg_percentage' in result.columns and 'fg_attempts_per_game' in result.columns:
            result['clutch_score'] = (
                result['fg_percentage'] / 100 * 
                np.minimum(result['fg_attempts_per_game'] / 2.0, 1.0)
            )
        
        # Consistency score (penalize very low or high percentages - indicates small sample)
        if 'fg_percentage' in result.columns:
            # Score peaks around 85% accuracy with enough volume
            accuracy_factor = 1 - abs(result['fg_percentage'] - 85) / 100
            result['consistency_score'] = np.maximum(accuracy_factor, 0.1)
        
        # Weather reliability (placeholder - would need weather data)
        # For now, use dome/outdoor stadium data if available
        result['weather_reliability'] = 0.8  # Default neutral value
        
        return result
    
    def get_required_columns(self) -> List[str]:
        """
        Get list of columns required for K feature engineering.
        
        Returns:
            List of column names that must be present in input data
        """
        return [
            'position',
            'games', 'games_played',  # Alternative names
            'fg_attempts', 'field_goal_attempts', 'fga',  # Alternative names
            'fg_made', 'field_goals_made', 'fgm',  # Alternative names  
            'xp_attempts', 'extra_point_attempts', 'xpa',  # Alternative names
            'xp_made', 'extra_points_made', 'xpm'  # Alternative names
        ]
    
    def get_generated_features(self) -> List[str]:
        """
        Get list of features that will be generated by this engineer.
        
        Returns:
            List of feature names that will be added to the DataFrame
        """
        base_features = [
            'fg_percentage',
            'xp_percentage', 
            'overall_kicking_percentage',
            'fg_attempts_per_game',
            'fg_made_per_game',
            'xp_attempts_per_game',
            'xp_made_per_game',
            'k_fantasy_points_per_game',
            'high_volume_kicker',
            'volume_adjusted_accuracy',
            'clutch_score',
            'consistency_score',
            'weather_reliability'
        ]
        
        # Add distance-based features if data is available  
        distance_features = []
        for distance in ['0_19', '20_29', '30_39', '40_49', '50_plus']:
            distance_features.extend([
                f'fg_percentage_{distance}',
            ])
        
        return base_features + distance_features + ['long_range_specialist']