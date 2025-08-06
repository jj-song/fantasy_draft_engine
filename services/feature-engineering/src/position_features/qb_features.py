"""
Feature engineering for quarterback (QB) position.

This module contains functions for generating QB-specific features from raw player data.

MIGRATION NOTICE: This module has been refactored to use the new QBFeatureEngineer class
from qb_features_v2.py. The original functions are preserved for backward compatibility
but now delegate to the new implementation that eliminates code duplication and uses
centralized utilities.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union

# Import the new implementation
try:
    from .qb_features_v2 import QBFeatureEngineer, engineer_qb_features as new_engineer_qb_features
    _has_new_implementation = True
except ImportError:
    _has_new_implementation = False
    

def engineer_qb_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate QB-specific features from player data.
    
    This function now delegates to the new QBFeatureEngineer class while maintaining
    backward compatibility with existing code.
    
    Args:
        df: DataFrame containing QB player data
        
    Returns:
        DataFrame with QB-specific features added
    """
    if _has_new_implementation:
        # Use the new refactored implementation
        return new_engineer_qb_features(df)
    else:
        # Fallback to legacy implementation if new one is not available
        return _legacy_engineer_qb_features(df)


def _legacy_engineer_qb_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Legacy QB feature engineering implementation.
    
    This is the original implementation preserved as a fallback.
    """
    # Make a copy to avoid modifying the original dataframe
    df_qb = df.copy()
    
    # Only keep QBs
    df_qb = df_qb[df_qb['position'] == 'QB']
    
    if df_qb.empty:
        return df_qb
    
    # Calculate efficiency metrics
    df_qb = _legacy_calculate_qb_efficiency_metrics(df_qb)
    
    # Calculate per-game averages
    df_qb = _legacy_calculate_qb_per_game_metrics(df_qb)
    
    return df_qb


def _legacy_get_qb_column_mapping(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """
    Legacy implementation: Get mapping of standard QB column names to actual column names.
    """
    available_cols = df.columns.tolist()
    mapping = {}
    
    # Passing attempts
    attempts_col = None
    for col in available_cols:
        if col.lower() in ['passing_attempts', 'attempts', 'att', 'pass_att']:
            attempts_col = col
            break
    mapping['passing_attempts'] = attempts_col
    
    # Passing completions
    completions_col = None
    for col in available_cols:
        if col.lower() in ['passing_completions', 'completions', 'comp', 'pass_comp']:
            completions_col = col
            break
    mapping['passing_completions'] = completions_col
    
    # Passing yards
    yards_col = None
    for col in available_cols:
        if col.lower() in ['passing_yards', 'pass_yards', 'yards', 'pass_yds']:
            yards_col = col
            break
    mapping['passing_yards'] = yards_col
    
    # Passing touchdowns
    tds_col = None
    for col in available_cols:
        if col.lower() in ['passing_touchdowns', 'passing_tds', 'pass_tds', 'pass_td']:
            tds_col = col
            break
    mapping['passing_touchdowns'] = tds_col
    
    # Passing interceptions
    ints_col = None
    for col in available_cols:
        if col.lower() in ['passing_interceptions', 'interceptions', 'ints', 'pass_int']:
            ints_col = col
            break
    mapping['passing_interceptions'] = ints_col
    
    return mapping


def _legacy_calculate_qb_efficiency_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Legacy implementation: Calculate QB efficiency metrics.
    """
    df = df.copy()
    
    # Get column mappings for QB stats
    col_mapping = _legacy_get_qb_column_mapping(df)
    
    # If we don't have the required columns, return empty metrics
    if not col_mapping['passing_attempts']:
        print(f"Warning: Missing passing attempts column for QB efficiency calculation")
        # Add empty metrics and return
        df['completion_percentage'] = 0
        df['yards_per_attempt'] = 0 
        df['touchdown_percentage'] = 0
        df['interception_percentage'] = 0
        df['passer_rating'] = 0
        return df
    
    # Use mapped column names
    attempts_col = col_mapping['passing_attempts']
    completions_col = col_mapping['passing_completions'] or 'completions'
    yards_col = col_mapping['passing_yards'] or 'passing_yards'
    tds_col = col_mapping['passing_touchdowns'] or 'passing_tds'
    ints_col = col_mapping['passing_interceptions'] or 'interceptions'
    
    # Completion percentage
    if completions_col in df.columns:
        df['completion_percentage'] = np.where(
            df[attempts_col] > 0,
            df[completions_col] / df[attempts_col] * 100,
            0
        )
    else:
        df['completion_percentage'] = 0
    
    # Yards per attempt
    if yards_col in df.columns:
        df['yards_per_attempt'] = np.where(
            df[attempts_col] > 0,
            df[yards_col] / df[attempts_col],
            0
        )
    else:
        df['yards_per_attempt'] = 0
    
    # Touchdown percentage
    if tds_col in df.columns:
        df['touchdown_percentage'] = np.where(
            df[attempts_col] > 0,
            df[tds_col] / df[attempts_col] * 100,
            0
        )
    else:
        df['touchdown_percentage'] = 0
    
    # Interception percentage
    if ints_col in df.columns:
        df['interception_percentage'] = np.where(
            df[attempts_col] > 0,
            df[ints_col] / df[attempts_col] * 100,
            0
        )
    else:
        df['interception_percentage'] = 0
    
    # Passer rating (simplified formula)
    df['passer_rating'] = _legacy_calculate_passer_rating(df)
    
    return df


def _legacy_calculate_qb_per_game_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Legacy implementation: Calculate QB per-game metrics.
    """
    df = df.copy()
    
    # Get column mappings
    col_mapping = _legacy_get_qb_column_mapping(df)
    
    # Find games played column
    games_col = None
    for col in df.columns:
        if col.lower() in ['games_played', 'games', 'g', 'gp']:
            games_col = col
            break
    
    if not games_col:
        print("Warning: No games column found for per-game calculations")
        return df
    
    # Avoid division by zero
    games_played = df[games_col].replace(0, 1)
    
    # Per-game passing stats using mapped columns
    if col_mapping['passing_yards']:
        df['passing_yards_per_game'] = df[col_mapping['passing_yards']] / games_played
    else:
        df['passing_yards_per_game'] = 0
        
    if col_mapping['passing_touchdowns']:
        df['passing_tds_per_game'] = df[col_mapping['passing_touchdowns']] / games_played
    else:
        df['passing_tds_per_game'] = 0
        
    if col_mapping['passing_completions']:
        df['passing_completions_per_game'] = df[col_mapping['passing_completions']] / games_played
    else:
        df['passing_completions_per_game'] = 0
        
    if col_mapping['passing_attempts']:
        df['passing_attempts_per_game'] = df[col_mapping['passing_attempts']] / games_played
    else:
        df['passing_attempts_per_game'] = 0
        
    if col_mapping['passing_interceptions']:
        df['passing_interceptions_per_game'] = df[col_mapping['passing_interceptions']] / games_played
    else:
        df['passing_interceptions_per_game'] = 0
    
    # Per-game rushing stats (QBs can rush too) - use similar mapping approach
    rushing_yards_col = None
    rushing_tds_col = None
    rushing_attempts_col = None
    
    for col in df.columns:
        if col.lower() in ['rushing_yards', 'rush_yards', 'rush_yds']:
            rushing_yards_col = col
        elif col.lower() in ['rushing_touchdowns', 'rushing_tds', 'rush_tds', 'rush_td']:
            rushing_tds_col = col
        elif col.lower() in ['rushing_attempts', 'carries', 'rush_att']:
            rushing_attempts_col = col
    
    df['rushing_yards_per_game'] = df[rushing_yards_col] / games_played if rushing_yards_col else 0
    df['rushing_tds_per_game'] = df[rushing_tds_col] / games_played if rushing_tds_col else 0
    df['rushing_attempts_per_game'] = df[rushing_attempts_col] / games_played if rushing_attempts_col else 0
    
    return df


def _legacy_calculate_passer_rating(df: pd.DataFrame) -> pd.Series:
    """
    Legacy implementation: Calculate NFL passer rating.
    """
    # Initialize with zeros
    passer_rating = pd.Series(0, index=df.index)
    
    # Only calculate for QBs with attempts
    mask = df['passing_attempts'] > 0
    
    if not mask.any():
        return passer_rating
    
    # NFL passer rating formula components
    a = np.clip((df.loc[mask, 'completion_percentage'] - 30) * 0.05, 0, 2.375)
    b = np.clip((df.loc[mask, 'yards_per_attempt'] - 3) * 0.25, 0, 2.375)
    c = np.clip(df.loc[mask, 'touchdown_percentage'] * 0.2, 0, 2.375)
    d = np.clip(2.375 - (df.loc[mask, 'interception_percentage'] * 0.25), 0, 2.375)
    
    # Final calculation
    passer_rating.loc[mask] = ((a + b + c + d) / 6) * 100
    
    return passer_rating


# Legacy function aliases for backward compatibility
def calculate_qb_efficiency_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Backward compatibility alias."""
    if _has_new_implementation:
        engineer = QBFeatureEngineer()
        return engineer._calculate_efficiency_metrics(df)
    else:
        return _legacy_calculate_qb_efficiency_metrics(df)


def calculate_qb_per_game_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Backward compatibility alias."""
    if _has_new_implementation:
        engineer = QBFeatureEngineer()
        return engineer._calculate_per_game_metrics(df)
    else:
        return _legacy_calculate_qb_per_game_metrics(df)


def calculate_passer_rating(df: pd.DataFrame) -> pd.Series:
    """Backward compatibility alias."""
    if _has_new_implementation:
        engineer = QBFeatureEngineer()
        return engineer._calculate_passer_rating(df)
    else:
        return _legacy_calculate_passer_rating(df)