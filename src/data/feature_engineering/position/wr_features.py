"""
Feature engineering for wide receiver (WR) position.

This module contains functions for generating WR-specific features from raw player data.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union


def engineer_wr_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate WR-specific features from player data.
    
    Args:
        df: DataFrame containing WR player data
        
    Returns:
        DataFrame with WR-specific features added
    """
    # Make a copy to avoid modifying the original dataframe
    df_wr = df.copy()
    
    # Only keep WRs
    df_wr = df_wr[df_wr['position'] == 'WR']
    
    if df_wr.empty:
        return df_wr
    
    # Calculate efficiency metrics
    df_wr = calculate_wr_efficiency_metrics(df_wr)
    
    # Calculate per-game averages
    df_wr = calculate_wr_per_game_metrics(df_wr)
    
    # Calculate usage metrics (requires team totals)
    df_wr = calculate_wr_usage_metrics(df_wr)
    
    return df_wr


def calculate_wr_efficiency_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate WR efficiency metrics.
    
    Args:
        df: DataFrame containing WR player data
        
    Returns:
        DataFrame with WR efficiency metrics added
    """
    # Make a copy to avoid modifying the original dataframe
    df = df.copy()
    
    # Catch rate
    df['catch_rate'] = np.where(
        df['targets'] > 0,
        df['receptions'] / df['targets'] * 100,
        0
    )
    
    # Yards per reception
    df['yards_per_reception'] = np.where(
        df['receptions'] > 0,
        df['receiving_yards'] / df['receptions'],
        0
    )
    
    # Yards per target
    df['yards_per_target'] = np.where(
        df['targets'] > 0,
        df['receiving_yards'] / df['targets'],
        0
    )
    
    # TD rate (per target)
    df['td_per_target'] = np.where(
        df['targets'] > 0,
        df['receiving_tds'] / df['targets'] * 100,
        0
    )
    
    # TD rate (per reception)
    df['td_per_reception'] = np.where(
        df['receptions'] > 0,
        df['receiving_tds'] / df['receptions'] * 100,
        0
    )
    
    # YAC per reception
    if 'yards_after_catch' in df.columns:
        df['yac_per_reception'] = np.where(
            df['receptions'] > 0,
            df['yards_after_catch'] / df['receptions'],
            0
        )
    
    return df


def calculate_wr_per_game_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate WR per-game metrics.
    
    Args:
        df: DataFrame containing WR player data
        
    Returns:
        DataFrame with WR per-game metrics added
    """
    # Make a copy to avoid modifying the original dataframe
    df = df.copy()
    
    # Avoid division by zero
    games_played = df['games_played'].replace(0, 1)
    
    # Per-game receiving stats
    df['targets_per_game'] = df['targets'] / games_played
    df['receptions_per_game'] = df['receptions'] / games_played
    df['receiving_yards_per_game'] = df['receiving_yards'] / games_played
    df['receiving_tds_per_game'] = df['receiving_tds'] / games_played
    
    # YAC per game
    if 'yards_after_catch' in df.columns:
        df['yac_per_game'] = df['yards_after_catch'] / games_played
    
    # Per-game rushing stats (some WRs get rush attempts)
    if 'rushing_attempts' in df.columns:
        df['rushing_attempts_per_game'] = df['rushing_attempts'] / games_played
        df['rushing_yards_per_game'] = df['rushing_yards'] / games_played
        df['rushing_tds_per_game'] = df['rushing_tds'] / games_played
    
    return df


def calculate_wr_usage_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate WR usage metrics based on team totals.
    
    Args:
        df: DataFrame containing WR player data
        
    Returns:
        DataFrame with WR usage metrics added
    """
    # Make a copy to avoid modifying the original dataframe
    df = df.copy()
    
    # This function requires team totals to be calculated first
    # For now, we'll add placeholder columns that should be populated later
    
    # Target share
    df['target_share'] = 0.0
    
    # Reception share
    df['reception_share'] = 0.0
    
    # Air yards share
    if 'air_yards' in df.columns:
        df['air_yards_share'] = 0.0
    
    # Red zone target share
    df['red_zone_target_share'] = 0.0
    
    return df
