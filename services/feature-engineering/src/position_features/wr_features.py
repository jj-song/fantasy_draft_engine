"""
Feature engineering for wide receiver (WR) position.

This module contains functions for generating WR-specific features from raw player data,
including industry-standard opportunity and usage metrics.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union
import logging
from pathlib import Path
import sys

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

logger = logging.getLogger(__name__)


def engineer_wr_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate WR-specific features from player data including industry-standard metrics.
    
    Args:
        df: DataFrame containing WR player data
        
    Returns:
        DataFrame with comprehensive WR-specific features added
    """
    # Make a copy to avoid modifying the original dataframe
    df_wr = df.copy()
    
    # Only keep WRs
    df_wr = df_wr[df_wr['position'] == 'WR']
    
    if df_wr.empty:
        return df_wr
    
    logger.info(f"Engineering features for {len(df_wr)} WR players")
    
    # Calculate basic efficiency metrics
    df_wr = calculate_wr_efficiency_metrics(df_wr)
    
    # Calculate per-game averages
    df_wr = calculate_wr_per_game_metrics(df_wr)
    
    # Calculate usage metrics (requires team totals)
    df_wr = calculate_wr_usage_metrics(df_wr)
    
    # Add industry-standard opportunity metrics
    df_wr = add_wr_opportunity_metrics(df_wr)
    
    # Add advanced usage analytics
    df_wr = add_wr_usage_analytics(df_wr)
    
    # Add WR-specific derived metrics
    df_wr = calculate_wr_advanced_metrics(df_wr)
    
    logger.info(f"Completed WR feature engineering with {len(df_wr.columns)} total features")
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
    
    # Use correct column name and avoid division by zero
    games_col = 'games' if 'games' in df.columns else 'games_played'
    if games_col not in df.columns:
        logger.warning("No games column found, using 16 as default")
        df[games_col] = 16
    
    games_played = df[games_col].replace(0, 1)
    
    # Per-game receiving stats
    df['targets_per_game'] = df['targets'] / games_played
    df['receptions_per_game'] = df['receptions'] / games_played
    df['receiving_yards_per_game'] = df['receiving_yards'] / games_played
    df['receiving_tds_per_game'] = df['receiving_tds'] / games_played
    
    # YAC per game
    if 'yards_after_catch' in df.columns:
        df['yac_per_game'] = df['yards_after_catch'] / games_played
    elif 'receiving_yards_after_catch' in df.columns:
        df['yac_per_game'] = df['receiving_yards_after_catch'] / games_played
    
    # Per-game rushing stats (some WRs get rush attempts)
    if 'rushing_attempts' in df.columns:
        df['rushing_attempts_per_game'] = df['rushing_attempts'] / games_played
        df['rushing_yards_per_game'] = df['rushing_yards'] / games_played
        df['rushing_tds_per_game'] = df['rushing_tds'] / games_played
    elif 'carries' in df.columns:
        df['rushing_attempts_per_game'] = df['carries'] / games_played
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


def add_wr_opportunity_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add industry-standard opportunity metrics for WRs using our opportunity_metrics module.
    
    Args:
        df: DataFrame containing WR player data
        
    Returns:
        DataFrame with opportunity metrics added/enhanced
    """
    try:
        from src.features.opportunity_metrics import OpportunityMetricsCalculator
        
        logger.info("Adding opportunity metrics for WRs")
        
        # Use our opportunity metrics calculator to enhance existing data
        calculator = OpportunityMetricsCalculator()
        enhanced_df = calculator.enhance_opportunity_metrics(df)
        
        # Add WR-specific opportunity calculations
        enhanced_df = calculate_wr_specific_opportunity_metrics(enhanced_df)
        
        return enhanced_df
        
    except Exception as e:
        logger.warning(f"Could not add opportunity metrics: {e}")
        return df


def add_wr_usage_analytics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add advanced usage analytics for WRs using our usage_analytics module.
    
    Args:
        df: DataFrame containing WR player data
        
    Returns:
        DataFrame with usage analytics added
    """
    try:
        from src.features.usage_analytics import UsageAnalyticsCalculator
        
        logger.info("Adding usage analytics for WRs")
        
        # Use our usage analytics calculator
        calculator = UsageAnalyticsCalculator()
        enhanced_df = calculator.calculate_all_usage_metrics(df)
        
        return enhanced_df
        
    except Exception as e:
        logger.warning(f"Could not add usage analytics: {e}")
        return df


def calculate_wr_specific_opportunity_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate WR-specific opportunity metrics beyond the general ones.
    
    Args:
        df: DataFrame with WR data and basic opportunity metrics
        
    Returns:
        DataFrame with WR-specific opportunity metrics added
    """
    result = df.copy()
    
    # Deep target rate (targets 15+ yards downfield)
    if 'adot' in result.columns:
        result['deep_target_indicator'] = (result['adot'] >= 15).astype(int)
        result['deep_target_rate'] = result['deep_target_indicator']  # This is simplified
    
    # Short/intermediate/deep target splits (if we have detailed air yards data)
    if 'receiving_air_yards' in result.columns and 'targets' in result.columns:
        # Approximate target splits based on average depth
        result['short_target_rate'] = np.where(
            result['adot'] <= 8,
            0.6,  # High short rate for low aDOT
            np.where(result['adot'] <= 15, 0.3, 0.1)  # Medium/low for higher aDOT
        )
        
        result['intermediate_target_rate'] = np.where(
            (result['adot'] > 8) & (result['adot'] <= 15),
            0.5,  # High intermediate rate for medium aDOT
            0.3   # Otherwise moderate
        )
        
        result['deep_target_rate'] = 1 - result['short_target_rate'] - result['intermediate_target_rate']
        result['deep_target_rate'] = np.clip(result['deep_target_rate'], 0, 1)
    
    # Target density (targets per route run - approximated)
    if 'route_participation_advanced' in result.columns and 'targets' in result.columns:
        result['target_density'] = np.where(
            result['route_participation_advanced'] > 0,
            result['targets'] / (result['route_participation_advanced'] * result.get('games', 16)),
            0
        )
    
    # Contested catch opportunity rate (approximated based on air yards and YAC)
    if 'adot' in result.columns and 'yac_per_target' in result.columns:
        # Higher aDOT with lower YAC suggests more contested catches
        result['contested_catch_rate'] = np.where(
            (result['adot'] > 10) & (result['yac_per_target'] < 3),
            0.3,  # High contested rate
            np.where(result['adot'] > 5, 0.15, 0.05)  # Medium/low
        )
    
    return result


def calculate_wr_advanced_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate advanced WR metrics that combine multiple data sources.
    
    Args:
        df: DataFrame with WR data and all previous metrics
        
    Returns:
        DataFrame with advanced WR metrics added
    """
    result = df.copy()
    
    # Air yards dominance (how much of team's air yards this WR commands)
    if 'air_yards_share' in result.columns:
        result['air_yards_dominance'] = np.where(
            result['air_yards_share'] >= 0.25,
            'High',
            np.where(result['air_yards_share'] >= 0.15, 'Medium', 'Low')
        )
    
    # Target efficiency score (combining catch rate and yards per target)
    if all(col in result.columns for col in ['catch_rate', 'yards_per_target']):
        # Normalize both metrics to 0-1 scale then combine
        catch_rate_norm = result['catch_rate'] / 100  # Convert percentage to decimal
        ypr_norm = np.clip(result['yards_per_target'] / 20, 0, 1)  # Cap at 20 yards
        
        result['target_efficiency_score'] = (catch_rate_norm * 0.6) + (ypr_norm * 0.4)
    
    # Fantasy relevance score (combines volume and efficiency)
    if all(col in result.columns for col in ['target_share', 'target_efficiency_score']):
        result['fantasy_relevance_score'] = (
            result['target_share'] * 0.7 +  # Volume is most important
            result['target_efficiency_score'] * 0.3
        )
    
    # Red zone threat level
    if 'red_zone_opportunities' in result.columns:
        result['red_zone_threat_level'] = np.where(
            result['red_zone_opportunities'] >= 10,
            'High',
            np.where(result['red_zone_opportunities'] >= 5, 'Medium', 'Low')
        )
    
    # Snap rate tier
    if 'avg_snap_share' in result.columns:
        result['snap_rate_tier'] = np.where(
            result['avg_snap_share'] >= 0.8,
            'Elite',
            np.where(
                result['avg_snap_share'] >= 0.6,
                'High',
                np.where(result['avg_snap_share'] >= 0.4, 'Medium', 'Low')
            )
        )
    
    # Usage ceiling (max theoretical targets based on snap rate and team pass attempts)
    if all(col in result.columns for col in ['avg_snap_share', 'team_target_market_share']):
        # This is an approximation of upside potential
        result['usage_ceiling'] = result['avg_snap_share'] * result['team_target_market_share'] * 1.2
        result['usage_ceiling'] = np.clip(result['usage_ceiling'], 0, 1)
    
    return result
