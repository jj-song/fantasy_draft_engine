"""
Value Over Replacement (VOR) Calculator

Calculates VOR scores for cross-position player comparisons.
"""

import pandas as pd
import numpy as np
from typing import Dict, List
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

import config


class VORCalculator:
    """Calculate Value Over Replacement for fantasy football players."""
    
    def __init__(self, replacement_ranks: Dict[str, int] = None):
        """
        Initialize VOR calculator.
        
        Args:
            replacement_ranks: Dictionary mapping positions to replacement rank thresholds
        """
        self.replacement_ranks = replacement_ranks or config.REPLACEMENT_RANKS
    
    def calculate_replacement_values(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate replacement level fantasy points for each position.
        
        Args:
            df: DataFrame with player projections
            
        Returns:
            Dictionary mapping positions to replacement level points
        """
        replacement_values = {}
        
        for position in df['position'].unique():
            pos_df = df[df['position'] == position].copy()
            
            if len(pos_df) == 0:
                continue
                
            # Sort by predicted points descending
            pos_df = pos_df.sort_values('predicted_points', ascending=False)
            
            # Get replacement rank for this position
            replacement_rank = self.replacement_ranks.get(position, len(pos_df))
            replacement_rank = min(replacement_rank, len(pos_df))
            
            if replacement_rank > 0:
                # Use the replacement_rank-th player's points as replacement level
                replacement_values[position] = pos_df.iloc[replacement_rank - 1]['predicted_points']
            else:
                # Fallback to minimum points
                replacement_values[position] = pos_df['predicted_points'].min()
        
        return replacement_values
    
    def calculate_vor_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate VOR scores for all players.
        
        Args:
            df: DataFrame with player projections
            
        Returns:
            DataFrame with VOR scores added
        """
        df = df.copy()
        
        # Get replacement values
        replacement_values = self.calculate_replacement_values(df)
        
        # Calculate VOR for each player
        df['vor'] = df.apply(
            lambda row: row['predicted_points'] - replacement_values.get(row['position'], 0),
            axis=1
        )
        
        return df
    
    def get_replacement_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Get a summary of replacement levels by position.
        
        Args:
            df: DataFrame with player projections
            
        Returns:
            DataFrame summarizing replacement levels
        """
        replacement_values = self.calculate_replacement_values(df)
        
        summary_data = []
        for position, replacement_points in replacement_values.items():
            replacement_rank = self.replacement_ranks.get(position, 0)
            
            summary_data.append({
                'position': position,
                'replacement_rank': replacement_rank,
                'replacement_points': replacement_points,
                'total_players': len(df[df['position'] == position])
            })
        
        return pd.DataFrame(summary_data)
    
    def validate_vor_calculation(self, df: pd.DataFrame) -> Dict[str, bool]:
        """
        Validate that VOR calculations make sense.
        
        Args:
            df: DataFrame with VOR scores
            
        Returns:
            Dictionary of validation results
        """
        validations = {}
        
        # Check that VOR scores exist
        validations['vor_column_exists'] = 'vor' in df.columns
        
        if 'vor' in df.columns:
            # Check that top players have positive VOR
            top_players = df.nlargest(20, 'vor')
            validations['top_players_positive_vor'] = (top_players['vor'] > 0).all()
            
            # Check that replacement level players have VOR near 0
            for position in df['position'].unique():
                pos_df = df[df['position'] == position].copy()
                if len(pos_df) == 0:
                    continue
                    
                replacement_rank = self.replacement_ranks.get(position, len(pos_df))
                if replacement_rank <= len(pos_df):
                    pos_df_sorted = pos_df.sort_values('vor', ascending=False)
                    replacement_vor = pos_df_sorted.iloc[replacement_rank - 1]['vor']
                    validations[f'{position}_replacement_vor_near_zero'] = abs(replacement_vor) < 0.1
        
        return validations