"""
Feature engineering for tight end (TE) position.

This module contains functions for generating TE-specific features from raw player data,
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


def engineer_te_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate TE-specific features from player data including industry-standard metrics.
    
    Args:
        df: DataFrame containing TE player data
        
    Returns:
        DataFrame with comprehensive TE-specific features added
    """
    # Make a copy to avoid modifying the original dataframe
    df_te = df.copy()
    
    # Only keep TEs
    df_te = df_te[df_te['position'] == 'TE']
    
    if df_te.empty:
        return df_te
    
    logger.info(f"Engineering features for {len(df_te)} TE players")
    
    # Calculate basic efficiency metrics
    df_te = calculate_te_efficiency_metrics(df_te)
    
    # Calculate per-game averages
    df_te = calculate_te_per_game_metrics(df_te)
    
    # Calculate usage metrics (requires team totals)
    df_te = calculate_te_usage_metrics(df_te)
    
    # Add industry-standard opportunity metrics
    df_te = add_te_opportunity_metrics(df_te)
    
    # Add advanced usage analytics
    df_te = add_te_usage_analytics(df_te)
    
    # Add TE-specific derived metrics
    df_te = calculate_te_advanced_metrics(df_te)
    
    logger.info(f"Completed TE feature engineering with {len(df_te.columns)} total features")
    return df_te


def calculate_te_efficiency_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate TE efficiency metrics.
    
    Args:
        df: DataFrame containing TE player data
        
    Returns:
        DataFrame with TE efficiency metrics added
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


def calculate_te_per_game_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate TE per-game metrics.
    
    Args:
        df: DataFrame containing TE player data
        
    Returns:
        DataFrame with TE per-game metrics added
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
    
    return df


def calculate_te_usage_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate TE usage metrics based on team totals.
    
    Args:
        df: DataFrame containing TE player data
        
    Returns:
        DataFrame with TE usage metrics added
    """
    # Make a copy to avoid modifying the original dataframe
    df = df.copy()
    
    # This function requires team totals to be calculated first
    # For now, we'll add placeholder columns that should be populated later
    
    # Target share
    df['target_share'] = 0.0
    
    # Reception share
    df['reception_share'] = 0.0
    
    # Red zone target share
    df['red_zone_target_share'] = 0.0
    
    return df


def add_te_opportunity_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add industry-standard opportunity metrics for TEs using our opportunity_metrics module.
    
    Args:
        df: DataFrame containing TE player data
        
    Returns:
        DataFrame with opportunity metrics added/enhanced
    """
    try:
        from src.features.opportunity_metrics import OpportunityMetricsCalculator
        
        logger.info("Adding opportunity metrics for TEs")
        
        # Use our opportunity metrics calculator to enhance existing data
        calculator = OpportunityMetricsCalculator()
        enhanced_df = calculator.enhance_opportunity_metrics(df)
        
        # Add TE-specific opportunity calculations
        enhanced_df = calculate_te_specific_opportunity_metrics(enhanced_df)
        
        return enhanced_df
        
    except Exception as e:
        logger.warning(f"Could not add opportunity metrics: {e}")
        return df


def add_te_usage_analytics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add advanced usage analytics for TEs using our usage_analytics module.
    
    Args:
        df: DataFrame containing TE player data
        
    Returns:
        DataFrame with usage analytics added
    """
    try:
        from src.features.usage_analytics import UsageAnalyticsCalculator
        
        logger.info("Adding usage analytics for TEs")
        
        # Use our usage analytics calculator
        calculator = UsageAnalyticsCalculator()
        enhanced_df = calculator.calculate_all_usage_metrics(df)
        
        return enhanced_df
        
    except Exception as e:
        logger.warning(f"Could not add usage analytics: {e}")
        return df


def calculate_te_specific_opportunity_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate TE-specific opportunity metrics beyond the general ones.
    
    Args:
        df: DataFrame with TE data and basic opportunity metrics
        
    Returns:
        DataFrame with TE-specific opportunity metrics added
    """
    result = df.copy()
    
    # TE seam route indicator (targets at intermediate depths)
    if 'adot' in result.columns:
        result['seam_route_indicator'] = ((result['adot'] >= 8) & (result['adot'] <= 18)).astype(int)
        result['seam_route_rate'] = result['seam_route_indicator']  # Simplified calculation
    
    # Short/intermediate/deep target splits optimized for TEs
    if 'receiving_air_yards' in result.columns and 'targets' in result.columns:
        # TEs typically work more in short-intermediate range
        result['short_target_rate'] = np.where(
            result['adot'] <= 6,
            0.7,  # High short rate for low aDOT TEs
            np.where(result['adot'] <= 12, 0.4, 0.2)  # Medium/low for higher aDOT
        )
        
        result['intermediate_target_rate'] = np.where(
            (result['adot'] > 6) & (result['adot'] <= 16),
            0.6,  # High intermediate rate for TEs
            0.3   # Otherwise moderate
        )
        
        result['deep_target_rate'] = 1 - result['short_target_rate'] - result['intermediate_target_rate']
        result['deep_target_rate'] = np.clip(result['deep_target_rate'], 0, 1)
    
    # In-line vs slot usage approximation (based on target patterns)
    if 'target_share' in result.columns and 'red_zone_opportunities' in result.columns:
        # TEs with high red zone usage likely play more in-line
        result['inline_usage_estimate'] = np.where(
            result['red_zone_opportunities'] >= 5,
            0.8,  # High in-line usage
            np.where(result['target_share'] >= 0.15, 0.4, 0.6)  # Slot vs in-line based on targets
        )
        
        result['slot_usage_estimate'] = 1 - result['inline_usage_estimate']
    
    # Blocking snap approximation (TEs who block more get fewer targets per snap)
    if 'targets_per_snap' in result.columns and 'avg_snap_share' in result.columns:
        # Lower targets per snap suggests more blocking
        result['blocking_snap_estimate'] = np.where(
            result['targets_per_snap'] < 0.1,
            0.6,  # High blocking estimate
            np.where(result['targets_per_snap'] < 0.15, 0.3, 0.1)  # Medium/low
        )
    
    # TE-specific contested catch rate (TEs face different coverage)
    if 'adot' in result.columns and 'yac_per_target' in result.columns:
        # TEs often have intermediate contested catches
        result['contested_catch_rate'] = np.where(
            (result['adot'] > 8) & (result['adot'] <= 16) & (result['yac_per_target'] < 4),
            0.25,  # Medium-high contested rate for seam routes
            np.where(result['adot'] > 16, 0.35, 0.1)  # Higher for deep, lower for short
        )
    
    return result


def calculate_te_advanced_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate advanced TE metrics that combine multiple data sources.
    
    Args:
        df: DataFrame with TE data and all previous metrics
        
    Returns:
        DataFrame with advanced TE metrics added
    """
    result = df.copy()
    
    # TE role classification (Receiving vs Blocking vs Hybrid)
    if all(col in result.columns for col in ['target_share', 'avg_snap_share']):
        result['te_role'] = np.where(
            (result['target_share'] >= 0.15) & (result['avg_snap_share'] >= 0.6),
            'Receiving',
            np.where(
                (result['target_share'] <= 0.08) & (result['avg_snap_share'] >= 0.5),
                'Blocking',
                'Hybrid'
            )
        )
    
    # Target efficiency score (combining catch rate and yards per target)
    if all(col in result.columns for col in ['catch_rate', 'yards_per_target']):
        # Normalize both metrics to 0-1 scale then combine
        catch_rate_norm = result['catch_rate'] / 100  # Convert percentage to decimal
        ypr_norm = np.clip(result['yards_per_target'] / 15, 0, 1)  # Cap at 15 yards (lower than WR)
        
        result['target_efficiency_score'] = (catch_rate_norm * 0.7) + (ypr_norm * 0.3)  # Favor reliability for TEs
    
    # Fantasy relevance score (different weighting than WRs)
    if all(col in result.columns for col in ['target_share', 'target_efficiency_score']):
        result['fantasy_relevance_score'] = (
            result['target_share'] * 0.6 +  # Volume still important but less than WRs
            result['target_efficiency_score'] * 0.4  # Efficiency more important for TEs
        )
    
    # Red zone value tier (TEs are crucial in red zone)
    if 'red_zone_opportunities' in result.columns:
        result['red_zone_value_tier'] = np.where(
            result['red_zone_opportunities'] >= 8,
            'Elite',  # High red zone usage is valuable
            np.where(
                result['red_zone_opportunities'] >= 4,
                'High',
                np.where(result['red_zone_opportunities'] >= 2, 'Medium', 'Low')
            )
        )
    
    # Snap utilization tier (different thresholds than WRs)
    if 'avg_snap_share' in result.columns:
        result['snap_utilization_tier'] = np.where(
            result['avg_snap_share'] >= 0.75,
            'Elite',
            np.where(
                result['avg_snap_share'] >= 0.55,
                'High',
                np.where(result['avg_snap_share'] >= 0.35, 'Medium', 'Low')
            )
        )
    
    # Versatility score (combination of receiving and potential blocking)
    if all(col in result.columns for col in ['target_share', 'blocking_snap_estimate']):
        # High versatility = decent receiving + significant blocking
        result['versatility_score'] = (
            np.clip(result['target_share'] * 2, 0, 1) * 0.4 +  # Receiving contribution
            result.get('blocking_snap_estimate', 0) * 0.6  # Blocking contribution
        )
    
    # Usage ceiling (max theoretical targets based on role and snaps)
    if all(col in result.columns for col in ['avg_snap_share', 'te_role']):
        # Different ceilings based on role
        role_multiplier = np.where(
            result['te_role'] == 'Receiving', 1.3,
            np.where(result['te_role'] == 'Hybrid', 0.8, 0.4)
        )
        result['usage_ceiling'] = result['avg_snap_share'] * role_multiplier * 0.25  # TE target rate ceiling
        result['usage_ceiling'] = np.clip(result['usage_ceiling'], 0, 0.3)  # Cap at 30% team targets
    
    return result
