"""
Feature engineering for running back (RB) position.

This module contains functions for generating RB-specific features from raw player data.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union


def engineer_rb_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate RB-specific features from player data.
    
    Args:
        df: DataFrame containing RB player data
        
    Returns:
        DataFrame with RB-specific features added
    """
    # Make a copy to avoid modifying the original dataframe
    df_rb = df.copy()
    
    # Only keep RBs
    df_rb = df_rb[df_rb['position'] == 'RB']
    
    if df_rb.empty:
        return df_rb
    
    # Calculate efficiency metrics
    df_rb = calculate_rb_efficiency_metrics(df_rb)
    
    # Calculate per-game averages
    df_rb = calculate_rb_per_game_metrics(df_rb)
    
    # Calculate usage metrics (requires team totals)
    df_rb = calculate_rb_usage_metrics(df_rb)
    
    return df_rb


def calculate_rb_efficiency_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate RB efficiency metrics.
    
    Args:
        df: DataFrame containing RB player data
        
    Returns:
        DataFrame with RB efficiency metrics added
    """
    # Make a copy to avoid modifying the original dataframe
    df = df.copy()
    
    # Yards per carry
    df['yards_per_carry'] = np.where(
        df['rushing_attempts'] > 0,
        df['rushing_yards'] / df['rushing_attempts'],
        0
    )
    
    # Yards per touch (rushing + receiving)
    df['yards_per_touch'] = np.where(
        (df['rushing_attempts'] + df['receptions']) > 0,
        (df['rushing_yards'] + df['receiving_yards']) / (df['rushing_attempts'] + df['receptions']),
        0
    )
    
    # Rushing TD rate
    df['rushing_td_rate'] = np.where(
        df['rushing_attempts'] > 0,
        df['rushing_tds'] / df['rushing_attempts'] * 100,
        0
    )
    
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
    
    # Receiving TD rate
    df['receiving_td_rate'] = np.where(
        df['targets'] > 0,
        df['receiving_tds'] / df['targets'] * 100,
        0
    )
    
    return df


def calculate_rb_per_game_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate RB per-game metrics.
    
    Args:
        df: DataFrame containing RB player data
        
    Returns:
        DataFrame with RB per-game metrics added
    """
    # Make a copy to avoid modifying the original dataframe
    df = df.copy()
    
    # Avoid division by zero
    games_played = df['games_played'].replace(0, 1)
    
    # Per-game rushing stats
    df['rushing_attempts_per_game'] = df['rushing_attempts'] / games_played
    df['rushing_yards_per_game'] = df['rushing_yards'] / games_played
    df['rushing_tds_per_game'] = df['rushing_tds'] / games_played
    
    # Per-game receiving stats
    df['targets_per_game'] = df['targets'] / games_played
    df['receptions_per_game'] = df['receptions'] / games_played
    df['receiving_yards_per_game'] = df['receiving_yards'] / games_played
    df['receiving_tds_per_game'] = df['receiving_tds'] / games_played
    
    # Total touches per game
    df['touches_per_game'] = (df['rushing_attempts'] + df['receptions']) / games_played
    
    # Total yards per game
    df['total_yards_per_game'] = (df['rushing_yards'] + df['receiving_yards']) / games_played
    
    # Total TDs per game
    df['total_tds_per_game'] = (df['rushing_tds'] + df['receiving_tds']) / games_played
    
    return df


def calculate_rb_usage_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate RB usage metrics based on team totals.
    
    Args:
        df: DataFrame containing RB player data
        
    Returns:
        DataFrame with RB usage metrics added
    """
    # Make a copy to avoid modifying the original dataframe
    df = df.copy()
    
    # This function requires team totals to be calculated first
    # For now, we'll add placeholder columns that should be populated later
    
    # Team rush attempt share
    df['team_rush_attempt_share'] = 0.0
    
    # Team target share
    df['team_target_share'] = 0.0
    
    # Team touch share (rush attempts + receptions)
    df['team_touch_share'] = 0.0
    
    # Red zone opportunity share
    df['red_zone_opportunity_share'] = 0.0
    
    return df
