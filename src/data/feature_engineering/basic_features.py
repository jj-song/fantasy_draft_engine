"""
Basic feature engineering for all player positions.
This serves as a fallback for when position-specific feature engineering isn't available.
"""

import pandas as pd
import numpy as np
from typing import List, Optional


class BasicFeatureEngineering:
    """
    Provides basic feature engineering functionality applicable to all positions.
    """
    
    def __init__(self):
        """Initialize the BasicFeatureEngineering class."""
        self.numeric_features = []
        self.categorical_features = ['team', 'position']
    
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply basic feature engineering transformations to the input data.
        
        Args:
            df: DataFrame with player data
            
        Returns:
            DataFrame with engineered features
        """
        # Create a copy to avoid modifying the original dataframe
        result = df.copy()
        
        # Identify numeric features
        self.numeric_features = [col for col in result.columns 
                               if col not in self.categorical_features 
                               and pd.api.types.is_numeric_dtype(result[col])
                               and col not in ['player_id', 'season', 'fantasy_points', 'fantasy_points_per_game']]
        
        # Fill missing values
        result = self._fill_missing_values(result)
        
        # Apply basic per-game transformations
        result = self._add_per_game_stats(result)
        
        # Add efficiency metrics
        result = self._add_efficiency_metrics(result)
        
        # Create interaction features if there are enough samples
        if len(result) > 20:
            result = self._add_interaction_features(result)
        
        return result
    
    def _fill_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fill missing values in the dataframe."""
        result = df.copy()
        
        # Fill numeric missing values with 0
        for col in self.numeric_features:
            if col in result.columns:
                result[col] = result[col].fillna(0)
        
        # Fill categorical missing values with 'Unknown'
        for col in self.categorical_features:
            if col in result.columns:
                result[col] = result[col].fillna('Unknown')
        
        return result
    
    def _add_per_game_stats(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add per-game statistics for relevant features."""
        result = df.copy()
        
        if 'games_played' in result.columns:
            # Ensure games_played is at least 1 to avoid division by zero
            result['games_played'] = result['games_played'].clip(lower=1)
            
            # Create per-game features for numeric statistics
            for col in self.numeric_features:
                if col in result.columns and col != 'games_played' and col != 'age' and col != 'experience':
                    # Only create per_game for raw counting stats
                    if not col.endswith('_per_game') and not col.endswith('_pct'):
                        result[f'{col}_per_game'] = result[col] / result['games_played']
        
        return result
    
    def _add_efficiency_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add efficiency metrics where applicable."""
        result = df.copy()
        
        # Add completion percentage if passing stats are present
        if 'passing_attempts' in result.columns and 'passing_completions' in result.columns:
            # Avoid division by zero
            mask = result['passing_attempts'] > 0
            result.loc[mask, 'completion_pct'] = result.loc[mask, 'passing_completions'] / result.loc[mask, 'passing_attempts']
            result['completion_pct'] = result['completion_pct'].fillna(0)
        
        # Add yards per attempt if attempts are present
        attempt_yardage_pairs = [
            ('passing_attempts', 'passing_yards', 'yards_per_attempt'),
            ('rushing_attempts', 'rushing_yards', 'yards_per_rush'),
            ('targets', 'receiving_yards', 'yards_per_target'),
            ('receptions', 'receiving_yards', 'yards_per_reception'),
            ('field_goal_attempts', 'field_goals_made', 'field_goal_pct')
        ]
        
        for attempts_col, yards_col, result_col in attempt_yardage_pairs:
            if attempts_col in result.columns and yards_col in result.columns:
                # Avoid division by zero
                mask = result[attempts_col] > 0
                result.loc[mask, result_col] = result.loc[mask, yards_col] / result.loc[mask, attempts_col]
                result[result_col] = result[result_col].fillna(0)
        
        # Add touchdown rates
        if 'passing_attempts' in result.columns and 'passing_touchdowns' in result.columns:
            mask = result['passing_attempts'] > 0
            result.loc[mask, 'passing_td_rate'] = result.loc[mask, 'passing_touchdowns'] / result.loc[mask, 'passing_attempts']
            result['passing_td_rate'] = result['passing_td_rate'].fillna(0)
            
        if 'rushing_attempts' in result.columns and 'rushing_touchdowns' in result.columns:
            mask = result['rushing_attempts'] > 0
            result.loc[mask, 'rushing_td_rate'] = result.loc[mask, 'rushing_touchdowns'] / result.loc[mask, 'rushing_attempts']
            result['rushing_td_rate'] = result['rushing_td_rate'].fillna(0)
            
        if 'targets' in result.columns and 'receiving_touchdowns' in result.columns:
            mask = result['targets'] > 0
            result.loc[mask, 'receiving_td_rate'] = result.loc[mask, 'receiving_touchdowns'] / result.loc[mask, 'targets']
            result['receiving_td_rate'] = result['receiving_td_rate'].fillna(0)
        
        return result
    
    def _add_interaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add interaction features between important numeric variables."""
        result = df.copy()
        
        # Identify the most important features (exclude derived features)
        core_features = [f for f in self.numeric_features if not (f.endswith('_per_game') or f.endswith('_pct') or f.endswith('_rate'))]
        
        # Limit to a reasonable number to avoid combinatorial explosion
        core_features = core_features[:5] if len(core_features) > 5 else core_features
        
        # Create interaction features
        for i, feat1 in enumerate(core_features):
            if feat1 not in result.columns:
                continue
                
            for feat2 in core_features[i+1:]:
                if feat2 not in result.columns:
                    continue
                    
                # Multiply features
                result[f'{feat1}_x_{feat2}'] = result[feat1] * result[feat2]
                
                # Calculate ratios if meaningful (avoid near-zero denominators)
                if (result[feat2].abs() > 1).sum() > 0.5 * len(result):
                    result[f'{feat1}_div_{feat2}'] = result[feat1] / result[feat2].clip(lower=1)
                if (result[feat1].abs() > 1).sum() > 0.5 * len(result):
                    result[f'{feat2}_div_{feat1}'] = result[feat2] / result[feat1].clip(lower=1)
        
        return result
