"""
Feature engineering for quarterback (QB) position.

This module contains functions for generating QB-specific features from raw player data.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union


def engineer_qb_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate QB-specific features from player data.
    
    Args:
        df: DataFrame containing QB player data
        
    Returns:
        DataFrame with QB-specific features added
    """
    # Make a copy to avoid modifying the original dataframe
    df_qb = df.copy()
    
    # Only keep QBs
    df_qb = df_qb[df_qb['position'] == 'QB']
    
    if df_qb.empty:
        return df_qb
    
    # Calculate efficiency metrics
    df_qb = calculate_qb_efficiency_metrics(df_qb)
    
    # Calculate per-game averages
    df_qb = calculate_qb_per_game_metrics(df_qb)
    
    return df_qb


def calculate_qb_efficiency_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate QB efficiency metrics.
    
    Args:
        df: DataFrame containing QB player data
        
    Returns:
        DataFrame with QB efficiency metrics added
    """
    # Make a copy to avoid modifying the original dataframe
    df = df.copy()
    
    # Completion percentage
    df['completion_percentage'] = np.where(
        df['passing_attempts'] > 0,
        df['passing_completions'] / df['passing_attempts'] * 100,
        0
    )
    
    # Yards per attempt
    df['yards_per_attempt'] = np.where(
        df['passing_attempts'] > 0,
        df['passing_yards'] / df['passing_attempts'],
        0
    )
    
    # Touchdown percentage
    df['touchdown_percentage'] = np.where(
        df['passing_attempts'] > 0,
        df['passing_tds'] / df['passing_attempts'] * 100,
        0
    )
    
    # Interception percentage
    df['interception_percentage'] = np.where(
        df['passing_attempts'] > 0,
        df['passing_interceptions'] / df['passing_attempts'] * 100,
        0
    )
    
    # Passer rating (simplified formula)
    df['passer_rating'] = calculate_passer_rating(df)
    
    return df


def calculate_qb_per_game_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate QB per-game metrics.
    
    Args:
        df: DataFrame containing QB player data
        
    Returns:
        DataFrame with QB per-game metrics added
    """
    # Make a copy to avoid modifying the original dataframe
    df = df.copy()
    
    # Avoid division by zero
    games_played = df['games_played'].replace(0, 1)
    
    # Per-game passing stats
    df['passing_yards_per_game'] = df['passing_yards'] / games_played
    df['passing_tds_per_game'] = df['passing_tds'] / games_played
    df['passing_completions_per_game'] = df['passing_completions'] / games_played
    df['passing_attempts_per_game'] = df['passing_attempts'] / games_played
    df['passing_interceptions_per_game'] = df['passing_interceptions'] / games_played
    
    # Per-game rushing stats (QBs can rush too)
    df['rushing_yards_per_game'] = df['rushing_yards'] / games_played
    df['rushing_tds_per_game'] = df['rushing_tds'] / games_played
    df['rushing_attempts_per_game'] = df['rushing_attempts'] / games_played
    
    return df


def calculate_passer_rating(df: pd.DataFrame) -> pd.Series:
    """
    Calculate NFL passer rating.
    
    Args:
        df: DataFrame containing QB player data
        
    Returns:
        Series with passer rating values
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
