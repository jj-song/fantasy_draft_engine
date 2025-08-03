"""
Feature engineering for defense/special teams (DST) position.

This module contains functions for generating DST-specific features from raw team data.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union


def engineer_dst_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate DST-specific features from team data.
    
    Args:
        df: DataFrame containing DST team data
        
    Returns:
        DataFrame with DST-specific features added
    """
    # Make a copy to avoid modifying the original dataframe
    df_dst = df.copy()
    
    # Only keep DSTs
    df_dst = df_dst[df_dst['position'] == 'DST']
    
    if df_dst.empty:
        return df_dst
    
    # Calculate efficiency metrics
    df_dst = calculate_dst_efficiency_metrics(df_dst)
    
    # Calculate per-game averages
    df_dst = calculate_dst_per_game_metrics(df_dst)
    
    return df_dst


def calculate_dst_efficiency_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate DST efficiency metrics.
    
    Args:
        df: DataFrame containing DST team data
        
    Returns:
        DataFrame with DST efficiency metrics added
    """
    # Make a copy to avoid modifying the original dataframe
    df = df.copy()
    
    # Turnover rate (per opponent play)
    if 'opponent_plays' in df.columns and 'turnovers_forced' in df.columns:
        df['turnover_rate'] = np.where(
            df['opponent_plays'] > 0,
            df['turnovers_forced'] / df['opponent_plays'] * 100,
            0
        )
    
    # Sack rate (per opponent pass attempt)
    if 'opponent_pass_attempts' in df.columns and 'sacks' in df.columns:
        df['sack_rate'] = np.where(
            df['opponent_pass_attempts'] > 0,
            df['sacks'] / df['opponent_pass_attempts'] * 100,
            0
        )
    
    # Points allowed per opponent play
    if 'opponent_plays' in df.columns and 'points_allowed' in df.columns:
        df['points_per_play_allowed'] = np.where(
            df['opponent_plays'] > 0,
            df['points_allowed'] / df['opponent_plays'],
            0
        )
    
    # Yards allowed per opponent play
    if 'opponent_plays' in df.columns and 'yards_allowed' in df.columns:
        df['yards_per_play_allowed'] = np.where(
            df['opponent_plays'] > 0,
            df['yards_allowed'] / df['opponent_plays'],
            0
        )
    
    return df


def calculate_dst_per_game_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate DST per-game metrics.
    
    Args:
        df: DataFrame containing DST team data
        
    Returns:
        DataFrame with DST per-game metrics added
    """
    # Make a copy to avoid modifying the original dataframe
    df = df.copy()
    
    # Avoid division by zero
    games_played = df['games_played'].replace(0, 1)
    
    # Per-game defensive stats
    if 'sacks' in df.columns:
        df['sacks_per_game'] = df['sacks'] / games_played
    
    if 'interceptions' in df.columns:
        df['interceptions_per_game'] = df['interceptions'] / games_played
    
    if 'fumbles_recovered' in df.columns:
        df['fumbles_recovered_per_game'] = df['fumbles_recovered'] / games_played
    
    if 'defensive_tds' in df.columns:
        df['defensive_tds_per_game'] = df['defensive_tds'] / games_played
    
    if 'special_teams_tds' in df.columns:
        df['special_teams_tds_per_game'] = df['special_teams_tds'] / games_played
    
    if 'safeties' in df.columns:
        df['safeties_per_game'] = df['safeties'] / games_played
    
    # Total turnovers forced per game
    if 'interceptions' in df.columns and 'fumbles_recovered' in df.columns:
        df['turnovers_forced_per_game'] = (df['interceptions'] + df['fumbles_recovered']) / games_played
    
    # Points allowed per game
    if 'points_allowed' in df.columns:
        df['points_allowed_per_game'] = df['points_allowed'] / games_played
    
    # Yards allowed per game
    if 'yards_allowed' in df.columns:
        df['yards_allowed_per_game'] = df['yards_allowed'] / games_played
    
    return df
