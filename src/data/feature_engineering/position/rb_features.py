"""
Feature engineering for running back (RB) position.

This module contains functions for generating RB-specific features from raw player data,
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


def engineer_rb_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate RB-specific features from player data including industry-standard metrics.
    
    Args:
        df: DataFrame containing RB player data
        
    Returns:
        DataFrame with comprehensive RB-specific features added
    """
    # Make a copy to avoid modifying the original dataframe
    df_rb = df.copy()
    
    # Only keep RBs
    df_rb = df_rb[df_rb['position'] == 'RB']
    
    if df_rb.empty:
        return df_rb
    
    logger.info(f"Engineering features for {len(df_rb)} RB players")
    
    # Calculate basic efficiency metrics
    df_rb = calculate_rb_efficiency_metrics(df_rb)
    
    # Calculate per-game averages
    df_rb = calculate_rb_per_game_metrics(df_rb)
    
    # Calculate usage metrics (requires team totals)
    df_rb = calculate_rb_usage_metrics(df_rb)
    
    # Add industry-standard opportunity metrics
    df_rb = add_rb_opportunity_metrics(df_rb)
    
    # Add advanced usage analytics
    df_rb = add_rb_usage_analytics(df_rb)
    
    # Add RB-specific derived metrics
    df_rb = calculate_rb_advanced_metrics(df_rb)
    
    logger.info(f"Completed RB feature engineering with {len(df_rb.columns)} total features")
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
    # Use 'carries' column (nfl_data_py uses 'carries' not 'rushing_attempts')
    carry_col = 'carries' if 'carries' in df.columns else 'rushing_attempts'
    df['yards_per_carry'] = np.where(
        df[carry_col] > 0,
        df['rushing_yards'] / df[carry_col],
        0
    )
    
    # Yards per touch (rushing + receiving)
    df['yards_per_touch'] = np.where(
        (df[carry_col] + df['receptions']) > 0,
        (df['rushing_yards'] + df['receiving_yards']) / (df[carry_col] + df['receptions']),
        0
    )
    
    # Rushing TD rate
    df['rushing_td_rate'] = np.where(
        df[carry_col] > 0,
        df['rushing_tds'] / df[carry_col] * 100,
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
    
    # Use correct column name and avoid division by zero
    games_col = 'games' if 'games' in df.columns else 'games_played'
    if games_col not in df.columns:
        logger.warning("No games column found, using 16 as default")
        df[games_col] = 16
    
    games_played = df[games_col].replace(0, 1)
    
    # Per-game rushing stats
    carry_col = 'carries' if 'carries' in df.columns else 'rushing_attempts'
    df['rushing_attempts_per_game'] = df[carry_col] / games_played
    df['rushing_yards_per_game'] = df['rushing_yards'] / games_played
    df['rushing_tds_per_game'] = df['rushing_tds'] / games_played
    
    # Per-game receiving stats
    df['targets_per_game'] = df['targets'] / games_played
    df['receptions_per_game'] = df['receptions'] / games_played
    df['receiving_yards_per_game'] = df['receiving_yards'] / games_played
    df['receiving_tds_per_game'] = df['receiving_tds'] / games_played
    
    # Total touches per game
    df['touches_per_game'] = (df[carry_col] + df['receptions']) / games_played
    
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


def add_rb_opportunity_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add industry-standard opportunity metrics for RBs using our opportunity_metrics module.
    
    Args:
        df: DataFrame containing RB player data
        
    Returns:
        DataFrame with opportunity metrics added/enhanced
    """
    try:
        from src.features.opportunity_metrics import OpportunityMetricsCalculator
        
        logger.info("Adding opportunity metrics for RBs")
        
        # Use our opportunity metrics calculator to enhance existing data
        calculator = OpportunityMetricsCalculator()
        enhanced_df = calculator.enhance_opportunity_metrics(df)
        
        # Add RB-specific opportunity calculations
        enhanced_df = calculate_rb_specific_opportunity_metrics(enhanced_df)
        
        return enhanced_df
        
    except Exception as e:
        logger.warning(f"Could not add opportunity metrics: {e}")
        return df


def add_rb_usage_analytics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add advanced usage analytics for RBs using our usage_analytics module.
    
    Args:
        df: DataFrame containing RB player data
        
    Returns:
        DataFrame with usage analytics added
    """
    try:
        from src.features.usage_analytics import UsageAnalyticsCalculator
        
        logger.info("Adding usage analytics for RBs")
        
        # Use our usage analytics calculator
        calculator = UsageAnalyticsCalculator()
        enhanced_df = calculator.calculate_all_usage_metrics(df)
        
        return enhanced_df
        
    except Exception as e:
        logger.warning(f"Could not add usage analytics: {e}")
        return df


def calculate_rb_specific_opportunity_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate RB-specific opportunity metrics beyond the general ones.
    
    Args:
        df: DataFrame with RB data and basic opportunity metrics
        
    Returns:
        DataFrame with RB-specific opportunity metrics added
    """
    result = df.copy()
    
    # Ensure we have the correct carry column name
    carry_col = 'carries' if 'carries' in result.columns else 'rushing_attempts'
    
    # Goal line carry rate (carries inside 5-yard line)
    if 'red_zone_carries' in result.columns:
        # Approximate goal line carries as subset of red zone carries
        result['goal_line_carries'] = result['red_zone_carries'] * 0.4  # Rough approximation
        result['goal_line_carry_rate'] = np.where(
            result[carry_col] > 0,
            result['goal_line_carries'] / result[carry_col],
            0
        )
    
    # Early down vs passing down usage
    carry_col = 'carries' if 'carries' in result.columns else 'rushing_attempts'
    if carry_col in result.columns and 'targets' in result.columns:
        total_opportunities = result[carry_col] + result['targets']
        result['early_down_rate'] = np.where(
            total_opportunities > 0,
            result[carry_col] / total_opportunities,
            0
        )
        result['passing_down_rate'] = 1 - result['early_down_rate']
    
    # Touch efficiency (fantasy points per touch)
    if all(col in result.columns for col in ['fantasy_points_ppr', carry_col, 'receptions']):
        total_touches = result[carry_col] + result['receptions']
        result['fantasy_points_per_touch'] = np.where(
            total_touches > 0,
            result['fantasy_points_ppr'] / total_touches,
            0
        )
    
    # Workhorse indicator (high-volume usage)
    carry_col = 'carries' if 'carries' in result.columns else 'rushing_attempts'
    if carry_col in result.columns and 'games' in result.columns:
        carries_per_game = result[carry_col] / result['games'].replace(0, 1)
        result['workhorse_indicator'] = (carries_per_game >= 15).astype(int)
    
    # Pass-catching back indicator
    if 'targets' in result.columns and 'games' in result.columns:
        targets_per_game = result['targets'] / result['games'].replace(0, 1)
        result['pass_catching_back'] = (targets_per_game >= 3).astype(int)
    
    # Short yardage specialist (high goal line + short adot)
    if 'goal_line_carries' in result.columns and 'adot' in result.columns:
        result['short_yardage_specialist'] = (
            (result['goal_line_carries'] >= 3) & (result['adot'] <= 2)
        ).astype(int)
    
    # Receiving versatility (ability to line up wide/slot)
    if 'adot' in result.columns and 'targets' in result.columns:
        # RBs with higher aDOT likely line up as receivers sometimes
        result['receiving_versatility'] = np.where(
            result['adot'] > 3,
            'High',  # Lines up as receiver
            np.where(result['adot'] > 1, 'Medium', 'Low')  # Mostly checkdowns
        )
    
    # Snap share utilization (touches per snap)
    if all(col in result.columns for col in [carry_col, 'targets', 'total_snaps']):
        total_touches = result[carry_col] + result['targets']
        result['snap_utilization_rate'] = np.where(
            result['total_snaps'] > 0,
            total_touches / result['total_snaps'],
            0
        )
    
    return result


def calculate_rb_advanced_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate advanced RB metrics that combine multiple data sources.
    
    Args:
        df: DataFrame with RB data and all previous metrics
        
    Returns:
        DataFrame with advanced RB metrics added
    """
    result = df.copy()
    
    # RB role classification (Workhorse vs Passing Down vs Change of Pace vs Goal Line)
    carry_col = 'carries' if 'carries' in result.columns else 'rushing_attempts'
    if all(col in result.columns for col in [carry_col, 'targets', 'games']):
        carries_per_game = result[carry_col] / result['games'].replace(0, 1)
        targets_per_game = result['targets'] / result['games'].replace(0, 1)
        
        result['rb_role'] = np.where(
            carries_per_game >= 15,
            'Workhorse',
            np.where(
                targets_per_game >= 4,
                'Passing_Down',
                np.where(
                    result.get('goal_line_carries', 0) >= 3,
                    'Goal_Line',
                    'Change_of_Pace'
                )
            )
        )
    
    # Touch efficiency score (combining yards per touch and TD rate)
    if all(col in result.columns for col in ['yards_per_touch', 'total_tds_per_game']):
        # Normalize both metrics then combine
        ypt_norm = np.clip(result['yards_per_touch'] / 8, 0, 1)  # Cap at 8 yards per touch
        td_norm = np.clip(result['total_tds_per_game'], 0, 1)  # Cap at 1 TD per game
        
        result['touch_efficiency_score'] = (ypt_norm * 0.7) + (td_norm * 0.3)
    
    # Fantasy upside score (combines volume and efficiency)
    if all(col in result.columns for col in ['touches_per_game', 'touch_efficiency_score']):
        # Normalize touches per game
        touches_norm = np.clip(result['touches_per_game'] / 25, 0, 1)  # Cap at 25 touches
        
        result['fantasy_upside_score'] = (
            touches_norm * 0.6 +  # Volume is most important for RBs
            result['touch_efficiency_score'] * 0.4
        )
    
    # Red zone value tier (critical for RB TDs)
    if 'red_zone_opportunities' in result.columns:
        result['red_zone_value_tier'] = np.where(
            result['red_zone_opportunities'] >= 12,
            'Elite',
            np.where(
                result['red_zone_opportunities'] >= 6,
                'High',
                np.where(result['red_zone_opportunities'] >= 3, 'Medium', 'Low')
            )
        )
    
    # Snap share tier (different thresholds for RBs)
    if 'avg_snap_share' in result.columns:
        result['snap_share_tier'] = np.where(
            result['avg_snap_share'] >= 0.7,
            'Elite',
            np.where(
                result['avg_snap_share'] >= 0.5,
                'High',
                np.where(result['avg_snap_share'] >= 0.3, 'Medium', 'Low')
            )
        )
    
    # Injury risk tier (based on touches and snap share)
    if all(col in result.columns for col in ['touches_per_game', 'snap_share_tier']):
        result['injury_risk_tier'] = np.where(
            (result['touches_per_game'] >= 20) & (result['snap_share_tier'].isin(['Elite', 'High'])),
            'High',
            np.where(
                result['touches_per_game'] >= 15,
                'Medium',
                'Low'
            )
        )
    
    # Usage sustainability (can this workload be maintained?)
    if all(col in result.columns for col in ['touches_per_game', 'avg_snap_share']):
        # High touches + high snaps = potential concern
        sustainability_score = (
            (1 - np.clip(result['touches_per_game'] / 25, 0, 1)) * 0.6 +
            (1 - result['avg_snap_share']) * 0.4
        )
        
        result['usage_sustainability'] = np.where(
            sustainability_score >= 0.7,
            'Sustainable',
            np.where(sustainability_score >= 0.4, 'Moderate_Risk', 'High_Risk')
        )
    
    # Age-adjusted projection factor (RBs decline faster)
    if 'age' in result.columns:
        result['rb_age_factor'] = np.where(
            result['age'] <= 26,
            1.0,  # Prime years
            np.where(
                result['age'] <= 29,
                0.9,  # Slight decline
                0.7   # Significant decline expected
            )
        )
    
    # Opportunity ceiling (max theoretical touches)
    if all(col in result.columns for col in ['avg_snap_share', 'rb_role']):
        # Different ceilings based on role
        role_multiplier = np.where(
            result['rb_role'] == 'Workhorse', 1.2,
            np.where(result['rb_role'] == 'Passing_Down', 0.8, 0.6)
        )
        result['opportunity_ceiling'] = result['avg_snap_share'] * role_multiplier * 25  # Max ~25 touches
        result['opportunity_ceiling'] = np.clip(result['opportunity_ceiling'], 0, 30)
    
    return result
