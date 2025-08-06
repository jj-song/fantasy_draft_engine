"""
QB Feature Engineering - Refactored Version

This module contains the QBFeatureEngineer class that inherits from BaseFeatureEngineer
and implements QB-specific feature engineering using centralized utilities.

This replaces the legacy qb_features.py with a cleaner, more maintainable architecture.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union

from ..core.base_feature_engineer import BaseFeatureEngineer
from ..core.column_mapper import ColumnMapper
from ..core.feature_utils import FeatureCalculator


class QBFeatureEngineer(BaseFeatureEngineer):
    """
    Feature engineer for quarterback (QB) position.
    
    Inherits from BaseFeatureEngineer to provide standardized feature engineering
    with QB-specific calculations and efficiency metrics.
    """
    
    def __init__(self):
        """Initialize QB feature engineer with position-specific settings."""
        super().__init__(position='QB')
        self.column_mapper = ColumnMapper()
        self.feature_calculator = FeatureCalculator()
    
    def validate_data(self, df: pd.DataFrame) -> bool:
        """
        Validate that DataFrame contains required QB data.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            bool: True if data is valid for QB feature engineering
        """
        if df.empty:
            self.logger.warning("Empty DataFrame provided for QB feature engineering")
            return False
            
        # Check for QB position data
        if 'position' not in df.columns:
            self.logger.error("Missing 'position' column in DataFrame")
            return False
            
        qb_data = df[df['position'] == 'QB']
        if qb_data.empty:
            self.logger.warning("No QB data found in DataFrame")
            return False
            
        # Check for at least one passing stat column
        passing_cols = self.column_mapper.get_column_mapping(df, ['passing'])
        if not any(passing_cols.values()):
            self.logger.warning("No passing statistics columns found for QB feature engineering")
            
        return True
    
    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate QB-specific features from player data.
        
        Args:
            df: DataFrame containing QB player data
            
        Returns:
            DataFrame with QB-specific features added
        """
        if not self.validate_data(df):
            return df.copy()
        
        # Filter to QB data only
        df_qb = df[df['position'] == 'QB'].copy()
        
        if df_qb.empty:
            return df_qb
        
        self.logger.info(f"Engineering features for {len(df_qb)} QB records")
        
        try:
            # Calculate efficiency metrics
            df_qb = self._calculate_efficiency_metrics(df_qb)
            
            # Calculate per-game averages
            df_qb = self._calculate_per_game_metrics(df_qb)
            
            # Calculate advanced metrics
            df_qb = self._calculate_advanced_metrics(df_qb)
            
            self.logger.info("QB feature engineering completed successfully")
            return df_qb
            
        except Exception as e:
            self.logger.error(f"Error in QB feature engineering: {str(e)}")
            raise
    
    def _calculate_efficiency_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate QB efficiency metrics using centralized column mapping.
        
        Args:
            df: DataFrame containing QB player data
            
        Returns:
            DataFrame with QB efficiency metrics added
        """
        df = df.copy()
        
        # Get standardized column mappings for passing stats
        passing_cols = self.column_mapper.get_column_mapping(df, ['passing'])
        
        attempts_col = passing_cols['passing_attempts']
        if not attempts_col:
            self.logger.warning("Missing passing attempts column for QB efficiency calculation")
            # Add default metrics and return
            for metric in ['completion_percentage', 'yards_per_attempt', 'touchdown_percentage', 
                          'interception_percentage', 'passer_rating']:
                df[metric] = 0.0
            return df
        
        # Completion percentage
        completions_col = passing_cols['passing_completions']
        if completions_col:
            df['completion_percentage'] = np.where(
                df[attempts_col] > 0,
                (df[completions_col] / df[attempts_col]) * 100,
                0.0
            )
        else:
            df['completion_percentage'] = 0.0
        
        # Yards per attempt
        yards_col = passing_cols['passing_yards']
        if yards_col:
            df['yards_per_attempt'] = np.where(
                df[attempts_col] > 0,
                df[yards_col] / df[attempts_col],
                0.0
            )
        else:
            df['yards_per_attempt'] = 0.0
        
        # Touchdown percentage
        tds_col = passing_cols['passing_touchdowns']
        if tds_col:
            df['touchdown_percentage'] = np.where(
                df[attempts_col] > 0,
                (df[tds_col] / df[attempts_col]) * 100,
                0.0
            )
        else:
            df['touchdown_percentage'] = 0.0
        
        # Interception percentage
        ints_col = passing_cols['passing_interceptions']
        if ints_col:
            df['interception_percentage'] = np.where(
                df[attempts_col] > 0,
                (df[ints_col] / df[attempts_col]) * 100,
                0.0
            )
        else:
            df['interception_percentage'] = 0.0
        
        # Passer rating (NFL formula)
        df['passer_rating'] = self._calculate_passer_rating(df)
        
        return df
    
    def _calculate_per_game_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate QB per-game metrics using centralized utilities.
        
        Args:
            df: DataFrame containing QB player data
            
        Returns:
            DataFrame with QB per-game metrics added
        """
        df = df.copy()
        
        # Get games played column using centralized mapper
        general_cols = self.column_mapper.get_column_mapping(df, ['general'])
        games_col = general_cols.get('games')  # The mapper uses 'games' as the key
        if not games_col:
            self.logger.warning("No games column found for per-game calculations")
            return df
        
        # Get column mappings
        passing_cols = self.column_mapper.get_column_mapping(df, ['passing'])
        rushing_cols = self.column_mapper.get_column_mapping(df, ['rushing'])
        
        # Calculate per-game passing stats
        passing_stats = {
            'passing_yards_per_game': passing_cols['passing_yards'],
            'passing_tds_per_game': passing_cols['passing_touchdowns'],
            'passing_completions_per_game': passing_cols['passing_completions'],
            'passing_attempts_per_game': passing_cols['passing_attempts'],
            'passing_interceptions_per_game': passing_cols['passing_interceptions']
        }
        
        # Use the feature calculator's per-game stats method
        games_played = df[games_col].replace(0, 1)  # Avoid division by zero
        
        for stat_name, col_name in passing_stats.items():
            if col_name and col_name in df.columns:
                df[stat_name] = df[col_name] / games_played
            else:
                df[stat_name] = 0.0
        
        # Calculate per-game rushing stats (QBs can rush too)
        rushing_stats = {
            'rushing_yards_per_game': rushing_cols['rushing_yards'],
            'rushing_tds_per_game': rushing_cols['rushing_touchdowns'],
            'rushing_attempts_per_game': rushing_cols['rushing_attempts']
        }
        
        for stat_name, col_name in rushing_stats.items():
            if col_name and col_name in df.columns:
                df[stat_name] = df[col_name] / games_played
            else:
                df[stat_name] = 0.0
        
        return df
    
    def _calculate_advanced_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate advanced QB metrics and efficiency ratios.
        
        Args:
            df: DataFrame containing QB player data
            
        Returns:
            DataFrame with advanced QB metrics added
        """
        df = df.copy()
        
        # QB efficiency rating (simplified)
        passing_attempts = df.get('passing_attempts', 1)
        passing_attempts = np.where(passing_attempts == 0, 1, passing_attempts)  # Avoid division by zero
        
        df['qb_efficiency'] = (
            df.get('passing_yards', 0) + 
            (df.get('passing_touchdowns', 0) * 20) - 
            (df.get('passing_interceptions', 0) * 25)
        ) / passing_attempts
        
        # Air yards efficiency (if available)
        if 'air_yards' in df.columns:
            df['air_yards_efficiency'] = np.where(
                df['air_yards'] > 0,
                df['passing_yards'] / df['air_yards'],
                0.0
            )
        else:
            df['air_yards_efficiency'] = 0.0
        
        # Rushing efficiency for mobile QBs
        rushing_cols = self.column_mapper.get_column_mapping(df, ['rushing'])
        if rushing_cols['rushing_attempts'] and rushing_cols['rushing_yards']:
            rush_attempts_col = rushing_cols['rushing_attempts']
            rush_yards_col = rushing_cols['rushing_yards']
            if rush_attempts_col in df.columns and rush_yards_col in df.columns:
                df['rushing_yards_per_carry'] = np.where(
                    df[rush_attempts_col] > 0,
                    df[rush_yards_col] / df[rush_attempts_col],
                    0.0
                )
            else:
                df['rushing_yards_per_carry'] = 0.0
        else:
            df['rushing_yards_per_carry'] = 0.0
        
        return df
    
    def _calculate_passer_rating(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate NFL passer rating using the official formula.
        
        Args:
            df: DataFrame containing QB player data with efficiency metrics
            
        Returns:
            Series with passer rating values
        """
        # Initialize with zeros
        passer_rating = pd.Series(0.0, index=df.index)
        
        # Only calculate for QBs with attempts
        if 'passing_attempts' not in df.columns:
            return passer_rating
            
        mask = df['passing_attempts'] > 0
        
        if not mask.any():
            return passer_rating
        
        try:
            # NFL passer rating formula components (0-2.375 each)
            a = np.clip((df.loc[mask, 'completion_percentage'] - 30) * 0.05, 0, 2.375)
            b = np.clip((df.loc[mask, 'yards_per_attempt'] - 3) * 0.25, 0, 2.375)
            c = np.clip(df.loc[mask, 'touchdown_percentage'] * 0.2, 0, 2.375)
            d = np.clip(2.375 - (df.loc[mask, 'interception_percentage'] * 0.25), 0, 2.375)
            
            # Final calculation: ((a + b + c + d) / 6) * 100
            passer_rating.loc[mask] = ((a + b + c + d) / 6) * 100
            
        except Exception as e:
            self.logger.warning(f"Error calculating passer rating: {str(e)}")
            passer_rating.loc[mask] = 0.0
        
        return passer_rating
    
    def get_required_columns(self) -> List[str]:
        """
        Get list of columns required for QB feature engineering.
        
        Returns:
            List of column names that must be present in input data
        """
        return [
            'position',  # Required to filter to QB data
            'games_played'  # Required for per-game calculations
        ]
    
    def get_generated_features(self) -> List[str]:
        """
        Get list of features that will be generated by this engineer.
        
        Returns:
            List of feature names that will be added to the DataFrame
        """
        return [
            # Efficiency metrics
            'completion_percentage',
            'yards_per_attempt',
            'touchdown_percentage',
            'interception_percentage',
            'passer_rating',
            
            # Per-game passing stats
            'passing_yards_per_game',
            'passing_tds_per_game',
            'passing_completions_per_game',
            'passing_attempts_per_game',
            'passing_interceptions_per_game',
            
            # Per-game rushing stats  
            'rushing_yards_per_game',
            'rushing_tds_per_game',
            'rushing_attempts_per_game',
            
            # Advanced metrics
            'qb_efficiency',
            'air_yards_efficiency',
            'rushing_yards_per_carry'
        ]
    
    def get_feature_names(self) -> List[str]:
        """
        Get list of feature names that this engineer creates.
        
        This method delegates to get_generated_features for consistency.
        
        Returns:
            List of feature column names
        """
        return self.get_generated_features()


# Legacy compatibility function
def engineer_qb_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Legacy compatibility function for QB feature engineering.
    
    This function maintains backward compatibility with existing code
    while using the new QBFeatureEngineer class internally.
    
    Args:
        df: DataFrame containing QB player data
        
    Returns:
        DataFrame with QB-specific features added
    """
    engineer = QBFeatureEngineer()
    return engineer.engineer_features(df)