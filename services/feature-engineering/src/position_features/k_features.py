"""
Feature engineering for kicker (K) position.

This module contains functions for generating K-specific features from raw player data.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union


def engineer_k_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate K-specific features from player data.
    
    Args:
        df: DataFrame containing K player data
        
    Returns:
        DataFrame with K-specific features added
    """
    # Make a copy to avoid modifying the original dataframe
    df_k = df.copy()
    
    # Only keep Ks
    df_k = df_k[df_k['position'] == 'K']
    
    if df_k.empty:
        return df_k
    
    # Calculate efficiency metrics
    df_k = calculate_k_efficiency_metrics(df_k)
    
    # Calculate per-game averages
    df_k = calculate_k_per_game_metrics(df_k)
    
    return df_k


def calculate_k_efficiency_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate K efficiency metrics.
    
    Args:
        df: DataFrame containing K player data
        
    Returns:
        DataFrame with K efficiency metrics added
    """
    # Make a copy to avoid modifying the original dataframe
    df = df.copy()
    
    # Field goal percentage
    df['fg_percentage'] = np.where(
        df['fg_attempts'] > 0,
        df['fg_made'] / df['fg_attempts'] * 100,
        0
    )
    
    # Extra point percentage
    df['xp_percentage'] = np.where(
        df['xp_attempts'] > 0,
        df['xp_made'] / df['xp_attempts'] * 100,
        0
    )
    
    # Field goal percentage by distance (if available)
    for distance in ['0_19', '20_29', '30_39', '40_49', '50_plus']:
        attempts_col = f'fg_attempts_{distance}'
        made_col = f'fg_made_{distance}'
        
        if attempts_col in df.columns and made_col in df.columns:
            df[f'fg_percentage_{distance}'] = np.where(
                df[attempts_col] > 0,
                df[made_col] / df[attempts_col] * 100,
                0
            )
    
    return df


def calculate_k_per_game_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate K per-game metrics.
    
    Args:
        df: DataFrame containing K player data
        
    Returns:
        DataFrame with K per-game metrics added
    """
    # Make a copy to avoid modifying the original dataframe
    df = df.copy()
    
    # Avoid division by zero
    games_played = df['games_played'].replace(0, 1)
    
    # Per-game kicking stats
    df['fg_attempts_per_game'] = df['fg_attempts'] / games_played
    df['fg_made_per_game'] = df['fg_made'] / games_played
    df['xp_attempts_per_game'] = df['xp_attempts'] / games_played
    df['xp_made_per_game'] = df['xp_made'] / games_played
    
    # Field goal attempts by distance per game (if available)
    for distance in ['0_19', '20_29', '30_39', '40_49', '50_plus']:
        attempts_col = f'fg_attempts_{distance}'
        made_col = f'fg_made_{distance}'
        
        if attempts_col in df.columns and made_col in df.columns:
            df[f'{attempts_col}_per_game'] = df[attempts_col] / games_played
            df[f'{made_col}_per_game'] = df[made_col] / games_played
    
    # Total points per game
    df['points_per_game'] = (df['fg_made'] * 3 + df['xp_made']) / games_played
    
    return df
